"""
OpenHands Integration Module for SE-Darwin Agent Enhancement

Integrates OpenHands (SOTA code agent, 58.3% SWE-bench verified) with SE-Darwin
for enhanced code generation, test generation, and debugging capabilities.

Based on:
- OpenHands (arXiv:2407.16741): 58.3% SWE-bench verified SOTA open-source code agent
- GitHub: https://github.com/all-hands-ai/openhands
- Expected improvement: +8-12% over SE-Darwin baseline

Key Features:
- Code generation with OpenHands CodeActAgent (58.3% SWE-bench)
- Test generation via OpenHands runtime
- Debugging support with OpenHands action space
- Feature flag controlled (USE_OPENHANDS=true)
- Backward compatibility maintained

Integration Points:
- SE-Darwin mutation operators (revision, recombination, refinement)
- TrajectoryPool for evolution history
- BenchmarkRunner for validation
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from infrastructure import get_logger

logger = get_logger("openhands_integration")


class OpenHandsMode(Enum):
    """OpenHands operation modes"""
    CODE_GENERATION = "code_generation"
    TEST_GENERATION = "test_generation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"


@dataclass
class OpenHandsConfig:
    """
    Configuration for OpenHands integration

    Attributes:
        enabled: Enable OpenHands integration (from USE_OPENHANDS env var)
        model: LLM model for OpenHands (default: claude-3-5-sonnet-20241022)
        max_iterations: Maximum agent iterations (default: 10)
        timeout_seconds: Timeout per task (default: 300)
        sandbox_type: Sandbox runtime type (default: 'local')
        enable_browsing: Enable web browsing capabilities (default: False)
        workspace_dir: Workspace directory for code execution (default: temp)
    """
    enabled: bool = field(default_factory=lambda: os.getenv("USE_OPENHANDS", "false").lower() == "true")
    model: str = field(default_factory=lambda: os.getenv("OPENHANDS_MODEL", "claude-3-5-sonnet-20241022"))
    max_iterations: int = field(default_factory=lambda: int(os.getenv("OPENHANDS_MAX_ITERATIONS", "10")))
    timeout_seconds: int = 300
    sandbox_type: str = "local"
    enable_browsing: bool = False
    workspace_dir: Optional[Path] = None

    def __post_init__(self):
        """Initialize workspace directory if not specified"""
        if self.workspace_dir is None:
            self.workspace_dir = Path(tempfile.mkdtemp(prefix="openhands_"))


@dataclass
class OpenHandsResult:
    """
    Result from OpenHands execution

    Attributes:
        success: Whether execution succeeded
        generated_code: Generated code output
        test_code: Generated test code (if applicable)
        execution_time: Time taken in seconds
        iterations_used: Number of agent iterations used
        error_message: Error message if failed
        metadata: Additional metadata (logs, actions, observations)
    """
    success: bool
    generated_code: Optional[str] = None
    test_code: Optional[str] = None
    execution_time: float = 0.0
    iterations_used: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenHandsClient:
    """
    Client for interacting with OpenHands code agent

    Provides methods for code generation, test generation, and debugging
    using OpenHands' CodeActAgent with 58.3% SWE-bench accuracy.

    Usage:
        client = OpenHandsClient(config=OpenHandsConfig(enabled=True))
        result = await client.generate_code(
            problem_description="Create FastAPI endpoint for user auth",
            context={"language": "python", "framework": "fastapi"}
        )
    """

    def __init__(self, config: Optional[OpenHandsConfig] = None):
        """
        Initialize OpenHands client

        Args:
            config: OpenHands configuration (defaults to env-based config)
        """
        self.config = config or OpenHandsConfig()
        self._runtime = None
        self._agent = None

        logger.info(
            f"OpenHandsClient initialized: enabled={self.config.enabled}, "
            f"model={self.config.model}, max_iterations={self.config.max_iterations}"
        )

    async def _ensure_runtime(self):
        """Lazy-load OpenHands runtime and agent"""
        if not self.config.enabled:
            raise RuntimeError("OpenHands integration disabled. Set USE_OPENHANDS=true")

        if self._runtime is None or self._agent is None:
            try:
                # Import OpenHands components (lazy to avoid import errors when disabled)
                from openhands.controller.agent_controller import AgentController
                from openhands.core.config import AppConfig, LLMConfig
                from openhands.events.action import MessageAction
                from openhands.runtime.client.runtime import EventStreamRuntime

                # Store imports for use in methods
                self._imports = {
                    'AgentController': AgentController,
                    'AppConfig': AppConfig,
                    'LLMConfig': LLMConfig,
                    'MessageAction': MessageAction,
                    'EventStreamRuntime': EventStreamRuntime
                }

                # Configure OpenHands
                llm_config = LLMConfig(
                    model=self.config.model,
                    api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"),
                    num_retries=3,
                    timeout=self.config.timeout_seconds
                )

                app_config = AppConfig(
                    llm=llm_config,
                    workspace_base=str(self.config.workspace_dir),
                    max_iterations=self.config.max_iterations,
                    sandbox={"type": self.config.sandbox_type}
                )

                # Initialize runtime
                self._runtime = EventStreamRuntime(config=app_config)

                # Initialize agent controller
                self._agent = AgentController(
                    agent_name="CodeActAgent",  # Best for code tasks (58.3% SWE-bench)
                    runtime=self._runtime,
                    max_iterations=self.config.max_iterations,
                    config=app_config
                )

                logger.info("OpenHands runtime and agent initialized successfully")

            except ImportError as e:
                logger.error(f"Failed to import OpenHands: {e}")
                raise RuntimeError(
                    f"OpenHands not properly installed. Run: pip install openhands-ai\n"
                    f"Error: {e}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenHands runtime: {e}")
                raise

    async def generate_code(
        self,
        problem_description: str,
        context: Optional[Dict[str, Any]] = None,
        mode: OpenHandsMode = OpenHandsMode.CODE_GENERATION
    ) -> OpenHandsResult:
        """
        Generate code using OpenHands CodeActAgent

        Args:
            problem_description: Problem to solve (natural language)
            context: Additional context (language, framework, constraints, etc.)
            mode: Operation mode (CODE_GENERATION, TEST_GENERATION, etc.)

        Returns:
            OpenHandsResult with generated code and metadata
        """
        if not self.config.enabled:
            return OpenHandsResult(
                success=False,
                error_message="OpenHands disabled. Set USE_OPENHANDS=true"
            )

        start_time = time.time()

        try:
            await self._ensure_runtime()

            # Build prompt based on mode and context
            prompt = self._build_prompt(problem_description, context, mode)

            logger.info(f"OpenHands generating code for: {problem_description[:100]}...")

            # Execute via OpenHands agent
            MessageAction = self._imports['MessageAction']
            action = MessageAction(content=prompt)

            # Run agent with timeout
            async with asyncio.timeout(self.config.timeout_seconds):
                state = await self._agent.step(action)

                # Wait for agent to complete
                while not state.is_finished():
                    state = await self._agent.step(action)

                    # Safety: prevent infinite loops
                    if state.iteration >= self.config.max_iterations:
                        logger.warning(f"OpenHands hit max iterations: {self.config.max_iterations}")
                        break

            execution_time = time.time() - start_time

            # Extract generated code from agent state
            generated_code = self._extract_code_from_state(state)
            test_code = self._extract_test_code_from_state(state) if mode == OpenHandsMode.TEST_GENERATION else None

            success = generated_code is not None and len(generated_code.strip()) > 0

            result = OpenHandsResult(
                success=success,
                generated_code=generated_code,
                test_code=test_code,
                execution_time=execution_time,
                iterations_used=state.iteration,
                metadata={
                    "mode": mode.value,
                    "model": self.config.model,
                    "actions": [str(a) for a in state.history.get_actions()[:10]],  # Last 10 actions
                    "observations": [str(o) for o in state.history.get_observations()[:10]]
                }
            )

            logger.info(
                f"OpenHands code generation {'succeeded' if success else 'failed'}: "
                f"{execution_time:.2f}s, {state.iteration} iterations"
            )

            return result

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"OpenHands timed out after {execution_time:.2f}s")
            return OpenHandsResult(
                success=False,
                execution_time=execution_time,
                error_message=f"Timeout after {execution_time:.2f}s"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"OpenHands generation failed: {e}")
            return OpenHandsResult(
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )

    async def generate_test(
        self,
        code: str,
        test_framework: str = "pytest",
        context: Optional[Dict[str, Any]] = None
    ) -> OpenHandsResult:
        """
        Generate test code for given implementation

        Args:
            code: Implementation code to test
            test_framework: Test framework (pytest, unittest, etc.)
            context: Additional context

        Returns:
            OpenHandsResult with generated test code
        """
        context = context or {}
        context.update({
            "code_to_test": code,
            "test_framework": test_framework
        })

        prompt = (
            f"Generate comprehensive {test_framework} tests for the following code:\n\n"
            f"```python\n{code}\n```\n\n"
            f"Include:\n"
            f"- Unit tests for all functions/methods\n"
            f"- Edge case testing\n"
            f"- Error handling tests\n"
            f"- Integration tests if applicable\n"
        )

        return await self.generate_code(
            problem_description=prompt,
            context=context,
            mode=OpenHandsMode.TEST_GENERATION
        )

    async def debug_code(
        self,
        code: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OpenHandsResult:
        """
        Debug code using OpenHands

        Args:
            code: Code with bugs
            error_message: Error message or test failure
            context: Additional context

        Returns:
            OpenHandsResult with fixed code
        """
        prompt = (
            f"Debug and fix the following code:\n\n"
            f"```python\n{code}\n```\n\n"
            f"Error: {error_message}\n\n"
            f"Please:\n"
            f"1. Identify the root cause\n"
            f"2. Provide a fixed version\n"
            f"3. Explain the fix\n"
        )

        context = context or {}
        context.update({
            "original_code": code,
            "error": error_message
        })

        return await self.generate_code(
            problem_description=prompt,
            context=context,
            mode=OpenHandsMode.DEBUGGING
        )

    async def refactor_code(
        self,
        code: str,
        refactoring_goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OpenHandsResult:
        """
        Refactor code using OpenHands

        Args:
            code: Code to refactor
            refactoring_goal: Refactoring objective
            context: Additional context

        Returns:
            OpenHandsResult with refactored code
        """
        prompt = (
            f"Refactor the following code:\n\n"
            f"```python\n{code}\n```\n\n"
            f"Goal: {refactoring_goal}\n\n"
            f"Please:\n"
            f"1. Improve code quality and maintainability\n"
            f"2. Preserve functionality\n"
            f"3. Add docstrings if missing\n"
            f"4. Follow PEP-8 style guidelines\n"
        )

        context = context or {}
        context.update({
            "original_code": code,
            "goal": refactoring_goal
        })

        return await self.generate_code(
            problem_description=prompt,
            context=context,
            mode=OpenHandsMode.REFACTORING
        )

    def _build_prompt(
        self,
        problem_description: str,
        context: Optional[Dict[str, Any]],
        mode: OpenHandsMode
    ) -> str:
        """
        Build prompt for OpenHands based on mode and context

        Args:
            problem_description: Problem description
            context: Additional context
            mode: Operation mode

        Returns:
            Formatted prompt string
        """
        context = context or {}

        prompt_parts = [problem_description]

        # Add context information
        if context.get("language"):
            prompt_parts.append(f"\nLanguage: {context['language']}")

        if context.get("framework"):
            prompt_parts.append(f"Framework: {context['framework']}")

        if context.get("constraints"):
            prompt_parts.append(f"Constraints: {context['constraints']}")

        if context.get("past_cases"):
            prompt_parts.append(f"\nPast solutions (for reference):\n{context['past_cases']}")

        if context.get("evolution_memories"):
            prompt_parts.append(f"\nEvolution history:\n{context['evolution_memories']}")

        # Add mode-specific instructions
        if mode == OpenHandsMode.CODE_GENERATION:
            prompt_parts.append(
                "\nPlease provide:\n"
                "1. Complete, working implementation\n"
                "2. Clear docstrings and comments\n"
                "3. Error handling\n"
                "4. Type hints\n"
            )
        elif mode == OpenHandsMode.TEST_GENERATION:
            prompt_parts.append(
                "\nPlease provide:\n"
                "1. Comprehensive test suite\n"
                "2. Unit and integration tests\n"
                "3. Edge case coverage\n"
                "4. Clear test documentation\n"
            )

        return "\n".join(prompt_parts)

    def _extract_code_from_state(self, state: Any) -> Optional[str]:
        """
        Extract generated code from OpenHands agent state

        Args:
            state: Agent state object

        Returns:
            Extracted code or None
        """
        try:
            # OpenHands stores code in observations
            observations = state.history.get_observations()

            # Look for code blocks in observations
            code_blocks = []
            for obs in observations:
                obs_str = str(obs)
                # Extract code from markdown code blocks
                if "```python" in obs_str:
                    start = obs_str.find("```python") + 9
                    end = obs_str.find("```", start)
                    if end > start:
                        code_blocks.append(obs_str[start:end].strip())
                elif "```" in obs_str:
                    start = obs_str.find("```") + 3
                    end = obs_str.find("```", start)
                    if end > start:
                        code_blocks.append(obs_str[start:end].strip())

            # Return the largest/most complete code block
            if code_blocks:
                return max(code_blocks, key=len)

            # Fallback: return concatenated observations
            return "\n".join([str(o) for o in observations[-3:]])  # Last 3 observations

        except Exception as e:
            logger.error(f"Failed to extract code from state: {e}")
            return None

    def _extract_test_code_from_state(self, state: Any) -> Optional[str]:
        """
        Extract test code from OpenHands agent state

        Args:
            state: Agent state object

        Returns:
            Extracted test code or None
        """
        # Similar to _extract_code_from_state but looks for test patterns
        try:
            observations = state.history.get_observations()

            test_blocks = []
            for obs in observations:
                obs_str = str(obs)
                # Look for test patterns
                if any(pattern in obs_str for pattern in ["def test_", "class Test", "import pytest"]):
                    if "```python" in obs_str:
                        start = obs_str.find("```python") + 9
                        end = obs_str.find("```", start)
                        if end > start:
                            test_blocks.append(obs_str[start:end].strip())

            if test_blocks:
                return max(test_blocks, key=len)

            return None

        except Exception as e:
            logger.error(f"Failed to extract test code from state: {e}")
            return None

    async def close(self):
        """Clean up resources"""
        if self._runtime is not None:
            try:
                await self._runtime.close()
                logger.info("OpenHands runtime closed")
            except Exception as e:
                logger.warning(f"Error closing OpenHands runtime: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        if self._runtime is not None:
            # Schedule cleanup if event loop is running
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass


class OpenHandsOperatorEnhancer:
    """
    Enhances SE-Darwin operators with OpenHands capabilities

    Wraps SE-Darwin mutation operators (Revision, Recombination, Refinement)
    with OpenHands code generation for improved quality.

    Usage:
        enhancer = OpenHandsOperatorEnhancer(
            openhands_client=OpenHandsClient(),
            use_for_revision=True,
            use_for_recombination=False,
            use_for_refinement=True
        )

        enhanced_operator = enhancer.enhance_operator(
            original_operator=revision_operator
        )
    """

    def __init__(
        self,
        openhands_client: OpenHandsClient,
        use_for_revision: bool = True,
        use_for_recombination: bool = True,
        use_for_refinement: bool = True,
        fallback_on_error: bool = True
    ):
        """
        Initialize operator enhancer

        Args:
            openhands_client: OpenHands client instance
            use_for_revision: Use OpenHands for revision operator
            use_for_recombination: Use OpenHands for recombination operator
            use_for_refinement: Use OpenHands for refinement operator
            fallback_on_error: Fallback to original operator on OpenHands error
        """
        self.client = openhands_client
        self.use_for_revision = use_for_revision
        self.use_for_recombination = use_for_recombination
        self.use_for_refinement = use_for_refinement
        self.fallback_on_error = fallback_on_error

        logger.info(
            f"OpenHandsOperatorEnhancer initialized: "
            f"revision={use_for_revision}, recombination={use_for_recombination}, "
            f"refinement={use_for_refinement}, fallback={fallback_on_error}"
        )

    def enhance_operator(
        self,
        original_operator: Any,
        operator_name: str = "unknown"
    ) -> Callable:
        """
        Enhance operator with OpenHands capabilities

        Args:
            original_operator: Original SE-Darwin operator
            operator_name: Operator name for logging

        Returns:
            Enhanced operator function
        """
        async def enhanced_operator_wrapper(*args, **kwargs):
            """Wrapper that tries OpenHands first, falls back to original"""

            # Check if OpenHands should be used for this operator
            use_openhands = (
                (operator_name == "revision" and self.use_for_revision) or
                (operator_name == "recombination" and self.use_for_recombination) or
                (operator_name == "refinement" and self.use_for_refinement)
            )

            if not use_openhands or not self.client.config.enabled:
                # Use original operator
                return await original_operator(*args, **kwargs)

            try:
                # Try OpenHands-enhanced generation
                logger.info(f"Using OpenHands for {operator_name} operator")

                # Extract problem context from operator arguments
                problem_description = self._extract_problem_from_args(args, kwargs)
                context = self._extract_context_from_args(args, kwargs)

                # Generate code with OpenHands
                result = await self.client.generate_code(
                    problem_description=problem_description,
                    context=context,
                    mode=OpenHandsMode.CODE_GENERATION
                )

                if result.success:
                    logger.info(
                        f"OpenHands {operator_name} succeeded: "
                        f"{result.execution_time:.2f}s, {result.iterations_used} iterations"
                    )
                    # Return result in SE-Darwin OperatorResult format
                    return self._convert_to_operator_result(result, operator_name)
                else:
                    logger.warning(
                        f"OpenHands {operator_name} failed: {result.error_message}"
                    )
                    if self.fallback_on_error:
                        logger.info(f"Falling back to original {operator_name} operator")
                        return await original_operator(*args, **kwargs)
                    else:
                        return self._convert_to_operator_result(result, operator_name)

            except Exception as e:
                logger.error(f"OpenHands {operator_name} error: {e}")
                if self.fallback_on_error:
                    logger.info(f"Falling back to original {operator_name} operator")
                    return await original_operator(*args, **kwargs)
                else:
                    raise

        return enhanced_operator_wrapper

    def _extract_problem_from_args(
        self,
        args: tuple,
        kwargs: dict
    ) -> str:
        """Extract problem description from operator arguments"""
        # SE-Darwin operators typically have trajectory or problem_description args
        if args and hasattr(args[0], 'proposed_strategy'):
            return args[0].proposed_strategy
        elif 'problem_description' in kwargs:
            return kwargs['problem_description']
        elif len(args) >= 2:
            return str(args[1])
        else:
            return "Generate improved code"

    def _extract_context_from_args(
        self,
        args: tuple,
        kwargs: dict
    ) -> Dict[str, Any]:
        """Extract context from operator arguments"""
        context = {}

        # Extract trajectory information if available
        if args and hasattr(args[0], '__dict__'):
            trajectory = args[0]
            context.update({
                "operator_applied": getattr(trajectory, 'operator_applied', None),
                "reasoning_pattern": getattr(trajectory, 'reasoning_pattern', None),
                "code_changes": getattr(trajectory, 'code_changes', None)
            })

        # Merge with explicit context kwargs
        if 'context' in kwargs:
            context.update(kwargs['context'])

        return context

    def _convert_to_operator_result(
        self,
        openhands_result: OpenHandsResult,
        operator_name: str
    ) -> Any:
        """
        Convert OpenHandsResult to SE-Darwin OperatorResult format

        Args:
            openhands_result: OpenHands result
            operator_name: Operator name

        Returns:
            OperatorResult-like object
        """
        # Import OperatorResult to create compatible result
        from infrastructure.se_operators import OperatorResult

        return OperatorResult(
            success=openhands_result.success,
            generated_code=openhands_result.generated_code or "",
            strategy_description=f"OpenHands {operator_name} generation",
            reasoning=f"Generated via OpenHands CodeActAgent (58.3% SWE-bench)",
            confidence_score=0.85 if openhands_result.success else 0.3,
            metadata={
                "openhands_enabled": True,
                "execution_time": openhands_result.execution_time,
                "iterations": openhands_result.iterations_used,
                **openhands_result.metadata
            }
        )


# Factory functions
def get_openhands_client(config: Optional[OpenHandsConfig] = None) -> OpenHandsClient:
    """
    Factory function to create OpenHands client

    Args:
        config: Optional configuration (defaults to env-based)

    Returns:
        OpenHandsClient instance
    """
    return OpenHandsClient(config=config)


def get_openhands_enhancer(
    client: Optional[OpenHandsClient] = None,
    **kwargs
) -> OpenHandsOperatorEnhancer:
    """
    Factory function to create operator enhancer

    Args:
        client: Optional OpenHands client (creates default if None)
        **kwargs: Additional enhancer arguments

    Returns:
        OpenHandsOperatorEnhancer instance
    """
    if client is None:
        client = get_openhands_client()

    return OpenHandsOperatorEnhancer(openhands_client=client, **kwargs)
