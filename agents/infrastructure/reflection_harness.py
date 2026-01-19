"""
ReflectionHarness - Automatic Quality Reflection Wrapper
Version: 1.0
Last Updated: October 15, 2025

Decorator pattern wrapper that adds automatic reflection capability to any agent.
Implements regeneration logic with configurable retry attempts and fallback behaviors.

Key Features:
- Decorator pattern for zero-friction integration
- Automatic regeneration on quality failures (max 2 attempts by default)
- Statistics tracking (attempts, regenerations, success rate)
- Configurable fallback behaviors (warn, fail, pass)
- Thread-safe async implementation
- Compatible with any agent output format

PURPOSE: Ensure all agent outputs meet quality standards before finalization
PATTERN: Decorator/Wrapper with automatic retry logic
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Awaitable, TypeVar, Generic
from enum import Enum
from functools import wraps

# Import ReflectionAgent with lazy import to avoid circular dependency
# CIRCULAR IMPORT FIX: agents.__init__.py imports all agents (deploy_agent, spec_agent, etc.)
# which import reflection_harness, creating a cycle when we import from agents package
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.reflection_agent import ReflectionAgent, ReflectionResult

# Runtime imports - use lazy import to avoid circular dependency through agents.__init__
REFLECTION_AGENT_AVAILABLE = False
ReflectionAgent = None
ReflectionResult = None
get_reflection_agent = None

def _lazy_import_reflection_agent():
    """Lazy import to avoid circular dependency"""
    global REFLECTION_AGENT_AVAILABLE, ReflectionAgent, ReflectionResult, get_reflection_agent

    if REFLECTION_AGENT_AVAILABLE:
        return True

    try:
        # Import directly from module, not from agents package (avoids __init__.py imports)
        from agents.reflection_agent import (
            ReflectionAgent as _ReflectionAgent,
            ReflectionResult as _ReflectionResult,
            get_reflection_agent as _get_reflection_agent
        )
        ReflectionAgent = _ReflectionAgent
        ReflectionResult = _ReflectionResult
        get_reflection_agent = _get_reflection_agent
        REFLECTION_AGENT_AVAILABLE = True
        return True
    except ImportError as e:
        logging.warning(f"ReflectionAgent not available - harness disabled: {e}")
        return False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for output


class FallbackBehavior(Enum):
    """Behavior when reflection fails and max retries exhausted"""
    WARN = "warn"  # Log warning and return best attempt
    FAIL = "fail"  # Raise exception
    PASS = "pass"  # Accept output anyway (bypass reflection)


@dataclass
class ReflectionStats:
    """Statistics for reflection harness"""
    total_invocations: int = 0
    total_reflections: int = 0
    total_regenerations: int = 0
    total_passes_first_attempt: int = 0
    total_passes_after_regen: int = 0
    total_failures: int = 0
    average_attempts: float = 0.0
    average_reflection_time: float = 0.0


@dataclass
class HarnessResult(Generic[T]):
    """
    Result from harness-wrapped execution

    Contains both the final output and metadata about the reflection process.
    """
    output: T
    passed_reflection: bool
    reflection_result: Optional[Any]  # ReflectionResult type (avoiding circular import)
    attempts_made: int
    regenerations: int
    total_time_seconds: float
    fallback_used: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReflectionHarness:
    """
    Wrapper that adds automatic reflection to agent outputs

    Usage Pattern 1 - Wrap function directly:
        harness = ReflectionHarness()
        result = await harness.wrap(my_function, "output content", "code")

    Usage Pattern 2 - Decorator:
        harness = ReflectionHarness()

        @harness.decorator(content_type="code")
        async def my_agent_function(spec):
            return generate_code(spec)

        result = await my_agent_function(spec)

    Features:
    - Automatic reflection on output
    - Regeneration on failure (configurable max attempts)
    - Statistics tracking
    - Fallback behaviors for edge cases
    - Thread-safe operation

    Configuration:
    - max_attempts: Maximum generation attempts (default: 2)
    - quality_threshold: Minimum quality score (default: 0.70)
    - fallback_behavior: What to do on ultimate failure
    - enable_stats: Track statistics
    """

    def __init__(
        self,
        reflection_agent: Optional["ReflectionAgent"] = None,
        max_attempts: int = 2,
        quality_threshold: float = 0.70,
        fallback_behavior: FallbackBehavior = FallbackBehavior.WARN,
        enable_stats: bool = True
    ):
        """
        Initialize ReflectionHarness

        Args:
            reflection_agent: ReflectionAgent instance (or create default)
            max_attempts: Maximum generation attempts
            quality_threshold: Minimum quality score to pass
            fallback_behavior: Behavior on ultimate failure
            enable_stats: Enable statistics tracking
        """
        # Lazy import on initialization (not module load)
        if not _lazy_import_reflection_agent():
            raise ImportError("ReflectionAgent not available - cannot create harness")

        if reflection_agent is not None:
            self.reflection_agent = reflection_agent
        else:
            self.reflection_agent = get_reflection_agent(
                quality_threshold=quality_threshold
            )
        self.max_attempts = max_attempts
        self.quality_threshold = quality_threshold
        self.fallback_behavior = fallback_behavior
        self.enable_stats = enable_stats

        # Statistics
        self.stats = ReflectionStats()
        self._lock = asyncio.Lock()

        logger.info("✅ ReflectionHarness initialized")
        logger.info(f"   Max attempts: {max_attempts}")
        logger.info(f"   Quality threshold: {quality_threshold}")
        logger.info(f"   Fallback behavior: {fallback_behavior.value}")

    async def wrap(
        self,
        generator_func: Callable[..., Awaitable[str]],
        content_type: str,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> HarnessResult[str]:
        """
        Wrap a generator function with automatic reflection

        Args:
            generator_func: Async function that generates content
            content_type: Type of content (code, documentation, etc.)
            context: Additional context for reflection
            *args: Positional arguments for generator_func
            **kwargs: Keyword arguments for generator_func

        Returns:
            HarnessResult with output and reflection metadata

        Raises:
            Exception: If fallback_behavior is FAIL and reflection fails
        """
        start_time = time.time()
        context = context or {}

        logger.info(f"🔄 Starting reflection harness for {content_type}")

        best_output = None
        best_result = None
        best_score = 0.0
        attempts = 0

        # Update stats
        if self.enable_stats:
            async with self._lock:
                self.stats.total_invocations += 1

        # Attempt generation + reflection loop
        while attempts < self.max_attempts:
            attempts += 1

            logger.info(f"   Attempt {attempts}/{self.max_attempts}...")

            try:
                # Generate content
                output = await generator_func(*args, **kwargs)

                # Reflect on output
                reflection_result = await self.reflection_agent.reflect(
                    content=output,
                    content_type=content_type,
                    context=context
                )

                # Update stats
                if self.enable_stats:
                    async with self._lock:
                        self.stats.total_reflections += 1

                # Track best attempt
                if reflection_result.overall_score > best_score:
                    best_output = output
                    best_result = reflection_result
                    best_score = reflection_result.overall_score

                # Check if passes
                if reflection_result.passes_threshold:
                    logger.info(f"   ✅ Passed reflection on attempt {attempts}")

                    # Update stats
                    if self.enable_stats:
                        async with self._lock:
                            if attempts == 1:
                                self.stats.total_passes_first_attempt += 1
                            else:
                                self.stats.total_passes_after_regen += 1
                                self.stats.total_regenerations += attempts - 1

                    return HarnessResult(
                        output=output,
                        passed_reflection=True,
                        reflection_result=reflection_result,
                        attempts_made=attempts,
                        regenerations=attempts - 1,
                        total_time_seconds=time.time() - start_time,
                        fallback_used=False,
                        metadata={
                            "content_type": content_type,
                            "final_score": reflection_result.overall_score
                        }
                    )
                else:
                    logger.warning(f"   ❌ Failed reflection on attempt {attempts}")
                    logger.warning(f"      Score: {reflection_result.overall_score:.2f}")
                    logger.warning(f"      Critical issues: {len(reflection_result.critical_issues)}")

                    # Log critical issues for debugging
                    for issue in reflection_result.critical_issues[:3]:
                        logger.warning(f"      - {issue}")

            except Exception as e:
                logger.error(f"   ❌ Error during attempt {attempts}: {e}")
                # Continue to next attempt

        # All attempts exhausted - apply fallback behavior
        logger.error(f"⚠️  All {self.max_attempts} attempts failed reflection")
        logger.error(f"   Best score achieved: {best_score:.2f}")
        logger.error(f"   Fallback behavior: {self.fallback_behavior.value}")

        # Update stats
        if self.enable_stats:
            async with self._lock:
                self.stats.total_failures += 1
                self.stats.total_regenerations += attempts - 1

        if self.fallback_behavior == FallbackBehavior.FAIL:
            raise Exception(
                f"Reflection failed after {self.max_attempts} attempts. "
                f"Best score: {best_score:.2f} (threshold: {self.quality_threshold})"
            )
        elif self.fallback_behavior == FallbackBehavior.PASS:
            logger.warning("⚠️  Bypassing reflection (fallback: PASS)")
            return HarnessResult(
                output=best_output or "",
                passed_reflection=False,
                reflection_result=best_result,
                attempts_made=attempts,
                regenerations=attempts - 1,
                total_time_seconds=time.time() - start_time,
                fallback_used=True,
                metadata={
                    "content_type": content_type,
                    "fallback_reason": "max_attempts_exhausted"
                }
            )
        else:  # FallbackBehavior.WARN (default)
            logger.warning("⚠️  Returning best attempt (fallback: WARN)")
            return HarnessResult(
                output=best_output or "",
                passed_reflection=False,
                reflection_result=best_result,
                attempts_made=attempts,
                regenerations=attempts - 1,
                total_time_seconds=time.time() - start_time,
                fallback_used=True,
                metadata={
                    "content_type": content_type,
                    "best_score": best_score,
                    "fallback_reason": "returned_best_attempt"
                }
            )

    def decorator(
        self,
        content_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator that wraps a function with reflection

        Usage:
            harness = ReflectionHarness()

            @harness.decorator(content_type="code")
            async def generate_code(spec):
                return build_code(spec)

            result = await generate_code(spec)

        Args:
            content_type: Type of content being generated
            context: Additional context for reflection

        Returns:
            Decorator function
        """
        def wrapper(func: Callable[..., Awaitable[str]]):
            @wraps(func)
            async def wrapped(*args, **kwargs) -> HarnessResult[str]:
                # Create a wrapper that calls the original function
                async def call_func():
                    return await func(*args, **kwargs)

                return await self.wrap(
                    generator_func=call_func,
                    content_type=content_type,
                    context=context
                )
            return wrapped
        return wrapper

    async def wrap_with_extraction(
        self,
        generator_func: Callable[..., Awaitable[Dict[str, Any]]],
        content_extractor: Callable[[Dict[str, Any]], str],
        content_type: str,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> HarnessResult[Dict[str, Any]]:
        """
        Wrap a function that returns structured data (e.g., JSON)

        Extracts content for reflection, then returns full structured output.

        Usage:
            result = await harness.wrap_with_extraction(
                generator_func=build_application,
                content_extractor=lambda x: x["code_files"]["main.py"],
                content_type="code",
                spec=my_spec
            )

        Args:
            generator_func: Function that returns Dict
            content_extractor: Function to extract reflection content from Dict
            content_type: Type of content
            context: Additional context
            *args: Args for generator_func
            **kwargs: Kwargs for generator_func

        Returns:
            HarnessResult with full Dict output
        """
        # Wrapper that extracts content
        async def extract_and_generate(*gen_args, **gen_kwargs) -> str:
            full_output = await generator_func(*gen_args, **gen_kwargs)
            return content_extractor(full_output)

        # Run reflection on extracted content
        result = await self.wrap(
            generator_func=extract_and_generate,
            content_type=content_type,
            context=context,
            *args,
            **kwargs
        )

        # Re-generate full output (we only reflected on extracted content)
        # In production, we'd store the full output - for now, regenerate
        full_output = await generator_func(*args, **kwargs)

        return HarnessResult(
            output=full_output,
            passed_reflection=result.passed_reflection,
            reflection_result=result.reflection_result,
            attempts_made=result.attempts_made,
            regenerations=result.regenerations,
            total_time_seconds=result.total_time_seconds,
            fallback_used=result.fallback_used,
            metadata=result.metadata
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get harness statistics

        Returns:
            Dictionary with statistics
        """
        total = self.stats.total_invocations
        avg_attempts = (
            (self.stats.total_reflections / total)
            if total > 0 else 0.0
        )

        success_rate = (
            (self.stats.total_passes_first_attempt + self.stats.total_passes_after_regen) / total
            if total > 0 else 0.0
        )

        first_attempt_success_rate = (
            self.stats.total_passes_first_attempt / total
            if total > 0 else 0.0
        )

        return {
            "total_invocations": self.stats.total_invocations,
            "total_reflections": self.stats.total_reflections,
            "total_regenerations": self.stats.total_regenerations,
            "total_passes_first_attempt": self.stats.total_passes_first_attempt,
            "total_passes_after_regen": self.stats.total_passes_after_regen,
            "total_failures": self.stats.total_failures,
            "average_attempts": avg_attempts,
            "success_rate": success_rate,
            "first_attempt_success_rate": first_attempt_success_rate,
            "quality_threshold": self.quality_threshold,
            "max_attempts": self.max_attempts,
            "fallback_behavior": self.fallback_behavior.value
        }

    def reset_statistics(self):
        """Reset all statistics to zero"""
        self.stats = ReflectionStats()
        logger.info("📊 Reflection harness statistics reset")


# Singleton instance for convenient access
_default_harness: Optional[ReflectionHarness] = None


def get_default_harness(
    quality_threshold: float = 0.70,
    max_attempts: int = 2,
    fallback_behavior: FallbackBehavior = FallbackBehavior.WARN
) -> ReflectionHarness:
    """
    Get or create default ReflectionHarness singleton

    Args:
        quality_threshold: Minimum quality score
        max_attempts: Maximum generation attempts
        fallback_behavior: Fallback behavior on failure

    Returns:
        ReflectionHarness instance
    """
    global _default_harness

    # Ensure ReflectionAgent is available before creating harness
    if not _lazy_import_reflection_agent():
        raise ImportError("ReflectionAgent not available - cannot create default harness")

    if _default_harness is None:
        _default_harness = ReflectionHarness(
            quality_threshold=quality_threshold,
            max_attempts=max_attempts,
            fallback_behavior=fallback_behavior
        )

    return _default_harness


# Convenience decorator using default harness
def reflect_on(
    content_type: str,
    context: Optional[Dict[str, Any]] = None,
    quality_threshold: float = 0.70,
    max_attempts: int = 2
):
    """
    Convenience decorator using default harness

    Usage:
        @reflect_on(content_type="code", quality_threshold=0.80)
        async def my_generator():
            return generate_code()

    Args:
        content_type: Type of content
        context: Additional context
        quality_threshold: Minimum quality score
        max_attempts: Maximum attempts

    Returns:
        Decorator function
    """
    harness = get_default_harness(
        quality_threshold=quality_threshold,
        max_attempts=max_attempts
    )
    return harness.decorator(content_type=content_type, context=context)
