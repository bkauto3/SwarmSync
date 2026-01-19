"""
Genesis Infrastructure Layer
Foundation utilities for agent system
"""

from .intent_abstraction import IntentExtractor, Intent, Action, Motive, BusinessType, Priority
from .logging_config import get_logger, genesis_logger, infrastructure_logger, agent_logger, a2a_logger

# Import error handling
try:
    from .error_handler import (
        ErrorCategory,
        ErrorSeverity,
        ErrorContext,
        RetryConfig,
        CircuitBreaker,
        OrchestrationError,
        DecompositionError,
        RoutingError,
        ValidationError,
        LLMError,
        ResourceError,
        log_error_with_context,
        retry_with_backoff,
        graceful_fallback,
        handle_orchestration_error,
        ErrorRecoveryStrategy
    )
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    ERROR_HANDLER_AVAILABLE = False
    ErrorCategory = None
    ErrorSeverity = None
    ErrorContext = None
    RetryConfig = None
    CircuitBreaker = None
    OrchestrationError = None
    DecompositionError = None
    RoutingError = None
    ValidationError = None
    LLMError = None
    ResourceError = None
    log_error_with_context = None
    retry_with_backoff = None
    graceful_fallback = None
    handle_orchestration_error = None
    ErrorRecoveryStrategy = None

# Import visual compression
try:
    from .visual_memory_compressor import VisualMemoryCompressor, VisualCompressionMode
    VISUAL_COMPRESSION_AVAILABLE = True
except ImportError:
    VISUAL_COMPRESSION_AVAILABLE = False
    VisualMemoryCompressor = None
    VisualCompressionMode = None

# Import graph attention mechanism
try:
    from .hybrid_rag_retriever import GraphAttentionMechanism, AttentionGuidedGraphTraversal
    GRAPH_ATTENTION_AVAILABLE = True
except ImportError:
    GRAPH_ATTENTION_AVAILABLE = False
    GraphAttentionMechanism = None
    AttentionGuidedGraphTraversal = None

# Import trajectory pool for OperatorType
try:
    from .trajectory_pool import OperatorType
    TRAJECTORY_POOL_AVAILABLE = True
except ImportError:
    TRAJECTORY_POOL_AVAILABLE = False
    OperatorType = None

# Import learning infrastructure (with graceful fallback)
try:
    from .reasoning_bank import get_reasoning_bank, ReasoningBank, MemoryType, OutcomeTag
    REASONING_BANK_AVAILABLE = True
except ImportError:
    REASONING_BANK_AVAILABLE = False
    get_reasoning_bank = None
    ReasoningBank = None
    MemoryType = None
    OutcomeTag = None

try:
    from .replay_buffer import get_replay_buffer, ReplayBuffer, Trajectory, ActionStep
    REPLAY_BUFFER_AVAILABLE = True
except ImportError:
    REPLAY_BUFFER_AVAILABLE = False
    get_replay_buffer = None
    ReplayBuffer = None
    Trajectory = None
    ActionStep = None

try:
    from .reflection_harness import ReflectionHarness, with_reflection
    REFLECTION_HARNESS_AVAILABLE = True
except ImportError:
    REFLECTION_HARNESS_AVAILABLE = False
    ReflectionHarness = None
    with_reflection = None

try:
    from .agentoccam_client import (
        AgentOccamClient,
        AgentOccamConfig,
        get_agent_occam_client,
    )
    AGENT_OCCAM_AVAILABLE = True
except ImportError:
    AGENT_OCCAM_AVAILABLE = False
    AgentOccamClient = None
    AgentOccamConfig = None
    get_agent_occam_client = None

try:
    from .aatc_system import (
        ToolDefinition,
        ToolField,
        ToolSchema,
        ToolRegistry,
        ToolValidationError,
        get_tool_registry,
    )
    AATC_SYSTEM_AVAILABLE = True
except ImportError:
    AATC_SYSTEM_AVAILABLE = False
    ToolDefinition = None
    ToolField = None
    ToolSchema = None
    ToolRegistry = None
    ToolValidationError = None
    get_tool_registry = None

__all__ = [
    # Intent abstraction
    "IntentExtractor",
    "Intent",
    "Action",
    "Motive",
    "BusinessType",
    "Priority",
    # Logging
    "get_logger",
    "genesis_logger",
    "infrastructure_logger",
    "agent_logger",
    "a2a_logger",
    # Error handling
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext",
    "RetryConfig",
    "CircuitBreaker",
    "OrchestrationError",
    "DecompositionError",
    "RoutingError",
    "ValidationError",
    "LLMError",
    "ResourceError",
    "log_error_with_context",
    "retry_with_backoff",
    "graceful_fallback",
    "handle_orchestration_error",
    "ErrorRecoveryStrategy",
    # Visual compression
    "VisualMemoryCompressor",
    "VisualCompressionMode",
    # Graph attention
    "GraphAttentionMechanism",
    "AttentionGuidedGraphTraversal",
    # Trajectory pool
    "OperatorType",
    # Learning infrastructure
    "get_reasoning_bank",
    "ReasoningBank",
    "MemoryType",
    "OutcomeTag",
    "get_replay_buffer",
    "ReplayBuffer",
    "Trajectory",
    "ActionStep",
    "ReflectionHarness",
    "with_reflection",
    "AgentOccamClient",
    "AgentOccamConfig",
    "get_agent_occam_client",
    "ToolDefinition",
    "ToolField",
    "ToolSchema",
    "ToolRegistry",
    "ToolValidationError",
    "get_tool_registry",
    # Availability flags
    "ERROR_HANDLER_AVAILABLE",
    "VISUAL_COMPRESSION_AVAILABLE",
    "GRAPH_ATTENTION_AVAILABLE",
    "TRAJECTORY_POOL_AVAILABLE",
    "REASONING_BANK_AVAILABLE",
    "REPLAY_BUFFER_AVAILABLE",
    "REFLECTION_HARNESS_AVAILABLE",
    "AGENT_OCCAM_AVAILABLE",
    "AATC_SYSTEM_AVAILABLE",
]
