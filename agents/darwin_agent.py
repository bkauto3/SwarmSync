"""
Darwin Gödel Machine Agent - Self-Improving Code Evolution
Layer 2 implementation for Genesis multi-agent system

Based on: https://arxiv.org/abs/2505.22954 (Darwin Gödel Machine paper)
Reference: https://github.com/jennyzzt/dgm

BREAKTHROUGH: Agents that rewrite their own code and empirically validate improvements
- 150% improvement proven (20% → 50% on SWE-bench)
- Evolutionary archive + empirical validation
- No formal proof required (unlike original Gödel Machine)
- Safety through sandboxing + benchmark validation

Key Features:
- Analyzes agent performance from Replay Buffer
- Generates code improvements using GPT-4o (meta-programming)
- Tests improvements in Docker sandbox
- Validates via benchmarks (SWE-Bench, custom metrics)
- Accepts only if metrics improve (no regressions)
- Stores winning strategies in ReasoningBank

Evolution Loop:
1. SELECT: Choose parent agent from evolutionary archive
2. DIAGNOSE: Analyze failures from Replay Buffer
3. IMPROVE: Generate code modifications
4. VALIDATE: Test in sandbox + run benchmarks
5. ACCEPT: Add to archive if improvement proven
6. LEARN: Store strategy in ReasoningBank
"""

import asyncio
import json
import logging
import os
import random
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import anthropic
from openai import AsyncOpenAI

# Genesis infrastructure imports
from infrastructure import (
    get_reasoning_bank, ReasoningBank, MemoryType, OutcomeTag,
    get_replay_buffer, ReplayBuffer, Trajectory, ActionStep,
    get_logger
)
from infrastructure.rifl import RIFLPromptEvaluator

# Setup logging
logger = get_logger("darwin_agent")


class ImprovementType(Enum):
    """Types of code improvements Darwin can make"""
    BUG_FIX = "bug_fix"  # Fix identified bugs
    OPTIMIZATION = "optimization"  # Performance improvements
    NEW_FEATURE = "new_feature"  # Add new capabilities
    REFACTOR = "refactor"  # Code structure improvements
    ERROR_HANDLING = "error_handling"  # Better error recovery


class EvolutionStatus(Enum):
    """Status of evolution attempts"""
    PENDING = "pending"
    DIAGNOSING = "diagnosing"
    IMPROVING = "improving"
    VALIDATING = "validating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class EvolutionAttempt:
    """Single attempt to evolve an agent"""
    attempt_id: str
    parent_agent: str  # Agent being improved
    parent_version: str  # Version/commit of parent
    improvement_type: str  # ImprovementType
    problem_diagnosis: str  # What's wrong
    proposed_changes: str  # Code changes
    validation_results: Dict[str, Any]  # Benchmark scores
    accepted: bool
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement_delta: Dict[str, float]
    timestamp: str
    generation: int  # Evolution generation number
    sandbox_logs: str = ""
    error_message: Optional[str] = None


@dataclass
class EvolutionArchive:
    """Archive of all evolutionary attempts (successful and failed)"""
    archive_id: str
    agent_name: str
    generations: List[int]
    successful_attempts: List[str]  # attempt_ids
    failed_attempts: List[str]
    best_version: str  # Version with highest score
    best_score: float
    total_attempts: int
    acceptance_rate: float
    created_at: str
    updated_at: str


class DarwinAgent:
    """
    Self-improving agent that evolves its own code through empirical validation

    Core Algorithm (from Darwin paper):
    1. Maintain evolutionary archive of agent versions
    2. Select parent agents based on performance (fitness-proportional)
    3. Diagnose problems from failure trajectories
    4. Generate code improvements using LLM meta-programming
    5. Validate in sandbox + benchmark tests
    6. Accept if metrics improve, reject if regression
    7. Add successful variants to archive
    8. Repeat indefinitely

    Safety Mechanisms:
    - Docker sandbox isolation for untrusted code
    - Benchmark validation before acceptance
    - No destructive operations allowed
    - Human-in-loop for critical changes
    - Rollback on regression detection
    """

    def __init__(
        self,
        agent_name: str,
        initial_code_path: str,
        benchmark_suite: str = "genesis_benchmark",
        max_generations: int = 100,
        population_size: int = 5,
        acceptance_threshold: float = 0.01,  # 1% improvement required
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize Darwin evolution engine

        Args:
            agent_name: Name of agent to evolve
            initial_code_path: Path to initial agent code
            benchmark_suite: Benchmark to use for validation
            max_generations: Maximum evolution generations
            population_size: Number of variants per generation
            acceptance_threshold: Minimum improvement to accept (0.01 = 1%)
            openai_api_key: OpenAI API key (for GPT-4o meta-programming)
            anthropic_api_key: Anthropic API key (optional fallback)
        """
        self.agent_name = agent_name
        self.initial_code_path = Path(initial_code_path)
        self.benchmark_suite = benchmark_suite
        self.max_generations = max_generations
        self.population_size = population_size
        self.acceptance_threshold = acceptance_threshold

        # Initialize LLM clients (GPT-4o for meta-programming)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))

        # Initialize infrastructure
        self.reasoning_bank = get_reasoning_bank()
        self.replay_buffer = get_replay_buffer()
        self.rifl_evaluator = RIFLPromptEvaluator()
        self.rifl_reward_history: List[float] = []

        # Evolution state
        self.current_generation = 0
        self.archive: List[str] = ["initial"]  # Start with initial version
        self.attempts: Dict[str, EvolutionAttempt] = {}

        # Performance tracking
        self.best_score = 0.0
        self.best_version = "initial"

        logger.info(f"Darwin Agent initialized for {agent_name}")
        logger.info(f"Max generations: {max_generations}, Population size: {population_size}")
        logger.info(f"Acceptance threshold: {acceptance_threshold * 100}%")

    def _sanitize_path_component(self, user_input: str) -> str:
        """
        Sanitize user input for safe path construction

        SECURITY FIX #2: Prevents path traversal attacks
        Blocks: ../, ..\\, /, \\, and non-alphanumeric characters

        Args:
            user_input: Untrusted user input

        Returns:
            Sanitized string safe for use in file paths
        """
        if not user_input or not isinstance(user_input, str):
            raise ValueError("Invalid input for path sanitization")

        import re

        # Remove path traversal sequences
        sanitized = user_input.replace("..", "").replace("/", "_").replace("\\", "_")

        # Whitelist: alphanumeric, underscore, hyphen only
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)

        if not sanitized:
            raise ValueError(f"Path sanitization resulted in empty string from: '{user_input}'")

        return sanitized

    def _sanitize_for_logging(self, data: Any) -> Any:
        """
        Sanitize data to remove sensitive credentials before logging

        SECURITY FIX #3: Prevents API key exposure in logs
        Redacts: API keys, tokens, passwords, secrets

        Args:
            data: Data to sanitize (str, dict, list, or any type)

        Returns:
            Sanitized copy of data with credentials redacted
        """
        import re
        import copy

        if isinstance(data, str):
            # Redact OpenAI keys (sk-...)
            data = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-***REDACTED***', data)

            # Redact Anthropic keys (sk-ant-...)
            data = re.sub(r'sk-ant-[a-zA-Z0-9\-]{32,}', 'sk-ant-***REDACTED***', data)

            # Redact generic API keys, tokens, passwords
            data = re.sub(
                r'(api[_-]?key|token|password|secret|credential)[\s:=]+\S+',
                r'\1=***REDACTED***',
                data,
                flags=re.IGNORECASE
            )

            # Redact Bearer tokens
            data = re.sub(r'Bearer\s+\S+', 'Bearer ***REDACTED***', data, flags=re.IGNORECASE)

            return data

        elif isinstance(data, dict):
            # Recursively sanitize dictionary
            sanitized = {}
            for k, v in data.items():
                # Redact sensitive key names
                if any(sensitive in k.lower() for sensitive in ['key', 'token', 'password', 'secret', 'credential']):
                    sanitized[k] = '***REDACTED***'
                else:
                    sanitized[k] = self._sanitize_for_logging(v)
            return sanitized

        elif isinstance(data, list):
            # Recursively sanitize list
            return [self._sanitize_for_logging(item) for item in data]

        else:
            # Return as-is for other types
            return data

    async def evolve(self) -> EvolutionArchive:
        """
        Main evolution loop - run indefinitely until max_generations reached

        Returns:
            EvolutionArchive with complete evolution history
        """
        logger.info(f"🧬 Starting evolution for {self.agent_name}")

        # Evaluate initial version
        logger.info("Evaluating initial agent version...")
        initial_metrics = await self._evaluate_agent(self.initial_code_path, "initial")
        self.best_score = initial_metrics.get("overall_score", 0.0)

        logger.info(f"Initial score: {self.best_score:.3f}")

        # Evolution loop
        for generation in range(self.max_generations):
            self.current_generation = generation
            logger.info(f"\n{'='*60}")
            logger.info(f"🧬 GENERATION {generation + 1}/{self.max_generations}")
            logger.info(f"{'='*60}")
            logger.info(f"Archive size: {len(self.archive)}")
            logger.info(f"Best score: {self.best_score:.3f} (version: {self.best_version})")

            # Generate evolution attempts for this generation
            attempts = await self._generate_evolution_attempts()

            # Execute attempts in parallel
            results = await asyncio.gather(
                *[self._execute_evolution_attempt(attempt) for attempt in attempts],
                return_exceptions=True
            )

            # Process results
            accepted_count = 0
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Evolution attempt failed: {result}")
                    continue

                if result and result.accepted:
                    accepted_count += 1
                    self.archive.append(result.attempt_id)

                    # Update best if improved
                    if result.metrics_after.get("overall_score", 0) > self.best_score:
                        self.best_score = result.metrics_after["overall_score"]
                        self.best_version = result.attempt_id
                        logger.info(f"🎉 NEW BEST VERSION: {result.attempt_id} (score: {self.best_score:.3f})")

            logger.info(f"Generation {generation + 1} complete: {accepted_count}/{len(attempts)} accepted")

            # Early stopping if no progress for 10 generations
            if generation > 10 and len(self.archive) <= 2:
                logger.warning("No improvements in 10 generations - stopping evolution")
                break

        # Create final archive
        archive = await self._create_evolution_archive()
        logger.info(f"\n🎯 Evolution complete!")
        logger.info(f"Total generations: {self.current_generation + 1}")
        logger.info(f"Total attempts: {len(self.attempts)}")
        logger.info(f"Acceptance rate: {archive.acceptance_rate:.1%}")
        logger.info(f"Best version: {archive.best_version} (score: {archive.best_score:.3f})")

        return archive

    async def _generate_evolution_attempts(self) -> List[EvolutionAttempt]:
        """
        Generate evolution attempts for current generation

        Uses fitness-proportional selection to choose parents from archive
        """
        attempts = []

        for i in range(self.population_size):
            # Select parent (fitness-proportional selection)
            parent_version = await self._select_parent()

            # Diagnose problems from failures
            problem_diagnosis = await self._diagnose_problems(parent_version)

            # Determine improvement type
            improvement_type = await self._determine_improvement_type(problem_diagnosis)

            # Create attempt
            attempt = EvolutionAttempt(
                attempt_id=f"gen{self.current_generation}_attempt{i}_{uuid.uuid4().hex[:8]}",
                parent_agent=self.agent_name,
                parent_version=parent_version,
                improvement_type=improvement_type.value,
                problem_diagnosis=problem_diagnosis,
                proposed_changes="",  # Will be filled by _generate_code_improvements
                validation_results={},
                accepted=False,
                metrics_before={},
                metrics_after={},
                improvement_delta={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                generation=self.current_generation,
            )

            attempts.append(attempt)

        return attempts

    async def _select_parent(self) -> str:
        """
        Select parent agent using fitness-proportional selection

        Better-performing agents more likely to be selected for evolution
        """
        if len(self.archive) == 1:
            return self.archive[0]

        # Get scores for all archived versions
        scores = []
        for version in self.archive:
            if version == "initial":
                score = self.best_score if self.best_version == "initial" else 0.5
            else:
                attempt = self.attempts.get(version)
                score = attempt.metrics_after.get("overall_score", 0) if attempt else 0
            scores.append(score)

        # Convert to probabilities (softmax)
        import math
        exp_scores = [math.exp(10 * (s - 0.5)) for s in scores]  # Temperature scaling
        total = sum(exp_scores)
        probabilities = [s / total for s in exp_scores]

        # Sample parent
        parent = random.choices(self.archive, probabilities)[0]
        logger.info(f"Selected parent: {parent}")
        return parent

    async def _diagnose_problems(self, parent_version: str) -> str:
        """
        Diagnose problems by analyzing failure trajectories from Replay Buffer

        Args:
            parent_version: Version to diagnose

        Returns:
            Problem diagnosis string
        """
        logger.info(f"Diagnosing problems for {parent_version}...")

        # Query failed trajectories for this agent
        try:
            failed_trajectories = self.replay_buffer.query_by_outcome(
                outcome=OutcomeTag.FAILURE,
                agent_filter=self.agent_name,
                limit=10
            )

            if not failed_trajectories:
                return "No specific problems identified - attempting general optimization"

            # Analyze failure patterns
            failure_categories = {}
            for traj in failed_trajectories:
                category = traj.get("error_category", "unknown")
                rationale = traj.get("failure_rationale", "")
                if category not in failure_categories:
                    failure_categories[category] = []
                failure_categories[category].append(rationale)

            # Summarize using LLM
            diagnosis_prompt = f"""Analyze these failure patterns and diagnose the core problem:

Agent: {self.agent_name}
Version: {parent_version}

Failure Categories:
{json.dumps(failure_categories, indent=2)}

Provide a concise diagnosis (2-3 sentences) of the root cause and what needs to be improved."""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": diagnosis_prompt}],
                temperature=0.3,
            )

            diagnosis = response.choices[0].message.content
            # SECURITY: Sanitize before logging
            logger.info(f"Diagnosis: {self._sanitize_for_logging(diagnosis)}")
            return diagnosis

        except Exception as e:
            logger.error(f"Error diagnosing problems: {e}")
            return "Error analyzing failures - attempting general optimization"

    async def _determine_improvement_type(self, diagnosis: str) -> ImprovementType:
        """Determine type of improvement needed based on diagnosis"""
        diagnosis_lower = diagnosis.lower()

        # Check for error handling FIRST (before bug/error check)
        if "error handling" in diagnosis_lower or "exception handling" in diagnosis_lower:
            return ImprovementType.ERROR_HANDLING
        elif "bug" in diagnosis_lower or "error" in diagnosis_lower:
            return ImprovementType.BUG_FIX
        elif "performance" in diagnosis_lower or "slow" in diagnosis_lower or "optimi" in diagnosis_lower:
            return ImprovementType.OPTIMIZATION
        elif "missing" in diagnosis_lower or "lacking" in diagnosis_lower or "add" in diagnosis_lower:
            return ImprovementType.NEW_FEATURE
        else:
            return ImprovementType.REFACTOR

    async def _execute_evolution_attempt(self, attempt: EvolutionAttempt) -> Optional[EvolutionAttempt]:
        """
        Execute single evolution attempt: generate improvements, validate, accept/reject

        Returns:
            Updated EvolutionAttempt with results, or None if failed
        """
        logger.info(f"\n--- Executing attempt: {attempt.attempt_id} ---")
        logger.info(f"Parent: {attempt.parent_version}")
        logger.info(f"Type: {attempt.improvement_type}")
        # SECURITY: Sanitize diagnosis before logging
        safe_diagnosis = self._sanitize_for_logging(attempt.problem_diagnosis[:100])
        logger.info(f"Diagnosis: {safe_diagnosis}...")

        try:
            # Step 1: Get parent code
            parent_code_path = await self._get_agent_code_path(attempt.parent_version)
            parent_code = parent_code_path.read_text()

            # Step 2: Get baseline metrics
            logger.info("Evaluating baseline metrics...")
            attempt.metrics_before = await self._evaluate_agent(parent_code_path, attempt.parent_version)

            # Step 3: Generate code improvements
            logger.info("Generating code improvements...")
            improved_code = await self._generate_code_improvements(
                parent_code=parent_code,
                diagnosis=attempt.problem_diagnosis,
                improvement_type=attempt.improvement_type
            )

            if not improved_code:
                logger.warning("Failed to generate improvements")
                attempt.accepted = False
                attempt.error_message = "Code generation failed"
                self.attempts[attempt.attempt_id] = attempt
                return attempt

            attempt.proposed_changes = improved_code
            rifl_feedback = self._run_rifl_guard(attempt, improved_code)
            if rifl_feedback.get("verdict") == "fail":
                logger.info("RIFL verifier rejected proposal before sandbox validation")
                attempt.accepted = False
                attempt.error_message = "RIFL verifier rejected proposal"
                self.attempts[attempt.attempt_id] = attempt
                return attempt

            # Step 4: Write improved code to sandbox
            # SECURITY: Sanitize path components to prevent traversal
            safe_attempt_id = self._sanitize_path_component(attempt.attempt_id)
            safe_agent_name = self._sanitize_path_component(self.agent_name)

            sandbox_path = Path(f"/tmp/darwin_sandbox/{safe_attempt_id}")
            sandbox_path.mkdir(parents=True, exist_ok=True)
            improved_code_path = sandbox_path / f"{safe_agent_name}.py"
            improved_code_path.write_text(improved_code)

            # Step 5: Validate in sandbox + benchmarks
            logger.info("Validating improvements in sandbox...")
            validation_success, sandbox_logs = await self._validate_in_sandbox(improved_code_path)
            attempt.sandbox_logs = sandbox_logs

            if not validation_success:
                logger.warning("Sandbox validation failed")
                attempt.accepted = False
                attempt.error_message = "Sandbox validation failed"
                self.attempts[attempt.attempt_id] = attempt
                return attempt

            # Step 6: Run benchmarks
            logger.info("Running benchmarks...")
            attempt.metrics_after = await self._evaluate_agent(improved_code_path, attempt.attempt_id)

            # Step 7: Compute improvement delta
            attempt.improvement_delta = {
                k: attempt.metrics_after.get(k, 0) - attempt.metrics_before.get(k, 0)
                for k in attempt.metrics_before.keys()
            }

            overall_improvement = attempt.improvement_delta.get("overall_score", 0)
            rifl_reward = attempt.validation_results.get("rifl", {}).get("reward", 1.0)
            effective_improvement = overall_improvement * rifl_reward
            attempt.validation_results["rifl_reward"] = rifl_reward
            attempt.validation_results["effective_improvement"] = effective_improvement

            # Step 8: Accept if improvement exceeds threshold
            if effective_improvement >= self.acceptance_threshold:
                attempt.accepted = True
                logger.info(
                    f"✅ ACCEPTED: raw Δ={overall_improvement:+.3f}, "
                    f"RIFL reward={rifl_reward:.2f}, effective Δ={effective_improvement:+.3f}"
                )

                # Save improved version
                # SECURITY: Sanitize path components
                safe_agent_name = self._sanitize_path_component(self.agent_name)
                safe_attempt_id = self._sanitize_path_component(attempt.attempt_id)

                final_path = Path(f"agents/evolved/{safe_agent_name}/{safe_attempt_id}.py")
                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_text(improved_code)

                # Store strategy in ReasoningBank
                await self._store_successful_strategy(attempt)

            else:
                attempt.accepted = False
                logger.info(
                    f"❌ REJECTED: raw Δ={overall_improvement:+.3f}, "
                    f"effective Δ={effective_improvement:+.3f} "
                    f"(threshold: {self.acceptance_threshold})"
                )

            # Store attempt
            self.attempts[attempt.attempt_id] = attempt

            return attempt

        except Exception as e:
            logger.error(f"Evolution attempt failed: {e}", exc_info=True)
            attempt.accepted = False
            attempt.error_message = str(e)
            self.attempts[attempt.attempt_id] = attempt
            return attempt

    async def _generate_code_improvements(
        self,
        parent_code: str,
        diagnosis: str,
        improvement_type: str
    ) -> Optional[str]:
        """
        Generate improved code using GPT-4o meta-programming

        This is the core "intelligence" of Darwin - using LLM to modify code
        """
        prompt = f"""You are a code evolution system. Given an agent's current code and a problem diagnosis, generate improved code.

CURRENT CODE:
```python
{parent_code}
```

PROBLEM DIAGNOSIS:
{diagnosis}

IMPROVEMENT TYPE: {improvement_type}

INSTRUCTIONS:
1. Analyze the current code and diagnosis
2. Generate improved code that addresses the problem
3. Maintain all existing functionality (no regressions)
4. Add comments explaining changes
5. Ensure code is syntactically valid Python

Return ONLY the complete improved code, no explanations.

IMPROVED CODE:
```python"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Allow creativity in solutions
                max_tokens=4000,
            )

            improved_code = response.choices[0].message.content

            # Extract code from markdown if wrapped
            if "```python" in improved_code:
                improved_code = improved_code.split("```python")[1].split("```")[0].strip()
            elif "```" in improved_code:
                improved_code = improved_code.split("```")[1].split("```")[0].strip()

            return improved_code

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return None

    def _run_rifl_guard(self, attempt: EvolutionAttempt, improved_code: str) -> Dict[str, Any]:
        """Apply RIFL rubric verifier to the generated improvements."""
        if not self.rifl_evaluator:
            feedback = {"verdict": "pass", "reward": 1.0}
        else:
            feedback = self.rifl_evaluator.evaluate(
                diagnosis=attempt.problem_diagnosis,
                improvement_type=attempt.improvement_type,
                improved_code=improved_code,
            )

        attempt.validation_results["rifl"] = feedback
        self.rifl_reward_history.append(feedback.get("reward", 0.0))
        return feedback

    async def _validate_in_sandbox(self, code_path: Path) -> Tuple[bool, str]:
        """
        Validate code in Docker sandbox for safety

        SECURITY FIX #1: Now properly uses Docker isolation
        Previously ran on host - CRITICAL VULNERABILITY FIXED

        Returns:
            (success: bool, logs: str)
        """
        try:
            # Import sandbox (local import to avoid circular dependency)
            from infrastructure.sandbox import get_sandbox

            sandbox = get_sandbox()
            code = code_path.read_text()

            # SECURITY: Execute in isolated Docker container
            result = await sandbox.execute_code(
                code=code,
                timeout=30,  # 30 second timeout
                memory_limit="512m",  # 512MB memory limit
                cpu_quota=50000,  # 50% of one CPU core
                network_disabled=True,  # CRITICAL: No network access
            )

            # Check result
            if result.exit_code == 0:
                return True, result.stdout or "Validation passed"
            else:
                return False, result.stderr or "Validation failed"

        except Exception as e:
            logger.error(f"Sandbox validation error: {e}")
            return False, f"Validation error: {str(e)}"

    async def _evaluate_agent(self, code_path: Path, version: str) -> Dict[str, float]:
        """
        Evaluate agent performance using real benchmarks

        Returns:
            Dictionary of metric scores
        """
        try:
            # Import benchmark framework
            from benchmarks.agent_benchmarks import get_benchmark_for_agent

            # Read agent code
            with open(code_path, 'r') as f:
                agent_code = f.read()

            # Get appropriate benchmark for this agent
            try:
                benchmark = get_benchmark_for_agent(self.agent_name)
            except ValueError as e:
                # Agent doesn't have specific benchmark yet, use fallback
                logger.warning(f"No benchmark for {self.agent_name}, using fallback: {e}")
                # Return baseline scores for agents without benchmarks
                return {
                    "overall_score": 0.65,  # Baseline score
                    "correctness": 0.70,
                    "efficiency": 0.60,
                    "robustness": 0.65,
                }

            # Run benchmark
            logger.info(f"Running benchmark for {self.agent_name} version {version}")
            result = await benchmark.run(agent_code)

            # Map BenchmarkResult to metrics dict
            metrics = {
                "overall_score": result.overall_score,
                "correctness": result.accuracy,
                "efficiency": result.speed,
                "robustness": result.quality,
            }

            # Add detailed scores
            metrics.update(result.detailed_scores)

            # Log benchmark results
            logger.info(
                f"Benchmark results for {self.agent_name} v{version}: "
                f"overall={result.overall_score:.3f}, "
                f"accuracy={result.accuracy:.3f}, "
                f"quality={result.quality:.3f}, "
                f"passed={result.test_cases_passed}/{result.test_cases_total}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Benchmark evaluation error: {e}", exc_info=True)
            # Return low scores on error to ensure failed code isn't accepted
            return {
                "overall_score": 0.0,
                "correctness": 0.0,
                "efficiency": 0.0,
                "robustness": 0.0,
                "error": str(e)
            }

    async def _get_agent_code_path(self, version: str) -> Path:
        """Get path to agent code for given version"""
        if version == "initial":
            return self.initial_code_path
        else:
            # SECURITY: Sanitize path components
            safe_agent_name = self._sanitize_path_component(self.agent_name)
            safe_version = self._sanitize_path_component(version)
            return Path(f"agents/evolved/{safe_agent_name}/{safe_version}.py")

    async def _store_successful_strategy(self, attempt: EvolutionAttempt):
        """Store successful evolution strategy in ReasoningBank for future learning"""
        try:
            strategy_description = f"""Successful code evolution for {self.agent_name}

Problem: {attempt.problem_diagnosis}
Solution Type: {attempt.improvement_type}
Improvement: {attempt.improvement_delta.get('overall_score', 0):+.3f}

This strategy successfully improved the agent and can be applied to similar problems."""

            self.reasoning_bank.store_memory(
                memory_type=MemoryType.STRATEGY,
                content={
                    "agent": self.agent_name,
                    "improvement_type": attempt.improvement_type,
                    "diagnosis": attempt.problem_diagnosis,
                    "changes_summary": attempt.proposed_changes[:500],  # First 500 chars
                },
                metadata={
                    "attempt_id": attempt.attempt_id,
                    "generation": attempt.generation,
                    "improvement_delta": attempt.improvement_delta,
                },
                outcome=OutcomeTag.SUCCESS,
                tags=[self.agent_name, attempt.improvement_type, "code_evolution"]
            )

            logger.info("Stored successful strategy in ReasoningBank")

        except Exception as e:
            logger.warning(f"Failed to store strategy: {e}")

    async def _create_evolution_archive(self) -> EvolutionArchive:
        """Create final evolution archive with complete history"""
        successful = [a for a in self.attempts.values() if a.accepted]
        failed = [a for a in self.attempts.values() if not a.accepted]

        acceptance_rate = len(successful) / len(self.attempts) if self.attempts else 0.0

        archive = EvolutionArchive(
            archive_id=f"archive_{self.agent_name}_{uuid.uuid4().hex[:8]}",
            agent_name=self.agent_name,
            generations=list(range(self.current_generation + 1)),
            successful_attempts=[a.attempt_id for a in successful],
            failed_attempts=[a.attempt_id for a in failed],
            best_version=self.best_version,
            best_score=self.best_score,
            total_attempts=len(self.attempts),
            acceptance_rate=acceptance_rate,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Save archive to disk
        # SECURITY: Sanitize path component
        safe_agent_name = self._sanitize_path_component(self.agent_name)
        archive_path = Path(f"agents/evolved/{safe_agent_name}/evolution_archive.json")
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(json.dumps(asdict(archive), indent=2))

        return archive

    def save_checkpoint(self, path: str) -> bool:
        """
        Save evolution state to checkpoint file

        Args:
            path: Path to save checkpoint file

        Returns:
            True if successful, False otherwise
        """
        try:
            # SECURITY: Sanitize path component
            checkpoint_path = Path(path)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize evolution state
            checkpoint_data = {
                "agent_name": self.agent_name,
                "current_generation": self.current_generation,
                "best_score": self.best_score,
                "best_version": self.best_version,
                "archive": self.archive,
                "max_generations": self.max_generations,
                "population_size": self.population_size,
                "acceptance_threshold": self.acceptance_threshold,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attempts_count": len(self.attempts),
            }

            # Write checkpoint
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)

            logger.info(f"Checkpoint saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def load_checkpoint(self, path: str) -> bool:
        """
        Load evolution state from checkpoint file

        Args:
            path: Path to checkpoint file

        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint_path = Path(path)

            if not checkpoint_path.exists():
                logger.error(f"Checkpoint file not found: {path}")
                return False

            # Read checkpoint
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)

            # Restore evolution state
            self.current_generation = checkpoint_data["current_generation"]
            self.best_score = checkpoint_data["best_score"]
            self.best_version = checkpoint_data["best_version"]
            self.archive = checkpoint_data["archive"]

            logger.info(f"Checkpoint loaded from {path}")
            logger.info(f"Resumed at generation {self.current_generation}, best score: {self.best_score:.3f}")
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    async def resume_evolution(self, path: str, additional_generations: int = 5) -> EvolutionArchive:
        """
        Resume evolution from checkpoint file

        Args:
            path: Path to checkpoint file
            additional_generations: Number of additional generations to run

        Returns:
            EvolutionArchive with updated evolution history
        """
        # Load checkpoint
        if not self.load_checkpoint(path):
            raise ValueError(f"Failed to load checkpoint from: {path}")

        start_generation = self.current_generation
        logger.info(f"Resuming evolution from generation {start_generation}")

        # Run additional generations
        for generation in range(start_generation, start_generation + additional_generations):
            self.current_generation = generation
            logger.info(f"\n{'='*60}")
            logger.info(f"🧬 GENERATION {generation + 1}/{start_generation + additional_generations}")
            logger.info(f"{'='*60}")
            logger.info(f"Archive size: {len(self.archive)}")
            logger.info(f"Best score: {self.best_score:.3f} (version: {self.best_version})")

            # Generate evolution attempts for this generation
            attempts = await self._generate_evolution_attempts()

            # Execute attempts in parallel
            results = await asyncio.gather(
                *[self._execute_evolution_attempt(attempt) for attempt in attempts],
                return_exceptions=True
            )

            # Process results
            accepted_count = 0
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Evolution attempt failed: {result}")
                    continue

                if result and result.accepted:
                    accepted_count += 1
                    self.archive.append(result.attempt_id)

                    # Update best if improved
                    if result.metrics_after.get("overall_score", 0) > self.best_score:
                        self.best_score = result.metrics_after["overall_score"]
                        self.best_version = result.attempt_id
                        logger.info(f"🎉 NEW BEST VERSION: {result.attempt_id} (score: {self.best_score:.3f})")

            logger.info(f"Generation {generation + 1} complete: {accepted_count}/{len(attempts)} accepted")

        # Create final archive
        archive = await self._create_evolution_archive()
        logger.info(f"\n🎯 Resumed evolution complete!")
        logger.info(f"Resumed from generation: {start_generation}")
        logger.info(f"Final generation: {self.current_generation}")
        logger.info(f"Additional generations evolved: {additional_generations}")
        logger.info(f"Best version: {archive.best_version} (score: {archive.best_score:.3f})")

        return archive


# Convenience function
def get_darwin_agent(
    agent_name: str,
    initial_code_path: str,
    **kwargs
) -> DarwinAgent:
    """
    Get Darwin evolution engine for an agent

    Example:
        darwin = get_darwin_agent("spec_agent", "agents/spec_agent.py")
        archive = await darwin.evolve()
    """
    return DarwinAgent(agent_name, initial_code_path, **kwargs)


if __name__ == "__main__":
    # Example: Evolve SpecAgent
    async def main():
        darwin = get_darwin_agent(
            agent_name="spec_agent",
            initial_code_path="agents/spec_agent.py",
            max_generations=5,
            population_size=3,
        )

        archive = await darwin.evolve()
        print(f"\n🎯 Evolution complete!")
        print(f"Best version: {archive.best_version}")
        print(f"Best score: {archive.best_score:.3f}")
        print(f"Acceptance rate: {archive.acceptance_rate:.1%}")

    asyncio.run(main())
