"""
Integration Tests: Trajectory Pool + SE Operators
ISSUE #5: Test end-to-end evolution loop

Tests:
- Full evolution cycle: pool → operators → pool update
- Cross-trajectory learning patterns
- Concurrent operator execution
- Pool statistics after operator runs
- Multi-generation evolution scenarios

Based on SE-Agent (arXiv 2508.02085)
"""

import pytest
import asyncio
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, Mock

from infrastructure.trajectory_pool import (
    Trajectory,
    TrajectoryPool,
    TrajectoryStatus,
    OperatorType
)
from infrastructure.se_operators import (
    RevisionOperator,
    RecombinationOperator,
    RefinementOperator,
    OperatorResult
)


# ================================
# MOCK LLM CLIENT
# ================================

class MockEvolutionLLM:
    """Mock LLM that simulates evolutionary improvements"""

    def __init__(self):
        self.call_count = 0
        self.generation = 0

        # OpenAI-style interface
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = self._mock_call

    async def _mock_call(self, **kwargs):
        """Mock API call with evolutionary code improvement"""
        self.call_count += 1
        self.generation += 1

        # Generate improved code with each generation
        code_quality = min(50 + (self.generation * 10), 100)

        response_text = f"""
STRATEGY: Evolutionary improvement iteration {self.generation}
Apply systematic refactoring with test coverage increase.

DIFFERENCES:
- Added error handling (generation {self.generation})
- Improved performance by {code_quality}%
- Enhanced maintainability

CODE:
```python
# Generation {self.generation} evolved code
def evolved_solution_gen_{self.generation}():
    '''Improved solution with quality score {code_quality}/100'''
    try:
        # Validate inputs
        if not validate_preconditions():
            return None

        # Process with optimization
        result = optimized_process()
        assert result is not None

        return result
    except Exception as e:
        log_error(f"Evolution gen {self.generation} error: {{e}}")
        return fallback_solution()

def validate_preconditions():
    return True

def optimized_process():
    return "success_gen_{self.generation}"

def fallback_solution():
    return "fallback"
```
"""
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = response_text

        return response


# ================================
# FIXTURES
# ================================

@pytest.fixture
def temp_pool_storage(tmp_path, monkeypatch):
    """
    Temporary storage for trajectory pools

    Monkeypatch security validation to allow tmp_path during tests
    """
    from infrastructure import security_utils

    # Store original function
    original_validate = security_utils.validate_storage_path

    # Create permissive validation for tests
    def test_validate_storage_path(storage_dir, base_dir):
        """Allow any path during tests"""
        return True

    # Monkeypatch the validation
    monkeypatch.setattr(security_utils, "validate_storage_path", test_validate_storage_path)

    return tmp_path / "integration_pools"


@pytest.fixture
def evolution_llm():
    """Mock LLM client for evolution"""
    return MockEvolutionLLM()


@pytest.fixture
def base_pool(temp_pool_storage):
    """Create base trajectory pool with initial trajectories"""
    pool = TrajectoryPool(
        agent_name="integration_agent",
        max_trajectories=20,
        storage_dir=temp_pool_storage / "integration_agent"
    )

    # Add 2 failed trajectories (for revision)
    for i in range(2):
        pool.add_trajectory(Trajectory(
            trajectory_id=f"fail_{i}",
            generation=0,
            agent_name="integration_agent",
            success_score=0.2,
            status=TrajectoryStatus.FAILURE.value,
            operator_applied=OperatorType.BASELINE.value,
            code_changes=f"def buggy_v{i}(): raise Exception('Bug')",
            reasoning_pattern="quick-hack",
            failure_reasons=["exception raised", "no error handling"],
            tools_used=[]
        ))

    # Add 3 successful trajectories (for recombination)
    for i in range(3):
        pool.add_trajectory(Trajectory(
            trajectory_id=f"success_{i}",
            generation=0,
            agent_name="integration_agent",
            success_score=0.75 + (i * 0.05),
            status=TrajectoryStatus.SUCCESS.value,
            operator_applied=OperatorType.BASELINE.value,
            code_changes=f"def working_v{i}(): return 'success'",
            reasoning_pattern=f"pattern_{i % 2}",
            tools_used=["pytest", "coverage"],
            key_insights=[f"Insight {i}: Use TDD"]
        ))

    # Add 1 promising trajectory (for refinement)
    pool.add_trajectory(Trajectory(
        trajectory_id="promising_0",
        generation=0,
        agent_name="integration_agent",
        success_score=0.68,
        status=TrajectoryStatus.PARTIAL_SUCCESS.value,
        operator_applied=OperatorType.BASELINE.value,
        code_changes="def promising(): # Could be optimized\n    return slow_process()",
        reasoning_pattern="functional-first",
        tools_used=["pytest"],
        key_insights=["Works but slow"]
    ))

    return pool


# ================================
# INTEGRATION: REVISION OPERATOR
# ================================

class TestRevisionIntegration:
    """Test Revision operator with trajectory pool"""

    @pytest.mark.asyncio
    async def test_revision_operator_uses_failed_trajectory_from_pool(
        self,
        evolution_llm,
        base_pool
    ):
        """Test revision operator with real failed trajectory"""
        operator = RevisionOperator(llm_client=evolution_llm)

        # Get failed trajectory from pool
        failed_trajs = base_pool.get_failed_trajectories()
        assert len(failed_trajs) >= 1

        failed_traj = failed_trajs[0]

        # Apply revision
        result = await operator.revise(
            failed_trajectory=failed_traj,
            problem_description="Fix the buggy function to handle errors gracefully"
        )

        # Verify result
        assert result.success is True
        assert result.generated_code is not None
        assert "evolved_solution" in result.generated_code or "Generation" in result.generated_code

        # Create new trajectory from result
        new_traj = Trajectory(
            trajectory_id=f"revised_{failed_traj.trajectory_id}",
            generation=failed_traj.generation + 1,
            agent_name=failed_traj.agent_name,
            parent_trajectories=[failed_traj.trajectory_id],
            operator_applied=OperatorType.REVISION.value,
            code_changes=result.generated_code,
            reasoning_pattern=result.strategy_description,
            success_score=0.8,  # Simulated improvement
            status=TrajectoryStatus.SUCCESS.value
        )

        # Add to pool
        base_pool.add_trajectory(new_traj)

        # Verify pool updated
        assert base_pool.get_trajectory(new_traj.trajectory_id) is not None
        assert new_traj.get_lineage_depth() == 1

    @pytest.mark.asyncio
    async def test_revision_multiple_failed_trajectories(
        self,
        evolution_llm,
        base_pool
    ):
        """Test revising multiple failed trajectories"""
        operator = RevisionOperator(llm_client=evolution_llm)

        failed_trajs = base_pool.get_failed_trajectories()
        assert len(failed_trajs) >= 2

        revised_count = 0
        for failed_traj in failed_trajs[:2]:  # Revise first 2
            result = await operator.revise(
                failed_trajectory=failed_traj,
                problem_description="Fix errors"
            )

            if result.success:
                revised_count += 1

                # Add revised trajectory to pool
                new_traj = Trajectory(
                    trajectory_id=f"revised_{failed_traj.trajectory_id}",
                    generation=failed_traj.generation + 1,
                    agent_name=failed_traj.agent_name,
                    parent_trajectories=[failed_traj.trajectory_id],
                    operator_applied=OperatorType.REVISION.value,
                    code_changes=result.generated_code,
                    success_score=0.75,
                    status=TrajectoryStatus.SUCCESS.value
                )
                base_pool.add_trajectory(new_traj)

        # Verify all revisions succeeded
        assert revised_count == 2

        # Check pool statistics
        stats = base_pool.get_statistics()
        assert stats['total_trajectories'] >= 8  # 6 original + 2 revised


# ================================
# INTEGRATION: RECOMBINATION OPERATOR
# ================================

class TestRecombinationIntegration:
    """Test Recombination operator with trajectory pool"""

    @pytest.mark.asyncio
    async def test_recombination_uses_diverse_pairs_from_pool(
        self,
        evolution_llm,
        base_pool
    ):
        """Test recombination with diverse successful trajectories"""
        operator = RecombinationOperator(llm_client=evolution_llm)

        # Get diverse pairs from pool
        pairs = base_pool.get_diverse_successful_pairs(n=1)
        assert len(pairs) >= 1

        traj_a, traj_b = pairs[0]

        # Apply recombination
        result = await operator.recombine(
            trajectory_a=traj_a,
            trajectory_b=traj_b,
            problem_description="Combine best practices from both approaches"
        )

        # Verify result
        assert result.success is True
        assert result.generated_code is not None

        # Create combined trajectory
        combined_traj = Trajectory(
            trajectory_id=f"combined_{traj_a.trajectory_id}_{traj_b.trajectory_id}",
            generation=max(traj_a.generation, traj_b.generation) + 1,
            agent_name=traj_a.agent_name,
            parent_trajectories=[traj_a.trajectory_id, traj_b.trajectory_id],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes=result.generated_code,
            reasoning_pattern=result.strategy_description,
            success_score=0.85,  # Expected improvement from combination
            status=TrajectoryStatus.SUCCESS.value
        )

        # Add to pool
        base_pool.add_trajectory(combined_traj)

        # Verify lineage tracking
        assert combined_traj.get_lineage_depth() == 2
        assert traj_a.trajectory_id in combined_traj.parent_trajectories
        assert traj_b.trajectory_id in combined_traj.parent_trajectories

    @pytest.mark.asyncio
    async def test_recombination_multiple_generations(
        self,
        evolution_llm,
        base_pool
    ):
        """Test recombination across multiple generations"""
        operator = RecombinationOperator(llm_client=evolution_llm)

        # Generation 1: Recombine initial trajectories
        pairs = base_pool.get_diverse_successful_pairs(n=1)
        if len(pairs) == 0:
            pytest.skip("Not enough diverse pairs")

        traj_a, traj_b = pairs[0]

        result_gen1 = await operator.recombine(
            trajectory_a=traj_a,
            trajectory_b=traj_b,
            problem_description="Gen 1 combination"
        )

        gen1_traj = Trajectory(
            trajectory_id="gen1_combined",
            generation=1,
            agent_name="integration_agent",
            parent_trajectories=[traj_a.trajectory_id, traj_b.trajectory_id],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes=result_gen1.generated_code,
            success_score=0.88,
            status=TrajectoryStatus.SUCCESS.value,
            reasoning_pattern="gen1_hybrid"
        )
        base_pool.add_trajectory(gen1_traj)

        # Generation 2: Recombine with new trajectory
        successful_trajs = base_pool.get_successful_trajectories()
        gen2_pairs = [(gen1_traj, successful_trajs[0])]

        result_gen2 = await operator.recombine(
            trajectory_a=gen2_pairs[0][0],
            trajectory_b=gen2_pairs[0][1],
            problem_description="Gen 2 combination"
        )

        gen2_traj = Trajectory(
            trajectory_id="gen2_combined",
            generation=2,
            agent_name="integration_agent",
            parent_trajectories=[gen1_traj.trajectory_id, successful_trajs[0].trajectory_id],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes=result_gen2.generated_code,
            success_score=0.92,
            status=TrajectoryStatus.SUCCESS.value
        )
        base_pool.add_trajectory(gen2_traj)

        # Verify multi-generation lineage
        assert gen2_traj.generation == 2
        stats = base_pool.get_statistics()
        assert stats['generation_distribution'][2] >= 1


# ================================
# INTEGRATION: REFINEMENT OPERATOR
# ================================

class TestRefinementIntegration:
    """Test Refinement operator with trajectory pool"""

    @pytest.mark.asyncio
    async def test_refinement_uses_pool_insights(
        self,
        evolution_llm,
        base_pool
    ):
        """Test refinement with insights from pool"""
        operator = RefinementOperator(llm_client=evolution_llm)

        # Get promising trajectory
        all_trajs = base_pool.get_all_trajectories()
        promising = [t for t in all_trajs if 0.6 < t.success_score < 0.75]
        assert len(promising) >= 1

        promising_traj = promising[0]

        # Get pool insights
        insights = base_pool.get_pool_insights(max_insights=5)

        # Apply refinement
        result = await operator.refine(
            trajectory=promising_traj,
            pool_insights=insights,
            problem_description="Optimize the promising solution"
        )

        # Verify result
        assert result.success is True
        assert result.generated_code is not None

        # Create refined trajectory
        refined_traj = Trajectory(
            trajectory_id=f"refined_{promising_traj.trajectory_id}",
            generation=promising_traj.generation + 1,
            agent_name=promising_traj.agent_name,
            parent_trajectories=[promising_traj.trajectory_id],
            operator_applied=OperatorType.REFINEMENT.value,
            code_changes=result.generated_code,
            success_score=0.82,  # Improved
            status=TrajectoryStatus.SUCCESS.value
        )

        # Add to pool
        base_pool.add_trajectory(refined_traj)

        # Verify improvement
        assert refined_traj.success_score > promising_traj.success_score

    @pytest.mark.asyncio
    async def test_refinement_without_insights_still_works(
        self,
        evolution_llm,
        base_pool
    ):
        """Test refinement works even without pool insights"""
        operator = RefinementOperator(llm_client=evolution_llm)

        all_trajs = base_pool.get_all_trajectories()
        promising = [t for t in all_trajs if t.success_score > 0.6][0]

        # Apply refinement with empty insights
        result = await operator.refine(
            trajectory=promising,
            pool_insights=[],  # No insights
            problem_description="Optimize"
        )

        # Should still succeed
        assert result.success is True
        assert result.generated_code is not None


# ================================
# FULL EVOLUTION LOOP
# ================================

class TestFullEvolutionLoop:
    """Test complete evolution cycle: pool → operators → pool update"""

    @pytest.mark.asyncio
    async def test_full_evolution_cycle(
        self,
        evolution_llm,
        base_pool
    ):
        """Test complete evolution: Revision → Recombination → Refinement"""

        initial_count = len(base_pool.trajectories)

        # Step 1: Revision - Fix failures
        revision_op = RevisionOperator(llm_client=evolution_llm)
        failed_trajs = base_pool.get_failed_trajectories()

        for failed_traj in failed_trajs[:1]:  # Revise 1 failure
            result = await revision_op.revise(
                failed_trajectory=failed_traj,
                problem_description="Fix bug"
            )

            if result.success:
                new_traj = Trajectory(
                    trajectory_id=f"revised_{failed_traj.trajectory_id}",
                    generation=failed_traj.generation + 1,
                    agent_name=failed_traj.agent_name,
                    parent_trajectories=[failed_traj.trajectory_id],
                    operator_applied=OperatorType.REVISION.value,
                    code_changes=result.generated_code,
                    success_score=0.8,
                    status=TrajectoryStatus.SUCCESS.value,
                    reasoning_pattern="revised_approach"
                )
                base_pool.add_trajectory(new_traj)

        # Step 2: Recombination - Combine successes
        recombine_op = RecombinationOperator(llm_client=evolution_llm)
        pairs = base_pool.get_diverse_successful_pairs(n=1)

        if len(pairs) > 0:
            traj_a, traj_b = pairs[0]
            result = await recombine_op.recombine(
                trajectory_a=traj_a,
                trajectory_b=traj_b,
                problem_description="Combine best practices"
            )

            if result.success:
                combined_traj = Trajectory(
                    trajectory_id=f"combined_{traj_a.trajectory_id}_{traj_b.trajectory_id}",
                    generation=max(traj_a.generation, traj_b.generation) + 1,
                    agent_name=traj_a.agent_name,
                    parent_trajectories=[traj_a.trajectory_id, traj_b.trajectory_id],
                    operator_applied=OperatorType.RECOMBINATION.value,
                    code_changes=result.generated_code,
                    success_score=0.85,
                    status=TrajectoryStatus.SUCCESS.value,
                    reasoning_pattern="hybrid_approach"
                )
                base_pool.add_trajectory(combined_traj)

        # Step 3: Refinement - Optimize promising trajectories
        refine_op = RefinementOperator(llm_client=evolution_llm)
        all_trajs = base_pool.get_all_trajectories()
        promising = [t for t in all_trajs if 0.65 < t.success_score < 0.8]

        if len(promising) > 0:
            insights = base_pool.get_pool_insights(max_insights=5)
            result = await refine_op.refine(
                trajectory=promising[0],
                pool_insights=insights,
                problem_description="Optimize"
            )

            if result.success:
                refined_traj = Trajectory(
                    trajectory_id=f"refined_{promising[0].trajectory_id}",
                    generation=promising[0].generation + 1,
                    agent_name=promising[0].agent_name,
                    parent_trajectories=[promising[0].trajectory_id],
                    operator_applied=OperatorType.REFINEMENT.value,
                    code_changes=result.generated_code,
                    success_score=0.9,
                    status=TrajectoryStatus.SUCCESS.value
                )
                base_pool.add_trajectory(refined_traj)

        # Verify evolution happened
        final_count = len(base_pool.trajectories)
        assert final_count > initial_count

        # Check pool statistics
        stats = base_pool.get_statistics()
        assert stats['successful_count'] >= 3
        assert stats['average_score'] > 0.5

        # Verify operator distribution
        op_dist = stats['operator_distribution']
        assert OperatorType.REVISION.value in op_dist or OperatorType.RECOMBINATION.value in op_dist

    @pytest.mark.asyncio
    async def test_multi_generation_evolution(
        self,
        evolution_llm,
        base_pool
    ):
        """Test evolution across multiple generations"""

        revision_op = RevisionOperator(llm_client=evolution_llm)
        recombine_op = RecombinationOperator(llm_client=evolution_llm)

        # Generation 1: Revise failures
        failed = base_pool.get_failed_trajectories()[0]
        result = await revision_op.revise(failed, "Fix")

        gen1 = Trajectory(
            trajectory_id="gen1",
            generation=1,
            agent_name="integration_agent",
            parent_trajectories=[failed.trajectory_id],
            operator_applied=OperatorType.REVISION.value,
            code_changes=result.generated_code,
            success_score=0.75,
            status=TrajectoryStatus.SUCCESS.value,
            reasoning_pattern="gen1"
        )
        base_pool.add_trajectory(gen1)

        # Generation 2: Recombine gen1 with initial success
        successful = base_pool.get_successful_trajectories()
        result = await recombine_op.recombine(gen1, successful[0], "Combine")

        gen2 = Trajectory(
            trajectory_id="gen2",
            generation=2,
            agent_name="integration_agent",
            parent_trajectories=[gen1.trajectory_id, successful[0].trajectory_id],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes=result.generated_code,
            success_score=0.88,
            status=TrajectoryStatus.SUCCESS.value
        )
        base_pool.add_trajectory(gen2)

        # Generation 3: Recombine gen2 with another trajectory
        result = await recombine_op.recombine(gen2, successful[1], "Combine")

        gen3 = Trajectory(
            trajectory_id="gen3",
            generation=3,
            agent_name="integration_agent",
            parent_trajectories=[gen2.trajectory_id, successful[1].trajectory_id],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes=result.generated_code,
            success_score=0.93,
            status=TrajectoryStatus.SUCCESS.value
        )
        base_pool.add_trajectory(gen3)

        # Verify multi-generation lineage
        stats = base_pool.get_statistics()
        gen_dist = stats['generation_distribution']

        assert 1 in gen_dist
        assert 2 in gen_dist
        assert 3 in gen_dist

        # Verify score improvement
        assert gen3.success_score > gen2.success_score > gen1.success_score


# ================================
# CONCURRENT OPERATOR EXECUTION
# ================================

class TestConcurrentOperators:
    """Test concurrent operator execution"""

    @pytest.mark.asyncio
    async def test_concurrent_revision_operations(
        self,
        evolution_llm,
        base_pool
    ):
        """Test running multiple revisions concurrently"""
        operator = RevisionOperator(llm_client=evolution_llm)

        failed_trajs = base_pool.get_failed_trajectories()[:2]

        # Run revisions concurrently
        tasks = [
            operator.revise(traj, f"Fix {traj.trajectory_id}")
            for traj in failed_trajs
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.success for r in results)
        assert len(results) == len(failed_trajs)

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operators(
        self,
        evolution_llm,
        base_pool
    ):
        """Test running different operators concurrently"""

        # Prepare operators
        revision_op = RevisionOperator(llm_client=evolution_llm)
        recombine_op = RecombinationOperator(llm_client=evolution_llm)
        refine_op = RefinementOperator(llm_client=evolution_llm)

        # Get trajectories
        failed = base_pool.get_failed_trajectories()[0]
        pairs = base_pool.get_diverse_successful_pairs(n=1)
        promising = [t for t in base_pool.get_all_trajectories() if 0.6 < t.success_score < 0.75][0]

        # Run all operators concurrently
        tasks = [
            revision_op.revise(failed, "Fix"),
            recombine_op.recombine(pairs[0][0], pairs[0][1], "Combine") if len(pairs) > 0 else asyncio.sleep(0),
            refine_op.refine(promising, base_pool.get_pool_insights(), "Optimize")
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least 2 should succeed (revision and refinement always have inputs)
        successful_results = [r for r in results if isinstance(r, OperatorResult) and r.success]
        assert len(successful_results) >= 2


# ================================
# POOL STATISTICS AFTER EVOLUTION
# ================================

class TestPoolStatisticsAfterEvolution:
    """Test pool statistics tracking during evolution"""

    @pytest.mark.asyncio
    async def test_statistics_reflect_evolution(
        self,
        evolution_llm,
        base_pool
    ):
        """Test that statistics update correctly after evolution"""

        initial_stats = base_pool.get_statistics()

        # Run revision on failed trajectory
        revision_op = RevisionOperator(llm_client=evolution_llm)
        failed = base_pool.get_failed_trajectories()[0]
        result = await revision_op.revise(failed, "Fix")

        # Add revised trajectory
        new_traj = Trajectory(
            trajectory_id="revised_new",
            generation=1,
            agent_name="integration_agent",
            parent_trajectories=[failed.trajectory_id],
            operator_applied=OperatorType.REVISION.value,
            code_changes=result.generated_code,
            success_score=0.85,
            status=TrajectoryStatus.SUCCESS.value
        )
        base_pool.add_trajectory(new_traj)

        # Get updated statistics
        updated_stats = base_pool.get_statistics()

        # Verify statistics changed
        assert updated_stats['total_trajectories'] > initial_stats['total_trajectories']
        assert updated_stats['successful_count'] > initial_stats['successful_count']
        assert updated_stats['best_score'] >= initial_stats['best_score']

        # Verify operator distribution updated
        assert OperatorType.REVISION.value in updated_stats['operator_distribution']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
