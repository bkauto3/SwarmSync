"""
Ring-1T Multi-Turn Reasoning System

Decomposes complex problems into sub-problems, solves iteratively with self-critique.
Target: 15% improvement on complex reasoning tasks.

Based on:
- Tree-of-Thoughts (ToT): Hierarchical problem decomposition
- Chain-of-Recursive-Thoughts (CoRT): Self-critique and refinement
- Self-RAG: Quality assessment and validation

Integration:
- HTDAG: Problem decomposition → DAG tasks
- HALO: Routing to specialized reasoning agents
- OTEL: Distributed tracing and metrics
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from opentelemetry.trace import Status, StatusCode
from infrastructure.observability import ObservabilityManager, SpanType, CorrelationContext
from infrastructure.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SubProblem:
    """Represents a decomposed sub-problem"""
    id: str
    description: str
    dependencies: List[str]  # IDs of sub-problems that must be solved first
    complexity: float  # 0.0-1.0
    status: str  # "pending", "in_progress", "completed", "failed"
    solution: Optional[str] = None
    reasoning_rounds: int = 0


@dataclass
class ReasoningAttempt:
    """Single reasoning attempt within a round"""
    round_number: int
    initial_solution: str
    critique: str
    refinement: str
    quality_score: float  # 0.0-1.0


class Ring1TReasoning:
    """
    Ring-1T Multi-turn Reasoning System.

    Decomposes complex problems, solves iteratively with self-critique.
    Target: 15% improvement on complex reasoning tasks.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        obs_manager: Optional[ObservabilityManager] = None,
        max_reasoning_rounds: int = 3,
        quality_threshold: float = 0.85
    ):
        """
        Initialize Ring-1T reasoning system

        Args:
            llm_client: LLM client for reasoning (GPT-4o or Claude Sonnet 4)
            obs_manager: Observability manager for tracing
            max_reasoning_rounds: Maximum reasoning rounds per sub-problem
            quality_threshold: Quality threshold for convergence (0.0-1.0)
        """
        self.llm_client = llm_client
        self.obs_manager = obs_manager or ObservabilityManager()
        self.max_reasoning_rounds = max_reasoning_rounds
        self.quality_threshold = quality_threshold

    async def solve(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_context: Optional[CorrelationContext] = None
    ) -> Dict[str, Any]:
        """
        Solve complex problem using Ring-1T reasoning.

        Args:
            problem: Problem description
            context: Additional context (constraints, requirements, etc.)
            correlation_context: Correlation context for tracing

        Returns:
            {
                "solution": str,
                "sub_problems": List[Dict],
                "reasoning_attempts": List[Dict],
                "total_rounds": int,
                "quality_score": float,
                "validation": Dict
            }
        """
        ctx = correlation_context or self.obs_manager.create_correlation_context(problem)

        with self.obs_manager.span(
            "ring1t.solve",
            SpanType.ORCHESTRATION,
            ctx,
            attributes={"problem_length": len(problem)}
        ) as span:
            try:
                # Step 1: Decompose problem
                sub_problems = await self._decompose_problem(problem, context, ctx)

                span.set_attribute("sub_problems_count", len(sub_problems))
                self.obs_manager.record_metric(
                    "ring1t.sub_problems_count",
                    len(sub_problems),
                    unit="count",
                    labels={"correlation_id": ctx.correlation_id}
                )

                # Step 2: Solve sub-problems in dependency order
                solved_sub_problems = await self._solve_sub_problems(sub_problems, ctx)

                # Step 3: Synthesize final solution
                final_solution = await self._synthesize_solution(
                    problem=problem,
                    sub_problems=solved_sub_problems,
                    context=ctx
                )

                # Step 4: Validate solution
                validation = await self._validate_solution(
                    problem=problem,
                    solution=final_solution,
                    context=ctx
                )

                # Calculate metrics
                total_rounds = sum(sp.reasoning_rounds for sp in solved_sub_problems)

                span.set_attribute("total_rounds", total_rounds)
                span.set_attribute("quality_score", validation["quality_score"])

                self.obs_manager.record_metric(
                    "ring1t.total_reasoning_rounds",
                    total_rounds,
                    unit="count",
                    labels={"correlation_id": ctx.correlation_id}
                )

                self.obs_manager.record_metric(
                    "ring1t.quality_score",
                    validation["quality_score"],
                    unit="score",
                    labels={"correlation_id": ctx.correlation_id}
                )

                return {
                    "solution": final_solution,
                    "sub_problems": [asdict(sp) for sp in solved_sub_problems],
                    "total_rounds": total_rounds,
                    "quality_score": validation["quality_score"],
                    "validation": validation
                }

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def _decompose_problem(
        self,
        problem: str,
        context: Optional[Dict[str, Any]],
        correlation_context: CorrelationContext
    ) -> List[SubProblem]:
        """
        Decompose problem into 3-5 sub-problems with dependencies.

        Uses LLM to analyze problem structure and create hierarchical decomposition.
        """
        with self.obs_manager.span(
            "ring1t.decompose",
            SpanType.HTDAG,
            correlation_context
        ) as span:
            # Build prompt
            system_prompt = """You are an expert problem decomposer. Break complex problems into 3-5 manageable sub-problems.
For each sub-problem:
1. Create clear, specific description
2. Identify dependencies (which sub-problems must be solved first)
3. Estimate complexity (0.0-1.0, where 1.0 is most complex)

Return valid JSON only, no other text."""

            context_str = f"\nContext: {json.dumps(context)}" if context else ""

            user_prompt = f"""Decompose this problem into 3-5 sub-problems:

Problem: {problem}{context_str}

Return JSON format:
{{
    "sub_problems": [
        {{
            "id": "sp1",
            "description": "Clear, specific description",
            "dependencies": [],
            "complexity": 0.6
        }}
    ]
}}"""

            # Call LLM
            response = await self.llm_client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # Low temperature for structured output
                max_tokens=2048
            )

            # Parse response
            try:
                # Clean response (remove markdown code blocks if present)
                response_clean = response.strip()
                if response_clean.startswith("```json"):
                    response_clean = response_clean[7:]
                if response_clean.startswith("```"):
                    response_clean = response_clean[3:]
                if response_clean.endswith("```"):
                    response_clean = response_clean[:-3]
                response_clean = response_clean.strip()

                decomposition = json.loads(response_clean)

                sub_problems = [
                    SubProblem(
                        id=sp["id"],
                        description=sp["description"],
                        dependencies=sp.get("dependencies", []),
                        complexity=sp.get("complexity", 0.5),
                        status="pending"
                    )
                    for sp in decomposition["sub_problems"]
                ]

                span.set_attribute("decomposition_success", True)
                span.set_attribute("sub_problem_count", len(sub_problems))

                return sub_problems

            except (json.JSONDecodeError, KeyError) as e:
                span.set_attribute("decomposition_success", False)
                span.set_attribute("parse_error", str(e))

                # Fallback: Create single sub-problem
                return [
                    SubProblem(
                        id="sp1",
                        description=problem,
                        dependencies=[],
                        complexity=0.8,
                        status="pending"
                    )
                ]

    async def _solve_sub_problems(
        self,
        sub_problems: List[SubProblem],
        correlation_context: CorrelationContext
    ) -> List[SubProblem]:
        """
        Solve sub-problems in dependency order using topological sort.
        """
        # Topological sort by dependencies
        sorted_problems = self._topological_sort(sub_problems)

        solved_problems = []

        for sub_problem in sorted_problems:
            # Gather solutions from dependencies
            dependency_solutions = {
                sp.id: sp.solution
                for sp in solved_problems
                if sp.id in sub_problem.dependencies
            }

            # Solve with reasoning loop
            solution = await self._reasoning_loop(
                sub_problem=sub_problem,
                dependency_solutions=dependency_solutions,
                context=correlation_context
            )

            sub_problem.solution = solution["final_solution"]
            sub_problem.reasoning_rounds = solution["rounds"]
            sub_problem.status = "completed"

            solved_problems.append(sub_problem)

        return solved_problems

    async def _reasoning_loop(
        self,
        sub_problem: SubProblem,
        dependency_solutions: Dict[str, str],
        context: CorrelationContext
    ) -> Dict[str, Any]:
        """
        Multi-turn reasoning loop for single sub-problem.

        Loop:
        1. Initial reasoning attempt
        2. Self-critique
        3. Refinement
        4. Quality check (repeat if <threshold, max 3 rounds)
        """
        reasoning_attempts = []
        current_solution = ""

        for round_num in range(1, self.max_reasoning_rounds + 1):
            with self.obs_manager.span(
                f"ring1t.reasoning_round_{round_num}",
                SpanType.EXECUTION,
                context,
                attributes={
                    "sub_problem_id": sub_problem.id,
                    "round": round_num,
                    "complexity": sub_problem.complexity
                }
            ) as span:
                # Initial reasoning
                initial_solution = await self._generate_reasoning(
                    sub_problem=sub_problem,
                    dependency_solutions=dependency_solutions,
                    previous_solution=current_solution if round_num > 1 else None
                )

                # Self-critique
                critique = await self._generate_critique(
                    sub_problem=sub_problem,
                    solution=initial_solution
                )

                # Refinement
                refinement = await self._generate_refinement(
                    sub_problem=sub_problem,
                    initial_solution=initial_solution,
                    critique=critique
                )

                # Quality check
                quality_score = await self._assess_quality(
                    sub_problem=sub_problem,
                    solution=refinement
                )

                reasoning_attempts.append(ReasoningAttempt(
                    round_number=round_num,
                    initial_solution=initial_solution,
                    critique=critique,
                    refinement=refinement,
                    quality_score=quality_score
                ))

                current_solution = refinement

                span.set_attribute("quality_score", quality_score)
                span.set_attribute("converged", quality_score >= self.quality_threshold)

                # Check if quality threshold met
                if quality_score >= self.quality_threshold:
                    logger.info(
                        f"Quality threshold met at round {round_num}: {quality_score:.3f}",
                        extra={"sub_problem_id": sub_problem.id, "round": round_num}
                    )
                    break

        return {
            "final_solution": current_solution,
            "rounds": len(reasoning_attempts),
            "reasoning_attempts": [asdict(ra) for ra in reasoning_attempts]
        }

    async def _generate_reasoning(
        self,
        sub_problem: SubProblem,
        dependency_solutions: Dict[str, str],
        previous_solution: Optional[str]
    ) -> str:
        """Generate initial reasoning for sub-problem"""
        system_prompt = """You are an expert problem solver. Provide step-by-step reasoning to solve the given sub-problem.
Use clear logic, consider dependencies, and provide actionable solutions."""

        dependencies_text = self._format_dependencies(dependency_solutions)
        previous_text = f"\n\nPrevious attempt:\n{previous_solution}\n\nImprove upon this solution." if previous_solution else ""

        user_prompt = f"""Solve this sub-problem using detailed reasoning:

Sub-problem: {sub_problem.description}

Dependencies (already solved):
{dependencies_text}{previous_text}

Provide step-by-step reasoning and solution."""

        return await self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1024
        )

    async def _generate_critique(
        self,
        sub_problem: SubProblem,
        solution: str
    ) -> str:
        """Generate self-critique of solution"""
        system_prompt = """You are a critical evaluator. Identify logical errors, gaps, and improvements in the given solution.
Be specific and constructive."""

        user_prompt = f"""Critically evaluate this solution:

Sub-problem: {sub_problem.description}
Solution: {solution}

Identify:
1. Logical errors or gaps
2. Missing considerations
3. Potential improvements

Be specific and constructive."""

        return await self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=512
        )

    async def _generate_refinement(
        self,
        sub_problem: SubProblem,
        initial_solution: str,
        critique: str
    ) -> str:
        """Generate refined solution based on critique"""
        system_prompt = """You are an expert solution refiner. Improve solutions by addressing critiques.
Provide clear, actionable improvements."""

        user_prompt = f"""Refine the solution based on the critique:

Sub-problem: {sub_problem.description}
Initial solution: {initial_solution}
Critique: {critique}

Provide improved solution addressing all critique points."""

        return await self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=1024
        )

    async def _assess_quality(
        self,
        sub_problem: SubProblem,
        solution: str
    ) -> float:
        """Assess solution quality (0.0-1.0)"""
        system_prompt = """You are a quality assessor. Rate solutions on a scale of 0.0 to 1.0.
Consider: correctness, completeness, clarity, logical soundness.
Return ONLY a float between 0.0 and 1.0, nothing else."""

        user_prompt = f"""Rate this solution's quality (0.0-1.0):

Sub-problem: {sub_problem.description}
Solution: {solution}

Return only a float between 0.0 and 1.0."""

        response = await self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,  # Deterministic
            max_tokens=10
        )

        try:
            # Extract float from response
            quality_score = float(response.strip())
            return max(0.0, min(1.0, quality_score))
        except ValueError:
            # Default if parsing fails
            return 0.5

    async def _synthesize_solution(
        self,
        problem: str,
        sub_problems: List[SubProblem],
        context: CorrelationContext
    ) -> str:
        """Synthesize final solution from sub-problem solutions"""
        with self.obs_manager.span(
            "ring1t.synthesize",
            SpanType.ORCHESTRATION,
            context
        ) as span:
            system_prompt = """You are an expert solution synthesizer. Combine sub-problem solutions into a coherent final answer.
Ensure the solution is complete, actionable, and addresses the original problem."""

            sub_solutions = self._format_sub_problem_solutions(sub_problems)

            user_prompt = f"""Synthesize final solution by combining sub-problem solutions:

Original problem: {problem}

Sub-problem solutions:
{sub_solutions}

Provide a coherent, complete solution to the original problem."""

            solution = await self.llm_client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=2048
            )

            span.set_attribute("solution_length", len(solution))

            return solution

    async def _validate_solution(
        self,
        problem: str,
        solution: str,
        context: CorrelationContext
    ) -> Dict[str, Any]:
        """Validate final solution"""
        with self.obs_manager.span(
            "ring1t.validate",
            SpanType.ORCHESTRATION,
            context
        ) as span:
            system_prompt = """You are a solution validator. Assess if solutions fully address problems.
Return valid JSON only."""

            user_prompt = f"""Validate this solution against the problem:

Problem: {problem}
Solution: {solution}

Assess:
1. Does it address all aspects of the problem?
2. Is it logically sound?
3. Is it complete and actionable?

Return JSON:
{{
    "quality_score": 0.0-1.0,
    "validation_passed": true/false,
    "issues": ["..."] or []
}}"""

            response = await self.llm_client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=512
            )

            try:
                # Clean response
                response_clean = response.strip()
                if response_clean.startswith("```json"):
                    response_clean = response_clean[7:]
                if response_clean.startswith("```"):
                    response_clean = response_clean[3:]
                if response_clean.endswith("```"):
                    response_clean = response_clean[:-3]
                response_clean = response_clean.strip()

                validation = json.loads(response_clean)

                span.set_attribute("validation_passed", validation.get("validation_passed", False))
                span.set_attribute("quality_score", validation.get("quality_score", 0.0))

                return validation

            except (json.JSONDecodeError, KeyError):
                # Default validation
                return {
                    "quality_score": 0.5,
                    "validation_passed": True,
                    "issues": []
                }

    def _topological_sort(
        self,
        sub_problems: List[SubProblem]
    ) -> List[SubProblem]:
        """
        Sort sub-problems by dependencies (topological order).

        Ensures dependencies are solved before dependent sub-problems.
        """
        sorted_problems = []
        remaining = sub_problems.copy()

        while remaining:
            # Find problem with all dependencies satisfied
            for problem in remaining:
                if all(dep_id in [sp.id for sp in sorted_problems] for dep_id in problem.dependencies):
                    sorted_problems.append(problem)
                    remaining.remove(problem)
                    break
            else:
                # Circular dependency or error - add remaining in original order
                sorted_problems.extend(remaining)
                break

        return sorted_problems

    def _format_dependencies(self, dependency_solutions: Dict[str, str]) -> str:
        """Format dependency solutions for prompt"""
        if not dependency_solutions:
            return "None"

        return "\n".join(
            f"- {dep_id}: {solution}"
            for dep_id, solution in dependency_solutions.items()
        )

    def _format_sub_problem_solutions(self, sub_problems: List[SubProblem]) -> str:
        """Format sub-problem solutions for prompt"""
        return "\n\n".join(
            f"Sub-problem {sp.id}: {sp.description}\nSolution: {sp.solution}"
            for sp in sub_problems
        )
