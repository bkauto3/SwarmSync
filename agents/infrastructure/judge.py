"""
Agent-as-a-Judge Pattern for Genesis Self-Improvement
Implements CMP (Coherent Multi-Perspective) scoring for code evaluation

Based on:
- HGM (arXiv:2510.21614): Hypothesis-Guided Multi-Agent with tree search
- Agent-as-a-Judge pattern: LLM-based evaluation with multi-perspective coherence
- Replaces fitness functions with CMP metric for better code quality assessment

Key Features:
- Multi-dimensional code evaluation (correctness, completeness, efficiency, safety)
- Coherent Multi-Perspective (CMP) scoring across evaluation dimensions
- Batch evaluation for efficient parallel scoring
- Integration with CaseBank for historical learning
- Production-ready with GPT-4o/Claude Sonnet 4 as judge LLMs

Architecture:
1. Judge LLM evaluates code across 4 dimensions
2. CMP metric aggregates scores with coherence penalty
3. Results stored to CaseBank for future reference
4. Batch processing for efficiency at scale
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Genesis infrastructure
from infrastructure import get_logger
from infrastructure.llm_client import LLMClient, LLMFactory, LLMProvider
from infrastructure.casebank import CaseBank, get_casebank

# OTEL observability
try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    tracer = None

logger = get_logger(__name__)


class EvaluationDimension(str, Enum):
    """Evaluation dimensions for code quality assessment"""
    CORRECTNESS = "correctness"  # Does the code solve the problem correctly?
    COMPLETENESS = "completeness"  # Are all requirements addressed?
    EFFICIENCY = "efficiency"  # Is the implementation efficient?
    SAFETY = "safety"  # Is the code safe and secure?


@dataclass
class JudgeScore:
    """
    Individual judge score with multi-dimensional evaluation

    Attributes:
        score: Overall score 0-100
        reasoning: Detailed explanation of the score
        dimensions: Scores per evaluation dimension
        timestamp: When the evaluation was performed
        judge_model: Which LLM was used as judge
        metadata: Additional context
    """
    score: float  # 0-100
    reasoning: str
    dimensions: Dict[EvaluationDimension, float]  # Each dimension 0-100
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    judge_model: str = "gpt-4o"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "score": self.score,
            "reasoning": self.reasoning,
            "dimensions": {dim.value: score for dim, score in self.dimensions.items()},
            "timestamp": self.timestamp.isoformat(),
            "judge_model": self.judge_model,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JudgeScore':
        """Create from dictionary"""
        return cls(
            score=data["score"],
            reasoning=data["reasoning"],
            dimensions={
                EvaluationDimension(dim): score
                for dim, score in data["dimensions"].items()
            },
            timestamp=datetime.fromisoformat(data["timestamp"]),
            judge_model=data.get("judge_model", "gpt-4o"),
            metadata=data.get("metadata", {})
        )


@dataclass
class CMPScore:
    """
    Coherent Multi-Perspective (CMP) score aggregating multiple judge scores

    CMP = mean(scores) - coherence_penalty

    Coherence penalty increases when dimension scores are inconsistent
    (e.g., high correctness but low safety is penalized)
    """
    mean_score: float
    coherence_penalty: float
    cmp_score: float
    judge_scores: List[JudgeScore]
    dimension_variance: Dict[EvaluationDimension, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "mean_score": self.mean_score,
            "coherence_penalty": self.coherence_penalty,
            "cmp_score": self.cmp_score,
            "judge_scores": [js.to_dict() for js in self.judge_scores],
            "dimension_variance": {
                dim.value: var for dim, var in self.dimension_variance.items()
            }
        }


class AgentJudge:
    """
    Agent-as-a-Judge pattern for code evaluation

    Uses LLM (GPT-4o or Claude Sonnet 4) to evaluate code across multiple dimensions:
    - Correctness: Does it solve the problem?
    - Completeness: Are all requirements met?
    - Efficiency: Is it optimized?
    - Safety: Is it secure and robust?

    Implements CMP (Coherent Multi-Perspective) scoring for better evaluation.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        casebank: Optional[CaseBank] = None,
        judge_model: str = "gpt-4o",
        coherence_weight: float = 0.15
    ):
        """
        Initialize Agent-as-a-Judge

        Args:
            llm_client: LLM client for judge evaluations
            casebank: CaseBank for storing evaluation history
            judge_model: Which model to use as judge (gpt-4o or claude-sonnet-4)
            coherence_weight: Weight for coherence penalty in CMP (default 0.15)
        """
        # Get LLM client (create if not provided)
        if llm_client is None:
            try:
                from anthropic import Anthropic
                import os
                llm_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            except Exception as e:
                logger.warning(f"Could not initialize LLM client: {e}")
                llm_client = None

        self.llm_client = llm_client
        self.casebank = casebank or get_casebank()
        self.judge_model = judge_model
        self.coherence_weight = coherence_weight

        logger.info(
            f"AgentJudge initialized with model={judge_model}, "
            f"coherence_weight={coherence_weight}"
        )

    async def score_output(
        self,
        output: str,
        criteria: str,
        context: Optional[Dict[str, Any]] = None
    ) -> JudgeScore:
        """
        Score a single output using judge LLM

        Args:
            output: Code or text to evaluate
            criteria: Evaluation criteria/task description
            context: Additional context (test results, benchmark data, etc.)

        Returns:
            JudgeScore with multi-dimensional evaluation
        """
        span_name = "agent_judge.score_output" if OTEL_AVAILABLE else None
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("judge.model", self.judge_model)
                span.set_attribute("output.length", len(output))
                return await self._score_output_impl(output, criteria, context)
        else:
            return await self._score_output_impl(output, criteria, context)

    async def _score_output_impl(
        self,
        output: str,
        criteria: str,
        context: Optional[Dict[str, Any]]
    ) -> JudgeScore:
        """Internal implementation of score_output"""
        context = context or {}

        # Build judge prompt with multi-dimensional evaluation
        prompt = self._build_judge_prompt(output, criteria, context)

        # Query judge LLM
        start_time = time.time()
        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=self.judge_model,
                temperature=0.3,  # Low temperature for consistent evaluation
                response_format={"type": "json_object"}
            )

            eval_time = time.time() - start_time

            # Parse response
            result = json.loads(response)

            # Extract scores
            dimensions = {
                EvaluationDimension.CORRECTNESS: result.get("correctness_score", 0.0),
                EvaluationDimension.COMPLETENESS: result.get("completeness_score", 0.0),
                EvaluationDimension.EFFICIENCY: result.get("efficiency_score", 0.0),
                EvaluationDimension.SAFETY: result.get("safety_score", 0.0)
            }

            # Calculate overall score as weighted average
            overall_score = sum(dimensions.values()) / len(dimensions)

            judge_score = JudgeScore(
                score=overall_score,
                reasoning=result.get("reasoning", ""),
                dimensions=dimensions,
                judge_model=self.judge_model,
                metadata={
                    "eval_time": eval_time,
                    "criteria": criteria,
                    "context_keys": list(context.keys())
                }
            )

            logger.info(
                f"Judge score: {overall_score:.1f} "
                f"(C:{dimensions[EvaluationDimension.CORRECTNESS]:.1f}, "
                f"Cm:{dimensions[EvaluationDimension.COMPLETENESS]:.1f}, "
                f"E:{dimensions[EvaluationDimension.EFFICIENCY]:.1f}, "
                f"S:{dimensions[EvaluationDimension.SAFETY]:.1f}) "
                f"in {eval_time:.2f}s"
            )

            return judge_score

        except Exception as e:
            logger.error(f"Judge evaluation failed: {e}", exc_info=True)
            # Return zero score on error
            return JudgeScore(
                score=0.0,
                reasoning=f"Evaluation failed: {str(e)}",
                dimensions={dim: 0.0 for dim in EvaluationDimension},
                judge_model=self.judge_model,
                metadata={"error": str(e)}
            )

    def _build_judge_prompt(
        self,
        output: str,
        criteria: str,
        context: Dict[str, Any]
    ) -> str:
        """Build evaluation prompt for judge LLM"""
        prompt = f"""You are an expert code reviewer evaluating agent-generated code.

TASK DESCRIPTION:
{criteria}

CODE TO EVALUATE:
```python
{output}
```

CONTEXT:
{json.dumps(context, indent=2)}

INSTRUCTIONS:
Evaluate the code across 4 dimensions, scoring each 0-100:

1. CORRECTNESS (0-100): Does the code correctly solve the stated problem?
   - Logical correctness
   - Edge case handling
   - Error-free execution

2. COMPLETENESS (0-100): Are all requirements addressed?
   - All features implemented
   - Documentation complete
   - Test coverage adequate

3. EFFICIENCY (0-100): Is the implementation efficient?
   - Time complexity reasonable
   - Memory usage optimized
   - No obvious performance issues

4. SAFETY (0-100): Is the code safe and secure?
   - No security vulnerabilities
   - Proper error handling
   - Safe resource management

Respond in JSON format:
{{
    "correctness_score": <0-100>,
    "completeness_score": <0-100>,
    "efficiency_score": <0-100>,
    "safety_score": <0-100>,
    "reasoning": "<detailed explanation of scores>"
}}

Be thorough but concise. Focus on objective criteria."""

        return prompt

    async def batch_score(
        self,
        outputs: List[Tuple[str, str, Optional[Dict[str, Any]]]]
    ) -> List[JudgeScore]:
        """
        Score multiple outputs in batch

        Args:
            outputs: List of (output, criteria, context) tuples

        Returns:
            List of JudgeScores in same order as inputs
        """
        tasks = [
            self.score_output(output, criteria, context)
            for output, criteria, context in outputs
        ]

        return await asyncio.gather(*tasks)

    def calculate_cmp_score(
        self,
        judge_scores: List[JudgeScore]
    ) -> CMPScore:
        """
        Calculate Coherent Multi-Perspective (CMP) score

        CMP = mean(scores) - coherence_penalty

        Coherence penalty increases when dimension scores are inconsistent
        across different evaluations of the same code.

        Args:
            judge_scores: List of judge scores for the same code

        Returns:
            CMPScore with aggregated evaluation
        """
        if not judge_scores:
            return CMPScore(
                mean_score=0.0,
                coherence_penalty=0.0,
                cmp_score=0.0,
                judge_scores=[],
                dimension_variance={}
            )

        # Calculate mean score
        mean_score = sum(js.score for js in judge_scores) / len(judge_scores)

        # Calculate variance per dimension
        dimension_variance = {}
        for dim in EvaluationDimension:
            dim_scores = [js.dimensions[dim] for js in judge_scores]
            if len(dim_scores) > 1:
                variance = sum((s - mean_score) ** 2 for s in dim_scores) / len(dim_scores)
            else:
                variance = 0.0
            dimension_variance[dim] = variance

        # Coherence penalty = weighted sum of variances
        total_variance = sum(dimension_variance.values())
        coherence_penalty = self.coherence_weight * total_variance

        # CMP score
        cmp_score = max(0.0, mean_score - coherence_penalty)

        logger.debug(
            f"CMP score: {cmp_score:.1f} "
            f"(mean={mean_score:.1f}, penalty={coherence_penalty:.1f})"
        )

        return CMPScore(
            mean_score=mean_score,
            coherence_penalty=coherence_penalty,
            cmp_score=cmp_score,
            judge_scores=judge_scores,
            dimension_variance=dimension_variance
        )

    async def store_to_casebank(
        self,
        score: JudgeScore,
        output: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Store evaluation to CaseBank for future reference

        Args:
            score: Judge score to store
            output: Code that was evaluated
            context: Evaluation context
        """
        # Generate unique ID for this evaluation
        eval_id = hashlib.sha256(
            f"{output}{context.get('criteria', '')}{score.timestamp}".encode()
        ).hexdigest()[:16]

        # Store to CaseBank
        case_data = {
            "eval_id": eval_id,
            "score": score.to_dict(),
            "output": output,
            "context": context,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            await self.casebank.store_case(
                case_id=eval_id,
                case_data=case_data,
                tags=["judge_evaluation", score.judge_model]
            )
            logger.debug(f"Stored evaluation {eval_id} to CaseBank")
        except Exception as e:
            logger.error(f"Failed to store to CaseBank: {e}", exc_info=True)


# Singleton instance
_agent_judge: Optional[AgentJudge] = None


def get_agent_judge(
    llm_client: Optional[LLMClient] = None,
    casebank: Optional[CaseBank] = None,
    judge_model: str = "gpt-4o",
    coherence_weight: float = 0.15
) -> AgentJudge:
    """
    Get or create singleton AgentJudge instance

    Args:
        llm_client: LLM client for judge evaluations (defaults to GPT-4o)
        casebank: CaseBank for storing evaluation history
        judge_model: Which model to use as judge
        coherence_weight: Weight for coherence penalty in CMP

    Returns:
        AgentJudge instance
    """
    global _agent_judge
    if _agent_judge is None:
        # Create default LLM client if not provided
        if llm_client is None:
            if judge_model == "gpt-4o":
                llm_client = LLMFactory.create(LLMProvider.GPT4O)
            elif judge_model == "claude-sonnet-4":
                llm_client = LLMFactory.create(LLMProvider.CLAUDE_SONNET_4)
            else:
                llm_client = LLMFactory.create(LLMProvider.GPT4O)

        _agent_judge = AgentJudge(
            llm_client=llm_client,
            casebank=casebank,
            judge_model=judge_model,
            coherence_weight=coherence_weight
        )
    return _agent_judge
