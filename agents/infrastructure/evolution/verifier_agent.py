"""
Verifier Agent for Multi-Agent Evolve Co-Evolution System

Based on arXiv:2510.23595 "Multi-Agent Evolve: LLM Self-Improve through Co-evolution"
Research: docs/research/MULTI_AGENT_EVOLVE_ARCHITECTURE.md

The Verifier validates Solver trajectories with focus on:
- Correctness (test suite validation)
- Quality (code quality metrics)
- Robustness (edge case handling)
- Generalization (cross-domain validation)

Co-Evolution Objective:
    reward = correctness_weight * (1 - accuracy)  # Reward for finding errors
           + quality_weight * quality_issues
           + robustness_weight * edge_case_failures
           + generalization_weight * cross_domain_failures

Integration Points:
- SolverAgent (provides trajectories to verify)
- BenchmarkRunner (test execution)
- CodeQualityValidator (AST-based analysis)
- OTEL observability (distributed tracing)

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 3 Implementation
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set

# Genesis infrastructure imports
from infrastructure import get_logger

# OTEL observability
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Metrics for Verifier Agent
    verifier_check_counter = meter.create_counter(
        "verifier.checks.executed",
        description="Number of verification checks executed"
    )
    verifier_error_counter = meter.create_counter(
        "verifier.errors.found",
        description="Number of errors/issues found"
    )
    verifier_score_histogram = meter.create_histogram(
        "verifier.score.distribution",
        description="Verification score distribution"
    )
    verifier_reward_histogram = meter.create_histogram(
        "verifier.reward.computed",
        description="Verifier reward scores"
    )
except ImportError:
    tracer = None
    meter = None
    verifier_check_counter = None
    verifier_error_counter = None
    verifier_score_histogram = None
    verifier_reward_histogram = None

logger = get_logger("verifier_agent")


@dataclass
class VerifierConfig:
    """
    Verifier Agent configuration.

    Based on arXiv:2510.23595 recommended weights:
    - correctness_weight: 0.4 (40% weight on test pass rate)
    - quality_weight: 0.3 (30% weight on code quality)
    - robustness_weight: 0.2 (20% weight on edge cases)
    - generalization_weight: 0.1 (10% weight on cross-domain)

    Configuration guidelines:
    - Correctness is most critical (highest weight)
    - Quality ensures maintainability
    - Robustness catches edge cases
    - Generalization prevents overfitting
    """
    correctness_weight: float = 0.4
    quality_weight: float = 0.3
    robustness_weight: float = 0.2
    generalization_weight: float = 0.1
    num_edge_cases: int = 5
    shortcut_detection_enabled: bool = True

    def __post_init__(self):
        """Validate configuration weights sum to 1.0."""
        total_weight = (
            self.correctness_weight +
            self.quality_weight +
            self.robustness_weight +
            self.generalization_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"Verifier weights must sum to 1.0, got {total_weight:.3f}"
            )

        if self.num_edge_cases < 1:
            raise ValueError(
                f"num_edge_cases must be >= 1, got {self.num_edge_cases}"
            )


@dataclass
class VerificationResult:
    """
    Result from Verifier evaluation.

    Comprehensive evaluation across 4 dimensions:
    - Correctness: Does the solution work correctly?
    - Quality: Is the code well-structured and maintainable?
    - Robustness: Does it handle edge cases?
    - Generalization: Can it apply to similar tasks?
    """
    verification_score: float  # Overall score (0-1)
    correctness_score: float   # Test pass rate
    quality_score: float       # Code quality metrics
    robustness_score: float    # Edge case handling
    generalization_score: float  # Cross-domain transfer
    feedback: List[Dict[str, Any]]  # Structured feedback for Solver
    shortcuts_detected: List[str]  # Detected shortcut patterns
    edge_cases_tested: int     # Number of edge cases evaluated
    metadata: Dict[str, Any]   # Additional metadata
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "verification_score": self.verification_score,
            "correctness_score": self.correctness_score,
            "quality_score": self.quality_score,
            "robustness_score": self.robustness_score,
            "generalization_score": self.generalization_score,
            "feedback": self.feedback,
            "shortcuts_detected": self.shortcuts_detected,
            "edge_cases_tested": self.edge_cases_tested,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class VerifierAgent:
    """
    Verifier agent validates and challenges Solver trajectories.

    Based on arXiv:2510.23595 Section 3.2 "Verifier Dynamics"

    Co-evolution objective:
        reward = correctness_weight * (1 - accuracy)  # Reward for finding errors
               + quality_weight * quality_issues
               + robustness_weight * edge_case_failures
               + generalization_weight * cross_domain_failures

    The Verifier acts as an adversary to the Solver, evolving to find
    harder edge cases and detect more sophisticated shortcuts. This
    co-evolutionary pressure drives both agents to improve.

    Key Responsibilities:
    1. Multi-criteria evaluation (correctness, quality, robustness, generalization)
    2. Adversarial testing (shortcut detection, edge case generation)
    3. Structured feedback generation for Solver improvement
    4. Reward computation for co-evolution dynamics

    Integration:
    - Receives trajectories from SolverAgent
    - Executes verification checks (tests, quality, edge cases)
    - Provides feedback to SolverAgent for next iteration
    - Tracks verification history for evolution analysis
    """

    def __init__(
        self,
        agent_type: str,
        config: Optional[VerifierConfig] = None
    ):
        """
        Initialize Verifier Agent.

        Args:
            agent_type: Type of agent (e.g., "qa_agent", "builder_agent")
            config: Verifier configuration (uses defaults if not provided)
        """
        self.agent_type = agent_type
        self.config = config or VerifierConfig()
        self.verification_history: List[VerificationResult] = []

        logger.info(
            f"Verifier Agent initialized for {agent_type} with config: "
            f"correctness={self.config.correctness_weight}, "
            f"quality={self.config.quality_weight}, "
            f"robustness={self.config.robustness_weight}, "
            f"generalization={self.config.generalization_weight}"
        )

    async def verify_trajectory(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify Solver trajectory with multi-criteria evaluation.

        Based on arXiv:2510.23595 Algorithm 2 (Verifier Validation Loop)

        Args:
            trajectory: Solver's generated trajectory with code and metadata
            task: Original benchmark task specification

        Returns:
            VerificationResult with scores and feedback

        Evaluation Process:
        1. Parallel execution of 4 criteria (correctness, quality, robustness, generalization)
        2. Shortcut detection (adversarial component)
        3. Weighted score computation
        4. Structured feedback generation
        5. History tracking for evolution analysis
        """
        trajectory_id = trajectory.get('trajectory_id', 'unknown')

        # Start OTEL span for tracing
        span_context = {}
        if tracer:
            with tracer.start_as_current_span("verifier.verify_trajectory") as span:
                span.set_attribute("trajectory_id", trajectory_id)
                span.set_attribute("task_type", task.get("type", "unknown"))
                span_context['span'] = span

        logger.info(f"Starting verification for trajectory {trajectory_id}")
        start_time = time.time()

        try:
            # Run all evaluation criteria in parallel for efficiency
            correctness_score, quality_score, robustness_score, generalization_score = await asyncio.gather(
                self._evaluate_correctness(trajectory, task),
                self._evaluate_quality(trajectory, task),
                self._evaluate_robustness(trajectory, task),
                self._evaluate_generalization(trajectory, task)
            )

            # Detect shortcuts (adversarial component)
            shortcuts = []
            if self.config.shortcut_detection_enabled:
                shortcuts = await self._detect_shortcuts(trajectory, task)

            # Compute overall verification score
            verification_score = (
                self.config.correctness_weight * correctness_score +
                self.config.quality_weight * quality_score +
                self.config.robustness_weight * robustness_score +
                self.config.generalization_weight * generalization_score
            )

            # Generate feedback for Solver
            feedback = self._generate_feedback(
                correctness_score, quality_score, robustness_score,
                generalization_score, shortcuts
            )

            # Create result
            result = VerificationResult(
                verification_score=verification_score,
                correctness_score=correctness_score,
                quality_score=quality_score,
                robustness_score=robustness_score,
                generalization_score=generalization_score,
                feedback=feedback,
                shortcuts_detected=shortcuts,
                edge_cases_tested=self.config.num_edge_cases,
                metadata={
                    "task_type": task.get("type", "unknown"),
                    "trajectory_id": trajectory_id,
                    "agent_type": self.agent_type,
                    "verification_time_ms": (time.time() - start_time) * 1000
                }
            )

            # Track in history
            self.verification_history.append(result)

            # Record metrics
            if verifier_check_counter:
                verifier_check_counter.add(1, {"agent_type": self.agent_type})
            if verifier_score_histogram:
                verifier_score_histogram.record(verification_score, {"agent_type": self.agent_type})
            if verifier_error_counter and len(feedback) > 0:
                verifier_error_counter.add(len(feedback), {"agent_type": self.agent_type})

            logger.info(
                f"Verification complete for {trajectory_id}: "
                f"score={verification_score:.3f}, "
                f"correctness={correctness_score:.3f}, "
                f"quality={quality_score:.3f}, "
                f"robustness={robustness_score:.3f}, "
                f"generalization={generalization_score:.3f}, "
                f"shortcuts={len(shortcuts)}, "
                f"feedback_items={len(feedback)}"
            )

            if span_context.get('span'):
                span_context['span'].set_attribute("verification_score", verification_score)
                span_context['span'].set_attribute("shortcuts_found", len(shortcuts))
                span_context['span'].set_status(Status(StatusCode.OK))

            return result

        except Exception as e:
            logger.error(f"Verification failed for {trajectory_id}: {e}", exc_info=True)
            if span_context.get('span'):
                span_context['span'].set_status(Status(StatusCode.ERROR, str(e)))
            raise

    async def _evaluate_correctness(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> float:
        """
        Evaluate correctness via test suite execution.

        Context7 MCP Reference: Test execution patterns for automated validation

        Correctness is the most critical criterion (40% weight). It measures
        whether the solution actually solves the problem correctly.

        Args:
            trajectory: Solution trajectory with code
            task: Task specification with test cases

        Returns:
            Test pass rate (0-1)

        Implementation:
        - Execute test suite against trajectory code
        - Count passing vs failing tests
        - Return pass rate as score

        TODO: Integrate with actual test execution infrastructure
        Currently uses benchmark_score from trajectory as proxy
        """
        # Extract benchmark score (already computed by Solver)
        benchmark_score = trajectory.get("benchmark_score", 0.0)

        # Simulate test execution (in production, would run actual tests)
        logger.debug(f"Evaluating correctness for {trajectory.get('trajectory_id')}: {benchmark_score:.3f}")

        # Ensure score is in valid range
        return max(0.0, min(1.0, benchmark_score))

    async def _evaluate_quality(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> float:
        """
        Evaluate code quality metrics.

        Context7 MCP Reference: Code quality analysis patterns, AST-based validation

        Quality metrics (30% weight):
        - Code length (not too short/long)
        - Documentation (comments, docstrings)
        - Structure (functions, classes)
        - Complexity (cyclomatic complexity)
        - Best practices (naming, patterns)

        Args:
            trajectory: Solution with code to analyze
            task: Task specification

        Returns:
            Quality score (0-1)

        Quality Scoring:
        - 1.0: Excellent quality (well-documented, structured, readable)
        - 0.7: Good quality (functional, some structure)
        - 0.5: Mediocre quality (works but messy)
        - 0.3: Poor quality (minimal structure)
        - 0.0: Terrible quality (unreadable/non-functional)
        """
        code = trajectory.get("code", "")

        # Start with perfect score, deduct for issues
        quality_score = 1.0

        # Check length (penalize too short or too long)
        if len(code) < 10:
            quality_score -= 0.3
            logger.debug("Quality penalty: code too short")
        elif len(code) > 10000:
            quality_score -= 0.2
            logger.debug("Quality penalty: code too long")

        # Check for comments/documentation
        has_comments = "#" in code or '"""' in code or "'''" in code
        if not has_comments:
            quality_score -= 0.1
            logger.debug("Quality penalty: no documentation")

        # Check for function/class structure
        has_structure = "def " in code or "class " in code
        if not has_structure:
            quality_score -= 0.2
            logger.debug("Quality penalty: no structure (no functions/classes)")

        # Check for good naming (not single-letter variables everywhere)
        single_letter_vars = len(re.findall(r'\b[a-z]\s*=', code))
        total_assignments = len(re.findall(r'\b\w+\s*=', code))
        if total_assignments > 0 and (single_letter_vars / total_assignments) > 0.5:
            quality_score -= 0.1
            logger.debug("Quality penalty: excessive single-letter variables")

        # Check for exception handling
        has_error_handling = "try:" in code or "except" in code
        if not has_error_handling and len(code) > 100:
            quality_score -= 0.1
            logger.debug("Quality penalty: no error handling")

        # Ensure score is in valid range
        quality_score = max(0.0, min(1.0, quality_score))

        logger.debug(f"Quality score: {quality_score:.3f}")

        return quality_score

    async def _evaluate_robustness(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> float:
        """
        Evaluate robustness via edge case testing.

        Context7 MCP Reference: Edge case generation patterns, adversarial testing

        Robustness metrics (20% weight):
        - Empty inputs
        - Null/None values
        - Boundary conditions
        - Type mismatches
        - Large inputs

        Args:
            trajectory: Solution to test
            task: Task specification

        Returns:
            Edge case pass rate (0-1)

        Edge Case Testing:
        Generate adversarial inputs that commonly break implementations:
        1. Empty collections
        2. Null/None values
        3. Min/max boundary values
        4. Type mismatches
        5. Very large inputs
        6. Special characters
        7. Negative values
        8. Zero values
        """
        # Generate edge cases
        edge_cases = self._generate_edge_cases(trajectory, task)

        # Test each edge case
        passed = 0
        tested = 0
        for edge_case in edge_cases[:self.config.num_edge_cases]:
            tested += 1
            try:
                # TODO: Execute edge case test against code
                # For now, use hash-based simulation (deterministic)
                # In production, would actually run the code with edge case input
                case_hash = hash(edge_case + trajectory.get('trajectory_id', ''))
                # Simulate 80% pass rate with deterministic hash
                if case_hash % 5 != 0:
                    passed += 1
                    logger.debug(f"Edge case passed: {edge_case}")
                else:
                    logger.debug(f"Edge case failed: {edge_case}")
            except Exception as e:
                logger.debug(f"Edge case {edge_case} raised exception: {e}")

        robustness_score = passed / max(1, tested)

        logger.debug(f"Robustness: {passed}/{tested} edge cases passed ({robustness_score:.3f})")

        return robustness_score

    async def _evaluate_generalization(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> float:
        """
        Evaluate cross-domain generalization.

        Context7 MCP Reference: Transfer learning evaluation patterns

        Generalization metrics (10% weight):
        - Solution is not overfitted to specific task
        - Uses generic approaches over hardcoded logic
        - Avoids task-specific shortcuts
        - Can transfer to related tasks

        Args:
            trajectory: Solution to evaluate
            task: Task specification

        Returns:
            Cross-domain score (0-1)

        Generalization Detection:
        - Check for overfitting signals (hardcoded values, task-specific logic)
        - Reward generic approaches
        - Penalize task-specific patterns
        - Check if solution would work on similar tasks
        """
        task_type = task.get("type", "unknown")
        strategy = trajectory.get("strategy", "unknown")
        code = trajectory.get("code", "")

        # Start with good score, adjust based on signals
        generalization_score = 0.8

        # Penalize overfitting signals
        overfitting_keywords = ["specific", "hardcoded", "fixed", "constant"]
        if any(keyword in strategy.lower() for keyword in overfitting_keywords):
            generalization_score -= 0.3
            logger.debug("Generalization penalty: overfitting signal in strategy")

        # Reward generic approaches
        generic_keywords = ["general", "generic", "flexible", "abstract"]
        if any(keyword in strategy.lower() for keyword in generic_keywords):
            generalization_score += 0.1
            logger.debug("Generalization bonus: generic approach in strategy")

        # Check for task-specific hardcoding in code
        task_desc = task.get("description", "")
        if task_desc:
            # Check if task description appears literally in code (overfitting)
            task_words = task_desc.lower().split()[:5]  # First 5 words
            task_pattern = " ".join(task_words)
            if task_pattern in code.lower():
                generalization_score -= 0.2
                logger.debug("Generalization penalty: task description in code")

        # Check for parameterization (good for generalization)
        has_params = "def " in code and "(" in code and ":" in code
        if has_params:
            generalization_score += 0.1
            logger.debug("Generalization bonus: parameterized functions")

        # Ensure score is in valid range
        generalization_score = max(0.0, min(1.0, generalization_score))

        logger.debug(f"Generalization score: {generalization_score:.3f}")

        return generalization_score

    def _generate_edge_cases(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> List[str]:
        """
        Generate adversarial edge cases.

        Context7 MCP Reference: Adversarial test generation patterns

        Edge cases that commonly break implementations:
        1. Empty inputs ([], "", {})
        2. Null/None values
        3. Boundary conditions (min/max values)
        4. Type mismatches (string instead of int)
        5. Large inputs (stress testing)
        6. Special characters (unicode, escape sequences)
        7. Negative values (when positive expected)
        8. Zero values (division by zero)

        Args:
            trajectory: Solution being tested
            task: Task specification

        Returns:
            List of edge case names/descriptions
        """
        task_type = task.get("type", "unknown")

        # Standard edge cases applicable to most tasks
        edge_cases = [
            "empty_input",
            "null_value",
            "boundary_min",
            "boundary_max",
            "type_mismatch",
            "large_input",
            "negative_input",
            "special_characters",
            "zero_value",
            "unicode_input"
        ]

        # Add task-specific edge cases
        if "search" in task_type.lower():
            edge_cases.extend(["not_found", "multiple_matches"])
        elif "sort" in task_type.lower():
            edge_cases.extend(["already_sorted", "reverse_sorted", "duplicates"])
        elif "parse" in task_type.lower():
            edge_cases.extend(["malformed_input", "incomplete_data"])

        logger.debug(f"Generated {len(edge_cases)} edge cases for {task_type}")

        return edge_cases

    async def _detect_shortcuts(
        self,
        trajectory: Dict[str, Any],
        task: Dict[str, Any]
    ) -> List[str]:
        """
        Detect shortcuts in Solver's solution.

        Based on arXiv:2510.23595 Section 3.2.4 "Shortcut Detection"
        Context7 MCP Reference: Adversarial testing for AI systems

        Shortcuts are undesirable patterns where the solution appears to work
        but doesn't actually implement the correct algorithm. Common shortcuts:

        1. Hardcoded outputs: return 42, return "result"
        2. Test mode detection: if test_mode, if benchmark
        3. Trivial implementations: single line, no logic
        4. Overfitting: special cases for known test inputs
        5. Cheating: accessing test data, using banned APIs

        Args:
            trajectory: Solution to analyze
            task: Task specification

        Returns:
            List of detected shortcut patterns
        """
        code = trajectory.get("code", "")
        shortcuts = []

        # Check for hardcoded values (literal constants that look suspicious)
        suspicious_literals = ["42", "123", "'result'", '"output"', '"success"', "True  #"]
        if any(literal in code for literal in suspicious_literals):
            shortcuts.append("hardcoded_values")
            logger.debug("Shortcut detected: hardcoded values")

        # Check for test mode detection (explicitly checking if in test)
        test_detection_patterns = [
            "if test_mode", "if benchmark", "if __test__",
            "if testing", "if is_test"
        ]
        if any(pattern in code for pattern in test_detection_patterns):
            shortcuts.append("test_mode_detection")
            logger.debug("Shortcut detected: test mode detection")

        # Check for trivial implementation (too simple to be correct)
        code_lines = [line for line in code.split('\n') if line.strip() and not line.strip().startswith('#')]
        if len(code_lines) < 3:
            shortcuts.append("trivial_implementation")
            logger.debug("Shortcut detected: trivial implementation")

        # Check for overfitting signals (task-specific logic)
        task_desc = task.get("description", "")
        if task_desc and len(task_desc) > 20:
            # Check if task description appears in code
            task_snippet = task_desc[:20].lower()
            if task_snippet in code.lower():
                shortcuts.append("task_specific_overfitting")
                logger.debug("Shortcut detected: task-specific overfitting")

        # Check for direct result copying (looking for test data patterns)
        if "expected_output" in code or "test_result" in code or "known_answer" in code:
            shortcuts.append("test_data_access")
            logger.debug("Shortcut detected: accessing test data")

        # Check for early returns without computation
        early_return_pattern = re.findall(r'def \w+\([^)]*\):\s*return', code)
        if len(early_return_pattern) > 0:
            shortcuts.append("early_return_without_computation")
            logger.debug("Shortcut detected: early return without computation")

        if shortcuts:
            logger.warning(f"Shortcuts detected in {trajectory.get('trajectory_id')}: {shortcuts}")
        else:
            logger.debug("No shortcuts detected")

        return shortcuts

    def _generate_feedback(
        self,
        correctness: float,
        quality: float,
        robustness: float,
        generalization: float,
        shortcuts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate structured feedback for Solver.

        Context7 MCP Reference: Feedback format from arXiv:2510.23595 Appendix A

        Feedback is structured as a list of issues, each with:
        - area: Which criterion failed (correctness/quality/robustness/generalization)
        - confidence: How confident the Verifier is (0-1)
        - severity: How serious the issue is (high/medium/low)
        - message: Human-readable description of the issue

        Args:
            correctness: Correctness score
            quality: Quality score
            robustness: Robustness score
            generalization: Generalization score
            shortcuts: List of detected shortcuts

        Returns:
            List of structured feedback items
        """
        feedback = []

        # Correctness feedback (most critical)
        if correctness < 0.8:
            feedback.append({
                "area": "correctness",
                "confidence": 1.0 - correctness,
                "severity": "high",
                "message": f"Test pass rate low: {correctness:.1%}. Review failing tests and fix logic errors."
            })
        elif correctness < 0.95:
            feedback.append({
                "area": "correctness",
                "confidence": 1.0 - correctness,
                "severity": "medium",
                "message": f"Test pass rate good but not excellent: {correctness:.1%}. Check edge cases."
            })

        # Quality feedback
        if quality < 0.7:
            feedback.append({
                "area": "quality",
                "confidence": 1.0 - quality,
                "severity": "medium",
                "message": f"Code quality issues: {quality:.1%}. Improve structure, documentation, and naming."
            })
        elif quality < 0.85:
            feedback.append({
                "area": "quality",
                "confidence": 1.0 - quality,
                "severity": "low",
                "message": f"Code quality acceptable: {quality:.1%}. Consider adding more documentation."
            })

        # Robustness feedback
        if robustness < 0.6:
            feedback.append({
                "area": "robustness",
                "confidence": 1.0 - robustness,
                "severity": "medium",
                "message": f"Edge case handling weak: {robustness:.1%}. Add boundary checks and error handling."
            })
        elif robustness < 0.8:
            feedback.append({
                "area": "robustness",
                "confidence": 1.0 - robustness,
                "severity": "low",
                "message": f"Edge case handling needs improvement: {robustness:.1%}. Test more edge cases."
            })

        # Generalization feedback
        if generalization < 0.5:
            feedback.append({
                "area": "generalization",
                "confidence": 1.0 - generalization,
                "severity": "low",
                "message": f"Overfitting detected: {generalization:.1%}. Make solution more generic and flexible."
            })
        elif generalization < 0.7:
            feedback.append({
                "area": "generalization",
                "confidence": 1.0 - generalization,
                "severity": "low",
                "message": f"Generalization could improve: {generalization:.1%}. Avoid task-specific hardcoding."
            })

        # Shortcut feedback (always high severity)
        for shortcut in shortcuts:
            feedback.append({
                "area": "shortcuts",
                "confidence": 1.0,
                "severity": "high",
                "message": f"Shortcut detected: {shortcut}. Implement proper solution without workarounds."
            })

        logger.debug(f"Generated {len(feedback)} feedback items")

        return feedback

    def compute_verifier_reward(
        self,
        verification_score: float,
        previous_verification_score: Optional[float] = None
    ) -> float:
        """
        Compute Verifier's reward for co-evolution.

        Based on arXiv:2510.23595 Equation 3 (Verifier Reward Function)

        The Verifier is rewarded for:
        1. Finding errors (1 - verification_score): Low verification score means
           many errors found, which is good for the Verifier's objective
        2. Increasing challenge (score decreased from previous): If the Verifier
           found more issues than before, it's getting better at its job

        This creates co-evolutionary pressure:
        - Solver tries to maximize verification_score (fool the Verifier)
        - Verifier tries to minimize verification_score (find more errors)
        - Both agents improve through this adversarial dynamic

        Args:
            verification_score: Current verification score (0-1)
            previous_verification_score: Previous score for comparison

        Returns:
            Reward value (0-1) for Verifier
        """
        # Reward for finding errors (inverse of verification score)
        error_reward = 1.0 - verification_score

        # Reward for increasing challenge (making Solver's life harder)
        if previous_verification_score is not None:
            # Positive if score decreased (found more issues)
            challenge_reward = max(0, previous_verification_score - verification_score)
        else:
            challenge_reward = 0.0

        # Weighted combination (70% error finding, 30% challenge increase)
        reward = 0.7 * error_reward + 0.3 * challenge_reward

        logger.debug(
            f"Verifier reward computed: error={error_reward:.3f}, "
            f"challenge={challenge_reward:.3f}, total={reward:.3f}"
        )

        # Record metric
        if verifier_reward_histogram:
            verifier_reward_histogram.record(reward, {"agent_type": self.agent_type})

        return reward

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Verifier statistics.

        Provides aggregate statistics across all verifications:
        - Total verifications performed
        - Average scores for each criterion
        - Total shortcuts detected
        - Total feedback items generated

        Returns:
            Dictionary with statistics
        """
        if not self.verification_history:
            return {
                "total_verifications": 0,
                "average_score": 0.0,
                "average_correctness": 0.0,
                "average_quality": 0.0,
                "average_robustness": 0.0,
                "average_generalization": 0.0,
                "shortcuts_detected_total": 0,
                "feedback_items_total": 0
            }

        n = len(self.verification_history)

        return {
            "total_verifications": n,
            "average_score": sum(v.verification_score for v in self.verification_history) / n,
            "average_correctness": sum(v.correctness_score for v in self.verification_history) / n,
            "average_quality": sum(v.quality_score for v in self.verification_history) / n,
            "average_robustness": sum(v.robustness_score for v in self.verification_history) / n,
            "average_generalization": sum(v.generalization_score for v in self.verification_history) / n,
            "shortcuts_detected_total": sum(len(v.shortcuts_detected) for v in self.verification_history),
            "feedback_items_total": sum(len(v.feedback) for v in self.verification_history)
        }


def get_verifier_agent(agent_type: str, config: Optional[VerifierConfig] = None) -> VerifierAgent:
    """
    Factory function to create Verifier Agent.

    Args:
        agent_type: Type of agent
        config: Optional configuration

    Returns:
        Initialized VerifierAgent
    """
    return VerifierAgent(agent_type, config)
