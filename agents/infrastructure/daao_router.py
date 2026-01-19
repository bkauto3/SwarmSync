"""
DAAO (Difficulty-Aware Agentic Orchestration) Router
Based on: arXiv 2509.11079 (September 2025)

Key Innovation: Route tasks to appropriate model based on difficulty
- Easy tasks → Gemini Flash ($0.03/1M tokens)
- Hard tasks → GPT-4o ($3/1M tokens)

Expected Impact: 64% cost at +11% accuracy (36% cost reduction)
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Setup logging
logger = logging.getLogger(__name__)

# Unsloth imports for adapter loading
try:
    from unsloth import FastLanguageModel
    HAS_UNSLOTH = True
except (ImportError, NotImplementedError, RuntimeError) as e:
    FastLanguageModel = None
    HAS_UNSLOTH = False
    logger.debug(f"Unsloth not available - fine-tuned adapter loading disabled (expected in Railway: {type(e).__name__})")

# Import Context Linter for validation
try:
    from infrastructure.context_linter import get_context_linter, ContextLinter, Message
    CONTEXT_LINTER_AVAILABLE = True
except ImportError:
    get_context_linter = None
    ContextLinter = None
    Message = None
    CONTEXT_LINTER_AVAILABLE = False
    logger.warning("Context Linter not available - context validation disabled")


class TaskDifficulty(Enum):
    """Task difficulty levels"""
    TRIVIAL = "trivial"  # <0.2: Very simple tasks
    EASY = "easy"        # 0.2-0.4: Simple tasks
    MEDIUM = "medium"    # 0.4-0.6: Moderate tasks
    HARD = "hard"        # 0.6-0.8: Complex tasks
    EXPERT = "expert"    # >0.8: Very complex tasks


class ModelTier(Enum):
    """Model cost tiers (ordered by cost: cheapest first)"""
    FREE = "local-llm"                    # $0.00/1M tokens (Qwen 7B local)
    ULTRA_CHEAP = "gemini-2.5-flash"      # $0.03/1M tokens
    CHEAP = "gemini-2.0-flash-lite"       # $0.10/1M tokens
    STANDARD = "claude-3.7-sonnet"        # $1.50/1M tokens
    PREMIUM = "gpt-4o"                    # $3.00/1M tokens
    ULTRA_PREMIUM = "claude-4-sonnet"     # $5.00/1M tokens


@dataclass
class TaskMetrics:
    """Metrics for difficulty estimation"""
    description_length: int
    num_steps: int
    num_tools_required: int
    priority: float
    complexity_keywords: int
    technical_depth: int


@dataclass
class RoutingDecision:
    """Routing decision with reasoning"""
    model: str
    difficulty: TaskDifficulty
    estimated_cost: float
    confidence: float
    reasoning: str


class DAAORouter:
    """
    Difficulty-Aware Agentic Orchestration Router

    Routes tasks to cost-appropriate models based on difficulty estimation.
    Based on research: arXiv 2509.11079

    Expected Results:
    - 64% of baseline cost
    - +11.21% accuracy improvement
    - Optimal model selection per task
    """

    # Difficulty estimation parameters
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_STEPS_CONSIDERED = 10
    MAX_TOOLS_CONSIDERED = 5
    MAX_COMPLEXITY_KEYWORDS = 5
    MAX_TECHNICAL_KEYWORDS = 5

    # Difficulty weights (must sum to 1.0)
    WEIGHT_LENGTH = 0.15
    WEIGHT_STEPS = 0.20
    WEIGHT_TOOLS = 0.20
    WEIGHT_COMPLEXITY = 0.20
    WEIGHT_TECHNICAL = 0.15
    WEIGHT_PRIORITY = 0.10

    # Difficulty thresholds
    THRESHOLD_TRIVIAL = 0.2
    THRESHOLD_EASY = 0.4
    THRESHOLD_MEDIUM = 0.6
    THRESHOLD_HARD = 0.8

    def __init__(self, context_linter: Optional[ContextLinter] = None, enable_safety: bool = True):
        # Model pricing (per 1M tokens) - FREE tier added for local LLMs
        self.model_costs = {
            ModelTier.FREE: 0.00,           # Local LLM (Qwen 7B) - FREE!
            ModelTier.ULTRA_CHEAP: 0.03,
            ModelTier.CHEAP: 0.10,
            ModelTier.STANDARD: 1.50,
            ModelTier.PREMIUM: 3.00,
            ModelTier.ULTRA_PREMIUM: 5.00,
        }

        # Context linter for validation
        self.context_linter = context_linter
        if CONTEXT_LINTER_AVAILABLE and self.context_linter is None:
            self.context_linter = get_context_linter()

        # WaltzRL safety integration (optional, disabled by default in tests)
        self.enable_safety = enable_safety
        self.safety_wrapper = None
        if enable_safety:
            try:
                from infrastructure.waltzrl_safety import get_waltzrl_safety
                self.safety_wrapper = get_waltzrl_safety(
                    enable_blocking=False,  # Don't block by default
                    feedback_only_mode=True,  # Log only initially
                    stage=1  # Pattern-based
                )
                logger.info("WaltzRL safety wrapper initialized")
            except ImportError:
                logger.warning("WaltzRL safety not available, continuing without safety checks")

        # Complexity indicators (all lowercase for matching)
        self.complexity_keywords = [
            'architecture', 'system', 'design', 'optimize', 'algorithm',
            'concurrent', 'distributed', 'scalable', 'performance',
            'security', 'integration', 'refactor', 'debug', 'analyze'
        ]

        self.technical_keywords = [
            'database', 'api', 'framework', 'deployment', 'infrastructure',
            'authentication', 'authorization', 'encryption', 'protocol',
            'microservice', 'containerize', 'orchestrate', 'pipeline'
        ]

        # Fine-tuned adapter registry
        self.adapters: Dict[str, Dict[str, Any]] = {}  # agent_name -> adapter_info
        # Use relative path for cloud deployment
        self.adapter_base_dir = Path(__file__).parent.parent / "models" / "finetuned_agents"
        self._load_available_adapters()

    def _load_available_adapters(self):
        """Scan for available fine-tuned adapters"""
        if not self.adapter_base_dir.exists():
            logger.debug("No adapter directory found, skipping adapter loading (expected in Railway)")
            return

        for agent_dir in self.adapter_base_dir.iterdir():
            if agent_dir.is_dir():
                adapter_path = agent_dir / "final_model"
                if adapter_path.exists():
                    agent_name = agent_dir.name
                    self.adapters[agent_name] = {
                        "path": str(adapter_path),
                        "loaded_at": datetime.now(timezone.utc).isoformat(),
                        "model": None,  # Lazy load
                        "tokenizer": None
                    }
                    logger.info(f"Adapter registered: {agent_name} at {adapter_path}")

        logger.info(f"Loaded {len(self.adapters)} adapter(s)")

    def load_adapter(self, agent_name: str, adapter_path: Optional[str] = None) -> bool:
        """
        Load fine-tuned adapter for agent.

        Args:
            agent_name: Agent name
            adapter_path: Optional explicit adapter path

        Returns:
            True if loaded successfully, False otherwise
        """
        if not HAS_UNSLOTH:
            logger.warning(f"Cannot load adapter for {agent_name}: Unsloth not available")
            return False

        try:
            # Use provided path or registry
            if adapter_path is None:
                if agent_name not in self.adapters:
                    logger.warning(f"No adapter found for agent: {agent_name}")
                    return False
                adapter_path = self.adapters[agent_name]["path"]

            logger.info(f"Loading adapter for {agent_name} from {adapter_path}")

            # Load model and tokenizer with adapter
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=adapter_path,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )

            # Update registry
            if agent_name not in self.adapters:
                self.adapters[agent_name] = {}

            self.adapters[agent_name].update({
                "path": adapter_path,
                "model": model,
                "tokenizer": tokenizer,
                "loaded_at": datetime.now(timezone.utc).isoformat()
            })

            logger.info(f"Adapter loaded successfully: {agent_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load adapter for {agent_name}: {e}", exc_info=True)
            return False

    def route_with_adapter(
        self,
        task: Dict,
        agent_name: Optional[str] = None
    ) -> Tuple[str, Optional[Any], Optional[Any]]:
        """
        Route task with adapter preference if available.

        Args:
            task: Task dictionary
            agent_name: Agent name (for adapter lookup)

        Returns:
            Tuple of (model_name, model_obj, tokenizer) - model/tokenizer None if no adapter
        """
        # Check if agent has fine-tuned adapter
        if agent_name and agent_name in self.adapters:
            adapter_info = self.adapters[agent_name]

            # Lazy load if not loaded
            if adapter_info.get("model") is None:
                self.load_adapter(agent_name)
                adapter_info = self.adapters[agent_name]

            # Return adapter model if available
            if adapter_info.get("model") is not None:
                logger.info(f"Using fine-tuned adapter for {agent_name}")
                return (
                    f"{agent_name}_finetuned",
                    adapter_info["model"],
                    adapter_info["tokenizer"]
                )

        # Fall back to standard DAAO routing
        decision = self.route_task(task)
        return (decision.model, None, None)

    def estimate_difficulty(self, task: Dict) -> float:
        """
        Estimate task difficulty using multiple heuristics

        Args:
            task: Task dictionary with description, priority, etc.

        Returns:
            float: Difficulty score (0.0 = trivial, 1.0 = expert)

        Raises:
            TypeError: If task is not a dictionary
        """
        # Input validation
        if not isinstance(task, dict):
            raise TypeError(f"Task must be a dictionary, got {type(task)}")

        # Extract and validate fields
        description = task.get('description', '') or ''
        if not isinstance(description, str):
            description = str(description)

        priority = task.get('priority', 0.5) or 0.5
        if not isinstance(priority, (int, float)):
            priority = 0.5
        priority = max(0.0, min(1.0, float(priority)))  # Clamp to 0-1

        required_tools = task.get('required_tools', []) or []
        if not isinstance(required_tools, list):
            required_tools = []

        steps = task.get('num_steps', 0) or 0
        if not isinstance(steps, (int, float)):
            steps = 0
        steps = max(0, int(steps))

        # Metric 1: Description length (longer = more complex)
        length_score = min(len(description) / self.MAX_DESCRIPTION_LENGTH, 1.0)

        # Metric 2: Number of steps (if provided)
        steps_score = min(steps / self.MAX_STEPS_CONSIDERED, 1.0)

        # Metric 3: Number of tools required
        tools_score = min(len(required_tools) / self.MAX_TOOLS_CONSIDERED, 1.0)

        # Metric 4: Complexity keywords
        complexity_count = sum(
            1 for keyword in self.complexity_keywords
            if keyword in description.lower()
        )
        complexity_score = min(complexity_count / self.MAX_COMPLEXITY_KEYWORDS, 1.0)

        # Metric 5: Technical keywords
        technical_count = sum(
            1 for keyword in self.technical_keywords
            if keyword in description.lower()
        )
        technical_score = min(technical_count / self.MAX_TECHNICAL_KEYWORDS, 1.0)

        # Metric 6: Priority (higher priority = potentially more complex)
        priority_score = priority

        # Weighted combination (weights defined as class constants)
        difficulty = (
            self.WEIGHT_LENGTH * length_score +
            self.WEIGHT_STEPS * steps_score +
            self.WEIGHT_TOOLS * tools_score +
            self.WEIGHT_COMPLEXITY * complexity_score +
            self.WEIGHT_TECHNICAL * technical_score +
            self.WEIGHT_PRIORITY * priority_score
        )

        return min(difficulty, 1.0)

    def select_model(self, difficulty: float, budget_conscious: bool = True, allow_local: bool = True) -> ModelTier:
        """
        Select appropriate model tier based on difficulty

        Args:
            difficulty: Difficulty score (0.0-1.0)
            budget_conscious: If True, prefer cheaper models when possible
            allow_local: If True, allow local LLM for trivial/easy tasks (FREE!)

        Returns:
            ModelTier: Selected model tier
        """
        if budget_conscious:
            # PHASE 6 OPTIMIZATION: Use local LLM first (FREE!)
            # Conservative routing (maximize cost savings)
            if difficulty < self.THRESHOLD_TRIVIAL and allow_local:
                return ModelTier.FREE  # Local LLM for trivial (FREE!)
            elif difficulty < self.THRESHOLD_TRIVIAL:
                return ModelTier.ULTRA_CHEAP  # Gemini Flash for trivial
            elif difficulty < self.THRESHOLD_EASY and allow_local:
                return ModelTier.FREE  # Local LLM for easy (FREE!)
            elif difficulty < self.THRESHOLD_EASY:
                return ModelTier.ULTRA_CHEAP  # Gemini Flash for easy
            elif difficulty < self.THRESHOLD_MEDIUM:
                return ModelTier.CHEAP  # Gemini Flash Lite for medium
            elif difficulty < self.THRESHOLD_HARD:
                return ModelTier.STANDARD  # Claude 3.7 Sonnet for hard
            elif difficulty < 0.9:
                return ModelTier.PREMIUM  # GPT-4o for very hard
            else:
                return ModelTier.ULTRA_PREMIUM  # Claude 4 for expert
        else:
            # Quality-focused routing (maximize accuracy)
            if difficulty < 0.3:
                return ModelTier.CHEAP
            elif difficulty < 0.5:
                return ModelTier.STANDARD
            elif difficulty < 0.7:
                return ModelTier.PREMIUM
            else:
                return ModelTier.ULTRA_PREMIUM

    def _estimate_tokens(self, task: Dict) -> int:
        """
        Estimate token count for a task

        Args:
            task: Task dictionary

        Returns:
            Estimated token count
        """
        base = 500  # Base tokens for system prompts

        # Estimate description tokens (~1.3 tokens per word)
        description = task.get('description', '') or ''
        if isinstance(description, str):
            desc_tokens = len(description.split()) * 1.3
        else:
            desc_tokens = 0

        # Additional tokens for steps and tools
        steps = task.get('num_steps', 0) or 0
        if isinstance(steps, (int, float)):
            steps = max(0, int(steps))
        else:
            steps = 0

        tools = task.get('required_tools', []) or []
        if isinstance(tools, list):
            tool_count = len(tools)
        else:
            tool_count = 0

        return int(base + desc_tokens + (steps * 200) + (tool_count * 300))

    def _calculate_confidence(self, difficulty_score: float) -> float:
        """
        Calculate routing confidence based on difficulty score

        Higher confidence at extremes (clear trivial/expert tasks)
        Lower confidence near thresholds (boundary cases)

        Args:
            difficulty_score: Difficulty score (0.0-1.0)

        Returns:
            Confidence score (0.0-1.0)
        """
        # Distance from nearest threshold (closer to threshold = less confident)
        thresholds = [
            self.THRESHOLD_TRIVIAL,
            self.THRESHOLD_EASY,
            self.THRESHOLD_MEDIUM,
            self.THRESHOLD_HARD
        ]
        min_threshold_distance = min(abs(difficulty_score - t) for t in thresholds)

        # Scale distance to confidence (max distance is 0.2, so scale by 5)
        confidence = min(min_threshold_distance * 5.0, 1.0)

        return confidence

    def route_task(
        self,
        task: Dict,
        budget_conscious: bool = True,
        context_messages: Optional[List] = None
    ) -> RoutingDecision:
        """
        Route task to appropriate model

        Args:
            task: Task dictionary with description, priority, etc.
            budget_conscious: Prefer cost savings over max quality
            context_messages: Optional context messages for validation

        Returns:
            RoutingDecision with model, difficulty, cost estimate, reasoning
        """
        # Validate context quality if provided
        context_valid = True
        context_metrics = {}

        if context_messages and self.context_linter and CONTEXT_LINTER_AVAILABLE:
            # Convert to Message objects if needed
            messages = []
            for msg in context_messages:
                if not isinstance(msg, Message):
                    messages.append(Message(
                        content=msg.get('content', ''),
                        role=msg.get('role', 'user'),
                        timestamp=datetime.now(timezone.utc),
                        source=msg.get('source', 'unknown')
                    ))
                else:
                    messages.append(msg)

            # Lint context
            linted = self.context_linter.lint_context(messages)

            # Check if context contract violated
            # If token reduction > 60%, context was too noisy - re-query recommended
            if linted.token_reduction_percent > 60:
                context_valid = False
                logger.warning(
                    f"Context quality low: {linted.token_reduction_percent:.1f}% tokens removed. "
                    f"Consider re-querying with stricter limits."
                )

            context_metrics = {
                'original_tokens': linted.original_tokens,
                'cleaned_tokens': linted.cleaned_tokens,
                'token_reduction_percent': linted.token_reduction_percent,
                'context_valid': context_valid
            }

            # Log quality metrics
            logger.info(
                f"Context validated: {linted.original_tokens} → {linted.cleaned_tokens} tokens "
                f"({linted.token_reduction_percent:.1f}% reduction), valid={context_valid}"
            )

        # Estimate difficulty
        difficulty_score = self.estimate_difficulty(task)

        # Categorize difficulty
        if difficulty_score < self.THRESHOLD_TRIVIAL:
            difficulty = TaskDifficulty.TRIVIAL
        elif difficulty_score < self.THRESHOLD_EASY:
            difficulty = TaskDifficulty.EASY
        elif difficulty_score < self.THRESHOLD_MEDIUM:
            difficulty = TaskDifficulty.MEDIUM
        elif difficulty_score < self.THRESHOLD_HARD:
            difficulty = TaskDifficulty.HARD
        else:
            difficulty = TaskDifficulty.EXPERT

        # Select model
        model_tier = self.select_model(difficulty_score, budget_conscious)

        # Estimate tokens dynamically based on task size
        estimated_tokens = self._estimate_tokens(task)
        estimated_cost = (self.model_costs[model_tier] / 1_000_000) * estimated_tokens

        # Calculate confidence (fixed formula - higher at extremes)
        confidence = self._calculate_confidence(difficulty_score)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            task, difficulty_score, model_tier, budget_conscious
        )

        # Log routing decision
        log_extra = {
            'task_id': task.get('id', 'unknown'),
            'difficulty': difficulty_score,
            'difficulty_category': difficulty.value,
            'confidence': confidence,
            'estimated_cost': estimated_cost,
            'estimated_tokens': estimated_tokens,
            'budget_conscious': budget_conscious,
            'model': model_tier.value
        }

        # Add context metrics if available
        if context_metrics:
            log_extra['context_metrics'] = context_metrics

        logger.info(
            f"Routed task to {model_tier.value}",
            extra=log_extra
        )

        return RoutingDecision(
            model=model_tier.value,
            difficulty=difficulty,
            estimated_cost=estimated_cost,
            confidence=confidence,
            reasoning=reasoning
        )

    def safety_filter_task(
        self,
        task: Dict,
        agent_name: str = "unknown"
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        Safety filter task before routing (WaltzRL integration).

        This method provides a safety gate BEFORE task routing:
        1. Analyzes task description for unsafe content
        2. Blocks unsafe tasks (if enabled)
        3. Logs safety metrics
        4. Returns safe/unsafe decision + explanation

        Args:
            task: Task dictionary with 'description' field
            agent_name: Name of agent requesting routing

        Returns:
            Tuple of (is_safe, blocked_message, safety_metrics)
            - is_safe: True if task is safe to route
            - blocked_message: Optional blocking message (if unsafe)
            - safety_metrics: Dict of safety scores and details

        Example:
            is_safe, msg, metrics = router.safety_filter_task(task, "qa-agent")
            if not is_safe:
                return {"error": msg, "metrics": metrics}
        """
        if not self.enable_safety or not self.safety_wrapper:
            # Safety disabled, pass through
            return True, None, {}

        description = task.get('description', '') or ''

        # Use WaltzRL safety wrapper to filter query
        is_safe, confidence, explanation = self.safety_wrapper.filter_unsafe_query(description)

        safety_metrics = {
            'is_safe': is_safe,
            'confidence': confidence,
            'agent_name': agent_name,
            'task_description_length': len(description)
        }

        if not is_safe:
            logger.warning(
                f"Safety filter BLOCKED task for {agent_name}: {explanation[:100]}... "
                f"(confidence={confidence:.2f})"
            )
            return False, explanation, safety_metrics
        else:
            logger.debug(
                f"Safety filter PASSED task for {agent_name} (confidence={confidence:.2f})"
            )
            return True, None, safety_metrics

    def safety_improve_response(
        self,
        query: str,
        response: str,
        agent_name: str = "unknown"
    ) -> Dict:
        """
        Improve agent response using WaltzRL safety wrapper.

        This method provides post-processing safety improvements:
        1. Analyzes response for safety issues
        2. Redacts sensitive data (PII, credentials)
        3. Rewrites over-refusals to be more helpful
        4. Returns improved response + metrics

        Args:
            query: Original user query
            response: Agent's response
            agent_name: Name of agent that generated response

        Returns:
            Dict with:
                - 'response': Final safe response (improved if needed)
                - 'original_response': Original response (for comparison)
                - 'safety_score': Safety score (0.0-1.0)
                - 'helpfulness_score': Helpfulness score (0.0-1.0)
                - 'blocked': Whether response was blocked
                - 'changes_made': List of changes applied

        Example:
            result = router.safety_improve_response(query, response, "support-agent")
            return result['response']  # Use improved response
        """
        if not self.enable_safety or not self.safety_wrapper:
            # Safety disabled, return original
            return {
                'response': response,
                'original_response': response,
                'safety_score': 1.0,
                'helpfulness_score': 1.0,
                'blocked': False,
                'changes_made': []
            }

        # Use collaborative filter (query + response analysis)
        filter_result = self.safety_wrapper.collaborative_filter(
            query=query,
            response=response,
            agent_name=agent_name
        )

        result = {
            'response': filter_result.final_response,
            'original_response': response,
            'safety_score': filter_result.safety_score.safety_score,
            'helpfulness_score': filter_result.safety_score.helpfulness_score,
            'blocked': filter_result.blocked,
            'changes_made': [
                issue.description for issue in filter_result.response_issues
            ],
            'processing_time_ms': filter_result.processing_time_ms
        }

        logger.info(
            f"Safety improved response for {agent_name}: "
            f"safety={result['safety_score']:.2f}, "
            f"helpfulness={result['helpfulness_score']:.2f}, "
            f"blocked={result['blocked']}, "
            f"changes={len(result['changes_made'])}"
        )

        return result

    def _generate_reasoning(
        self,
        task: Dict,
        difficulty: float,
        model: ModelTier,
        budget_conscious: bool
    ) -> str:
        """Generate human-readable routing reasoning"""
        description = (task.get('description', '') or '')[:100]  # Handle None

        reasons = []

        # Difficulty assessment
        if difficulty < 0.3:
            reasons.append(f"Task is simple (difficulty: {difficulty:.2f})")
        elif difficulty < 0.6:
            reasons.append(f"Task is moderate (difficulty: {difficulty:.2f})")
        else:
            reasons.append(f"Task is complex (difficulty: {difficulty:.2f})")

        # Model selection
        if budget_conscious:
            reasons.append(f"Cost-optimized routing to {model.value}")
        else:
            reasons.append(f"Quality-focused routing to {model.value}")

        # Cost impact
        cost = self.model_costs[model]
        if cost < 0.5:
            reasons.append("Low cost model selected")
        elif cost < 2.0:
            reasons.append("Medium cost model selected")
        else:
            reasons.append("High cost model selected for quality")

        return " | ".join(reasons)

    def estimate_cost_savings(
        self,
        tasks: List[Dict],
        baseline_model: ModelTier = ModelTier.PREMIUM
    ) -> Dict[str, float]:
        """
        Estimate cost savings from DAAO routing vs. always using baseline model

        Args:
            tasks: List of tasks to route
            baseline_model: Model that would be used without DAAO

        Returns:
            Dictionary with cost metrics
        """
        # Handle empty task list
        if not tasks:
            return {
                'daao_cost': 0.0,
                'baseline_cost': 0.0,
                'savings': 0.0,
                'savings_percent': 0.0,
                'num_tasks': 0
            }

        baseline_cost_per_task = self.model_costs[baseline_model] / 1000

        daao_total_cost = 0.0
        baseline_total_cost = 0.0

        for task in tasks:
            decision = self.route_task(task)
            daao_total_cost += decision.estimated_cost
            baseline_total_cost += baseline_cost_per_task

        savings = baseline_total_cost - daao_total_cost
        savings_percent = (savings / baseline_total_cost) * 100 if baseline_total_cost > 0 else 0

        logger.info(
            f"Cost savings analysis complete",
            extra={
                'num_tasks': len(tasks),
                'daao_cost': daao_total_cost,
                'baseline_cost': baseline_total_cost,
                'savings': savings,
                'savings_percent': savings_percent,
                'baseline_model': baseline_model.value
            }
        )

        return {
            'daao_cost': daao_total_cost,
            'baseline_cost': baseline_total_cost,
            'savings': savings,
            'savings_percent': savings_percent,
            'num_tasks': len(tasks)
        }


# Factory function
def get_daao_router() -> DAAORouter:
    """
    Factory function to create DAAO router instance

    Returns:
        DAAORouter: Configured router ready for task routing

    Example:
        >>> router = get_daao_router()
        >>> decision = router.route_task({'description': 'Fix bug', 'priority': 0.5})
        >>> print(f"Route to: {decision.model}")
    """
    return DAAORouter()


# Example usage
if __name__ == "__main__":
    router = get_daao_router()

    # Test tasks
    test_tasks = [
        {
            'description': 'Fix typo in README.md',
            'priority': 0.1,
            'required_tools': []
        },
        {
            'description': 'Design and implement a scalable microservices architecture with authentication, database integration, and deployment pipeline',
            'priority': 0.9,
            'required_tools': ['docker', 'kubernetes', 'database', 'auth', 'ci/cd']
        },
        {
            'description': 'Write a function to calculate factorial',
            'priority': 0.3,
            'required_tools': []
        },
        {
            'description': 'Optimize database queries and implement caching for performance',
            'priority': 0.7,
            'required_tools': ['database', 'redis', 'profiler']
        }
    ]

    print("=" * 80)
    print("DAAO ROUTING DEMONSTRATION")
    print("=" * 80)

    for i, task in enumerate(test_tasks, 1):
        decision = router.route_task(task)
        print(f"\nTask {i}: {task['description'][:60]}...")
        print(f"  Difficulty: {decision.difficulty.value}")
        print(f"  Model: {decision.model}")
        print(f"  Est. Cost: ${decision.estimated_cost:.6f}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reasoning: {decision.reasoning}")

    # Cost savings estimate
    print("\n" + "=" * 80)
    print("COST SAVINGS ESTIMATE")
    print("=" * 80)

    savings = router.estimate_cost_savings(test_tasks)
    print(f"Tasks: {savings['num_tasks']}")
    print(f"Baseline Cost (GPT-4o for all): ${savings['baseline_cost']:.6f}")
    print(f"DAAO Cost (optimized): ${savings['daao_cost']:.6f}")
    print(f"Savings: ${savings['savings']:.6f} ({savings['savings_percent']:.1f}%)")
    print(f"\nExpected from paper: 36% cost reduction")
    print(f"Actual in demo: {savings['savings_percent']:.1f}% cost reduction")


# ===== SGLang MTP Integration =====

class InferenceBackend(Enum):
    """Inference backend options."""
    STANDARD = "standard"      # Standard API calls
    SGLANG_MTP = "sglang_mtp"  # SGLang with Multi-Token Prediction
    VLLM = "vllm"              # vLLM inference


@dataclass
class BackendRoutingDecision:
    """Decision for routing to inference backend."""
    backend: InferenceBackend
    use_speculative_decoding: bool
    expected_speedup: float
    reasoning: str


class SGLangRouter:
    """
    Routes tasks to appropriate inference backend.

    Integration with SGLang MTP for high-throughput scenarios:
    - Batch inference → SGLang MTP (2-4x speedup)
    - Single requests → Standard API
    - Long generations → SGLang with CUDA graphs
    """

    def __init__(self):
        """Initialize SGLang router."""
        self.backends_available = {
            InferenceBackend.STANDARD: True,
            InferenceBackend.SGLANG_MTP: False,  # Requires SGLang server
            InferenceBackend.VLLM: False,  # Requires vLLM server
        }

    def set_backend_availability(self, backend: InferenceBackend, available: bool):
        """Set whether a backend is available."""
        self.backends_available[backend] = available
        logger.info(f"Backend {backend.value} availability: {available}")

    def route_to_sglang(self, task: Dict, model: str) -> bool:
        """
        Determine if task should use SGLang MTP.

        Criteria:
        - Batch size > 8 → Use SGLang (better batching)
        - Generation length > 512 → Use SGLang (CUDA graphs benefit)
        - High throughput requirement → Use SGLang

        Args:
            task: Task dictionary
            model: Model name

        Returns:
            True if should use SGLang
        """
        if not self.backends_available[InferenceBackend.SGLANG_MTP]:
            return False

        # Check batch size
        batch_size = task.get('batch_size', 1)
        if batch_size > 8:
            logger.debug(f"Routing to SGLang: batch_size={batch_size} > 8")
            return True

        # Check generation length
        max_tokens = task.get('max_tokens', 256)
        if max_tokens > 512:
            logger.debug(f"Routing to SGLang: max_tokens={max_tokens} > 512")
            return True

        # Check throughput requirement
        throughput_critical = task.get('throughput_critical', False)
        if throughput_critical:
            logger.debug("Routing to SGLang: throughput_critical=True")
            return True

        return False

    def use_speculative_decoding(self, task_type: str) -> bool:
        """
        Determine if task should use speculative decoding.

        Speculative decoding benefits:
        - Generation tasks (2-4x speedup)
        - QA/chat (2x speedup typical)

        NOT beneficial:
        - Classification (single token)
        - Embeddings

        Args:
            task_type: Type of task (generation, qa, classification, etc.)

        Returns:
            True if should use speculative decoding
        """
        speculative_beneficial = [
            'generation',
            'qa',
            'chat',
            'summarization',
            'translation',
            'code_generation'
        ]

        return task_type.lower() in speculative_beneficial

    def select_backend(
        self,
        task: Dict,
        model: str,
        task_type: str = "generation"
    ) -> BackendRoutingDecision:
        """
        Select optimal inference backend for task.

        Args:
            task: Task dictionary
            model: Model name
            task_type: Type of task

        Returns:
            BackendRoutingDecision with backend choice
        """
        # Check if SGLang should be used
        use_sglang = self.route_to_sglang(task, model)

        if use_sglang:
            use_spec = self.use_speculative_decoding(task_type)

            # Estimate speedup
            batch_size = task.get('batch_size', 1)
            max_tokens = task.get('max_tokens', 256)

            speedup = 1.0
            if use_spec:
                # Speculative decoding: 2-4x speedup
                speedup *= 2.5
            if batch_size > 16:
                # Good batching: 1.5x additional speedup
                speedup *= 1.5
            if max_tokens > 512:
                # CUDA graphs benefit: 1.2x additional
                speedup *= 1.2

            return BackendRoutingDecision(
                backend=InferenceBackend.SGLANG_MTP,
                use_speculative_decoding=use_spec,
                expected_speedup=speedup,
                reasoning=f"SGLang MTP selected: batch_size={batch_size}, "
                          f"max_tokens={max_tokens}, speculative={use_spec}, "
                          f"expected speedup={speedup:.1f}x"
            )

        # Fallback to standard
        return BackendRoutingDecision(
            backend=InferenceBackend.STANDARD,
            use_speculative_decoding=False,
            expected_speedup=1.0,
            reasoning="Standard API: small batch, short generation"
        )

    def estimate_sglang_benefit(
        self,
        tasks: List[Dict],
        baseline_tokens_per_sec: float = 50.0
    ) -> Dict[str, Any]:
        """
        Estimate benefit of using SGLang for task set.

        Args:
            tasks: List of tasks
            baseline_tokens_per_sec: Baseline throughput without SGLang

        Returns:
            Dictionary with benefit estimates
        """
        total_tasks = len(tasks)
        sglang_tasks = sum(1 for t in tasks if self.route_to_sglang(t, "gpt-4o"))

        if sglang_tasks == 0:
            return {
                'sglang_tasks': 0,
                'total_tasks': total_tasks,
                'sglang_usage_pct': 0.0,
                'estimated_speedup': 1.0,
                'estimated_time_saved_pct': 0.0
            }

        # Average speedup (conservative estimate: 2.5x)
        avg_speedup = 2.5

        # Time saved calculation
        # Assume even distribution of work
        sglang_pct = sglang_tasks / total_tasks
        time_saved_pct = sglang_pct * (1 - 1/avg_speedup) * 100

        return {
            'sglang_tasks': sglang_tasks,
            'total_tasks': total_tasks,
            'sglang_usage_pct': (sglang_tasks / total_tasks) * 100,
            'estimated_speedup': avg_speedup,
            'estimated_time_saved_pct': time_saved_pct,
            'estimated_throughput_tokens_per_sec': baseline_tokens_per_sec * (
                sglang_pct * avg_speedup + (1 - sglang_pct)
            )
        }


# Example integration with DAAORouter
class EnhancedDAAORouter(DAAORouter):
    """
    DAAO Router with SGLang MTP integration.

    Combines difficulty-aware routing with inference backend optimization.
    """

    def __init__(self, context_linter=None):
        super().__init__(context_linter)
        self.sglang_router = SGLangRouter()

    def route_task_with_backend(
        self,
        task: Dict,
        budget_conscious: bool = True,
        task_type: str = "generation"
    ) -> Tuple[RoutingDecision, BackendRoutingDecision]:
        """
        Route task with both model and backend selection.

        Args:
            task: Task dictionary
            budget_conscious: Prefer cheaper models
            task_type: Type of task

        Returns:
            Tuple of (RoutingDecision, BackendRoutingDecision)
        """
        # Model selection (existing DAAO logic)
        model_decision = self.route_task(task, budget_conscious)

        # Backend selection (new SGLang logic)
        backend_decision = self.sglang_router.select_backend(
            task,
            model_decision.model,
            task_type
        )

        return model_decision, backend_decision

    def enable_sglang(self, enabled: bool = True):
        """Enable/disable SGLang MTP backend."""
        self.sglang_router.set_backend_availability(
            InferenceBackend.SGLANG_MTP,
            enabled
        )
        logger.info(f"SGLang MTP backend: {'enabled' if enabled else 'disabled'}")


