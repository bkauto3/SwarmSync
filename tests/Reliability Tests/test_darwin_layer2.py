"""
Comprehensive Tests for Darwin Layer 2 - Self-Improving Agents
Tests all components of the self-improvement system

Components Tested:
1. DarwinAgent - Code evolution loop
2. CodeSandbox - Safe execution environment
3. BenchmarkRunner - Empirical validation
4. WorldModel - Outcome prediction
5. RLWarmStartSystem - Checkpoint management
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

# Darwin components
from agents.darwin_agent import DarwinAgent, EvolutionAttempt, ImprovementType, EvolutionStatus
from infrastructure.sandbox import CodeSandbox, SandboxResult, SandboxStatus
from infrastructure.benchmark_runner import BenchmarkRunner, BenchmarkType, BenchmarkStatus, Task
from infrastructure.world_model import WorldModel, WorldState, Prediction
from infrastructure.rl_warmstart import RLWarmStartSystem, Checkpoint, CheckpointQuality

# Infrastructure
from infrastructure import OutcomeTag


class TestCodeSandbox:
    """Test suite for Docker-based code sandbox"""

    @pytest.mark.asyncio
    async def test_simple_execution(self):
        """Test basic code execution in sandbox"""
        sandbox = CodeSandbox()

        result = await sandbox.execute_code(
            code="print('Hello from sandbox!')",
            timeout=10
        )

        assert result.status == SandboxStatus.COMPLETED.value
        assert result.exit_code == 0
        assert "Hello from sandbox!" in result.stdout

    @pytest.mark.asyncio
    async def test_syntax_error_detection(self):
        """Test sandbox detects syntax errors"""
        sandbox = CodeSandbox()

        result = await sandbox.execute_code(
            code="print('missing closing paren'",
            timeout=10
        )

        assert result.status == SandboxStatus.FAILED.value
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        """Test sandbox enforces timeout"""
        sandbox = CodeSandbox()

        result = await sandbox.execute_code(
            code="import time; time.sleep(100)",
            timeout=2
        )

        assert result.status == SandboxStatus.TIMEOUT.value
        assert result.execution_time < 5  # Should kill quickly

    @pytest.mark.asyncio
    async def test_syntax_validation(self):
        """Test standalone syntax validation"""
        sandbox = CodeSandbox()

        # Valid syntax
        valid, error = await sandbox.validate_syntax("print('hello')")
        assert valid is True
        assert error == ""

        # Invalid syntax
        valid, error = await sandbox.validate_syntax("print('missing paren'")
        assert valid is False
        assert "SyntaxError" in error or "invalid syntax" in error.lower()

    @pytest.mark.asyncio
    async def test_requirements_installation(self):
        """Test installing requirements in sandbox"""
        sandbox = CodeSandbox()

        result = await sandbox.execute_code(
            code="import requests; print(f'Requests version: {requests.__version__}')",
            timeout=60,
            requirements=["requests"]
        )

        # Should succeed (or fail gracefully if network unavailable)
        assert result.status in [SandboxStatus.COMPLETED.value, SandboxStatus.FAILED.value]


class TestBenchmarkRunner:
    """Test suite for benchmark validation system"""

    @pytest.mark.asyncio
    async def test_genesis_benchmark_load(self):
        """Test Genesis custom benchmark loads correctly"""
        runner = BenchmarkRunner()

        tasks = runner._benchmark_suites.get("genesis_custom", [])
        assert len(tasks) > 0, "Genesis benchmark should have tasks"
        assert all(isinstance(t, Task) for t in tasks)

    @pytest.mark.asyncio
    async def test_benchmark_execution(self):
        """Test running benchmark against an agent"""
        runner = BenchmarkRunner()

        # Create dummy agent
        dummy_agent = Path(tempfile.mktemp(suffix=".py"))
        dummy_agent.write_text("""
def generate(business_type, description):
    return f"Specification for {business_type}: {description}. Tech stack: Python, React."

def run(**kwargs):
    return generate(**kwargs)
""")

        try:
            result = await runner.run_benchmark(
                agent_code_path=dummy_agent,
                agent_name="test_agent",
                agent_version="v1.0",
                benchmark_type=BenchmarkType.GENESIS_CUSTOM,
            )

            assert result.status == BenchmarkStatus.COMPLETED.value
            assert result.tasks_total > 0
            assert 0.0 <= result.overall_score <= 1.0
            assert "accuracy" in result.metrics

        finally:
            if dummy_agent.exists():
                dummy_agent.unlink()

    @pytest.mark.asyncio
    async def test_task_execution(self):
        """Test individual task execution"""
        runner = BenchmarkRunner()

        dummy_agent = Path(tempfile.mktemp(suffix=".py"))
        dummy_agent.write_text("def test(): return 'result'")

        try:
            task = Task(
                task_id="test_task",
                description="Test task",
                input_data={"param": "value"},
                expected_output={"has_result": True},
                test_code="def test_test(result): return True",
            )

            result = await runner._execute_task(dummy_agent, task)

            assert "task_id" in result
            assert "passed" in result

        finally:
            if dummy_agent.exists():
                dummy_agent.unlink()


class TestWorldModel:
    """Test suite for world model predictions"""

    @pytest.mark.asyncio
    async def test_world_model_initialization(self):
        """Test world model initializes correctly"""
        model = WorldModel()

        assert model.state_dim == 128
        assert model.action_dim == 128
        assert model.hidden_dim == 256

    @pytest.mark.asyncio
    async def test_prediction(self):
        """Test world model prediction"""
        model = WorldModel()

        state = WorldState(
            agent_name="test_agent",
            code_snapshot="hash123",
            recent_actions=["action1"],
            metrics={"overall_score": 0.6},
            context={},
        )

        prediction = await model.predict(
            current_state=state,
            proposed_action="def new_function(): return 'improved'"
        )

        assert isinstance(prediction, Prediction)
        assert 0.0 <= prediction.success_probability <= 1.0
        assert -1.0 <= prediction.expected_improvement <= 1.0
        assert 0.0 <= prediction.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_training(self):
        """Test world model training (smoke test)"""
        model = WorldModel()

        # Training should complete without errors
        await model.train(num_epochs=2, batch_size=16)

        # Should have training history
        # Note: May be empty if no trajectories in Replay Buffer
        assert isinstance(model.training_history, list)


class TestRLWarmStartSystem:
    """Test suite for RL warm-start checkpoint system"""

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self):
        """Test creating and saving checkpoints"""
        system = RLWarmStartSystem(checkpoints_dir=Path(tempfile.mkdtemp()))

        # Create dummy code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'checkpoint code'")

        try:
            checkpoint = await system.save_checkpoint(
                agent_name="test_agent",
                version="v1.0",
                code_path=dummy_code,
                metrics={"overall_score": 0.85},
            )

            assert checkpoint.checkpoint_id.startswith("cp_test_agent")
            assert checkpoint.quality_tier in [qt.value for qt in CheckpointQuality]
            assert checkpoint.code_path.exists()

        finally:
            if dummy_code.exists():
                dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_get_best_checkpoint(self):
        """Test retrieving best checkpoint"""
        system = RLWarmStartSystem(checkpoints_dir=Path(tempfile.mkdtemp()))

        # Create multiple checkpoints
        for i, score in enumerate([0.6, 0.8, 0.7]):
            dummy_code = Path(tempfile.mktemp(suffix=".py"))
            dummy_code.write_text(f"# Version {i}")

            await system.save_checkpoint(
                agent_name="test_agent",
                version=f"v{i}",
                code_path=dummy_code,
                metrics={"overall_score": score},
            )

            dummy_code.unlink()

        # Get best checkpoint
        best = await system.get_best_checkpoint("test_agent")

        assert best is not None
        assert best.metrics["overall_score"] == 0.8  # Highest score

    @pytest.mark.asyncio
    async def test_warmstart_config_creation(self):
        """Test creating warm-start configuration"""
        system = RLWarmStartSystem(checkpoints_dir=Path(tempfile.mkdtemp()))

        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("# code")

        checkpoint = await system.save_checkpoint(
            agent_name="test_agent",
            version="v1.0",
            code_path=dummy_code,
            metrics={"overall_score": 0.85},
        )

        dummy_code.unlink()

        config = await system.create_warmstart_config(
            checkpoint=checkpoint,
            target_task="new_task"
        )

        assert config.checkpoint_id == checkpoint.checkpoint_id
        assert config.expected_boost > 0.0  # Should expect some improvement

    @pytest.mark.asyncio
    async def test_quality_tier_determination(self):
        """Test checkpoint quality tier assignment"""
        system = RLWarmStartSystem(checkpoints_dir=Path(tempfile.mkdtemp()))

        test_cases = [
            (0.95, CheckpointQuality.EXCELLENT),
            (0.80, CheckpointQuality.GOOD),
            (0.60, CheckpointQuality.FAIR),
            (0.40, CheckpointQuality.POOR),
        ]

        for success_rate, expected_tier in test_cases:
            tier = system._determine_quality_tier(success_rate)
            assert tier == expected_tier


class TestDarwinAgent:
    """Test suite for Darwin evolution agent"""

    @pytest.mark.asyncio
    async def test_darwin_initialization(self, mock_openai_patch):
        """Test Darwin agent initializes correctly"""
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        darwin = DarwinAgent(
            agent_name="test_agent",
            initial_code_path=str(dummy_code),
            max_generations=2,
            population_size=2,
        )

        assert darwin.agent_name == "test_agent"
        assert darwin.max_generations == 2
        assert darwin.population_size == 2
        assert len(darwin.archive) == 1  # Initial version

        dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_parent_selection(self, mock_openai_patch):
        """Test fitness-proportional parent selection"""
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        darwin = DarwinAgent(
            agent_name="test_agent",
            initial_code_path=str(dummy_code),
        )

        parent = await darwin._select_parent()

        assert parent in darwin.archive

        dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_improvement_type_determination(self, mock_openai_patch):
        """Test improvement type classification"""
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        darwin = DarwinAgent(
            agent_name="test_agent",
            initial_code_path=str(dummy_code),
        )

        # Test different diagnoses
        test_cases = [
            ("Fix bug in validation logic", ImprovementType.BUG_FIX),
            ("Optimize performance bottleneck", ImprovementType.OPTIMIZATION),
            ("Add missing feature", ImprovementType.NEW_FEATURE),
            ("Improve error handling", ImprovementType.ERROR_HANDLING),
        ]

        for diagnosis, expected_type in test_cases:
            improvement_type = await darwin._determine_improvement_type(diagnosis)
            assert improvement_type == expected_type

        dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_code_generation(self, mock_openai_patch):
        """Test LLM code generation with mocked OpenAI API"""
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        darwin = DarwinAgent(
            agent_name="test_agent",
            initial_code_path=str(dummy_code),
        )

        # Use mocked OpenAI client (from mock_openai_patch fixture)
        improved_code = await darwin._generate_code_improvements(
            parent_code="def agent(): return 'old'",
            diagnosis="Improve return value",
            improvement_type=ImprovementType.OPTIMIZATION.value
        )

        # Verify mock returned valid code
        assert improved_code is not None
        assert isinstance(improved_code, str)
        assert len(improved_code) > 0
        assert "def " in improved_code  # Should contain function definition

        dummy_code.unlink()


class TestIntegration:
    """Integration tests for complete Layer 2 system"""

    @pytest.mark.asyncio
    async def test_full_darwin_evolution_cycle(self, mock_openai_patch, mock_sandbox):
        """Test complete evolution cycle with mocked LLM and sandbox"""
        # Create initial agent
        initial_code = Path(tempfile.mktemp(suffix=".py"))
        initial_code.write_text("""
def generate(business_type, description):
    return f"Spec for {business_type}: {description}"
""")

        try:
            # Use mock sandbox execution (faster, no Docker required)
            mock_sandbox.use_mock = True

            darwin = DarwinAgent(
                agent_name="test_evolution_agent",
                initial_code_path=str(initial_code),
                max_generations=1,  # Just 1 generation for testing
                population_size=1,  # Just 1 attempt
            )

            # Run evolution with mocked LLM and sandbox
            archive = await darwin.evolve()

            # Verify evolution completed
            assert archive.agent_name == "test_evolution_agent"
            assert archive.total_attempts >= 0
            assert 0.0 <= archive.acceptance_rate <= 1.0
            assert len(archive.successful_attempts) >= 0

        finally:
            if initial_code.exists():
                initial_code.unlink()

    @pytest.mark.asyncio
    async def test_checkpoint_to_warmstart_workflow(self):
        """Test complete checkpoint → warm-start workflow"""
        # Create checkpoint system
        warmstart_system = RLWarmStartSystem(
            checkpoints_dir=Path(tempfile.mkdtemp())
        )

        # Create agent code
        agent_code = Path(tempfile.mktemp(suffix=".py"))
        agent_code.write_text("def agent(): return 'v1'")

        try:
            # 1. Save checkpoint
            checkpoint = await warmstart_system.save_checkpoint(
                agent_name="workflow_agent",
                version="v1.0",
                code_path=agent_code,
                metrics={"overall_score": 0.80},
            )

            # 2. Get best checkpoint
            best = await warmstart_system.get_best_checkpoint("workflow_agent")
            assert best.checkpoint_id == checkpoint.checkpoint_id

            # 3. Create warm-start config
            config = await warmstart_system.create_warmstart_config(
                checkpoint=best,
                target_task="test_task"
            )
            assert config.expected_boost > 0.0

            # 4. Initialize from checkpoint
            target_path = Path(tempfile.mktemp(suffix=".py"))
            success = await warmstart_system.initialize_from_checkpoint(
                checkpoint=best,
                target_path=target_path
            )

            assert success is True
            assert target_path.exists()

            # Cleanup target
            if target_path.exists():
                target_path.unlink()

        finally:
            if agent_code.exists():
                agent_code.unlink()


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
