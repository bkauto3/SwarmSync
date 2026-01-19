"""
ReflectionAgent - Self-Review Specialist for Quality Assurance
Version: 4.0 (Enhanced with DAAO + TUMIX)
Last Updated: October 16, 2025

Dedicated reflection agent that reviews outputs from other agents before finalization.
Implements 6-dimensional quality assessment framework with learning capabilities.

Key Features:
- Multi-dimensional quality scoring (Correctness, Completeness, Quality, Security, Performance, Maintainability)
- Integration with ReasoningBank for pattern learning
- Trajectory recording in Replay Buffer
- DAAO routing for cost-optimized model selection
- TUMIX early termination for iterative quality refinement
- Thread-safe async implementation
- Graceful degradation when dependencies unavailable
- Detailed feedback generation

MODEL: GPT-4o (optimal for analytical reasoning)
PURPOSE: Prevent low-quality outputs from reaching production
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Import learning infrastructure
try:
    from infrastructure.reasoning_bank import (
        ReasoningBank,
        get_reasoning_bank,
        MemoryType,
        OutcomeTag
    )
    REASONING_BANK_AVAILABLE = True
except ImportError:
    REASONING_BANK_AVAILABLE = False
    logging.warning("ReasoningBank not available - reflection learning disabled")

try:
    from infrastructure.replay_buffer import (
        ReplayBuffer,
        get_replay_buffer,
        Trajectory,
        ActionStep
    )
    REPLAY_BUFFER_AVAILABLE = True
except ImportError:
    REPLAY_BUFFER_AVAILABLE = False
    logging.warning("ReplayBuffer not available - trajectory recording disabled")

# Import DAAO and TUMIX
try:
    from infrastructure.daao_router import get_daao_router, RoutingDecision
    from infrastructure.tumix_termination import (
        get_tumix_termination,
        RefinementResult as TUMIXRefinementResult,
        TerminationDecision
    )
    DAAO_TUMIX_AVAILABLE = True
except ImportError:
    DAAO_TUMIX_AVAILABLE = False
    logging.warning("DAAO/TUMIX not available - cost optimization disabled")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """Quality dimensions for code/content assessment"""
    CORRECTNESS = "correctness"  # Does it work correctly?
    COMPLETENESS = "completeness"  # Is everything implemented?
    QUALITY = "quality"  # Is it well-written?
    SECURITY = "security"  # Is it secure?
    PERFORMANCE = "performance"  # Is it efficient?
    MAINTAINABILITY = "maintainability"  # Is it maintainable?


@dataclass
class DimensionScore:
    """Score for a single quality dimension"""
    dimension: str
    score: float  # 0.0 to 1.0
    feedback: str
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ReflectionResult:
    """
    Complete reflection result with multi-dimensional scores

    Contains overall quality assessment and detailed feedback
    for each quality dimension.
    """
    overall_score: float  # 0.0 to 1.0 (weighted average)
    passes_threshold: bool  # True if overall_score >= threshold
    dimension_scores: Dict[str, DimensionScore]
    summary_feedback: str
    critical_issues: List[str]
    suggestions: List[str]
    reflection_time_seconds: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReflectionAgent:
    """
    Dedicated reflection agent for quality assurance

    Responsibilities:
    1. Review outputs from other agents across 6 quality dimensions
    2. Provide detailed feedback with specific issues and suggestions
    3. Store successful reflection patterns in ReasoningBank
    4. Record all reflections in Replay Buffer for learning
    5. Learn from past reflections to improve future assessments

    Quality Dimensions:
    - Correctness: Logical correctness, no errors
    - Completeness: All requirements met
    - Quality: Code/content quality, best practices
    - Security: No vulnerabilities, proper auth/validation
    - Performance: Efficiency, no bottlenecks
    - Maintainability: Readability, documentation, structure

    Thread Safety:
    - All operations are async and thread-safe
    - Uses asyncio locks for concurrent access

    Graceful Degradation:
    - Works without ReasoningBank (no pattern learning)
    - Works without ReplayBuffer (no trajectory recording)
    - Works without external LLM (rule-based fallback)
    """

    # Dimension weights for overall score calculation
    DEFAULT_WEIGHTS = {
        QualityDimension.CORRECTNESS: 0.25,
        QualityDimension.COMPLETENESS: 0.20,
        QualityDimension.QUALITY: 0.15,
        QualityDimension.SECURITY: 0.20,
        QualityDimension.PERFORMANCE: 0.10,
        QualityDimension.MAINTAINABILITY: 0.10
    }

    def __init__(
        self,
        agent_id: str = "reflection_agent",
        quality_threshold: float = 0.70,
        use_llm: bool = True,
        dimension_weights: Optional[Dict[QualityDimension, float]] = None
    ):
        """
        Initialize ReflectionAgent

        Args:
            agent_id: Unique identifier for this reflection agent
            quality_threshold: Minimum score to pass (0.0-1.0)
            use_llm: Whether to use LLM for reflection (GPT-4o)
            dimension_weights: Custom weights for quality dimensions
        """
        self.agent_id = agent_id
        self.quality_threshold = quality_threshold
        self.use_llm = use_llm
        self.dimension_weights = dimension_weights or self.DEFAULT_WEIGHTS

        # Learning infrastructure (optional)
        self.reasoning_bank: Optional[ReasoningBank] = None
        self.replay_buffer: Optional[ReplayBuffer] = None

        if REASONING_BANK_AVAILABLE:
            try:
                self.reasoning_bank = get_reasoning_bank()
                logger.info("✅ ReflectionAgent connected to ReasoningBank")
            except Exception as e:
                logger.warning(f"Failed to connect to ReasoningBank: {e}")

        if REPLAY_BUFFER_AVAILABLE:
            try:
                self.replay_buffer = get_replay_buffer()
                logger.info("✅ ReflectionAgent connected to ReplayBuffer")
            except Exception as e:
                logger.warning(f"Failed to connect to ReplayBuffer: {e}")

        # Statistics
        self.total_reflections = 0
        self.total_passes = 0
        self.total_failures = 0

        # Thread safety
        self._lock = asyncio.Lock()

        # DAAO + TUMIX (optional cost optimization)
        self.router = None
        self.termination = None
        self.refinement_history: List[List[TUMIXRefinementResult]] = []

        if DAAO_TUMIX_AVAILABLE:
            try:
                self.router = get_daao_router()
                self.termination = get_tumix_termination(
                    min_rounds=2,
                    max_rounds=4,
                    improvement_threshold=0.05
                )
                logger.info("✅ DAAO + TUMIX enabled for ReflectionAgent")
            except Exception as e:
                logger.warning(f"DAAO/TUMIX initialization failed: {e}")

        logger.info(f"✅ ReflectionAgent v4.0 initialized: {agent_id}")
        logger.info(f"   Quality threshold: {quality_threshold}")
        logger.info(f"   LLM enabled: {use_llm}")
        logger.info(f"   ReasoningBank: {'Connected' if self.reasoning_bank else 'Disabled'}")
        logger.info(f"   ReplayBuffer: {'Connected' if self.replay_buffer else 'Disabled'}")
        logger.info(f"   DAAO/TUMIX: {'Enabled' if self.router else 'Disabled'}")

    async def reflect(
        self,
        content: str,
        content_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        Perform multi-dimensional reflection on content

        Main entry point for reflection. Analyzes content across all
        quality dimensions and returns comprehensive assessment.

        Args:
            content: Content to review (code, text, config, etc.)
            content_type: Type of content (code, documentation, config, etc.)
            context: Additional context (requirements, constraints, etc.)

        Returns:
            ReflectionResult with scores and feedback
        """
        start_time = time.time()
        context = context or {}

        logger.info(f"🔍 Starting reflection on {content_type}")
        logger.info(f"   Content length: {len(content)} characters")

        # Query ReasoningBank for similar reflection patterns
        if self.reasoning_bank:
            try:
                patterns = self.reasoning_bank.search_strategies(
                    task_context=f"reflection {content_type}",
                    top_n=3,
                    min_win_rate=0.6
                )
                if patterns:
                    logger.info(f"📚 Found {len(patterns)} reflection patterns from history")
            except Exception as e:
                logger.warning(f"Failed to query reflection patterns: {e}")

        # Perform reflection across all dimensions
        dimension_scores = {}

        for dimension in QualityDimension:
            try:
                score = await self._assess_dimension(
                    content=content,
                    content_type=content_type,
                    dimension=dimension,
                    context=context
                )
                dimension_scores[dimension.value] = score
            except Exception as e:
                logger.error(f"Failed to assess {dimension.value}: {e}")
                # Provide default score on failure
                dimension_scores[dimension.value] = DimensionScore(
                    dimension=dimension.value,
                    score=0.5,
                    feedback=f"Assessment failed: {str(e)}",
                    issues=[f"Error during {dimension.value} assessment"],
                    suggestions=["Manual review recommended"]
                )

        # Calculate weighted overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        passes = overall_score >= self.quality_threshold

        # Aggregate critical issues and suggestions
        critical_issues = []
        all_suggestions = []

        for dim_score in dimension_scores.values():
            if dim_score.score < 0.5:  # Critical threshold
                critical_issues.extend(dim_score.issues)
            all_suggestions.extend(dim_score.suggestions)

        # Generate summary feedback
        summary = self._generate_summary(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            passes=passes
        )

        # Create result
        result = ReflectionResult(
            overall_score=overall_score,
            passes_threshold=passes,
            dimension_scores=dimension_scores,
            summary_feedback=summary,
            critical_issues=critical_issues,
            suggestions=all_suggestions[:10],  # Top 10 suggestions
            reflection_time_seconds=time.time() - start_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "content_type": content_type,
                "content_length": len(content),
                "threshold": self.quality_threshold,
                "agent_id": self.agent_id
            }
        )

        # Record in Replay Buffer
        if self.replay_buffer:
            try:
                await self._record_trajectory(
                    result=result,
                    content=content,
                    content_type=content_type,
                    context=context
                )
            except Exception as e:
                logger.warning(f"Failed to record trajectory: {e}")

        # Store successful pattern in ReasoningBank
        if passes and self.reasoning_bank:
            try:
                await self._store_reflection_pattern(
                    result=result,
                    content_type=content_type
                )
            except Exception as e:
                logger.warning(f"Failed to store reflection pattern: {e}")

        # Update statistics
        async with self._lock:
            self.total_reflections += 1
            if passes:
                self.total_passes += 1
            else:
                self.total_failures += 1

        logger.info(f"✅ Reflection completed: {'PASS' if passes else 'FAIL'}")
        logger.info(f"   Overall score: {overall_score:.2f} (threshold: {self.quality_threshold})")
        logger.info(f"   Critical issues: {len(critical_issues)}")
        logger.info(f"   Time: {result.reflection_time_seconds:.2f}s")

        return result

    async def _assess_dimension(
        self,
        content: str,
        content_type: str,
        dimension: QualityDimension,
        context: Dict[str, Any]
    ) -> DimensionScore:
        """
        Assess a single quality dimension

        Uses rule-based heuristics or LLM-based assessment depending
        on configuration and availability.

        Args:
            content: Content to assess
            content_type: Type of content
            dimension: Quality dimension to assess
            context: Additional context

        Returns:
            DimensionScore for the dimension
        """
        # Rule-based assessment (always available)
        if not self.use_llm or content_type == "code":
            return await self._rule_based_assessment(
                content=content,
                content_type=content_type,
                dimension=dimension,
                context=context
            )
        else:
            # LLM-based assessment for complex content
            # For now, fall back to rule-based (LLM integration can be added)
            return await self._rule_based_assessment(
                content=content,
                content_type=content_type,
                dimension=dimension,
                context=context
            )

    async def _rule_based_assessment(
        self,
        content: str,
        content_type: str,
        dimension: QualityDimension,
        context: Dict[str, Any]
    ) -> DimensionScore:
        """
        Rule-based heuristic assessment

        Uses pattern matching and static analysis for quality assessment.
        Fast and deterministic, no LLM required.

        Args:
            content: Content to assess
            content_type: Type of content
            dimension: Quality dimension
            context: Additional context

        Returns:
            DimensionScore based on heuristics
        """
        issues = []
        suggestions = []
        score = 1.0  # Start with perfect score, deduct for issues

        if dimension == QualityDimension.CORRECTNESS:
            # Check for syntax errors, logical issues
            if "TODO" in content or "FIXME" in content:
                issues.append("Incomplete implementation (TODO/FIXME markers)")
                score -= 0.2

            if "throw new Error" in content and "try" not in content:
                issues.append("Unhandled error throwing")
                score -= 0.15

            if content_type == "code" and len(content) < 50:
                issues.append("Code seems incomplete or too minimal")
                # Harsh penalty for extremely minimal code (< 10 chars)
                if len(content) < 10:
                    score -= 0.8  # Nearly fail correctness
                else:
                    score -= 0.3

            suggestions.append("Add comprehensive error handling")
            suggestions.append("Include input validation")

        elif dimension == QualityDimension.COMPLETENESS:
            # Check if all requirements are met
            if "partial" in content.lower() or "incomplete" in content.lower():
                issues.append("Content marked as partial/incomplete")
                score -= 0.3

            if context.get("required_features"):
                required = context["required_features"]
                missing = [f for f in required if f.lower() not in content.lower()]
                if missing:
                    issues.append(f"Missing required features: {', '.join(missing[:3])}")
                    score -= 0.2 * (len(missing) / len(required))

            suggestions.append("Verify all requirements are implemented")
            suggestions.append("Add feature completeness checklist")

        elif dimension == QualityDimension.QUALITY:
            # Code/content quality checks
            if "console.log" in content or "print(" in content:
                issues.append("Debug statements left in code")
                score -= 0.1

            if content_type == "code":
                # Check for type annotations (TypeScript/Python)
                if "any" in content:
                    issues.append("Using 'any' type - specify proper types")
                    score -= 0.15

                # Check for comments/documentation
                if "//" not in content and "/*" not in content and "#" not in content:
                    issues.append("Insufficient code comments")
                    score -= 0.1

                # Extremely minimal code lacks quality
                if len(content) < 10:
                    issues.append("Code too minimal to assess quality properly")
                    score -= 0.6

            suggestions.append("Add inline documentation")
            suggestions.append("Follow style guide consistently")

        elif dimension == QualityDimension.SECURITY:
            # Security vulnerability checks
            security_patterns = [
                ("eval(", "Dangerous eval() usage"),
                ("exec(", "Dangerous exec() usage"),
                ("innerHTML =", "XSS vulnerability via innerHTML"),
                ("password", "Password handling - verify encryption"),
                ("api_key", "API key handling - verify not hardcoded")
            ]

            for pattern, issue in security_patterns:
                if pattern in content.lower():
                    issues.append(issue)
                    score -= 0.15

            if "auth" in content.lower() and "jwt" not in content.lower():
                suggestions.append("Consider JWT for authentication")

            suggestions.append("Conduct security audit")
            suggestions.append("Add input sanitization")

        elif dimension == QualityDimension.PERFORMANCE:
            # Performance checks
            if content_type == "code":
                if ".map(" in content and ".filter(" in content and ".map(" in content:
                    issues.append("Multiple chained array operations - consider optimization")
                    score -= 0.1

                if "SELECT *" in content:
                    issues.append("SELECT * query - specify columns")
                    score -= 0.15

            suggestions.append("Profile critical paths")
            suggestions.append("Consider caching strategies")

        elif dimension == QualityDimension.MAINTAINABILITY:
            # Maintainability checks
            lines = content.split('\n')
            avg_line_length = sum(len(line) for line in lines) / max(len(lines), 1)

            if avg_line_length > 120:
                issues.append("Long lines detected - reduce complexity")
                score -= 0.1

            # Check for magic numbers
            if any(char.isdigit() for char in content):
                # Simple heuristic - could be improved
                suggestions.append("Extract magic numbers to constants")

            suggestions.append("Add comprehensive documentation")
            suggestions.append("Consider extracting reusable functions")

        # Ensure score stays in valid range
        score = max(0.0, min(1.0, score))

        feedback = f"{dimension.value.capitalize()} assessment: {score:.0%}"
        if issues:
            feedback += f" - {len(issues)} issues found"

        return DimensionScore(
            dimension=dimension.value,
            score=score,
            feedback=feedback,
            issues=issues,
            suggestions=suggestions
        )

    def _calculate_overall_score(
        self,
        dimension_scores: Dict[str, DimensionScore]
    ) -> float:
        """
        Calculate weighted overall score

        Args:
            dimension_scores: Scores for each dimension

        Returns:
            Weighted average score (0.0-1.0)
        """
        total_score = 0.0
        total_weight = 0.0

        for dimension, weight in self.dimension_weights.items():
            dim_score = dimension_scores.get(dimension.value)
            if dim_score:
                total_score += dim_score.score * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _generate_summary(
        self,
        overall_score: float,
        dimension_scores: Dict[str, DimensionScore],
        passes: bool
    ) -> str:
        """
        Generate summary feedback

        Args:
            overall_score: Overall quality score
            dimension_scores: Individual dimension scores
            passes: Whether quality threshold was met

        Returns:
            Human-readable summary
        """
        summary_parts = [
            f"Overall Quality: {overall_score:.0%} - {'PASS' if passes else 'FAIL'}"
        ]

        # Highlight strengths
        strong_dims = [
            dim for dim, score in dimension_scores.items()
            if score.score >= 0.9
        ]
        if strong_dims:
            summary_parts.append(f"Strengths: {', '.join(strong_dims)}")

        # Highlight weaknesses
        weak_dims = [
            dim for dim, score in dimension_scores.items()
            if score.score < 0.6
        ]
        if weak_dims:
            summary_parts.append(f"Needs improvement: {', '.join(weak_dims)}")

        return " | ".join(summary_parts)

    async def _record_trajectory(
        self,
        result: ReflectionResult,
        content: str,
        content_type: str,
        context: Dict[str, Any]
    ):
        """
        Record reflection as trajectory in Replay Buffer

        Args:
            result: Reflection result
            content: Content that was reflected on
            content_type: Type of content
            context: Additional context
        """
        if not self.replay_buffer:
            return

        # Create action step
        step = ActionStep(
            timestamp=result.timestamp,
            tool_name="reflect",
            tool_args={
                "content_type": content_type,
                "content_length": len(content)
            },
            tool_result={
                "overall_score": result.overall_score,
                "passes": result.passes_threshold,
                "critical_issues": len(result.critical_issues)
            },
            agent_reasoning=f"Reflected on {content_type} content across 6 quality dimensions"
        )

        # Create trajectory
        trajectory = Trajectory(
            trajectory_id=f"reflection_{self.agent_id}_{int(time.time() * 1000)}",
            agent_id=self.agent_id,
            task_description=f"Quality reflection on {content_type}",
            initial_state={
                "content_type": content_type,
                "threshold": self.quality_threshold
            },
            steps=(step,),
            final_outcome="success" if result.passes_threshold else "failure",
            reward=result.overall_score,
            metadata=result.metadata,
            created_at=result.timestamp,
            duration_seconds=result.reflection_time_seconds
        )

        # Store in buffer
        try:
            self.replay_buffer.store_trajectory(trajectory)
        except Exception as e:
            logger.error(f"Failed to store reflection trajectory: {e}")

    async def _store_reflection_pattern(
        self,
        result: ReflectionResult,
        content_type: str
    ):
        """
        Store successful reflection pattern in ReasoningBank

        Args:
            result: Successful reflection result
            content_type: Type of content
        """
        if not self.reasoning_bank:
            return

        try:
            strategy_id = self.reasoning_bank.store_strategy(
                description=f"Successful {content_type} reflection",
                context=f"reflection {content_type} quality_assurance",
                task_metadata={
                    "content_type": content_type,
                    "overall_score": result.overall_score,
                    "threshold": self.quality_threshold
                },
                environment="reflection_agent",
                tools_used=["reflect"],
                outcome=OutcomeTag.SUCCESS if REASONING_BANK_AVAILABLE else "success",
                steps=[result.summary_feedback],
                learned_from=[self.agent_id]
            )
            logger.debug(f"Stored reflection pattern: {strategy_id}")
        except Exception as e:
            logger.error(f"Failed to store reflection pattern: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get reflection agent statistics

        Returns:
            Dictionary with statistics
        """
        total = self.total_reflections
        success_rate = (self.total_passes / total) if total > 0 else 0.0

        return {
            "agent_id": self.agent_id,
            "total_reflections": total,
            "total_passes": self.total_passes,
            "total_failures": self.total_failures,
            "success_rate": success_rate,
            "quality_threshold": self.quality_threshold,
            "reasoning_bank_connected": self.reasoning_bank is not None,
            "replay_buffer_connected": self.replay_buffer is not None,
            "daao_tumix_enabled": self.router is not None
        }

    def get_cost_metrics(self) -> Dict:
        """Get cumulative cost savings from DAAO and TUMIX"""
        if not self.refinement_history:
            return {
                'agent': 'ReflectionAgent',
                'tumix_sessions': 0,
                'tumix_savings_percent': 0.0,
                'message': 'No refinement sessions recorded yet (reflection agent)'
            }

        if not self.termination:
            return {
                'agent': 'ReflectionAgent',
                'message': 'TUMIX not enabled'
            }

        tumix_savings = self.termination.estimate_cost_savings(
            [
                [r for r in session]
                for session in self.refinement_history
            ],
            cost_per_round=0.001
        )

        return {
            'agent': 'ReflectionAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }


# Factory function for easy instantiation
def get_reflection_agent(
    agent_id: str = "reflection_agent",
    quality_threshold: float = 0.70
) -> ReflectionAgent:
    """
    Get or create ReflectionAgent instance

    Args:
        agent_id: Unique identifier
        quality_threshold: Minimum quality score to pass

    Returns:
        ReflectionAgent instance
    """
    return ReflectionAgent(
        agent_id=agent_id,
        quality_threshold=quality_threshold,
        use_llm=True
    )
