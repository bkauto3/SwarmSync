"""
LLM Client Abstraction Layer
Provides unified interface for multiple LLM providers (GPT-4o, Claude Sonnet 4, Gemini Flash)
With intelligent routing for 50-60% cost reduction + context profile optimization
"""
import json
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

# Import context profile system
from infrastructure.context_profiles import (
    ContextProfile,
    ContextProfileManager,
    get_profile_manager,
    estimate_tokens_from_chars
)

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    GPT4O = "gpt-4o"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"        # NEW: Fast, cheap model
    GEMINI_FLASH = "gemini-2.0-flash-exp"        # Vision + text, ultra-cheap


class LLMClient(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from LLM

        Args:
            system_prompt: System-level instructions
            user_prompt: User request/query
            response_schema: Expected JSON schema for response
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

        Returns:
            Dictionary matching response_schema

        Raises:
            LLMClientError: If API call fails or response is invalid
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context_profile: Optional[ContextProfile] = None,
        auto_select_profile: bool = True
    ) -> str:
        """
        Generate unstructured text output

        Args:
            system_prompt: System-level instructions
            user_prompt: User request/query
            temperature: Sampling temperature
            max_tokens: Maximum response length
            context_profile: Explicit context profile (LONGDOC, VIDEO, CODE)
            auto_select_profile: Auto-select profile based on content

        Returns:
            Generated text string
        """
        pass

    @abstractmethod
    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Tokenize text and return token IDs (for Agent-Lightning caching).

        This method converts text into token IDs for caching in RAG systems.
        By caching token IDs instead of text, we eliminate re-tokenization overhead
        and achieve 60-80% latency reduction.

        Args:
            text: Text to tokenize
            return_ids: Return token IDs (True) or tokens (False)

        Returns:
            List of token IDs

        Raises:
            LLMClientError: If tokenization fails
        """
        pass

    @abstractmethod
    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate text from pre-tokenized input (vLLM Agent-Lightning optimization).

        This method accepts token IDs directly, bypassing tokenization. Used in
        token-cached RAG to eliminate re-tokenization overhead.

        Args:
            prompt_token_ids: List of token IDs representing the prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with:
                - text: Generated text
                - token_ids: Generated token IDs (if supported)
                - usage: Token usage statistics

        Raises:
            LLMClientError: If generation fails
        """
        pass


class LLMClientError(Exception):
    """Base exception for LLM client errors"""
    pass


class OpenAIClient(LLMClient):
    """
    GPT-4o client for task decomposition and orchestration

    Optimized for:
    - Strategic decision making
    - Hierarchical task decomposition
    - Structured output generation (JSON mode)

    Cost: $3/1M tokens
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize OpenAI client (supports local LLM or OpenAI API)

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (default: gpt-4o, or llama-3.1-8b for local)
        """
        try:
            import openai
            self.openai = openai
        except ImportError:
            raise LLMClientError(
                "OpenAI package not installed. Run: pip install openai"
            )

        # Check if we should use local LLM (COST-FREE)
        self.use_local_llm = os.getenv("USE_LOCAL_LLMS", "false").lower() == "true"
        self.local_llm_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8003")

        # P0 FIX: Validate local LLM URL to prevent SSRF attacks
        if self.use_local_llm:
            self._validate_local_llm_url(self.local_llm_url)

        if self.use_local_llm:
            # Local LLM mode (FREE)
            # P0 FIX: Use None for local mode (no real API key needed)
            self.api_key = None
            self.client = openai.AsyncOpenAI(
                base_url=f"{self.local_llm_url}/v1",
                api_key="local-llm-sentinel"  # Sentinel value, not user credentials
            )
            self.model = "llama-3.1-8b"  # Local model
            logger.info(f"OpenAI client initialized with LOCAL LLM: {self.local_llm_url} (COST-FREE)")
        else:
            # OpenAI API mode ($$$ costs)
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise LLMClientError(
                    "OPENAI_API_KEY not set. Either pass api_key parameter or set environment variable."
                )
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.model = model
            logger.info(f"OpenAI client initialized with model: {model}")

        # Initialize context profile manager
        self.profile_manager = get_profile_manager()

    def _validate_local_llm_url(self, url: str) -> None:
        """
        Validate local LLM URL for SSRF protection.

        P0 Security Fix: Prevents Server-Side Request Forgery attacks by:
        - Restricting to HTTP/HTTPS schemes only
        - Whitelisting localhost addresses only
        - Restricting port range to 8000-9000

        Args:
            url: Local LLM URL to validate

        Raises:
            LLMClientError: If URL fails validation
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise LLMClientError(f"Invalid URL format: {url}")

        # Only allow HTTP/HTTPS schemes
        if parsed.scheme not in ("http", "https"):
            raise LLMClientError(
                f"Invalid URL scheme '{parsed.scheme}'. Only http/https allowed."
            )

        # Whitelist allowed hosts (localhost only)
        ALLOWED_HOSTS = ["127.0.0.1", "localhost", "::1"]
        if parsed.hostname not in ALLOWED_HOSTS:
            raise LLMClientError(
                f"Security: Only localhost allowed for local LLM. Got: {parsed.hostname}"
            )

        # Restrict port range to typical local LLM ports
        if parsed.port and (parsed.port < 8000 or parsed.port > 9000):
            raise LLMClientError(
                f"Security: Port must be 8000-9000 for local LLM. Got: {parsed.port}"
            )

        logger.info(f"Local LLM URL validated: {url}")

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using GPT-4o JSON mode

        Uses OpenAI's JSON mode for guaranteed valid JSON responses
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                timeout=60.0  # 60 second timeout
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMClientError("Empty response from OpenAI API")

            result = json.loads(content)

            logger.debug(f"OpenAI response: {len(content)} chars, {response.usage.total_tokens} tokens")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise LLMClientError(f"Invalid JSON from OpenAI: {e}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMClientError(f"OpenAI API call failed: {e}")

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context_profile: Optional[ContextProfile] = None,
        auto_select_profile: bool = True
    ) -> str:
        """Generate unstructured text output with optional context profile"""

        # Auto-select profile if not specified
        if auto_select_profile and not context_profile:
            context_length = len(system_prompt) + len(user_prompt)
            has_video = "video" in user_prompt.lower() or "frame" in user_prompt.lower()
            has_code = "code" in user_prompt.lower() or "repository" in user_prompt.lower()

            context_profile = self.profile_manager.select_profile(
                task_type=system_prompt,
                context_length=context_length,
                has_video=has_video,
                has_code=has_code
            )

            logger.info(f"Auto-selected profile: {context_profile.value}")

        # Validate context length if profile specified
        if context_profile:
            context_length = len(system_prompt) + len(user_prompt)
            estimated_tokens = estimate_tokens_from_chars(system_prompt + user_prompt)

            is_valid, error_msg = self.profile_manager.validate_context_length(
                profile=context_profile,
                context_length=estimated_tokens
            )

            if not is_valid:
                logger.warning(error_msg)

            # Log cost savings
            config = self.profile_manager.get_config(context_profile)
            savings = self.profile_manager.estimate_cost_savings(
                profile=context_profile,
                tokens=estimated_tokens,
                baseline_cost_per_1m=3.0  # $3/1M tokens for GPT-4o
            )
            logger.info(
                f"Profile cost savings: ${savings['savings']:.4f} "
                f"({savings['savings_pct']:.1f}%) - {config.description}"
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=60.0
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMClientError("Empty response from OpenAI API")

            logger.debug(f"OpenAI text response: {len(content)} chars")

            return content

        except Exception as e:
            logger.error(f"OpenAI text generation error: {e}")
            raise LLMClientError(f"OpenAI text generation failed: {e}")

    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Tokenize text using tiktoken (OpenAI's tokenizer).

        Note: This is a local tokenization (no API call) using tiktoken library.
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Get encoder for model
            encoding = tiktoken.encoding_for_model(self.model)

            # Tokenize
            token_ids = encoding.encode(text)

            logger.debug(f"Tokenized {len(text)} chars → {len(token_ids)} tokens")

            return token_ids

        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            raise LLMClientError(f"Tokenization failed: {e}")

    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate from token IDs (vLLM Agent-Lightning optimization).

        Note: OpenAI API doesn't support direct token ID input yet.
        We decode token IDs back to text as a workaround.
        For true zero-copy token passing, use vLLM-compatible APIs.
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Decode token IDs back to text
            encoding = tiktoken.encoding_for_model(self.model)
            text = encoding.decode(prompt_token_ids)

            # Generate using text API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": text}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=60.0
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMClientError("Empty response from OpenAI API")

            # Return vLLM-compatible response
            return {
                "text": content,
                "token_ids": encoding.encode(content),  # Generated token IDs
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"Generate from token IDs error: {e}")
            raise LLMClientError(f"Generation from token IDs failed: {e}")


class GeminiClient(LLMClient):
    """
    Gemini 2.0 Flash client for vision tasks and high-throughput cheap operations

    Optimized for:
    - Vision tasks (image/screenshot analysis, OCR)
    - High-throughput simple tasks
    - Ultra-low cost operations (20X cheaper than Claude for vision)

    Cost: $0.03/1M tokens (100X cheaper than GPT-4o)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client

        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
            model: Model name (default: gemini-2.0-flash-exp)
        """
        try:
            from google import genai
            self.genai = genai
        except ImportError:
            raise LLMClientError(
                "Google GenAI package not installed. Run: pip install google-genai"
            )

        # Try both GEMINI_API_KEY and GOOGLE_API_KEY for backwards compatibility
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise LLMClientError(
                "GEMINI_API_KEY or GOOGLE_API_KEY not set. Either pass api_key parameter or set environment variable.\n"
                "Get your API key from: https://aistudio.google.com/apikey"
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model = model

        # Initialize context profile manager
        self.profile_manager = get_profile_manager()

        logger.info(f"Gemini client initialized with model: {model}")

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using Gemini

        Note: Gemini doesn't have native JSON mode yet, so we include schema in prompt
        and parse the response carefully.
        """
        try:
            # Combine system and user prompts (Gemini doesn't separate them)
            combined_prompt = (
                f"{system_prompt}\n\n"
                f"{user_prompt}\n\n"
                f"IMPORTANT: Respond with valid JSON only (no markdown, no explanations).\n"
                f"Expected schema:\n{json.dumps(response_schema, indent=2)}"
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=combined_prompt,
            )

            content = response.text
            if not content:
                raise LLMClientError("Empty response from Gemini API")

            # Gemini might wrap JSON in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()

            result = json.loads(content)

            logger.debug(f"Gemini response: {len(content)} chars")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {content[:500]}")
            raise LLMClientError(f"Invalid JSON from Gemini: {e}")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise LLMClientError(f"Gemini API call failed: {e}")

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context_profile: Optional[ContextProfile] = None,
        auto_select_profile: bool = True
    ) -> str:
        """
        Generate unstructured text output with optional context profile

        Supports both text-only and multimodal (text + image) inputs.
        Pass images in user_prompt as PIL Image objects or file paths.
        """
        # Auto-select profile if not specified
        if auto_select_profile and not context_profile:
            context_length = len(system_prompt) + len(user_prompt)
            has_video = "video" in user_prompt.lower() or "frame" in user_prompt.lower()
            has_code = "code" in user_prompt.lower() or "repository" in user_prompt.lower()

            context_profile = self.profile_manager.select_profile(
                task_type=system_prompt,
                context_length=context_length,
                has_video=has_video,
                has_code=has_code
            )

            logger.info(f"Auto-selected profile: {context_profile.value}")

        # Validate context length if profile specified
        if context_profile:
            estimated_tokens = estimate_tokens_from_chars(system_prompt + user_prompt)

            is_valid, error_msg = self.profile_manager.validate_context_length(
                profile=context_profile,
                context_length=estimated_tokens
            )

            if not is_valid:
                logger.warning(error_msg)

            # Log cost savings
            config = self.profile_manager.get_config(context_profile)
            savings = self.profile_manager.estimate_cost_savings(
                profile=context_profile,
                tokens=estimated_tokens,
                baseline_cost_per_1m=0.03  # $0.03/1M tokens for Gemini
            )
            logger.info(
                f"Profile cost savings: ${savings['savings']:.4f} "
                f"({savings['savings_pct']:.1f}%) - {config.description}"
            )

        try:
            # Combine system and user prompts
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"

            response = self.client.models.generate_content(
                model=self.model,
                contents=combined_prompt,
            )

            content = response.text
            if not content:
                raise LLMClientError("Empty response from Gemini API")

            logger.debug(f"Gemini text response: {len(content)} chars")

            return content

        except Exception as e:
            logger.error(f"Gemini text generation error: {e}")
            raise LLMClientError(f"Gemini text generation failed: {e}")

    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Tokenize text using tiktoken as approximation (Gemini doesn't expose tokenizer)

        Note: This is an approximation using cl100k_base encoding.
        For production, consider using character-based estimation (1 token ≈ 4 chars).
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Use cl100k_base as approximation for Gemini tokens
            encoding = tiktoken.get_encoding("cl100k_base")
            token_ids = encoding.encode(text)

            logger.debug(f"Tokenized {len(text)} chars → {len(token_ids)} tokens (estimated)")

            return token_ids

        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            raise LLMClientError(f"Tokenization failed: {e}")

    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate from token IDs (decode and call Gemini API)

        Note: Gemini API doesn't support direct token ID input.
        We decode to text as a workaround.
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Decode token IDs to text
            encoding = tiktoken.get_encoding("cl100k_base")
            text = encoding.decode(prompt_token_ids)

            # Generate using Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
            )

            content = response.text
            if not content:
                raise LLMClientError("Empty response from Gemini API")

            # Return vLLM-compatible response
            return {
                "text": content,
                "token_ids": encoding.encode(content),  # Estimated token IDs
                "usage": {
                    "prompt_tokens": len(prompt_token_ids),
                    "completion_tokens": len(encoding.encode(content)),
                    "total_tokens": len(prompt_token_ids) + len(encoding.encode(content))
                }
            }

        except Exception as e:
            logger.error(f"Generate from token IDs error: {e}")
            raise LLMClientError(f"Generation from token IDs failed: {e}")


class AnthropicClient(LLMClient):
    """
    Claude Sonnet 4 client for code generation and complex reasoning

    Optimized for:
    - Code generation (72.7% SWE-bench accuracy)
    - Complex multi-step reasoning
    - Long-context tasks

    Cost: $3/1M tokens
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Anthropic client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name (default: claude-sonnet-4-20250514)
        """
        try:
            import anthropic
            self.anthropic = anthropic
        except ImportError:
            raise LLMClientError(
                "Anthropic package not installed. Run: pip install anthropic"
            )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMClientError(
                "ANTHROPIC_API_KEY not set. Either pass api_key parameter or set environment variable."
            )

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = model

        # Initialize context profile manager
        self.profile_manager = get_profile_manager()

        logger.info(f"Anthropic client initialized with model: {model}")

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using Claude

        Note: Claude doesn't have native JSON mode, so we include schema in prompt
        and parse the response carefully.
        """
        try:
            # Add schema to prompt for guidance
            schema_prompt = (
                f"{user_prompt}\n\n"
                f"IMPORTANT: Respond with valid JSON only (no markdown, no explanations).\n"
                f"Expected schema:\n{json.dumps(response_schema, indent=2)}"
            )

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": schema_prompt}],
                timeout=60.0
            )

            content = response.content[0].text
            if not content:
                raise LLMClientError("Empty response from Anthropic API")

            # Claude sometimes wraps JSON in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()

            result = json.loads(content)

            logger.debug(f"Anthropic response: {len(content)} chars")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic JSON response: {e}")
            logger.error(f"Raw response: {content[:500]}")
            raise LLMClientError(f"Invalid JSON from Anthropic: {e}")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise LLMClientError(f"Anthropic API call failed: {e}")

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context_profile: Optional[ContextProfile] = None,
        auto_select_profile: bool = True
    ) -> str:
        """Generate unstructured text output with optional context profile"""

        # Auto-select profile if not specified
        if auto_select_profile and not context_profile:
            context_length = len(system_prompt) + len(user_prompt)
            has_video = "video" in user_prompt.lower() or "frame" in user_prompt.lower()
            has_code = "code" in user_prompt.lower() or "repository" in user_prompt.lower()

            context_profile = self.profile_manager.select_profile(
                task_type=system_prompt,
                context_length=context_length,
                has_video=has_video,
                has_code=has_code
            )

            logger.info(f"Auto-selected profile: {context_profile.value}")

        # Validate context length if profile specified
        if context_profile:
            estimated_tokens = estimate_tokens_from_chars(system_prompt + user_prompt)

            is_valid, error_msg = self.profile_manager.validate_context_length(
                profile=context_profile,
                context_length=estimated_tokens
            )

            if not is_valid:
                logger.warning(error_msg)

            # Log cost savings
            config = self.profile_manager.get_config(context_profile)
            savings = self.profile_manager.estimate_cost_savings(
                profile=context_profile,
                tokens=estimated_tokens,
                baseline_cost_per_1m=3.0  # $3/1M tokens for Claude
            )
            logger.info(
                f"Profile cost savings: ${savings['savings']:.4f} "
                f"({savings['savings_pct']:.1f}%) - {config.description}"
            )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=60.0
            )

            content = response.content[0].text
            if not content:
                raise LLMClientError("Empty response from Anthropic API")

            logger.debug(f"Anthropic text response: {len(content)} chars")

            return content

        except Exception as e:
            logger.error(f"Anthropic text generation error: {e}")
            raise LLMClientError(f"Anthropic text generation failed: {e}")

    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Tokenize text using Claude's tokenizer (via API count_tokens).

        Note: Anthropic doesn't provide direct tokenization API, so we use a workaround
        by estimating tokens (1 token ≈ 4 characters for English text).
        For production, consider using tiktoken with cl100k_base encoding as approximation.
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Use cl100k_base as approximation for Claude tokens
            # This is not perfect but gives reasonable estimates
            encoding = tiktoken.get_encoding("cl100k_base")
            token_ids = encoding.encode(text)

            logger.debug(f"Tokenized {len(text)} chars → {len(token_ids)} tokens (estimated)")

            return token_ids

        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            raise LLMClientError(f"Tokenization failed: {e}")

    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate from token IDs (decode and call Claude API).

        Note: Claude API doesn't support direct token ID input.
        We decode to text as a workaround.
        """
        try:
            import tiktoken
        except ImportError:
            raise LLMClientError(
                "tiktoken not installed. Run: pip install tiktoken"
            )

        try:
            # Decode token IDs to text
            encoding = tiktoken.get_encoding("cl100k_base")
            text = encoding.decode(prompt_token_ids)

            # Generate using Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": text}],
                timeout=60.0
            )

            content = response.content[0].text
            if not content:
                raise LLMClientError("Empty response from Anthropic API")

            # Return vLLM-compatible response
            return {
                "text": content,
                "token_ids": encoding.encode(content),  # Estimated token IDs
                "usage": {
                    "prompt_tokens": len(prompt_token_ids),
                    "completion_tokens": len(encoding.encode(content)),
                    "total_tokens": len(prompt_token_ids) + len(encoding.encode(content))
                }
            }

        except Exception as e:
            logger.error(f"Generate from token IDs error: {e}")
            raise LLMClientError(f"Generation from token IDs failed: {e}")


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing without API calls

    Returns predefined responses for deterministic testing
    """

    def __init__(self, mock_responses: Optional[Dict[str, Any]] = None):
        """
        Initialize mock client

        Args:
            mock_responses: Dictionary of prompt patterns -> responses
        """
        self.mock_responses = mock_responses or {}
        self.call_count = 0
        self.last_prompts = []

        logger.info("Mock LLM client initialized")

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """Return mock structured response"""
        self.call_count += 1
        self.last_prompts.append((system_prompt, user_prompt))

        # Check for pattern match
        for pattern, response in self.mock_responses.items():
            if pattern.lower() in user_prompt.lower():
                logger.debug(f"Mock response matched pattern: {pattern}")
                return response

        # Default mock response for task decomposition
        return {
            "tasks": [
                {
                    "task_id": "mock_task_1",
                    "task_type": "design",
                    "description": "Mock task 1",
                    "dependencies": [],
                    "estimated_duration": 1.0
                },
                {
                    "task_id": "mock_task_2",
                    "task_type": "implement",
                    "description": "Mock task 2",
                    "dependencies": ["mock_task_1"],
                    "estimated_duration": 2.0
                }
            ]
        }

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Return mock text response"""
        self.call_count += 1
        self.last_prompts.append((system_prompt, user_prompt))

        return "Mock LLM response text"

    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Mock tokenization (deterministic for testing).

        Returns simple token IDs: [1, 2, 3, ...] based on text length.
        """
        # Simple mock: 1 token per 4 characters
        num_tokens = max(1, len(text) // 4)
        token_ids = list(range(1, num_tokens + 1))

        logger.debug(f"Mock tokenized {len(text)} chars → {len(token_ids)} tokens")

        return token_ids

    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Mock generation from token IDs (deterministic for testing).
        """
        self.call_count += 1

        # Mock response based on prompt token count
        response_text = f"Mock response for {len(prompt_token_ids)} prompt tokens"

        return {
            "text": response_text,
            "token_ids": list(range(1, len(response_text) // 4 + 1)),
            "usage": {
                "prompt_tokens": len(prompt_token_ids),
                "completion_tokens": len(response_text) // 4,
                "total_tokens": len(prompt_token_ids) + len(response_text) // 4
            }
        }


class LLMFactory:
    """
    Factory for creating LLM clients

    Usage:
        client = LLMFactory.create(LLMProvider.GPT4O)
        response = await client.generate_structured_output(...)
    """

    @staticmethod
    def create(
        provider: LLMProvider,
        api_key: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """
        Create LLM client for specified provider

        Args:
            provider: LLM provider enum
            api_key: Optional API key (defaults to env var)
            **kwargs: Additional provider-specific arguments

        Returns:
            Initialized LLM client

        Raises:
            ValueError: If provider not supported
            LLMClientError: If client initialization fails
        """
        if provider == LLMProvider.GPT4O:
            return OpenAIClient(api_key=api_key, **kwargs)
        elif provider == LLMProvider.CLAUDE_SONNET_4:
            return AnthropicClient(api_key=api_key, **kwargs)
        elif provider == LLMProvider.CLAUDE_HAIKU_4_5:
            return AnthropicClient(api_key=api_key, model="claude-haiku-4-5", **kwargs)
        elif provider == LLMProvider.GEMINI_FLASH:
            return GeminiClient(api_key=api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def create_mock(mock_responses: Optional[Dict[str, Any]] = None) -> MockLLMClient:
        """
        Create mock LLM client for testing

        Args:
            mock_responses: Dictionary of prompt patterns -> responses

        Returns:
            Mock LLM client
        """
        return MockLLMClient(mock_responses=mock_responses)


# Cost tracking utilities
class CostTracker:
    """
    Track LLM API costs across providers

    Cost estimates (per 1M tokens):
    - GPT-4o: $3
    - Claude Sonnet 4: $3
    - Gemini Flash: $0.03
    """

    COST_PER_MILLION_TOKENS = {
        LLMProvider.GPT4O: 3.0,
        LLMProvider.CLAUDE_SONNET_4: 3.0,
        LLMProvider.GEMINI_FLASH: 0.03
    }

    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self.provider_usage = {}

    def track_usage(
        self,
        provider: LLMProvider,
        tokens: int
    ) -> float:
        """
        Track token usage and calculate cost

        Args:
            provider: LLM provider used
            tokens: Number of tokens consumed

        Returns:
            Cost in USD for this call
        """
        cost_per_token = self.COST_PER_MILLION_TOKENS[provider] / 1_000_000
        call_cost = tokens * cost_per_token

        self.total_tokens += tokens
        self.total_cost += call_cost

        if provider not in self.provider_usage:
            self.provider_usage[provider] = {"tokens": 0, "cost": 0.0}

        self.provider_usage[provider]["tokens"] += tokens
        self.provider_usage[provider]["cost"] += call_cost

        return call_cost

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "by_provider": {
                provider.value: {
                    "tokens": usage["tokens"],
                    "cost_usd": round(usage["cost"], 4)
                }
                for provider, usage in self.provider_usage.items()
            }
        }


class RoutedLLMClient(LLMClient):
    """
    LLM Client with intelligent routing for 50-60% cost reduction

    Routes requests to optimal model based on task complexity:
    - Simple tasks → Claude Haiku ($0.25/1M) - 70-80% of requests
    - Complex tasks → Claude Sonnet ($3/1M) - 15-25% of requests
    - Vision tasks → Gemini Flash ($0.03/1M) - 5% of requests

    Integrates with InferenceRouter for routing decisions.
    """

    def __init__(
        self,
        agent_name: str,
        enable_routing: bool = True,
        enable_auto_escalation: bool = True,
        api_keys: Optional[Dict[str, str]] = None,
        casebank: Optional['CaseBank'] = None
    ):
        """
        Initialize routed LLM client

        Args:
            agent_name: Name of requesting agent (for routing context)
            enable_routing: Enable intelligent routing (if False, always use Sonnet)
            enable_auto_escalation: Enable auto-retry with Sonnet on low confidence
            api_keys: Optional dict of API keys {"anthropic": "...", "openai": "..."}
            casebank: Optional CaseBank instance for memory-based routing
        """
        from infrastructure.inference_router import InferenceRouter

        self.agent_name = agent_name
        self.enable_routing = enable_routing
        self.casebank = casebank
        self.router = InferenceRouter(
            enable_auto_escalation=enable_auto_escalation,
            casebank=casebank
        )

        # Initialize clients
        api_keys = api_keys or {}
        self.haiku_client = AnthropicClient(
            api_key=api_keys.get("anthropic"),
            model="claude-haiku-4-5"
        )
        self.sonnet_client = AnthropicClient(
            api_key=api_keys.get("anthropic"),
            model="claude-sonnet-4-20250514"
        )

        # Initialize Gemini client (graceful fallback if not available)
        try:
            self.gemini_client = GeminiClient(
                api_key=api_keys.get("gemini") or api_keys.get("google")
            )
            logger.info("Gemini client initialized for vision routing")
        except LLMClientError as e:
            self.gemini_client = None
            logger.warning(f"Gemini client not available: {e}. Vision tasks will fall back to Sonnet.")

        logger.info(
            f"RoutedLLMClient initialized for {agent_name} "
            f"(routing={'enabled' if enable_routing else 'disabled'})"
        )

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.0,
        routing_context: Optional[Dict[str, Any]] = None,
        use_memory_routing: bool = True
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output with intelligent routing

        Args:
            system_prompt: System-level instructions
            user_prompt: User request/query
            response_schema: Expected JSON schema
            temperature: Sampling temperature
            routing_context: Optional routing hints (has_image, task_type, etc.)
            use_memory_routing: Enable memory-based routing (default True)

        Returns:
            Dictionary matching response_schema
        """
        routing_context = routing_context or {}

        # Route to optimal model (with optional memory routing)
        if self.enable_routing and use_memory_routing and self.casebank:
            # Use CaseBank-enhanced memory routing
            model_id, routing_metadata = await self.router.route_with_memory(
                agent_name=self.agent_name,
                task=user_prompt,
                context=routing_context
            )
            logger.debug(
                f"{self.agent_name} memory routing: {routing_metadata['routing_type']} "
                f"→ {model_id}"
            )
        elif self.enable_routing:
            # Use base routing only
            model_id = await self.router.route_request(
                agent_name=self.agent_name,
                task=user_prompt,
                context=routing_context
            )
        else:
            # Routing disabled → always use Sonnet
            model_id = "claude-sonnet-4-5"

        # Select client based on routed model
        if "haiku" in model_id.lower():
            client = self.haiku_client
            logger.debug(f"{self.agent_name} using Haiku for structured output")
        elif "gemini" in model_id.lower():
            if self.gemini_client:
                client = self.gemini_client
                logger.debug(f"{self.agent_name} using Gemini for structured output")
            else:
                # Fallback to Sonnet if Gemini not available
                client = self.sonnet_client
                logger.warning("Gemini not available, falling back to Sonnet")
        else:
            client = self.sonnet_client
            logger.debug(f"{self.agent_name} using Sonnet for structured output")

        # Generate response
        try:
            response = await client.generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                temperature=temperature
            )

            # Auto-escalation check (if Haiku was used)
            if "haiku" in model_id.lower() and self.router.enable_auto_escalation:
                # Simple confidence heuristic: check response completeness
                confidence = self._estimate_confidence(response, response_schema)

                should_escalate = await self.router.escalate_to_accurate(
                    agent_name=self.agent_name,
                    task=user_prompt,
                    haiku_response=str(response),
                    confidence_score=confidence
                )

                if should_escalate:
                    logger.warning(
                        f"{self.agent_name} escalating to Sonnet (confidence={confidence:.2f})"
                    )
                    response = await self.sonnet_client.generate_structured_output(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_schema=response_schema,
                        temperature=temperature
                    )

            return response

        except Exception as e:
            logger.error(f"Routed LLM call failed: {e}")
            raise

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        routing_context: Optional[Dict[str, Any]] = None,
        use_memory_routing: bool = True
    ) -> str:
        """
        Generate unstructured text with intelligent routing

        Args:
            system_prompt: System-level instructions
            user_prompt: User request/query
            temperature: Sampling temperature
            max_tokens: Maximum response length
            routing_context: Optional routing hints
            use_memory_routing: Enable memory-based routing (default True)

        Returns:
            Generated text string
        """
        routing_context = routing_context or {}

        # Route to optimal model (with optional memory routing)
        if self.enable_routing and use_memory_routing and self.casebank:
            # Use CaseBank-enhanced memory routing
            model_id, routing_metadata = await self.router.route_with_memory(
                agent_name=self.agent_name,
                task=user_prompt,
                context=routing_context
            )
            logger.debug(
                f"{self.agent_name} memory routing: {routing_metadata['routing_type']} "
                f"→ {model_id}"
            )
        elif self.enable_routing:
            # Use base routing only
            model_id = await self.router.route_request(
                agent_name=self.agent_name,
                task=user_prompt,
                context=routing_context
            )
        else:
            model_id = "claude-sonnet-4-5"

        # Select client
        if "haiku" in model_id.lower():
            client = self.haiku_client
        elif "gemini" in model_id.lower():
            client = self.gemini_client if self.gemini_client else self.sonnet_client
        else:
            client = self.sonnet_client

        # Generate response
        try:
            response = await client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Auto-escalation check
            if "haiku" in model_id.lower() and self.router.enable_auto_escalation:
                confidence = len(response) / max(len(user_prompt), 100)  # Simple heuristic

                should_escalate = await self.router.escalate_to_accurate(
                    agent_name=self.agent_name,
                    task=user_prompt,
                    haiku_response=response,
                    confidence_score=min(confidence, 0.95)
                )

                if should_escalate:
                    response = await self.sonnet_client.generate_text(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

            return response

        except Exception as e:
            logger.error(f"Routed text generation failed: {e}")
            raise

    def _estimate_confidence(
        self,
        response: Dict[str, Any],
        expected_schema: Dict[str, Any]
    ) -> float:
        """
        Estimate confidence score for structured output

        Simple heuristic based on response completeness:
        - All expected keys present → 0.9
        - Missing some keys → 0.5
        - Empty response → 0.1

        Args:
            response: Generated response
            expected_schema: Expected schema

        Returns:
            Confidence score (0.0-1.0)
        """
        if not response:
            return 0.1

        # Check if response has expected structure
        expected_keys = set(expected_schema.get("properties", {}).keys())
        actual_keys = set(response.keys())

        if expected_keys <= actual_keys:
            # All expected keys present
            return 0.9
        elif actual_keys:
            # Some keys present
            overlap = len(expected_keys & actual_keys) / max(len(expected_keys), 1)
            return 0.5 + (overlap * 0.3)
        else:
            # No expected keys
            return 0.2

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics for cost analysis"""
        return self.router.get_routing_stats()

    async def tokenize(
        self,
        text: str,
        return_ids: bool = True
    ) -> List[int]:
        """
        Tokenize text using the active client

        Routes to Haiku client for tokenization (cheaper/faster)
        """
        return await self.haiku_client.tokenize(text, return_ids)

    async def generate_from_token_ids(
        self,
        prompt_token_ids: List[int],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate from token IDs (vLLM Agent-Lightning optimization)

        Uses Haiku client by default (faster/cheaper for cached inputs)
        """
        return await self.haiku_client.generate_from_token_ids(
            prompt_token_ids,
            max_tokens,
            temperature
        )

