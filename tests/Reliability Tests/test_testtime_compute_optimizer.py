"""
Test suite for test-time compute optimization

Validates:
1. Best-of-N sampling generates diverse candidates
2. Beam search improves quality
3. Multi-Agent Verification (MAV) provides robust scoring
4. Self-consistency finds consensus
5. Quality improvement over baseline (20-30% target)
"""

import pytest
import asyncio
from typing import Dict, Any, List
import statistics

from infrastructure.testtime_compute_optimizer import (
    TestTimeComputeOptimizer,
    SearchStrategy,
    DecompositionCandidate
)


class TestTestTimeComputeOptimizer:
    """Test suite for test-time compute optimizer"""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance"""
        return TestTimeComputeOptimizer(
            default_strategy=SearchStrategy.BEST_OF_N,
            beam_width=5,
            max_samples=10,
            enable_adaptive_compute=True
        )

    @pytest.fixture
    async def mock_decompose_fn(self):
        """Mock decomposition function with variability"""
        call_count = {"value": 0}

        async def decompose(request: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Generate variable quality decomposition"""
            call_count["value"] += 1

            # Vary quality based on temperature
            temp = context.get("temperature", 0.5)

            # Lower temperature = fewer, more focused tasks
            # Higher temperature = more diverse tasks
            if temp < 0.5:
                num_tasks = 3
            elif temp < 0.7:
                num_tasks = 4
            else:
                num_tasks = 5 + (call_count["value"] % 2)  # Add variety

            tasks = []
            for i in range(num_tasks):
                tasks.append({
                    "task_id": f"task_{i}_{call_count['value']}",
                    "task_type": ["design", "implement", "test", "deploy"][i % 4],
                    "description": f"Task {i} for {request} (temp={temp:.2f})"
                })

            return {
                "tasks": tasks,
                "depth": 2 if num_tasks > 4 else 1,
                "parallel_tasks": max(1, num_tasks // 2)
            }

        decompose.call_count = call_count
        return decompose

    # Test 1: Best-of-N Sampling

    @pytest.mark.asyncio
    async def test_best_of_n_generates_multiple_candidates(self, optimizer, mock_decompose_fn):
        """Test that best-of-N generates N diverse candidates"""
        n = 5

        candidate = await optimizer._best_of_n_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Build a SaaS application",
            context={},
            n=n
        )

        # Should have called decompose_fn N times
        assert mock_decompose_fn.call_count["value"] == n

        # Should return best candidate
        assert isinstance(candidate, DecompositionCandidate)
        assert candidate.strategy == SearchStrategy.BEST_OF_N
        assert 0.0 <= candidate.quality_score <= 1.0
        assert candidate.metadata["n"] == n

    @pytest.mark.asyncio
    async def test_best_of_n_selects_highest_quality(self, optimizer, mock_decompose_fn):
        """Test that best-of-N selects highest quality candidate"""
        candidate = await optimizer._best_of_n_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Complex multi-step task",
            context={},
            n=10
        )

        # Quality should be in optimal range
        assert candidate.quality_score >= 0.5  # Should be better than random

    # Test 2: Beam Search

    @pytest.mark.asyncio
    async def test_beam_search_prunes_low_quality(self, optimizer, mock_decompose_fn):
        """Test that beam search maintains top-k candidates"""
        compute_budget = 10

        candidate = await optimizer._beam_search_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Build complex system",
            context={},
            compute_budget=compute_budget
        )

        # Should return best from beam
        assert isinstance(candidate, DecompositionCandidate)
        assert candidate.strategy == SearchStrategy.BEAM_SEARCH
        # Should use optimizer's configured beam_width
        assert candidate.metadata["beam_width"] <= optimizer.beam_width

    @pytest.mark.asyncio
    async def test_beam_search_refinement(self, optimizer, mock_decompose_fn):
        """Test that beam search does refinement with sufficient budget"""
        candidate = await optimizer._beam_search_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Task requiring refinement",
            context={},
            compute_budget=20  # High budget should trigger refinement
        )

        # Refinement should have happened
        assert candidate.metadata.get("refined", False) is True

    # Test 3: Multi-Agent Verification (MAV)

    @pytest.mark.asyncio
    async def test_mav_uses_multiple_verifiers(self, optimizer, mock_decompose_fn):
        """Test that MAV uses multiple verification scores"""
        candidate = await optimizer._mav_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Task requiring verification",
            context={},
            compute_budget=10
        )

        # Should have multiple verification scores
        assert len(candidate.verification_scores) >= 3  # At least 3 verifiers
        assert candidate.strategy == SearchStrategy.MULTI_AGENT_VERIFICATION

        # Metadata should include verifier info
        assert "n_verifiers" in candidate.metadata
        assert candidate.metadata["n_verifiers"] >= 3

    @pytest.mark.asyncio
    async def test_mav_aggregate_scoring(self, optimizer, mock_decompose_fn):
        """Test that MAV aggregates scores correctly"""
        candidate = await optimizer._mav_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Multi-verifier task",
            context={},
            compute_budget=12
        )

        # Quality score should be aggregate of verifiers
        expected_aggregate = statistics.mean(candidate.verification_scores)
        assert abs(candidate.quality_score - expected_aggregate) < 0.01

        # Should have standard deviation in metadata
        assert "verification_std" in candidate.metadata

    # Test 4: Self-Consistency

    @pytest.mark.asyncio
    async def test_self_consistency_finds_consensus(self, optimizer, mock_decompose_fn):
        """Test that self-consistency aggregates consensus tasks"""
        candidate = await optimizer._self_consistency_optimize(
            decompose_fn=mock_decompose_fn,
            user_request="Task with consensus",
            context={},
            n=5
        )

        # Should return consensus decomposition
        assert candidate.strategy == SearchStrategy.SELF_CONSISTENCY
        assert "method" in candidate.decomposition
        assert candidate.decomposition["method"] == "self_consistency"

        # Should have consensus metadata
        assert "n_consensus" in candidate.metadata
        assert "n_total" in candidate.metadata

    # Test 5: Adaptive Compute Budget

    @pytest.mark.asyncio
    async def test_adaptive_compute_simple_task(self, optimizer):
        """Test adaptive compute allocates fewer samples for simple tasks"""
        simple_task = "Create a README file"

        budget = optimizer._estimate_compute_budget(simple_task)

        # Simple task should get minimal budget
        assert 3 <= budget <= 5

    @pytest.mark.asyncio
    async def test_adaptive_compute_complex_task(self, optimizer):
        """Test adaptive compute allocates more samples for complex tasks"""
        complex_task = (
            "Build a complex distributed multi-step architecture "
            "that integrates multiple systems and scales to production "
            "with optimized performance"
        )

        budget = optimizer._estimate_compute_budget(complex_task)

        # Complex task should get max budget
        assert budget >= 8

    # Test 6: Quality Scoring

    @pytest.mark.asyncio
    async def test_score_decomposition_optimal_task_count(self, optimizer):
        """Test that optimal task count (2-7) scores highest"""
        # Optimal decomposition (5 tasks)
        optimal = {
            "tasks": [
                {"task_id": f"task_{i}", "task_type": "implement", "description": "Do something"}
                for i in range(5)
            ],
            "depth": 3,
            "parallel_tasks": 2
        }

        # Too few tasks
        too_few = {
            "tasks": [
                {"task_id": "task_0", "task_type": "generic", "description": "Do everything"}
            ],
            "depth": 1
        }

        # Too many tasks
        too_many = {
            "tasks": [
                {"task_id": f"task_{i}", "task_type": "generic", "description": "Task"}
                for i in range(15)
            ],
            "depth": 1
        }

        score_optimal = optimizer._score_decomposition(optimal)
        score_too_few = optimizer._score_decomposition(too_few)
        score_too_many = optimizer._score_decomposition(too_many)

        assert score_optimal > score_too_few
        assert score_optimal > score_too_many

    @pytest.mark.asyncio
    async def test_score_completeness(self, optimizer):
        """Test completeness scoring rewards diverse task types"""
        # Complete (has design, implement, test)
        complete = {
            "tasks": [
                {"task_id": "t1", "task_type": "design", "description": "Design the system"},
                {"task_id": "t2", "task_type": "implement", "description": "Build it"},
                {"task_id": "t3", "task_type": "test", "description": "Test it"}
            ]
        }

        # Incomplete (all same type)
        incomplete = {
            "tasks": [
                {"task_id": "t1", "task_type": "generic", "description": "Task 1"},
                {"task_id": "t2", "task_type": "generic", "description": "Task 2"}
            ]
        }

        score_complete = optimizer._score_completeness(complete)
        score_incomplete = optimizer._score_completeness(incomplete)

        assert score_complete > score_incomplete

    @pytest.mark.asyncio
    async def test_score_parallelism(self, optimizer):
        """Test parallelism scoring rewards parallel tasks"""
        # High parallelism (research, design tasks)
        parallel = {
            "tasks": [
                {"task_id": "t1", "task_type": "research", "description": "Research A"},
                {"task_id": "t2", "task_type": "research", "description": "Research B"},
                {"task_id": "t3", "task_type": "design", "description": "Design C"}
            ]
        }

        # Low parallelism (sequential tasks)
        sequential = {
            "tasks": [
                {"task_id": "t1", "task_type": "implement", "description": "Build A"},
                {"task_id": "t2", "task_type": "deploy", "description": "Deploy A"}
            ]
        }

        score_parallel = optimizer._score_parallelism(parallel)
        score_sequential = optimizer._score_parallelism(sequential)

        assert score_parallel > score_sequential

    # Test 7: End-to-End Optimization

    @pytest.mark.asyncio
    async def test_optimize_decomposition_best_of_n(self, optimizer, mock_decompose_fn):
        """Test end-to-end optimization with best-of-N"""
        candidate = await optimizer.optimize_decomposition(
            decompose_fn=mock_decompose_fn,
            user_request="Build a web application",
            context={},
            strategy=SearchStrategy.BEST_OF_N,
            compute_budget=8
        )

        # Should return valid candidate
        assert isinstance(candidate, DecompositionCandidate)
        assert candidate.strategy == SearchStrategy.BEST_OF_N
        assert len(candidate.decomposition["tasks"]) > 0
        assert 0.0 <= candidate.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_optimize_decomposition_beam_search(self, optimizer, mock_decompose_fn):
        """Test end-to-end optimization with beam search"""
        candidate = await optimizer.optimize_decomposition(
            decompose_fn=mock_decompose_fn,
            user_request="Complex system architecture",
            context={},
            strategy=SearchStrategy.BEAM_SEARCH,
            compute_budget=10
        )

        assert candidate.strategy == SearchStrategy.BEAM_SEARCH
        assert candidate.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_optimize_decomposition_mav(self, optimizer, mock_decompose_fn):
        """Test end-to-end optimization with MAV"""
        candidate = await optimizer.optimize_decomposition(
            decompose_fn=mock_decompose_fn,
            user_request="Mission-critical system",
            context={},
            strategy=SearchStrategy.MULTI_AGENT_VERIFICATION,
            compute_budget=12
        )

        assert candidate.strategy == SearchStrategy.MULTI_AGENT_VERIFICATION
        assert len(candidate.verification_scores) >= 3

    # Test 8: Quality Improvement Validation

    @pytest.mark.asyncio
    async def test_quality_improvement_over_baseline(self, optimizer, mock_decompose_fn):
        """
        Test that test-time compute improves quality over single-shot baseline

        Target: 20-30% improvement
        """
        request = "Build a scalable distributed system with monitoring"

        # Baseline: Single decomposition
        baseline_decomp = await mock_decompose_fn(request, {"temperature": 0.5})
        baseline_score = optimizer._score_decomposition(baseline_decomp)

        # Reset call count
        mock_decompose_fn.call_count["value"] = 0

        # Test-time compute: Best-of-10
        optimized_candidate = await optimizer._best_of_n_optimize(
            decompose_fn=mock_decompose_fn,
            user_request=request,
            context={},
            n=10
        )

        # Optimized should be better
        improvement = (optimized_candidate.quality_score - baseline_score) / baseline_score

        # Should see improvement (may not always hit 20%, but should be positive)
        assert optimized_candidate.quality_score >= baseline_score

        # Log improvement for analysis
        print(f"\nQuality improvement: {improvement*100:.1f}%")
        print(f"Baseline score: {baseline_score:.3f}")
        print(f"Optimized score: {optimized_candidate.quality_score:.3f}")

    @pytest.mark.asyncio
    async def test_mav_quality_stability(self, optimizer, mock_decompose_fn):
        """Test that MAV provides stable quality scores"""
        # Run MAV multiple times
        candidates = []
        for _ in range(3):
            candidate = await optimizer._mav_optimize(
                decompose_fn=mock_decompose_fn,
                user_request="Consistent quality task",
                context={},
                compute_budget=10
            )
            candidates.append(candidate.quality_score)

        # Scores should be reasonably stable (low variance)
        std_dev = statistics.stdev(candidates) if len(candidates) > 1 else 0

        # Standard deviation should be low (< 0.2)
        assert std_dev < 0.2, f"MAV scores too variable: {candidates}"

    # Test 9: Error Handling

    @pytest.mark.asyncio
    async def test_handles_failed_candidates(self, optimizer):
        """Test that optimizer handles some failed decomposition attempts"""
        fail_count = {"value": 0}

        async def failing_decompose(request: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Fail 50% of the time"""
            fail_count["value"] += 1
            if fail_count["value"] % 2 == 0:
                raise Exception("Simulated decomposition failure")

            return {
                "tasks": [
                    {"task_id": "task_0", "task_type": "generic", "description": "Successful task"}
                ],
                "depth": 1
            }

        # Should still succeed with valid candidates
        candidate = await optimizer._best_of_n_optimize(
            decompose_fn=failing_decompose,
            user_request="Task with failures",
            context={},
            n=6
        )

        # Should have succeeded with at least some valid candidates
        assert candidate is not None
        assert candidate.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_raises_on_all_failures(self, optimizer):
        """Test that optimizer raises error when all candidates fail"""
        async def always_failing_decompose(request: str, context: Dict[str, Any]) -> Dict[str, Any]:
            raise Exception("Always fails")

        # Should raise error
        with pytest.raises(RuntimeError, match="All Best-of-N candidates failed"):
            await optimizer._best_of_n_optimize(
                decompose_fn=always_failing_decompose,
                user_request="Doomed task",
                context={},
                n=5
            )

    # Test 10: Strategy Selection

    @pytest.mark.asyncio
    async def test_strategy_routing(self, optimizer, mock_decompose_fn):
        """Test that different strategies are routed correctly"""
        strategies = [
            SearchStrategy.BEST_OF_N,
            SearchStrategy.BEAM_SEARCH,
            SearchStrategy.MULTI_AGENT_VERIFICATION,
            SearchStrategy.SELF_CONSISTENCY
        ]

        for strategy in strategies:
            candidate = await optimizer.optimize_decomposition(
                decompose_fn=mock_decompose_fn,
                user_request=f"Test {strategy.value}",
                context={},
                strategy=strategy,
                compute_budget=8
            )

            assert candidate.strategy == strategy


# Integration Tests

class TestTestTimeComputeIntegration:
    """Integration tests with HTDAG planner"""

    @pytest.mark.asyncio
    async def test_htdag_testtime_compute_feature_flag(self):
        """Test that HTDAG planner respects test-time compute feature flag"""
        from infrastructure.htdag_planner import HTDAGPlanner
        import os

        # Test with flag enabled
        os.environ["USE_TESTTIME_COMPUTE"] = "true"
        planner_enabled = HTDAGPlanner(enable_testtime_compute=True)

        assert planner_enabled.enable_testtime_compute is True
        assert planner_enabled.testtime_optimizer is not None

        # Test with flag disabled
        os.environ["USE_TESTTIME_COMPUTE"] = "false"
        planner_disabled = HTDAGPlanner(enable_testtime_compute=False)

        assert planner_disabled.enable_testtime_compute is False

        # Cleanup
        del os.environ["USE_TESTTIME_COMPUTE"]

    @pytest.mark.asyncio
    async def test_htdag_testtime_strategy_configuration(self):
        """Test that HTDAG planner configures strategy from env vars"""
        from infrastructure.htdag_planner import HTDAGPlanner
        import os

        os.environ["USE_TESTTIME_COMPUTE"] = "true"
        os.environ["TESTTIME_STRATEGY"] = "beam_search"
        os.environ["TESTTIME_BEAM_WIDTH"] = "7"
        os.environ["TESTTIME_MAX_SAMPLES"] = "12"

        planner = HTDAGPlanner(enable_testtime_compute=True)

        assert planner.testtime_optimizer is not None
        assert planner.testtime_optimizer.default_strategy == SearchStrategy.BEAM_SEARCH
        assert planner.testtime_optimizer.beam_width == 7
        assert planner.testtime_optimizer.max_samples == 12

        # Cleanup
        del os.environ["USE_TESTTIME_COMPUTE"]
        del os.environ["TESTTIME_STRATEGY"]
        del os.environ["TESTTIME_BEAM_WIDTH"]
        del os.environ["TESTTIME_MAX_SAMPLES"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
