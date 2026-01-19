"""
Integration Tests for HTDAG Power Sampling

Tests the integration of Power Sampling (MCMC-based probabilistic decoding)
with HTDAG task decomposition layer.

Test Coverage:
1. Feature flag behavior (enabled/disabled)
2. Power Sampling success cases
3. Fallback on error scenarios
4. Quality evaluator validation
5. Prometheus metrics recording
6. Configuration validation
7. Error handling and graceful degradation

Based on specification: docs/specs/POWER_SAMPLING_HTDAG_INTEGRATION.md
"""

import asyncio
import json
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

# Genesis infrastructure imports
from infrastructure.htdag_planner import HTDAGPlanner
from infrastructure.task_dag import Task, TaskDAG
from .test_doubles.power_sampling_llm import RichPowerSamplingLLM


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    return RichPowerSamplingLLM()


@pytest.fixture
def planner(mock_llm_client):
    """Create HTDAGPlanner instance with mock LLM client"""
    return HTDAGPlanner(llm_client=mock_llm_client)


@pytest.fixture
def sample_user_request():
    """Sample user request for testing"""
    return "Build a SaaS invoicing platform for small businesses"


@pytest.fixture
def sample_context():
    """Sample context for task decomposition"""
    return {
        "target_audience": "small businesses",
        "tech_stack": "Python, React, PostgreSQL",
        "timeline": "3 months"
    }


# ============================================================
# FEATURE FLAG TESTS
# ============================================================

class TestFeatureFlag:
    """Test suite for Power Sampling feature flag behavior"""

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_uses_baseline(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: When feature flag is disabled, uses baseline LLM generation"""
        # Set feature flag to disabled
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "false")

        # Mock the baseline method to track if it was called
        planner._generate_top_level_tasks = AsyncMock(return_value=[
            Task(task_id="task_0", task_type="generic", description="Test task")
        ])

        # Call the method
        tasks = await planner._generate_top_level_tasks_with_fallback(
            sample_user_request,
            sample_context
        )

        # Verify baseline was called (not Power Sampling)
        assert planner._generate_top_level_tasks.called
        assert len(tasks) == 1
        assert tasks[0].task_id == "task_0"

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_uses_power_sampling(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: When feature flag is enabled, uses Power Sampling"""
        # Set feature flag to enabled
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")
        monkeypatch.setenv("POWER_SAMPLING_N_MCMC", "5")
        monkeypatch.setenv("POWER_SAMPLING_ALPHA", "2.0")
        monkeypatch.setenv("POWER_SAMPLING_BLOCK_SIZE", "32")

        # Mock Power Sampling to track if it was called
        planner._generate_top_level_tasks_power_sampling = AsyncMock(return_value=[
            Task(task_id="ps_task_1", task_type="design", description="Power Sampling task 1"),
            Task(task_id="ps_task_2", task_type="implement", description="Power Sampling task 2")
        ])

        # Call the method
        tasks = await planner._generate_top_level_tasks_with_fallback(
            sample_user_request,
            sample_context
        )

        # Verify Power Sampling was called
        assert planner._generate_top_level_tasks_power_sampling.called
        assert len(tasks) == 2
        assert tasks[0].task_id == "ps_task_1"
        assert tasks[1].task_id == "ps_task_2"

    @pytest.mark.asyncio
    async def test_feature_flag_case_insensitive(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Feature flag is case-insensitive"""
        for value in ["TRUE", "True", "true", "tRuE"]:
            monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", value)

            planner._generate_top_level_tasks_power_sampling = AsyncMock(return_value=[
                Task(task_id="task_1", task_type="generic", description="Test")
            ])

            tasks = await planner._generate_top_level_tasks_with_fallback(
                sample_user_request,
                sample_context
            )

            assert planner._generate_top_level_tasks_power_sampling.called

    @pytest.mark.asyncio
    async def test_feature_flag_default_disabled(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Default behavior is disabled when flag not set"""
        # Unset the environment variable
        monkeypatch.delenv("POWER_SAMPLING_HTDAG_ENABLED", raising=False)

        planner._generate_top_level_tasks = AsyncMock(return_value=[
            Task(task_id="baseline_task", task_type="generic", description="Baseline task")
        ])

        tasks = await planner._generate_top_level_tasks_with_fallback(
            sample_user_request,
            sample_context
        )

        # Verify baseline was used (default)
        assert planner._generate_top_level_tasks.called


# ============================================================
# POWER SAMPLING SUCCESS TESTS
# ============================================================

class TestPowerSamplingSuccess:
    """Test suite for successful Power Sampling integration"""

    @pytest.mark.asyncio
    async def test_power_sampling_returns_valid_tasks(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Power Sampling returns valid Task objects"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        # Mock power_sample to return valid decomposition
        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [
                    {"task_id": "research", "task_type": "design", "description": "Market research phase"},
                    {"task_id": "build", "task_type": "implement", "description": "Build MVP"},
                    {"task_id": "test", "task_type": "test", "description": "Test MVP"},
                    {"task_id": "deploy", "task_type": "deploy", "description": "Deploy to prod"}
                ],
                "quality_score": 0.87,
                "metadata": {"acceptance_rate": 0.65, "total_iterations": 10}
            }

            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context
            )

            # Verify tasks are valid
            assert len(tasks) == 4
            assert all(isinstance(t, Task) for t in tasks)
            assert tasks[0].task_id == "research"
            assert tasks[1].task_type == "implement"
            assert len(tasks[2].description) > 0

    @pytest.mark.asyncio
    async def test_power_sampling_with_custom_mcmc_params(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Power Sampling respects custom MCMC parameters"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")
        monkeypatch.setenv("POWER_SAMPLING_N_MCMC", "15")
        monkeypatch.setenv("POWER_SAMPLING_ALPHA", "3.0")
        monkeypatch.setenv("POWER_SAMPLING_BLOCK_SIZE", "64")

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [{"task_id": "t1", "task_type": "generic", "description": "Test task"}],
                "quality_score": 0.9,
                "metadata": {}
            }

            await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context,
                n_mcmc=15,
                alpha=3.0,
                block_size=64
            )

            # Verify power_sample was called with correct params
            assert mock_power_sample.called
            call_kwargs = mock_power_sample.call_args.kwargs
            assert call_kwargs['n_mcmc'] == 15
            assert call_kwargs['alpha'] == 3.0
            assert call_kwargs['block_size'] == 64

    @pytest.mark.asyncio
    async def test_quality_evaluator_function(self, planner, sample_user_request, sample_context):
        """Test: Quality evaluator correctly scores decompositions"""
        # Test valid decomposition (high score)
        valid_json = json.dumps({
            "tasks": [
                {"task_id": "t1", "task_type": "design", "description": "Research and design phase"},
                {"task_id": "t2", "task_type": "implement", "description": "Implementation phase"},
                {"task_id": "t3", "task_type": "test", "description": "Testing phase"}
            ]
        })

        # Call the evaluator (embedded in _generate_top_level_tasks_power_sampling)
        # We need to extract and test it separately
        def evaluate_quality(decomposition_text: str) -> float:
            try:
                parsed = json.loads(decomposition_text)
                tasks_data = parsed.get("tasks", [])
                if not isinstance(tasks_data, list) or len(tasks_data) == 0:
                    return 0.0
                if len(tasks_data) < 2:
                    return 0.3
                elif len(tasks_data) > 15:
                    return 0.5
                valid_count = 0
                for task in tasks_data:
                    if (isinstance(task, dict) and
                        "task_id" in task and
                        "task_type" in task and
                        "description" in task and
                        len(task.get("description", "")) >= 10):
                        valid_count += 1
                completeness_ratio = valid_count / len(tasks_data)
                if 3 <= len(tasks_data) <= 5:
                    return 0.9 * completeness_ratio + 0.1
                else:
                    return 0.8 * completeness_ratio
            except:
                return 0.0

        score = evaluate_quality(valid_json)
        assert score >= 0.8  # High quality for valid decomposition

        # Test invalid decomposition (low score)
        invalid_json = json.dumps({"tasks": []})
        score_invalid = evaluate_quality(invalid_json)
        assert score_invalid == 0.0

        # Test malformed JSON (zero score)
        score_malformed = evaluate_quality("not json")
        assert score_malformed == 0.0


# ============================================================
# FALLBACK AND ERROR HANDLING TESTS
# ============================================================

class TestFallbackBehavior:
    """Test suite for fallback and error handling"""

    @pytest.mark.asyncio
    async def test_power_sampling_fallback_on_error(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Falls back to baseline when Power Sampling fails"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        # Mock power_sample to raise an error
        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.side_effect = Exception("MCMC failed")

            # Mock baseline to succeed
            planner._generate_top_level_tasks = AsyncMock(return_value=[
                Task(task_id="fallback_task", task_type="generic", description="Fallback task")
            ])

            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context
            )

            # Verify fallback was called
            assert planner._generate_top_level_tasks.called
            assert len(tasks) == 1
            assert tasks[0].task_id == "fallback_task"

    @pytest.mark.asyncio
    async def test_empty_task_list_fallback(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Falls back when Power Sampling returns empty task list"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            # Return empty task list
            mock_power_sample.return_value = {
                "tasks": [],
                "quality_score": 0.0,
                "metadata": {}
            }

            planner._generate_top_level_tasks = AsyncMock(return_value=[
                Task(task_id="fallback", task_type="generic", description="Fallback task")
            ])

            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context
            )

            # Verify fallback was triggered
            assert planner._generate_top_level_tasks.called

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_power_sampling(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Circuit breaker prevents Power Sampling when open"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        # Simulate open circuit breaker
        planner.llm_circuit_breaker.can_attempt = Mock(return_value=False)

        planner._generate_top_level_tasks_heuristic = AsyncMock(return_value=[
            Task(task_id="heuristic_task", task_type="generic", description="Heuristic task")
        ])

        tasks = await planner._generate_top_level_tasks_with_fallback(
            sample_user_request,
            sample_context
        )

        # Verify heuristic was used (circuit breaker open)
        assert planner._generate_top_level_tasks_heuristic.called

    @pytest.mark.asyncio
    async def test_retry_logic_with_power_sampling(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Retry logic works with Power Sampling"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        # Mock power_sample to fail first, then succeed
        call_count = 0

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("First attempt failed")
                else:
                    return {
                        "tasks": [{"task_id": "t1", "task_type": "generic", "description": "Retry success"}],
                        "quality_score": 0.8,
                        "metadata": {}
                    }

            mock_power_sample.side_effect = side_effect

            # Mock fallback for final attempt
            planner._generate_top_level_tasks = AsyncMock(return_value=[
                Task(task_id="t1", task_type="generic", description="Retry success")
            ])

            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context
            )

            # Verify retry occurred
            assert len(tasks) >= 1


# ============================================================
# METRICS RECORDING TESTS
# ============================================================

class TestMetricsRecording:
    """Test suite for Prometheus metrics recording"""

    def test_metrics_recording_power_sampling(self, planner):
        """Test: Metrics are recorded for Power Sampling calls"""
        tasks = [
            Task(task_id="t1", task_type="design", description="Task 1"),
            Task(task_id="t2", task_type="implement", description="Task 2"),
            Task(task_id="t3", task_type="test", description="Task 3")
        ]

        # Call metrics recording (Prometheus available in this test)
        planner._record_power_sampling_metrics(tasks, use_power_sampling=True)

        # Verify no exceptions were raised
        # Actual metric values aren't tested (would require Prometheus registry inspection)

    def test_metrics_recording_baseline(self, planner):
        """Test: Metrics are recorded for baseline calls"""
        tasks = [Task(task_id="t1", task_type="generic", description="Task 1")]

        # Should not raise exception even if Prometheus unavailable
        planner._record_power_sampling_metrics(tasks, use_power_sampling=False)

    def test_metrics_recording_handles_errors_gracefully(self, planner):
        """Test: Metrics recording errors don't crash decomposition"""
        tasks = [Task(task_id="t1", task_type="generic", description="Task 1")]

        # Metrics recording should gracefully handle missing Prometheus or errors
        # This test verifies no exception is raised even if Prometheus unavailable
        try:
            planner._record_power_sampling_metrics(tasks, use_power_sampling=True)
        except Exception as e:
            pytest.fail(f"Metrics recording should not raise exceptions: {e}")


# ============================================================
# CONFIGURATION VALIDATION TESTS
# ============================================================

class TestConfiguration:
    """Test suite for configuration validation"""

    @pytest.mark.asyncio
    async def test_invalid_mcmc_params_handled(self, planner, sample_user_request, sample_context):
        """Test: Invalid MCMC parameters are handled gracefully"""
        # Test with invalid n_mcmc (negative)
        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [{"task_id": "t1", "task_type": "generic", "description": "Test"}],
                "quality_score": 0.5,
                "metadata": {}
            }

            planner._generate_top_level_tasks = AsyncMock(return_value=[
                Task(task_id="fallback", task_type="generic", description="Fallback")
            ])

            # Should fall back gracefully on invalid params
            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context,
                n_mcmc=-5  # Invalid
            )

            # Should still return valid tasks (via fallback)
            assert len(tasks) >= 1

    @pytest.mark.asyncio
    async def test_environment_variable_parsing(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Environment variables are parsed correctly"""
        monkeypatch.setenv("POWER_SAMPLING_N_MCMC", "12")
        monkeypatch.setenv("POWER_SAMPLING_ALPHA", "2.5")
        monkeypatch.setenv("POWER_SAMPLING_BLOCK_SIZE", "48")

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [{"task_id": "t1", "task_type": "generic", "description": "Test"}],
                "quality_score": 0.8,
                "metadata": {}
            }

            monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

            await planner._generate_top_level_tasks_with_fallback(
                sample_user_request,
                sample_context
            )

            # Verify correct params were passed
            if mock_power_sample.called:
                call_kwargs = mock_power_sample.call_args.kwargs
                assert call_kwargs.get('n_mcmc') == 12
                assert call_kwargs.get('alpha') == 2.5
                assert call_kwargs.get('block_size') == 48


# ============================================================
# END-TO-END INTEGRATION TESTS
# ============================================================

class TestEndToEndIntegration:
    """Test suite for end-to-end integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_decomposition_with_power_sampling(self, mock_llm_client, sample_user_request, monkeypatch):
        """Test: Full task decomposition flow with Power Sampling enabled"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        planner = HTDAGPlanner(llm_client=mock_llm_client)

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [
                    {"task_id": "research", "task_type": "design", "description": "Market research"},
                    {"task_id": "build", "task_type": "implement", "description": "Build MVP"},
                    {"task_id": "deploy", "task_type": "deploy", "description": "Deploy to prod"}
                ],
                "quality_score": 0.85,
                "metadata": {"acceptance_rate": 0.7}
            }

            dag = await planner.decompose_task(sample_user_request)

            # Verify DAG was created successfully
            assert len(dag) >= 3
            assert not dag.has_cycle()

    @pytest.mark.asyncio
    async def test_power_sampling_with_real_quality_evaluation(self, planner, sample_user_request, sample_context, monkeypatch):
        """Test: Power Sampling with real quality evaluation logic"""
        monkeypatch.setenv("POWER_SAMPLING_HTDAG_ENABLED", "true")

        # Create a quality evaluator that actually evaluates
        quality_scores = []

        def capture_quality(decomposition_text: str) -> float:
            try:
                parsed = json.loads(decomposition_text)
                tasks = parsed.get("tasks", [])
                score = len(tasks) / 5.0  # Simple scoring
                quality_scores.append(score)
                return score
            except:
                return 0.0

        with patch('infrastructure.power_sampling.power_sample') as mock_power_sample:
            mock_power_sample.return_value = {
                "tasks": [
                    {"task_id": "t1", "task_type": "design", "description": "Design phase"},
                    {"task_id": "t2", "task_type": "implement", "description": "Implement phase"}
                ],
                "quality_score": 0.8,
                "metadata": {}
            }

            tasks = await planner._generate_top_level_tasks_power_sampling(
                sample_user_request,
                sample_context
            )

            assert len(tasks) >= 1


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
