"""
SE Evolution Operators - Multi-Trajectory Optimization
Part of SE-Darwin integration (Day 7)

Based on SE-Agent (arXiv 2508.02085): https://github.com/JARVIS-Xs/SE-Agent

Three core operators:
1. REVISION - Alternative strategies from failures
2. RECOMBINATION - Crossover of successful elements
3. REFINEMENT - Optimization of promising trajectories
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from infrastructure.trajectory_pool import Trajectory, TrajectoryPool, OperatorType
from infrastructure.security_utils import (
    sanitize_for_prompt,
    validate_generated_code
)

logger = logging.getLogger(__name__)


@dataclass
class OperatorResult:
    """Result from applying an evolution operator"""
    success: bool
    generated_code: Optional[str]
    strategy_description: str
    reasoning: str
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None


class BaseOperator:
    """Base class for evolution operators"""

    def __init__(self, llm_client=None):
        """
        Initialize operator

        Args:
            llm_client: LLM client for generating strategies (OpenAI, Anthropic, etc.)
        """
        self.llm_client = llm_client

    async def _call_llm(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> str:
        """
        Call LLM API

        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if self.llm_client is None:
            logger.warning("No LLM client configured, returning mock response")
            return "# Mock LLM response - configure llm_client for real generation"

        try:
            # Support different LLM clients
            if hasattr(self.llm_client, 'chat'):
                # OpenAI-style client
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return response.choices[0].message.content

            elif hasattr(self.llm_client, 'messages'):
                # Anthropic-style client
                response = await self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    system=system_prompt if system_prompt else None,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            else:
                logger.error(f"Unsupported LLM client type: {type(self.llm_client)}")
                return "# Error: Unsupported LLM client"

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return f"# Error calling LLM: {str(e)}"


class RevisionOperator(BaseOperator):
    """
    Generates alternative strategies from failed trajectories

    Based on SE-Agent's "alternative_strategy" operator.
    Analyzes failures and creates architecturally orthogonal approaches.
    """

    async def revise(
        self,
        failed_trajectory: Trajectory,
        problem_description: str
    ) -> OperatorResult:
        """
        Generate alternative strategy from failure

        Args:
            failed_trajectory: Failed trajectory to learn from
            problem_description: Original problem description

        Returns:
            OperatorResult with revised strategy
        """
        logger.info(f"Applying REVISION to trajectory {failed_trajectory.trajectory_id}")

        # Build context from failure
        failure_context = self._build_failure_context(failed_trajectory)

        # Generate alternative strategy
        system_prompt = """You are an expert software engineering strategist specializing in breakthrough problem-solving.

Your task is to generate a FUNDAMENTALLY DIFFERENT approach to a problem, based on analyzing a previous failed attempt.

Create a completely orthogonal strategy that:
1. Uses different investigation paradigms (e.g., runtime analysis vs static analysis)
2. Approaches from unconventional angles (e.g., user impact vs code structure)
3. Employs alternative tools and techniques
4. Follows different logical progression

CRITICAL: Your strategy must be architecturally dissimilar to avoid the same limitations and blind spots.

If the previous approach failed due to early termination or cost limits, prioritize:
- More focused, direct approaches
- Faster problem identification techniques
- Incremental validation methods
- Minimal viable change strategies"""

        # SECURITY FIX (ISSUE #3): Sanitize all user-controlled inputs
        safe_problem = sanitize_for_prompt(problem_description, max_length=500)
        safe_reasoning = sanitize_for_prompt(failed_trajectory.reasoning_pattern, max_length=200)
        safe_failures = sanitize_for_prompt(
            ', '.join(failed_trajectory.failure_reasons) if failed_trajectory.failure_reasons else 'Unknown',
            max_length=200
        )
        safe_code = sanitize_for_prompt(
            failed_trajectory.code_changes[:300] if failed_trajectory.code_changes else 'No code changes recorded',
            max_length=300
        )

        prompt = f"""Generate a radically different solution strategy:

PROBLEM:
{safe_problem}

PREVIOUS FAILED APPROACH:
Strategy: {safe_reasoning}
Tools Used: {', '.join(failed_trajectory.tools_used) if failed_trajectory.tools_used else 'None'}
Failure Reasons: {safe_failures}
Code Changes Attempted:
{safe_code}

Requirements for alternative strategy:
1. Adopt different investigation paradigm (e.g., empirical vs theoretical)
2. Start from alternative entry point (e.g., dependencies vs core logic)
3. Use non-linear logical sequence (e.g., symptom-to-cause vs cause-to-symptom)
4. Integrate unconventional techniques (e.g., profiling, fuzzing, visualization)
5. Prioritize overlooked aspects (e.g., performance, edge cases, integration)

Provide:
1. High-level strategy (2-3 sentences)
2. Key differences from failed approach (2-3 bullet points)
3. Concrete code improvements (Python code)

Format:
STRATEGY: [strategy description]
DIFFERENCES: [key differences]
CODE:
```python
[improved code]
```"""

        try:
            response = await self._call_llm(prompt, system_prompt, max_tokens=2000)

            # Parse response
            strategy, code = self._parse_llm_response(response)

            return OperatorResult(
                success=True,
                generated_code=code,
                strategy_description=strategy,
                reasoning=f"Revised failed trajectory {failed_trajectory.trajectory_id} with alternative approach"
            )

        except Exception as e:
            logger.error(f"Revision failed: {e}")
            return OperatorResult(
                success=False,
                generated_code=None,
                strategy_description="",
                reasoning="",
                error_message=str(e)
            )

    def _build_failure_context(self, trajectory: Trajectory) -> str:
        """Build context string from failed trajectory"""
        context_parts = [
            f"Trajectory ID: {trajectory.trajectory_id}",
            f"Generation: {trajectory.generation}",
            f"Success Score: {trajectory.success_score:.2f}",
            f"Reasoning Pattern: {trajectory.reasoning_pattern}",
        ]

        if trajectory.failure_reasons:
            context_parts.append(f"Failures: {', '.join(trajectory.failure_reasons)}")

        if trajectory.tools_used:
            context_parts.append(f"Tools: {', '.join(trajectory.tools_used)}")

        return "\n".join(context_parts)

    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        Parse LLM response into strategy and code

        SECURITY FIX (ISSUE #4): Validates generated code before returning
        """
        strategy = ""
        code = ""

        # Extract strategy
        if "STRATEGY:" in response:
            strategy_part = response.split("STRATEGY:")[1].split("DIFFERENCES:")[0] if "DIFFERENCES:" in response else response.split("STRATEGY:")[1].split("CODE:")[0]
            strategy = strategy_part.strip()

        # Extract code
        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            # Fallback: use entire response as code
            code = response

        # SECURITY FIX (ISSUE #4): Validate generated code
        is_valid, error = validate_generated_code(code)
        if not is_valid:
            logger.error(f"Code validation failed in RevisionOperator: {error}")
            code = f"# SECURITY: Code validation failed - {error}\n# Original code rejected for safety"

        return strategy, code


class RecombinationOperator(BaseOperator):
    """
    Combines strengths from multiple successful trajectories

    Based on SE-Agent's "crossover" operator.
    Creates synergistic hybrid strategies from successful elements.
    """

    async def recombine(
        self,
        trajectory_a: Trajectory,
        trajectory_b: Trajectory,
        problem_description: str
    ) -> OperatorResult:
        """
        Generate hybrid strategy from two trajectories

        Args:
            trajectory_a: First successful trajectory
            trajectory_b: Second successful trajectory
            problem_description: Original problem description

        Returns:
            OperatorResult with combined strategy
        """
        logger.info(f"Applying RECOMBINATION to trajectories {trajectory_a.trajectory_id} + {trajectory_b.trajectory_id}")

        system_prompt = """You are an expert software engineering strategy consultant specializing in synthesis and optimization.

Your task is to analyze two different approaches to a software engineering problem and create a SUPERIOR HYBRID strategy that combines their strengths while avoiding their weaknesses.

You will be given a problem and two different approaches that have been tried. Your job is to:
1. Identify the strengths and effective elements of each approach
2. Recognize common pitfalls or limitations shared by both approaches
3. Synthesize a new strategy that leverages the best aspects of both while addressing their shortcomings
4. Create an approach that is more robust and comprehensive than either individual strategy

CRITICAL: Your strategy should be a thoughtful synthesis, not just a simple combination. Focus on how the approaches can complement each other and cover each other's blind spots."""

        # SECURITY FIX (ISSUE #3): Sanitize all user-controlled inputs
        safe_problem = sanitize_for_prompt(problem_description, max_length=400)
        safe_reasoning_a = sanitize_for_prompt(trajectory_a.reasoning_pattern, max_length=200)
        safe_code_a = sanitize_for_prompt(
            trajectory_a.code_changes[:300] if trajectory_a.code_changes else 'No code recorded',
            max_length=300
        )
        safe_reasoning_b = sanitize_for_prompt(trajectory_b.reasoning_pattern, max_length=200)
        safe_code_b = sanitize_for_prompt(
            trajectory_b.code_changes[:300] if trajectory_b.code_changes else 'No code recorded',
            max_length=300
        )

        prompt = f"""Analyze these two approaches and create a superior hybrid strategy:

PROBLEM:
{safe_problem}

APPROACH 1 (Score: {trajectory_a.success_score:.2f}):
Strategy: {safe_reasoning_a}
Tools: {', '.join(trajectory_a.tools_used) if trajectory_a.tools_used else 'None'}
Key Insights: {', '.join(trajectory_a.key_insights) if trajectory_a.key_insights else 'None'}
Code Changes:
{safe_code_a}

APPROACH 2 (Score: {trajectory_b.success_score:.2f}):
Strategy: {safe_reasoning_b}
Tools: {', '.join(trajectory_b.tools_used) if trajectory_b.tools_used else 'None'}
Key Insights: {', '.join(trajectory_b.key_insights) if trajectory_b.key_insights else 'None'}
Code Changes:
{safe_code_b}

Create a crossover strategy that:
1. Combines the most effective elements from both approaches
2. Addresses the limitations observed in each approach
3. Covers blind spots that neither approach addressed individually
4. Provides a more comprehensive and robust solution methodology

Requirements for the hybrid strategy:
- Synthesize complementary strengths (if one excels at analysis and another at implementation, combine both)
- Mitigate shared weaknesses (if both rush to implementation, emphasize planning)
- Fill coverage gaps (if both focus on code but ignore testing, integrate testing)
- Create synergistic effects where the combination is more powerful than individual parts

Provide:
1. Hybrid strategy description (2-3 sentences)
2. How it combines strengths (2-3 bullet points)
3. Combined code improvements (Python code)

Format:
STRATEGY: [hybrid strategy]
STRENGTHS COMBINED: [how it's better]
CODE:
```python
[combined code]
```"""

        try:
            response = await self._call_llm(prompt, system_prompt, max_tokens=2000)

            strategy, code = self._parse_llm_response(response)

            return OperatorResult(
                success=True,
                generated_code=code,
                strategy_description=strategy,
                reasoning=f"Combined trajectories {trajectory_a.trajectory_id} + {trajectory_b.trajectory_id}"
            )

        except Exception as e:
            logger.error(f"Recombination failed: {e}")
            return OperatorResult(
                success=False,
                generated_code=None,
                strategy_description="",
                reasoning="",
                error_message=str(e)
            )

    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        Parse LLM response into strategy and code

        SECURITY FIX (ISSUE #4): Validates generated code before returning
        """
        strategy = ""
        code = ""

        if "STRATEGY:" in response:
            strategy_part = response.split("STRATEGY:")[1].split("STRENGTHS")[0] if "STRENGTHS" in response else response.split("STRATEGY:")[1].split("CODE:")[0]
            strategy = strategy_part.strip()

        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            code = response

        # SECURITY FIX (ISSUE #4): Validate generated code
        is_valid, error = validate_generated_code(code)
        if not is_valid:
            logger.error(f"Code validation failed in RecombinationOperator: {error}")
            code = f"# SECURITY: Code validation failed - {error}\n# Original code rejected for safety"

        return strategy, code


class RefinementOperator(BaseOperator):
    """
    Optimizes promising trajectories using pool insights

    Based on SE-Agent's refinement operator.
    Eliminates redundancies and enhances efficiency.
    """

    async def refine(
        self,
        trajectory: Trajectory,
        pool_insights: List[str],
        problem_description: str
    ) -> OperatorResult:
        """
        Refine promising trajectory

        Args:
            trajectory: Trajectory to refine
            pool_insights: Insights from trajectory pool
            problem_description: Original problem description

        Returns:
            OperatorResult with refined strategy
        """
        logger.info(f"Applying REFINEMENT to trajectory {trajectory.trajectory_id}")

        system_prompt = """You are a software engineering optimization specialist.

Your task is to refine and optimize a PROMISING solution trajectory by eliminating redundancies and enhancing efficiency using insights from other attempts.

Focus on:
1. Removing redundant steps
2. Streamlining action sequences
3. Incorporating risk mitigation from pool insights
4. Ensuring no systematic failure modes

The goal is to take something that already works reasonably well and make it excellent."""

        # SECURITY FIX (ISSUE #3): Sanitize all user-controlled inputs
        safe_problem = sanitize_for_prompt(problem_description, max_length=400)
        safe_reasoning = sanitize_for_prompt(trajectory.reasoning_pattern, max_length=200)
        safe_code = sanitize_for_prompt(
            trajectory.code_changes[:400] if trajectory.code_changes else 'No code recorded',
            max_length=400
        )

        # Sanitize insights (user-generated content)
        safe_insights = [sanitize_for_prompt(insight, max_length=100) for insight in pool_insights[:5]]
        insights_text = "\n".join(f"- {insight}" for insight in safe_insights) if safe_insights else "No insights available"

        prompt = f"""Optimize this promising trajectory:

PROBLEM:
{safe_problem}

CURRENT TRAJECTORY (Score: {trajectory.success_score:.2f}):
Strategy: {safe_reasoning}
Tools: {', '.join(trajectory.tools_used) if trajectory.tools_used else 'None'}
Code Changes:
{safe_code}

INSIGHTS FROM OTHER ATTEMPTS:
{insights_text}

Optimize the trajectory by:
1. Removing redundant steps (identify any duplicated logic)
2. Streamlining action sequences (eliminate unnecessary intermediates)
3. Incorporating risk mitigation from pool insights
4. Ensuring no systematic failure modes

Provide:
1. Optimization summary (2-3 sentences)
2. Key improvements (2-3 bullet points)
3. Refined code (Python code)

Format:
OPTIMIZATION: [what was improved]
IMPROVEMENTS: [specific enhancements]
CODE:
```python
[refined code]
```"""

        try:
            response = await self._call_llm(prompt, system_prompt, max_tokens=2000)

            strategy, code = self._parse_llm_response(response)

            return OperatorResult(
                success=True,
                generated_code=code,
                strategy_description=strategy,
                reasoning=f"Refined trajectory {trajectory.trajectory_id} using pool insights"
            )

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return OperatorResult(
                success=False,
                generated_code=None,
                strategy_description="",
                reasoning="",
                error_message=str(e)
            )

    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        Parse LLM response into optimization and code

        SECURITY FIX (ISSUE #4): Validates generated code before returning
        """
        optimization = ""
        code = ""

        if "OPTIMIZATION:" in response:
            opt_part = response.split("OPTIMIZATION:")[1].split("IMPROVEMENTS:")[0] if "IMPROVEMENTS:" in response else response.split("OPTIMIZATION:")[1].split("CODE:")[0]
            optimization = opt_part.strip()

        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            code = response

        # SECURITY FIX (ISSUE #4): Validate generated code
        is_valid, error = validate_generated_code(code)
        if not is_valid:
            logger.error(f"Code validation failed in RefinementOperator: {error}")
            code = f"# SECURITY: Code validation failed - {error}\n# Original code rejected for safety"

        return optimization, code


# Factory functions
def get_revision_operator(llm_client=None) -> RevisionOperator:
    """Get RevisionOperator instance"""
    return RevisionOperator(llm_client=llm_client)


def get_recombination_operator(llm_client=None) -> RecombinationOperator:
    """Get RecombinationOperator instance"""
    return RecombinationOperator(llm_client=llm_client)


def get_refinement_operator(llm_client=None) -> RefinementOperator:
    """Get RefinementOperator instance"""
    return RefinementOperator(llm_client=llm_client)
