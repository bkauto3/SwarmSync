"""
Centralized Error Handling Utilities for Genesis Orchestration System

Provides:
1. Retry logic with exponential backoff
2. Error classification and categorization
3. Graceful degradation strategies
4. Structured error logging with context
5. Circuit breaker pattern for repeated failures
"""
import asyncio
import logging
import time
import json
from typing import Callable, Any, Optional, Dict, List, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error classification for targeted recovery strategies"""
    DECOMPOSITION = "decomposition"  # Task decomposition failures
    ROUTING = "routing"              # Agent routing failures
    VALIDATION = "validation"        # Plan validation failures
    NETWORK = "network"              # API timeouts, connection issues
    RESOURCE = "resource"            # Memory/task limits exceeded
    LLM = "llm"                      # LLM-specific failures
    SECURITY = "security"            # Security violations
    UNKNOWN = "unknown"              # Unclassified errors


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Warning, system continues
    MEDIUM = "medium"    # Recoverable, retry recommended
    HIGH = "high"        # Critical, requires fallback
    FATAL = "fatal"      # Unrecoverable, abort operation


@dataclass
class ErrorContext:
    """Structured error context for debugging"""
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    error_message: str
    component: str  # Which component failed (htdag, halo, aop)
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for logging"""
        return {
            "category": self.error_category.value,
            "severity": self.error_severity.value,
            "message": self.error_message,
            "component": self.component,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), indent=2)


class RetryConfig:
    """Configuration for retry logic with exponential backoff"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add random jitter (0-50% of delay) to prevent thundering herd
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent repeated failures

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self) -> None:
        """Record successful operation"""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit breaker recovered: {self.success_count} successes")
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
        elif self.state == "CLOSED":
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.error(
                    f"Circuit breaker opened: {self.failure_count} consecutive failures"
                )
            self.state = "OPEN"

    def can_attempt(self) -> bool:
        """Check if operation should be attempted"""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if recovery timeout elapsed
            if self.last_failure_time and \
               time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = "HALF_OPEN"
                return True
            return False

        # HALF_OPEN state
        return True


class OrchestrationError(Exception):
    """Base exception for orchestration errors"""
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}


class DecompositionError(OrchestrationError):
    """Task decomposition failures"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.DECOMPOSITION,
            severity=ErrorSeverity.HIGH,
            context=context
        )


class RoutingError(OrchestrationError):
    """Agent routing failures"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.ROUTING,
            severity=ErrorSeverity.HIGH,
            context=context
        )


class ValidationError(OrchestrationError):
    """Plan validation failures"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class LLMError(OrchestrationError):
    """LLM-specific failures (timeout, rate limit, invalid response)"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.LLM,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class ResourceError(OrchestrationError):
    """Resource limit exceeded (memory, tasks, budget)"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            context=context
        )


def log_error_with_context(error_context: ErrorContext) -> None:
    """Log error with full structured context"""
    log_level = {
        ErrorSeverity.LOW: logging.WARNING,
        ErrorSeverity.MEDIUM: logging.ERROR,
        ErrorSeverity.HIGH: logging.ERROR,
        ErrorSeverity.FATAL: logging.CRITICAL
    }.get(error_context.error_severity, logging.ERROR)

    logger.log(
        log_level,
        f"[{error_context.component}] {error_context.error_category.value.upper()} ERROR: "
        f"{error_context.error_message}",
        extra={"error_context": error_context.to_dict()}
    )


async def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    error_types: Optional[List[Type[Exception]]] = None,
    component: str = "unknown",
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Retry async function with exponential backoff

    Args:
        func: Async function to retry
        config: Retry configuration (defaults to 3 retries, exponential backoff)
        error_types: List of exception types to retry (default: all)
        component: Component name for logging
        context: Additional context for error logging

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    error_types = error_types or [Exception]
    context = context or {}

    last_error = None

    for attempt in range(config.max_retries + 1):
        try:
            result = await func()

            if attempt > 0:
                logger.info(
                    f"[{component}] Retry succeeded on attempt {attempt + 1}/{config.max_retries + 1}"
                )

            return result

        except tuple(error_types) as e:
            last_error = e

            if attempt < config.max_retries:
                delay = config.get_delay(attempt)

                error_ctx = ErrorContext(
                    error_category=ErrorCategory.UNKNOWN,
                    error_severity=ErrorSeverity.MEDIUM,
                    error_message=f"Attempt {attempt + 1} failed: {str(e)}",
                    component=component,
                    metadata={
                        **context,
                        "attempt": attempt + 1,
                        "max_retries": config.max_retries,
                        "next_delay": delay
                    }
                )

                log_error_with_context(error_ctx)

                logger.info(f"[{component}] Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
            else:
                # Final attempt failed
                error_ctx = ErrorContext(
                    error_category=ErrorCategory.UNKNOWN,
                    error_severity=ErrorSeverity.HIGH,
                    error_message=f"All {config.max_retries + 1} attempts failed: {str(e)}",
                    component=component,
                    metadata=context
                )

                log_error_with_context(error_ctx)
                raise


def graceful_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    component: str = "unknown",
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for graceful degradation: try primary, fall back on failure

    Usage:
        @graceful_fallback(primary_llm_func, fallback_heuristic_func, component="htdag")
        async def decompose_task(...):
            # Will try primary first, fall back to heuristic on failure
    """
    async def wrapper(*args, **kwargs):
        context_dict = context or {}

        try:
            return await primary_func(*args, **kwargs)

        except Exception as e:
            logger.warning(
                f"[{component}] Primary function failed: {str(e)}, falling back to alternative"
            )

            error_ctx = ErrorContext(
                error_category=ErrorCategory.UNKNOWN,
                error_severity=ErrorSeverity.MEDIUM,
                error_message=f"Primary failed, using fallback: {str(e)}",
                component=component,
                metadata=context_dict
            )

            log_error_with_context(error_ctx)

            return await fallback_func(*args, **kwargs)

    return wrapper


def handle_orchestration_error(
    error: Exception,
    component: str,
    task_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ErrorContext:
    """
    Classify and handle orchestration errors

    Args:
        error: Exception that occurred
        component: Component where error occurred (htdag, halo, aop)
        task_id: Task ID if applicable
        agent_name: Agent name if applicable
        context: Additional context

    Returns:
        ErrorContext with classification and metadata
    """
    import traceback

    # Classify error
    if isinstance(error, (DecompositionError, ValidationError, RoutingError, LLMError, ResourceError)):
        category = error.category
        severity = error.severity
        error_context_data = error.context
    elif isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        category = ErrorCategory.NETWORK
        severity = ErrorSeverity.MEDIUM
        error_context_data = {}
    elif isinstance(error, MemoryError):
        category = ErrorCategory.RESOURCE
        severity = ErrorSeverity.HIGH
        error_context_data = {}
    elif "SecurityError" in str(type(error).__name__):
        category = ErrorCategory.SECURITY
        severity = ErrorSeverity.FATAL
        error_context_data = {}
    else:
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        error_context_data = {}

    error_ctx = ErrorContext(
        error_category=category,
        error_severity=severity,
        error_message=str(error),
        component=component,
        task_id=task_id,
        agent_name=agent_name,
        stack_trace=traceback.format_exc(),
        metadata={**(context or {}), **error_context_data}
    )

    log_error_with_context(error_ctx)

    return error_ctx


class ErrorRecoveryStrategy:
    """Defines recovery strategies for different error categories"""

    @staticmethod
    async def recover_from_decomposition_error(
        error_ctx: ErrorContext,
        fallback_func: Optional[Callable] = None
    ) -> Any:
        """
        Recovery strategy for decomposition errors

        Strategy:
        1. Try simpler decomposition (reduce depth)
        2. Use heuristic-based decomposition
        3. Return single-task DAG as last resort
        """
        logger.info(f"[{error_ctx.component}] Attempting decomposition error recovery")

        if fallback_func:
            try:
                result = await fallback_func()
                logger.info(f"[{error_ctx.component}] Fallback decomposition succeeded")
                return result
            except Exception as e:
                logger.error(f"[{error_ctx.component}] Fallback decomposition also failed: {e}")

        # Last resort: return None and let caller handle
        return None

    @staticmethod
    async def recover_from_routing_error(
        error_ctx: ErrorContext,
        fallback_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        Recovery strategy for routing errors

        Strategy:
        1. Try generic fallback agent (builder_agent)
        2. Mark task as unassigned for manual review
        """
        logger.info(f"[{error_ctx.component}] Attempting routing error recovery")

        if fallback_agent:
            logger.info(f"[{error_ctx.component}] Using fallback agent: {fallback_agent}")
            return fallback_agent

        # Default fallback
        logger.warning(f"[{error_ctx.component}] No suitable agent found, using builder_agent as fallback")
        return "builder_agent"

    @staticmethod
    async def recover_from_validation_error(
        error_ctx: ErrorContext,
        retry_routing: bool = True
    ) -> Dict[str, Any]:
        """
        Recovery strategy for validation errors

        Strategy:
        1. Retry routing with stricter constraints
        2. Relax validation criteria (if safe)
        3. Return partial plan with warnings
        """
        logger.info(f"[{error_ctx.component}] Attempting validation error recovery")

        return {
            "retry_recommended": retry_routing,
            "relaxed_validation": False,
            "warnings": [error_ctx.error_message]
        }

    @staticmethod
    async def recover_from_llm_error(
        error_ctx: ErrorContext,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Recovery strategy for LLM errors

        Strategy:
        1. Check cache for similar requests
        2. Use simpler prompt/model
        3. Fall back to heuristics
        """
        logger.info(f"[{error_ctx.component}] Attempting LLM error recovery")

        return {
            "use_fallback_model": True,
            "use_cached_response": use_cache,
            "use_heuristics": True
        }
