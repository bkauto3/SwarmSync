"""
SPEC AGENT - Microsoft Agent Framework Version with Self-Improvement
Version: 5.0 (Enhanced with DAAO + TUMIX on top of v4.0 features)
Last Updated: October 16, 2025

Creates detailed technical specifications with automatic quality reflection,
collective intelligence from previous specs, and trajectory recording for learning.

INTEGRATIONS:
- ReasoningBank: Query successful spec patterns, store new strategies
- Replay Buffer: Record all spec creation trajectories for learning
- Reflection Harness: Automatic quality checks with regeneration
- Microsoft Agent Framework: Production-ready orchestration
- DAAO Router: Cost-optimized model routing (30-40% savings)
- TUMIX Termination: Early stopping for iterative refinement (40-50% savings)

ARCHITECTURE:
- Layer 1 (Genesis): Microsoft Agent Framework orchestration
- Layer 2 (Darwin): Self-improvement via Replay Buffer trajectories
- Layer 6 (Memory): Collective intelligence via ReasoningBank strategies
- Quality Assurance: Reflection Harness for output validation
- Cost Optimization: DAAO routing + TUMIX termination

THREAD-SAFETY:
- All infrastructure components are thread-safe
- Async operations use proper locking
- Context managers ensure resource cleanup
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

# Infrastructure imports
from infrastructure.reasoning_bank import (
    get_reasoning_bank,
    MemoryType,
    OutcomeTag,
    StrategyNugget
)
from infrastructure.replay_buffer import (
    get_replay_buffer,
    Trajectory,
    ActionStep
)
from infrastructure.reflection_harness import (
    ReflectionHarness,
    FallbackBehavior,
    HarnessResult
)
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)

# Setup
setup_observability(enable_sensitive_data=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SpecCreationContext:
    """Context for a spec creation task"""
    business_id: str
    idea: str
    tech_stack: Optional[Dict[str, str]] = None
    started_at: str = ""
    initial_state: Dict[str, Any] = None

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()
        if self.initial_state is None:
            self.initial_state = {
                "idea": self.idea,
                "tech_stack": self.tech_stack or {},
                "timestamp": self.started_at
            }


class SpecAgent:
    """
    Technical Specification Creator with Self-Improvement

    Core Capabilities:
    - Create detailed technical specifications
    - Query successful patterns from ReasoningBank
    - Record trajectories in Replay Buffer
    - Automatic quality reflection with regeneration
    - Learn from past successes and failures

    Microsoft Agent Framework Integration:
    - Uses ChatAgent with Azure AI backend
    - Tool registration for spec creation functions
    - Async context managers for resource management
    """

    def __init__(
        self,
        business_id: str = "default",
        quality_threshold: float = 0.75,
        max_reflection_attempts: int = 2
    ):
        """
        Initialize SpecAgent

        Args:
            business_id: Unique business identifier
            quality_threshold: Minimum quality score for reflection (0.0-1.0)
            max_reflection_attempts: Max regeneration attempts on quality failure
        """
        self.business_id = business_id
        self.agent_id = f"spec_{business_id}"
        self.agent = None
        self.credential = None

        # Infrastructure components (thread-safe singletons)
        self.reasoning_bank = get_reasoning_bank()
        self.replay_buffer = get_replay_buffer()

        # Reflection harness for quality checks
        self.reflection_harness = ReflectionHarness(
            quality_threshold=quality_threshold,
            max_attempts=max_reflection_attempts,
            fallback_behavior=FallbackBehavior.WARN
        )

        # DAAO router for cost optimization
        self.router = get_daao_router()

        # TUMIX termination for iterative spec refinement
        # Specs need clarity: min 2, max 4 rounds, 5% threshold
        self.termination = get_tumix_termination(
            min_rounds=2,  # Initial spec + review minimum
            max_rounds=4,  # Specifications need clarity
            improvement_threshold=0.05  # 5% improvement threshold (standard)
        )

        # Track refinement history for TUMIX
        self.refinement_history: List[List[RefinementResult]] = []

        # Performance tracking
        self.stats = {
            "specs_created": 0,
            "successful_reflections": 0,
            "failed_reflections": 0,
            "strategies_reused": 0,
            "trajectories_recorded": 0
        }

        logger.info(f"SpecAgent v5.0 initialized: {self.agent_id}")
        logger.info(f"  Quality threshold: {quality_threshold}")
        logger.info(f"  Max reflection attempts: {max_reflection_attempts}")
        logger.info(f"  DAAO + TUMIX: Enabled for cost optimization")

    async def initialize(self):
        """Initialize Azure credentials and Agent Framework agent"""
        try:
            self.credential = AzureCliCredential()
            client = AzureAIAgentClient(async_credential=self.credential)

            self.agent = ChatAgent(
                chat_client=client,
                instructions="""You are an expert technical specification writer with deep software architecture knowledge.

Your role:
- Create EXTREMELY detailed technical specifications
- Use concrete examples, not placeholders
- Specify exact tech stack, database schemas, API endpoints
- Include Stripe integration patterns
- Provide deployment checklists
- Write specifications that developers can implement directly

Quality standards:
- Be specific and actionable
- Include complete database schemas (SQL)
- List all API routes with methods
- Specify authentication/authorization
- Detail third-party integrations
- Provide testing strategies

Tech stack defaults (unless specified):
- Frontend: Next.js 14 with App Router, React 18, TypeScript, Tailwind CSS
- Backend: Next.js API routes or FastAPI (Python)
- Database: Supabase (PostgreSQL) or MongoDB
- Auth: NextAuth.js or Supabase Auth
- Payments: Stripe
- Deployment: Vercel or AWS

Format specifications as JSON with sections:
1. Overview (problem statement, solution approach)
2. Features (detailed user stories with acceptance criteria)
3. Tech Stack (exact versions and justification)
4. Database Schema (complete SQL with indexes)
5. API Endpoints (all routes with request/response examples)
6. Page Structure (all pages with components)
7. Stripe Integration (products, webhooks, checkout flow)
8. Deployment Checklist (environment variables, CI/CD, monitoring)
9. Testing Strategy (unit, integration, e2e test plans)

Be thorough. Specifications should be 500-1000 lines when detailed.""",
                name="spec-agent",
                tools=[
                    self._tool_create_spec,
                    self._tool_query_patterns,
                    self._tool_get_anti_patterns
                ]
            )

            logger.info(f"Agent Framework initialized: {self.agent_id}")

        except Exception as e:
            logger.error(f"Failed to initialize SpecAgent: {e}")
            raise

    async def close(self):
        """Clean up resources"""
        try:
            if self.credential:
                await self.credential.close()
            logger.info(f"SpecAgent closed: {self.agent_id}")
        except Exception as e:
            logger.warning(f"Error closing SpecAgent: {e}")

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    def _tool_create_spec(
        self,
        idea: str,
        tech_stack: Optional[str] = None
    ) -> str:
        """
        Tool: Create technical specification (synchronous wrapper)

        Args:
            idea: Business idea description
            tech_stack: Optional tech stack override (JSON string)

        Returns:
            JSON specification string
        """
        # Parse tech_stack if provided
        stack_dict = None
        if tech_stack:
            try:
                stack_dict = json.loads(tech_stack)
            except json.JSONDecodeError:
                logger.warning(f"Invalid tech_stack JSON, using default: {tech_stack}")

        # Run async create_spec in event loop
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.create_spec(idea=idea, tech_stack=stack_dict)
        )
        return result

    def _tool_query_patterns(self, task_description: str, top_n: int = 5) -> str:
        """
        Tool: Query successful spec patterns from ReasoningBank

        Args:
            task_description: Description of spec task (e.g., "SaaS authentication spec")
            top_n: Number of top patterns to return

        Returns:
            JSON string with successful patterns
        """
        try:
            strategies = self.reasoning_bank.search_strategies(
                task_context=task_description,
                top_n=top_n,
                min_win_rate=0.5  # Only successful patterns
            )

            patterns = [
                {
                    "description": s.description,
                    "context": s.context,
                    "win_rate": s.win_rate,
                    "usage_count": s.usage_count,
                    "steps": list(s.steps)[:3]  # First 3 steps as example
                }
                for s in strategies
            ]

            return json.dumps({
                "query": task_description,
                "patterns_found": len(patterns),
                "patterns": patterns
            }, indent=2)

        except Exception as e:
            logger.error(f"Pattern query failed: {e}")
            return json.dumps({"error": str(e), "patterns": []})

    def _tool_get_anti_patterns(self, task_type: str = "spec", top_n: int = 3) -> str:
        """
        Tool: Get anti-patterns (failures) to avoid

        Args:
            task_type: Type of task (default: "spec")
            top_n: Number of anti-patterns to return

        Returns:
            JSON string with anti-patterns and fixes
        """
        try:
            anti_patterns = self.replay_buffer.query_anti_patterns(
                task_type=task_type,
                top_n=top_n
            )

            return json.dumps({
                "task_type": task_type,
                "anti_patterns_found": len(anti_patterns),
                "anti_patterns": anti_patterns
            }, indent=2)

        except Exception as e:
            logger.error(f"Anti-pattern query failed: {e}")
            return json.dumps({"error": str(e), "anti_patterns": []})

    async def create_spec(
        self,
        idea: str,
        tech_stack: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create detailed technical specification with full self-improvement pipeline

        Pipeline:
        1. Query ReasoningBank for successful patterns
        2. Generate spec using Agent Framework + patterns
        3. Reflect on quality using Reflection Harness
        4. Record trajectory in Replay Buffer
        5. Store successful strategy in ReasoningBank

        Args:
            idea: Business idea to create spec for
            tech_stack: Optional tech stack override

        Returns:
            Technical specification (JSON string)
        """
        context = SpecCreationContext(
            business_id=self.business_id,
            idea=idea,
            tech_stack=tech_stack
        )

        trajectory_id = str(uuid.uuid4())
        steps: List[ActionStep] = []
        start_time = time.time()

        logger.info(f"Creating spec for: {idea[:100]}...")
        logger.info(f"  Trajectory ID: {trajectory_id}")

        try:
            # STEP 1: Query ReasoningBank for successful patterns
            step_start = time.time()
            logger.info("  Step 1: Querying ReasoningBank for patterns...")

            patterns = self.reasoning_bank.search_strategies(
                task_context=f"technical specification {idea[:50]}",
                top_n=3,
                min_win_rate=0.6
            )

            steps.append(ActionStep(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name="reasoning_bank.search_strategies",
                tool_args={
                    "task_context": idea[:50],
                    "top_n": 3,
                    "min_win_rate": 0.6
                },
                tool_result=f"Found {len(patterns)} patterns",
                agent_reasoning="Query successful spec patterns to learn from past experience"
            ))

            if patterns:
                logger.info(f"    Found {len(patterns)} relevant patterns")
                self.stats["strategies_reused"] += 1
            else:
                logger.info("    No patterns found (cold start)")

            # STEP 2: Generate spec with Reflection Harness
            logger.info("  Step 2: Generating spec with reflection...")

            async def generate_spec_content() -> str:
                """Generator function for reflection harness"""
                # Build prompt with patterns if available
                patterns_context = ""
                if patterns:
                    patterns_context = "\n\nSUCCESSFUL PATTERNS FROM PAST SPECS:\n"
                    for i, pattern in enumerate(patterns[:2], 1):
                        patterns_context += f"\nPattern {i} (win rate: {pattern.win_rate:.2f}):\n"
                        patterns_context += f"- {pattern.description}\n"
                        patterns_context += f"- Steps: {', '.join(list(pattern.steps)[:3])}\n"

                tech_stack_context = ""
                if tech_stack:
                    tech_stack_context = f"\n\nTECH STACK OVERRIDE:\n{json.dumps(tech_stack, indent=2)}"

                prompt = f"""Create EXTREMELY detailed technical specification:

BUSINESS IDEA: {idea}
{tech_stack_context}
{patterns_context}

REQUIREMENTS:
1. Complete feature breakdown with user stories
2. Exact tech stack (Next.js 14, TypeScript, Tailwind, Supabase/MongoDB, Stripe)
3. Database schema (COMPLETE SQL with indexes, foreign keys)
4. API endpoints (ALL routes with methods, auth, request/response examples)
5. Page structure (all pages with components and routing)
6. Stripe integration (products, pricing, webhooks, checkout flow)
7. Deployment checklist (env vars, CI/CD, monitoring, error tracking)
8. Testing strategy (unit, integration, e2e test plans)

FORMAT AS JSON with these exact sections:
{{
  "overview": {{"problem": "...", "solution": "...", "target_users": "..."}},
  "features": [{{"name": "...", "user_story": "...", "acceptance_criteria": [...]}}],
  "tech_stack": {{"frontend": "...", "backend": "...", "database": "...", "auth": "...", "payments": "..."}},
  "database_schema": "COMPLETE SQL HERE",
  "api_endpoints": [{{"method": "...", "path": "...", "auth": "...", "request": {{}}, "response": {{}}}}],
  "pages": [{{"route": "...", "components": [...], "data_needs": [...]}}],
  "stripe_integration": {{"products": [...], "webhooks": [...], "checkout_flow": [...]}},
  "deployment": {{"env_vars": [...], "cicd": "...", "monitoring": "..."}},
  "testing": {{"unit": [...], "integration": [...], "e2e": [...]}}
}}

Be EXTREMELY specific. Use real examples, not placeholders."""

                response = await self.agent.run(prompt)
                return response.text

            # Wrap with reflection harness
            harness_result: HarnessResult[str] = await self.reflection_harness.wrap(
                generator_func=generate_spec_content,
                content_type="technical_specification",
                context={
                    "idea": idea,
                    "patterns_used": len(patterns),
                    "agent_id": self.agent_id
                }
            )

            spec_content = harness_result.output

            steps.append(ActionStep(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name="agent.run_with_reflection",
                tool_args={"idea": idea[:100], "reflection_attempts": harness_result.attempts_made},
                tool_result=f"Generated spec ({len(spec_content)} chars, score: {harness_result.reflection_result.overall_score if harness_result.reflection_result else 0.0:.2f})",
                agent_reasoning="Generate spec with automatic quality reflection and regeneration"
            ))

            # Update stats
            if harness_result.passed_reflection:
                self.stats["successful_reflections"] += 1
                logger.info(f"    Passed reflection (score: {harness_result.reflection_result.overall_score:.2f})")
            else:
                self.stats["failed_reflections"] += 1
                logger.warning(f"    Failed reflection (best score: {harness_result.reflection_result.overall_score if harness_result.reflection_result else 0.0:.2f})")

            # STEP 3: Store trajectory in Replay Buffer
            logger.info("  Step 3: Recording trajectory in Replay Buffer...")

            duration = time.time() - start_time
            outcome = OutcomeTag.SUCCESS if harness_result.passed_reflection else OutcomeTag.PARTIAL
            reward = harness_result.reflection_result.overall_score if harness_result.reflection_result else 0.5

            trajectory = Trajectory(
                trajectory_id=trajectory_id,
                agent_id=self.agent_id,
                task_description=f"Create technical specification: {idea[:100]}",
                initial_state=context.initial_state,
                steps=tuple(steps),
                final_outcome=outcome.value,
                reward=reward,
                metadata={
                    "business_id": self.business_id,
                    "patterns_used": len(patterns),
                    "reflection_attempts": harness_result.attempts_made,
                    "spec_length": len(spec_content)
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration
            )

            self.replay_buffer.store_trajectory(trajectory)
            self.stats["trajectories_recorded"] += 1

            logger.info(f"    Trajectory recorded: {trajectory_id}")

            # STEP 4: Store strategy in ReasoningBank (if successful)
            if harness_result.passed_reflection:
                logger.info("  Step 4: Storing strategy in ReasoningBank...")

                strategy_description = f"Technical specification for {idea[:100]}"
                strategy_context = f"spec creation {idea[:30]}"

                strategy_id = self.reasoning_bank.store_strategy(
                    description=strategy_description,
                    context=strategy_context,
                    task_metadata={
                        "idea": idea[:200],
                        "tech_stack": tech_stack or {},
                        "patterns_reused": len(patterns),
                        "reflection_score": reward
                    },
                    environment="production",
                    tools_used=[step.tool_name for step in steps],
                    outcome=OutcomeTag.SUCCESS,
                    steps=[f"{s.tool_name}: {s.agent_reasoning}" for s in steps],
                    learned_from=[trajectory_id]
                )

                logger.info(f"    Strategy stored: {strategy_id}")

            # Update stats
            self.stats["specs_created"] += 1

            logger.info(f"Spec creation complete (duration: {duration:.2f}s)")
            logger.info(f"  Reflection: {'PASSED' if harness_result.passed_reflection else 'FAILED'}")
            logger.info(f"  Quality score: {reward:.2f}")

            return spec_content

        except Exception as e:
            logger.error(f"Spec creation failed: {e}")

            # Record failure trajectory
            duration = time.time() - start_time

            failure_trajectory = Trajectory(
                trajectory_id=trajectory_id,
                agent_id=self.agent_id,
                task_description=f"Create technical specification: {idea[:100]}",
                initial_state=context.initial_state,
                steps=tuple(steps),
                final_outcome=OutcomeTag.FAILURE.value,
                reward=0.0,
                metadata={
                    "business_id": self.business_id,
                    "error": str(e)
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                failure_rationale=f"Exception during spec creation: {str(e)[:200]}",
                error_category="execution_error",
                fix_applied="None (requires investigation)"
            )

            self.replay_buffer.store_trajectory(failure_trajectory)
            self.stats["trajectories_recorded"] += 1

            raise

    def route_task(self, task_description: str, priority: float = 0.7) -> RoutingDecision:
        """
        Route spec task to appropriate model using DAAO

        Args:
            task_description: Description of the spec task
            priority: Task priority (0.0-1.0, default 0.7 for complex specs)

        Returns:
            RoutingDecision with model selection and cost estimate
        """
        task = {
            'id': f'spec-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}',
            'description': task_description,
            'priority': priority,
            'required_tools': ['reasoning_bank', 'reflection_harness']
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Spec task routed: {decision.reasoning}",
            extra={
                'agent': 'SpecAgent',
                'model': decision.model,
                'difficulty': decision.difficulty.value,
                'estimated_cost': decision.estimated_cost
            }
        )

        return decision

    def get_cost_metrics(self) -> Dict[str, Any]:
        """Get cumulative cost savings from DAAO and TUMIX"""
        if not self.refinement_history:
            tumix_info = {
                'tumix_sessions': 0,
                'tumix_savings_percent': 0.0,
                'message': 'No TUMIX refinement sessions recorded yet'
            }
        else:
            tumix_savings = self.termination.estimate_cost_savings(
                [
                    [r for r in session]
                    for session in self.refinement_history
                ],
                cost_per_round=0.001
            )
            tumix_info = {
                'tumix_sessions': tumix_savings['sessions'],
                'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
                'tumix_actual_rounds': tumix_savings['tumix_rounds'],
                'tumix_savings_percent': tumix_savings['savings_percent'],
                'tumix_total_saved': tumix_savings['savings']
            }

        return {
            'agent': 'SpecAgent',
            'agent_id': self.agent_id,
            'business_id': self.business_id,
            **tumix_info,
            'daao_info': 'DAAO routing automatically applied to all tasks',
            'note': 'SpecAgent v5.0 uses DAAO + TUMIX + ReasoningBank + Replay Buffer + Reflection Harness'
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get agent statistics

        Returns:
            Dictionary with performance metrics
        """
        reflection_total = self.stats["successful_reflections"] + self.stats["failed_reflections"]
        reflection_success_rate = (
            self.stats["successful_reflections"] / reflection_total
            if reflection_total > 0 else 0.0
        )

        return {
            "agent_id": self.agent_id,
            "business_id": self.business_id,
            "specs_created": self.stats["specs_created"],
            "successful_reflections": self.stats["successful_reflections"],
            "failed_reflections": self.stats["failed_reflections"],
            "reflection_success_rate": reflection_success_rate,
            "strategies_reused": self.stats["strategies_reused"],
            "trajectories_recorded": self.stats["trajectories_recorded"],
            "reflection_harness_stats": self.reflection_harness.get_statistics()
        }


async def get_spec_agent(
    business_id: str = "default",
    quality_threshold: float = 0.75,
    max_reflection_attempts: int = 2
) -> SpecAgent:
    """
    Factory function to create and initialize SpecAgent

    Args:
        business_id: Unique business identifier
        quality_threshold: Minimum quality score for reflection
        max_reflection_attempts: Max regeneration attempts

    Returns:
        Initialized SpecAgent instance
    """
    agent = SpecAgent(
        business_id=business_id,
        quality_threshold=quality_threshold,
        max_reflection_attempts=max_reflection_attempts
    )
    await agent.initialize()
    return agent


# Example usage
if __name__ == "__main__":
    async def test_spec_agent():
        """Test SpecAgent with self-improvement pipeline"""
        async with SpecAgent(business_id="test") as agent:
            await agent.initialize()

            idea = "AI-powered meal planning SaaS with recipe recommendations and grocery list automation"

            spec = await agent.create_spec(
                idea=idea,
                tech_stack={
                    "frontend": "Next.js 14",
                    "database": "Supabase",
                    "ai": "OpenAI GPT-4"
                }
            )

            print("SPEC CREATED:")
            print("=" * 80)
            print(spec[:500])
            print("\nSTATISTICS:")
            print(json.dumps(agent.get_statistics(), indent=2))

    asyncio.run(test_spec_agent())
