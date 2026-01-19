"""
Local LLM Client for Genesis Agents

Provides interface to local Qwen2.5-VL-7B-Instruct model for all agent inference.
Zero-cost alternative to cloud APIs.
"""

import logging
import os
import yaml
from typing import Dict, Any, Optional

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Setup logger first
logger = logging.getLogger("local_llm_client")

# Try to import Unsloth for optimization
try:
    import torch
    # Unsloth requires GPU - only import if CUDA is available
    if torch.cuda.is_available():
        from unsloth import FastLanguageModel
        UNSLOTH_AVAILABLE = True
    else:
        # CPU-only system - skip Unsloth
        UNSLOTH_AVAILABLE = False
        logger.debug("Unsloth skipped (requires GPU, using CPU offload instead) - expected in Railway")
except (ImportError, NotImplementedError):
    UNSLOTH_AVAILABLE = False
    logger.debug("Unsloth not available (ImportError/NotImplementedError) - expected in Railway")


class LocalLLMClient:
    """Client for local LLM - DISABLED for Railway deployment."""

    def __init__(self, config_path: str = "config/local_llm_config.yml"):
        """Initialize with disabled state - no model loading for Railway"""
        self.config = {}  # Don't load config
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self.loaded = False
        logger.info("LocalLLMClient initialized in disabled mode (Railway deployment)")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except:
            return {"llm_backend": {"model_name": "Qwen/Qwen2.5-VL-7B-Instruct"}}

    def load_model(self) -> bool:
        """Disabled for Railway deployment - use cloud APIs instead"""
        logger.info("Local LLM loading disabled - using cloud APIs (Vertex AI/OpenAI)")
        return False

    def generate(self, prompt: str, max_new_tokens: int = 2048, **kwargs) -> str:
        """Disabled for Railway deployment"""
        logger.warning("Local LLM generate called but disabled - returning empty string")
        return ""

    def generate_disabled(self, prompt: str, max_new_tokens: int = 2048, **kwargs) -> str:
        if not self.loaded and not self.load_model():
            return "ERROR: Model not loaded"

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens, **kwargs)
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            return f"ERROR: {e}"

_client = None

def get_local_llm_client():
    global _client
    if _client is None:
        _client = LocalLLMClient()
    return _client
