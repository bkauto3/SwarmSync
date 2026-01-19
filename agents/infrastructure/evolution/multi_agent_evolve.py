"""
Multi-Agent Evolve orchestration with Solver-Verifier co-evolution.

Based on arXiv:2510.23595 "Multi-Agent Evolve: LLM Self-Improve through Co-evolution"
Research: docs/research/MULTI_AGENT_EVOLVE_ARCHITECTURE.md

Co-evolution system where Solver and Verifier compete:
- Solver: Generates diverse, high-quality solutions
- Verifier: Finds errors and provides adversarial feedback
- Loop: Both agents improve through competitive pressure

Algorithm 3 (Joint Training Loop):
1. Solver generates N trajectories (diverse solutions)
2. Verifier evaluates each trajectory (4 criteria)
3. Compute rewards for both agents (competitive)
4. Check convergence (4 criteria)
5. Update memory if score > threshold
6. Repeat until converged or max iterations

Integration Points:
- SolverAgent (Phase 2, 766 lines, 36/36 tests passing)
- VerifierAgent (Phase 3, 921 lines, 34/34 tests passing)
- TrajectoryPool (persistent trajectory storage)
- OTEL observability (distributed tracing)

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 4 Implementation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

# Genesis infrastructure imports
from infrastructure import get_logger
from infrastructure.evolution.solver_agent import (
    SolverAgent,
    SolverConfig,
    SolverTrajectory,
    VerifierFeedback
)
from infrastructure.evolution.verifier_agent import (
    VerifierAgent,
    VerifierConfig,
    VerificationResult
)
from infrastructure.trajectory_pool import (
    TrajectoryPool,
    get_trajectory_pool
)

# OTEL observability
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Metrics for Co-Evolution
    coevo_iteration_counter = meter.create_counter(
        "coevolution.iterations.completed",
        description="Number of co-evolution iterations completed"
    )
    coevo_convergence_counter = meter.create_counter(
        "coevolution.convergence.detected",
        description="Number of times convergence was detected"
    )
    coevo_score_histogram = meter.create_histogram(
        "coevolution.best_score",
        description="Best verification scores achieved"
    )
except ImportError:
    tracer = None
    meter = None
    coevo_iteration_counter = None
    coevo_convergence_counter = None
    coevo_score_histogram = None

logger = get_logger("multi_agent_evolve")


@dataclass
class CoEvolutionConfig:
    """
    Co-evolution loop configuration.

    Based on arXiv:2510.23595 Section 4.3 "Training Hyperparameters"

    Recommended values:
    - max_iterations: 10 (typical convergence in 5-8 iterations)
    - convergence_threshold: 0.05 (5% improvement needed to continue)
    - min_iterations: 3 (minimum iterations before convergence check)
    - store_threshold: 0.75 (minimum score to store in TrajectoryPool)

    Attributes:
        max_iterations: Maximum co-evolution iterations
        convergence_threshold: Minimum improvement to continue (0-1)
        min_iterations: Minimum iterations before checking convergence
        store_threshold: Minimum score to store trajectory in memory (0-1)
        enable_memory: Whether to use TrajectoryPool for memory
    """
    max_iterations: int = 10
    convergence_threshold: float = 0.05
    min_iterations: int = 3
    store_threshold: float = 0.75
    enable_memory: bool = True


@dataclass
class CoEvolutionResult:
    """
    Result from co-evolution loop.

    Contains best trajectory, convergence metrics, and reward history.

    Attributes:
        best_trajectory: Best trajectory found (as dict for serialization)
        final_score: Final verification score (0-1)
        iterations_used: Number of iterations executed
        converged: Whether convergence was detected
        solver_rewards: List of average Solver rewards per iteration
        verifier_rewards: List of average Verifier rewards per iteration
        convergence_history: List of best scores per iteration
        metadata: Additional metadata (task type, agent type, etc.)
    """
    best_trajectory: Dict[str, Any]
    final_score: float
    iterations_used: int
    converged: bool
    solver_rewards: List[float]
    verifier_rewards: List[float]
    convergence_history: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentEvolve:
    """
    Co-evolution system with Solver-Verifier competitive dynamics.

    Based on arXiv:2510.23595 Algorithm 3 "Joint Training Protocol"

    Training Loop:
    1. Solver generates N trajectories (diverse solutions)
    2. Verifier evaluates each trajectory (4 criteria)
    3. Compute rewards for both agents (competitive)
    4. Check convergence (4 criteria)
    5. Update memory if score > threshold
    6. Repeat until converged or max iterations

    Co-Evolutionary Pressure:
    - Solver: Maximize verification_score (fool Verifier)
    - Verifier: Minimize verification_score (find errors)
    - Both agents improve through adversarial feedback

    Usage:
        mae = MultiAgentEvolve("qa_agent")
        result = await mae.evolve(task)
        print(f"Best score: {result.final_score}")
    """

    def __init__(
        self,
        agent_type: str,
        solver_config: Optional[SolverConfig] = None,
        verifier_config: Optional[VerifierConfig] = None,
        coevolution_config: Optional[CoEvolutionConfig] = None
    ):
        """
        Initialize Multi-Agent Evolve system.

        Args:
            agent_type: Agent type (e.g., "qa_agent", "builder_agent")
            solver_config: Optional custom Solver configuration
            verifier_config: Optional custom Verifier configuration
            coevolution_config: Optional custom co-evolution configuration
        """
        self.agent_type = agent_type
        self.solver = SolverAgent(agent_type, solver_config)
        self.verifier = VerifierAgent(agent_type, verifier_config)
        self.config = coevolution_config or CoEvolutionConfig()

        # Memory integration
        self.trajectory_pool = get_trajectory_pool(agent_type) if self.config.enable_memory else None

        # Tracking
        self.iteration_history: List[Dict[str, Any]] = []

        logger.info(
            f"Initialized MultiAgentEvolve for {agent_type} "
            f"(max_iter={self.config.max_iterations}, "
            f"memory={self.config.enable_memory})"
        )

    async def evolve(
        self,
        task: Dict[str, Any],
        max_iterations: Optional[int] = None
    ) -> CoEvolutionResult:
        """
        Run co-evolution loop with Solver-Verifier dynamics.

        Based on arXiv:2510.23595 Algorithm 3 (Joint Training Loop)

        Args:
            task: Benchmark task specification with keys:
                - type: Task type (e.g., "code_generation", "validation")
                - description: Task description
                - test_cases: Optional test cases for validation
                - constraints: Optional constraints
            max_iterations: Override default max iterations

        Returns:
            CoEvolutionResult with best trajectory and metrics

        Algorithm:
        1. Initialize tracking variables
        2. For each iteration:
           a. Solver generates N trajectories
           b. Verifier evaluates all trajectories
           c. Compute rewards for both agents
           d. Track best trajectory
           e. Store in memory if score > threshold
           f. Check convergence (4 criteria)
           g. Generate feedback for next iteration
        3. Return final result with metrics
        """
        max_iter = max_iterations or self.config.max_iterations

        # Start OTEL span for full evolution
        span_ctx = tracer.start_span("coevolution.evolve") if tracer else None

        try:
            logger.info(
                f"Starting co-evolution for {task.get('type', 'unknown')} "
                f"(max {max_iter} iterations)"
            )

            # Initialize tracking
            best_trajectory = None
            best_score = 0.0
            verifier_feedback = None
            convergence_history = []
            solver_rewards = []
            verifier_rewards = []
            converged = False
            convergence_reason = None

            for iteration in range(max_iter):
                logger.info(f"=== Iteration {iteration + 1}/{max_iter} ===")

                # Step 1: Solver generates trajectories
                trajectories = await self.solver.generate_trajectories(
                    task, verifier_feedback
                )
                logger.info(f"Solver generated {len(trajectories)} trajectories")

                # Step 2: Verifier evaluates all trajectories
                verification_results = []
                for traj in trajectories:
                    # Convert SolverTrajectory to dict for Verifier
                    traj_dict = {
                        "trajectory_id": traj.trajectory_id,
                        "code": traj.code,
                        "reasoning": traj.reasoning,
                        "generation_method": traj.generation_method,
                        "solver_confidence": traj.solver_confidence,
                        "diversity_score": traj.diversity_score,
                        "metadata": traj.metadata
                    }

                    result = await self.verifier.verify_trajectory(traj_dict, task)
                    verification_results.append(result)

                    # Track best trajectory
                    if result.verification_score > best_score:
                        best_score = result.verification_score
                        best_trajectory = traj_dict
                        logger.info(
                            f"New best score: {best_score:.3f} from "
                            f"{traj.trajectory_id}"
                        )

                # Step 3: Compute rewards for both agents
                iter_solver_rewards = []
                iter_verifier_rewards = []

                prev_verifier_score = (
                    verification_results[-1].verification_score
                    if iteration > 0 and len(verification_results) > 0
                    else None
                )

                for traj, verif_result in zip(trajectories, verification_results):
                    # Solver reward (quality + diversity + verifier challenge)
                    # Note: compute_solver_reward expects benchmark_score, not verifier_score
                    # Using verification_score as proxy for quality
                    solver_reward = self.solver.compute_solver_reward(
                        traj,
                        benchmark_score=verif_result.verification_score,
                        verifier_score=verif_result.verification_score
                    )
                    iter_solver_rewards.append(solver_reward)

                    # Verifier reward (error detection + challenge improvement)
                    verifier_reward = self.verifier.compute_verifier_reward(
                        verif_result.verification_score,
                        prev_verifier_score
                    )
                    iter_verifier_rewards.append(verifier_reward)

                avg_solver_reward = (
                    sum(iter_solver_rewards) / len(iter_solver_rewards)
                    if iter_solver_rewards else 0.0
                )
                avg_verifier_reward = (
                    sum(iter_verifier_rewards) / len(iter_verifier_rewards)
                    if iter_verifier_rewards else 0.0
                )

                solver_rewards.append(avg_solver_reward)
                verifier_rewards.append(avg_verifier_reward)

                logger.info(
                    f"Rewards - Solver: {avg_solver_reward:.3f}, "
                    f"Verifier: {avg_verifier_reward:.3f}"
                )

                # Step 4: Update feedback for next iteration
                # Convert VerificationResult to VerifierFeedback objects
                verifier_feedback = []
                for traj, verif_result in zip(trajectories, verification_results):
                    feedback_obj = VerifierFeedback(
                        trajectory_id=traj.trajectory_id,
                        verifier_score=verif_result.verification_score,
                        correctness_score=verif_result.correctness_score,
                        quality_score=verif_result.quality_score,
                        robustness_score=verif_result.robustness_score,
                        generalization_score=verif_result.generalization_score,
                        correctness_feedback=self._extract_feedback_by_area(
                            verif_result.feedback, "correctness"
                        ),
                        quality_feedback=self._extract_feedback_by_area(
                            verif_result.feedback, "quality"
                        ),
                        robustness_feedback=self._extract_feedback_by_area(
                            verif_result.feedback, "robustness"
                        ),
                        shortcuts_detected=verif_result.shortcuts_detected,
                        weak_areas=self._extract_weak_areas(verif_result.feedback),
                        timestamp=verif_result.timestamp
                    )
                    verifier_feedback.append(feedback_obj)

                # Step 5: Store best trajectory in memory if above threshold
                if (self.trajectory_pool and
                    best_trajectory and
                    best_score >= self.config.store_threshold):
                    await self._store_trajectory(best_trajectory, best_score, task)

                # Step 6: Track convergence
                convergence_history.append(best_score)

                # Step 7: Check convergence
                converged, convergence_reason = self._check_convergence(
                    convergence_history, iteration, max_iter
                )

                # Store iteration data
                self.iteration_history.append({
                    "iteration": iteration + 1,
                    "best_score": best_score,
                    "solver_reward": avg_solver_reward,
                    "verifier_reward": avg_verifier_reward,
                    "trajectories_generated": len(trajectories),
                    "converged": converged,
                    "convergence_reason": convergence_reason if converged else None
                })

                # Record metrics
                if coevo_iteration_counter:
                    coevo_iteration_counter.add(1, {"agent_type": self.agent_type})

                if converged:
                    logger.info(
                        f"Converged at iteration {iteration + 1}: "
                        f"{convergence_reason}"
                    )
                    if coevo_convergence_counter:
                        coevo_convergence_counter.add(
                            1,
                            {
                                "agent_type": self.agent_type,
                                "reason": convergence_reason
                            }
                        )
                    break

            # Record final score
            if coevo_score_histogram:
                coevo_score_histogram.record(
                    best_score,
                    {"agent_type": self.agent_type}
                )

            # Final result
            result = CoEvolutionResult(
                best_trajectory=best_trajectory or {},
                final_score=best_score,
                iterations_used=iteration + 1,
                converged=converged,
                solver_rewards=solver_rewards,
                verifier_rewards=verifier_rewards,
                convergence_history=convergence_history,
                metadata={
                    "task_type": task.get("type", "unknown"),
                    "agent_type": self.agent_type,
                    "final_iteration": iteration + 1,
                    "max_iterations": max_iter,
                    "convergence_reason": convergence_reason
                }
            )

            logger.info(
                f"Co-evolution complete: score={best_score:.3f}, "
                f"iterations={iteration + 1}, converged={converged}"
            )

            if span_ctx and tracer:
                span_ctx.set_attribute("iterations_used", iteration + 1)
                span_ctx.set_attribute("final_score", best_score)
                span_ctx.set_attribute("converged", converged)
                span_ctx.set_status(Status(StatusCode.OK))
                span_ctx.end()

            return result

        except Exception as e:
            logger.error(f"Co-evolution failed: {e}", exc_info=True)
            if span_ctx and tracer:
                span_ctx.set_status(Status(StatusCode.ERROR, str(e)))
                span_ctx.end()
            raise

    def _check_convergence(
        self,
        convergence_history: List[float],
        current_iteration: int,
        max_iterations: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check convergence using 4 criteria.

        Based on arXiv:2510.23595 Section 4.2 "Convergence Detection"

        Criteria:
        1. Score plateau (< 5% improvement in last 3 iterations)
        2. High score (> 0.95 = excellent solution)
        3. Max iterations reached
        4. Min iterations not met (prevent premature convergence)

        Args:
            convergence_history: List of best scores per iteration
            current_iteration: Current iteration index (0-based)
            max_iterations: Override max iterations (if None, uses config)

        Returns:
            Tuple of (converged: bool, reason: str or None)
        """
        # Use provided max_iterations or fall back to config
        max_iter = max_iterations or self.config.max_iterations

        # Criterion 3: Max iterations reached (check BEFORE min_iterations)
        # This ensures we converge when reaching max, even if below min_iterations
        if current_iteration >= max_iter - 1:
            return True, "max_iterations_reached"

        # Criterion 4: Don't converge before min iterations
        if current_iteration < self.config.min_iterations:
            return False, None

        # Criterion 2: High score achieved (>0.95)
        if convergence_history and convergence_history[-1] >= 0.95:
            return True, "high_score_achieved"

        # Criterion 1: Score plateau (last 3 iterations)
        if len(convergence_history) >= 3:
            recent_scores = convergence_history[-3:]
            improvement = max(recent_scores) - min(recent_scores)

            if improvement < self.config.convergence_threshold:
                return True, "score_plateau"

        return False, None

    def _extract_feedback_by_area(
        self,
        feedback_list: List[Dict[str, Any]],
        area: str
    ) -> str:
        """
        Extract feedback messages for a specific area.

        Args:
            feedback_list: List of feedback dictionaries
            area: Area to extract (correctness/quality/robustness)

        Returns:
            Combined feedback messages for that area
        """
        messages = [
            f["message"]
            for f in feedback_list
            if f.get("area") == area
        ]
        return " ".join(messages) if messages else f"No {area} issues detected."

    def _extract_weak_areas(
        self,
        feedback_list: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract weak areas from feedback.

        Args:
            feedback_list: List of feedback dictionaries

        Returns:
            List of weak area descriptions
        """
        weak_areas = []
        for f in feedback_list:
            if f.get("severity") in ["high", "medium"]:
                weak_areas.append(f"{f.get('area', 'unknown')}: {f.get('message', '')}")
        return weak_areas

    async def _store_trajectory(
        self,
        trajectory: Dict[str, Any],
        score: float,
        task: Dict[str, Any]
    ) -> None:
        """
        Store trajectory in memory pool for future reuse.

        Enriches trajectory with metadata before storage:
        - Verification score
        - Task type
        - Agent type
        - Storage timestamp

        Args:
            trajectory: Trajectory dict to store
            score: Verification score for this trajectory
            task: Original task specification
        """
        if not self.trajectory_pool:
            return

        # Add metadata for storage
        trajectory_with_meta = {
            **trajectory,
            "verification_score": score,
            "task_type": task.get("type", "unknown"),
            "agent_type": self.agent_type,
            "stored_for_reuse": True,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            await self.trajectory_pool.add(trajectory_with_meta)

            logger.debug(
                f"Stored trajectory {trajectory.get('trajectory_id')} "
                f"with score {score:.3f}"
            )
        except Exception as e:
            logger.warning(f"Failed to store trajectory: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive co-evolution statistics.

        Returns:
            Dict with statistics:
            - total_iterations: Number of iterations executed
            - best_score: Best verification score achieved
            - final_score: Final verification score
            - converged: Whether convergence was detected
            - convergence_reason: Reason for convergence (if applicable)
            - avg_solver_reward: Average Solver reward across iterations
            - avg_verifier_reward: Average Verifier reward across iterations
            - trajectories_generated_total: Total trajectories generated
            - iteration_history: Full iteration-by-iteration history
        """
        if not self.iteration_history:
            return {
                "total_iterations": 0,
                "best_score": 0.0,
                "converged": False
            }

        return {
            "total_iterations": len(self.iteration_history),
            "best_score": max(
                iter["best_score"] for iter in self.iteration_history
            ),
            "final_score": self.iteration_history[-1]["best_score"],
            "converged": self.iteration_history[-1]["converged"],
            "convergence_reason": self.iteration_history[-1].get(
                "convergence_reason"
            ),
            "avg_solver_reward": sum(
                iter["solver_reward"] for iter in self.iteration_history
            ) / len(self.iteration_history),
            "avg_verifier_reward": sum(
                iter["verifier_reward"] for iter in self.iteration_history
            ) / len(self.iteration_history),
            "trajectories_generated_total": sum(
                iter["trajectories_generated"] for iter in self.iteration_history
            ),
            "iteration_history": self.iteration_history
        }
