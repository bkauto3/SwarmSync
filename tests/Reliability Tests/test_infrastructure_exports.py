"""
Test Infrastructure Exports

Verifies that all expected classes and functions are properly exported
from the infrastructure module.

Author: Hudson (Code Review Agent)
Date: October 25, 2025
"""

import pytest


class TestInfrastructureExports:
    """Test that all infrastructure exports are accessible"""

    def test_error_handling_exports(self):
        """Test error handling classes and functions are exported"""
        from infrastructure import (
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
            ErrorRecoveryStrategy,
            ERROR_HANDLER_AVAILABLE
        )

        # Verify availability flag is True
        assert ERROR_HANDLER_AVAILABLE, "Error handler should be available"

        # Verify classes are not None
        assert ErrorCategory is not None
        assert ErrorSeverity is not None
        assert ErrorContext is not None
        assert RetryConfig is not None
        assert CircuitBreaker is not None
        assert OrchestrationError is not None
        assert DecompositionError is not None
        assert RoutingError is not None
        assert ValidationError is not None
        assert LLMError is not None
        assert ResourceError is not None

        # Verify functions are not None
        assert log_error_with_context is not None
        assert retry_with_backoff is not None
        assert graceful_fallback is not None
        assert handle_orchestration_error is not None
        assert ErrorRecoveryStrategy is not None

        print("✓ Error handling exports verified")

    def test_visual_compression_exports(self):
        """Test visual compression classes are exported"""
        from infrastructure import (
            VisualMemoryCompressor,
            VisualCompressionMode,
            VISUAL_COMPRESSION_AVAILABLE
        )

        # If not available (missing dependencies), skip verification
        if not VISUAL_COMPRESSION_AVAILABLE:
            print("⚠ Visual compression not available (missing dependencies)")
            assert VisualMemoryCompressor is None
            assert VisualCompressionMode is None
            pytest.skip("Visual compression dependencies not installed")
            return

        # Verify classes are not None
        assert VisualMemoryCompressor is not None
        assert VisualCompressionMode is not None

        # Verify VisualCompressionMode has expected attributes
        assert hasattr(VisualCompressionMode, 'TEXT')
        assert hasattr(VisualCompressionMode, 'BASE')
        assert hasattr(VisualCompressionMode, 'SMALL')
        assert hasattr(VisualCompressionMode, 'TINY')

        print("✓ Visual compression exports verified")

    def test_error_category_enum(self):
        """Test ErrorCategory enum has expected values"""
        from infrastructure import ErrorCategory

        assert hasattr(ErrorCategory, 'DECOMPOSITION')
        assert hasattr(ErrorCategory, 'ROUTING')
        assert hasattr(ErrorCategory, 'VALIDATION')
        assert hasattr(ErrorCategory, 'NETWORK')
        assert hasattr(ErrorCategory, 'RESOURCE')
        assert hasattr(ErrorCategory, 'LLM')
        assert hasattr(ErrorCategory, 'SECURITY')
        assert hasattr(ErrorCategory, 'UNKNOWN')

        print("✓ ErrorCategory enum verified")

    def test_error_severity_enum(self):
        """Test ErrorSeverity enum has expected values"""
        from infrastructure import ErrorSeverity

        assert hasattr(ErrorSeverity, 'LOW')
        assert hasattr(ErrorSeverity, 'MEDIUM')
        assert hasattr(ErrorSeverity, 'HIGH')
        assert hasattr(ErrorSeverity, 'FATAL')

        print("✓ ErrorSeverity enum verified")

    def test_circuit_breaker_instantiation(self):
        """Test CircuitBreaker can be instantiated"""
        from infrastructure import CircuitBreaker

        cb = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2
        )

        assert cb is not None
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.success_threshold == 2
        assert cb.state == "CLOSED"

        print("✓ CircuitBreaker instantiation verified")

    def test_retry_config_instantiation(self):
        """Test RetryConfig can be instantiated"""
        from infrastructure import RetryConfig

        config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )

        assert config is not None
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

        # Test delay calculation
        delay = config.get_delay(0)
        assert delay >= 0.5  # With jitter, should be >= 50% of initial_delay
        assert delay <= 1.5  # With jitter, should be <= 150% of initial_delay

        print("✓ RetryConfig instantiation verified")

    def test_orchestration_error_hierarchy(self):
        """Test OrchestrationError exception hierarchy"""
        from infrastructure import (
            OrchestrationError,
            DecompositionError,
            RoutingError,
            ValidationError,
            LLMError,
            ResourceError
        )

        # Test base class
        error = OrchestrationError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

        # Test derived classes
        decomp_error = DecompositionError("Decomposition failed")
        assert isinstance(decomp_error, OrchestrationError)

        routing_error = RoutingError("Routing failed")
        assert isinstance(routing_error, OrchestrationError)

        validation_error = ValidationError("Validation failed")
        assert isinstance(validation_error, OrchestrationError)

        llm_error = LLMError("LLM failed")
        assert isinstance(llm_error, OrchestrationError)

        resource_error = ResourceError("Resource limit exceeded")
        assert isinstance(resource_error, OrchestrationError)

        print("✓ OrchestrationError hierarchy verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
