"""
Tests for Local LLM Provider Integration (P1-5)

Author: Claude (P1 Fixes)
Date: November 3, 2025
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from infrastructure.local_llm_provider import (
    LocalLLMProvider,
    get_local_llm_provider
)
from infrastructure.hybrid_llm_client import FallbackStrategy


class TestLocalLLMProvider:
    """Tests for LocalLLMProvider."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test provider initializes correctly."""
        provider = LocalLLMProvider(
            enable_local_llm=True,
            fallback_strategy=FallbackStrategy.FULL_CASCADE
        )

        assert provider.enable_local_llm is True
        assert provider.hybrid_client is not None

    @pytest.mark.asyncio
    async def test_initialization_from_env(self, monkeypatch):
        """Test provider reads configuration from environment."""
        monkeypatch.setenv("USE_LOCAL_LLM", "true")
        monkeypatch.setenv("LOCAL_LLM_FALLBACK_STRATEGY", "OPENAI_ONLY")

        provider = LocalLLMProvider()

        assert provider.enable_local_llm is True

    @pytest.mark.asyncio
    async def test_generate_text_mock(self):
        """Test generate_text calls hybrid client."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock the hybrid client
        provider.hybrid_client.complete_text = AsyncMock(return_value="Test response")

        async with provider:
            response = await provider.generate_text(
                system_prompt="You are helpful",
                user_prompt="Hello",
                temperature=0.7,
                max_tokens=100
            )

        assert response == "Test response"
        provider.hybrid_client.complete_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_structured_output_valid_json(self):
        """Test structured output with valid JSON response."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock response with JSON
        provider.hybrid_client.complete_text = AsyncMock(
            return_value='{"result": "success", "value": 42}'
        )

        async with provider:
            response = await provider.generate_structured_output(
                system_prompt="Return JSON",
                user_prompt="Test",
                response_schema={"result": "string", "value": "number"}
            )

        assert response == {"result": "success", "value": 42}

    @pytest.mark.asyncio
    async def test_generate_structured_output_json_in_markdown(self):
        """Test structured output with JSON in markdown code block."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock response with markdown JSON block
        provider.hybrid_client.complete_text = AsyncMock(
            return_value='```json\n{"result": "success"}\n```'
        )

        async with provider:
            response = await provider.generate_structured_output(
                system_prompt="Return JSON",
                user_prompt="Test",
                response_schema={"result": "string"}
            )

        assert response == {"result": "success"}

    @pytest.mark.asyncio
    async def test_generate_structured_output_invalid_json(self):
        """Test structured output with invalid JSON raises error."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock response with invalid JSON
        provider.hybrid_client.complete_text = AsyncMock(
            return_value='This is not JSON'
        )

        async with provider:
            with pytest.raises(ValueError, match="invalid JSON"):
                await provider.generate_structured_output(
                    system_prompt="Return JSON",
                    user_prompt="Test",
                    response_schema={"result": "string"}
                )

    @pytest.mark.asyncio
    async def test_tokenize(self):
        """Test tokenization (approximate)."""
        provider = LocalLLMProvider(enable_local_llm=False)

        tokens = await provider.tokenize("Hello, world!")

        # Should return list of token IDs
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    @pytest.mark.asyncio
    async def test_get_usage_metrics(self):
        """Test getting usage metrics from hybrid client."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock metrics
        provider.hybrid_client.get_metrics = MagicMock(return_value={
            "total_requests": 100,
            "local_llm_successes": 99,
            "openai_fallbacks": 1
        })

        metrics = provider.get_usage_metrics()

        assert metrics["total_requests"] == 100
        assert metrics["local_llm_successes"] == 99

    def test_factory_function(self):
        """Test factory function returns LocalLLMProvider."""
        provider = get_local_llm_provider(
            enable_local_llm=True,
            fallback_strategy=FallbackStrategy.OPENAI_ONLY
        )

        assert isinstance(provider, LocalLLMProvider)
        assert provider.enable_local_llm is True


class TestLocalLLMProviderIntegration:
    """Integration tests for LocalLLMProvider."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test provider works as async context manager."""
        provider = LocalLLMProvider(enable_local_llm=False)

        async with provider as p:
            assert p is provider

        # Should not raise errors

    @pytest.mark.asyncio
    async def test_disabled_local_llm(self):
        """Test provider works when local LLM is disabled."""
        provider = LocalLLMProvider(enable_local_llm=False)

        # Mock the hybrid client to simulate cloud API
        provider.hybrid_client.complete_text = AsyncMock(return_value="Cloud response")

        async with provider:
            response = await provider.generate_text(
                system_prompt="Test",
                user_prompt="Hello"
            )

        assert response == "Cloud response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
