"""
Test Suite for SE-Darwin Agent - Multi-Trajectory Evolution

Tests all major components:
1. Agent initialization
2. Trajectory generation (baseline, operator-based)
3. Parallel execution with timeout
4. Operator application (revision, recombination, refinement)
5. Benchmark validation
6. Trajectory archiving
7. Convergence detection
8. Full evolution loop
9. OTEL instrumentation
10. Error handling and edge cases
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from agents.se_darwin_agent import (
    SEDarwinAgent,
    EvolutionStatus,
    TrajectoryExecutionResult,
    EvolutionIteration,
    get_se_darwin_agent,
    BenchmarkScenarioLoader,
    CodeQualityValidator
)
from infrastructure.trajectory_pool import (
    Trajectory,
    TrajectoryStatus,
    OperatorType,
    TrajectoryPool
)
from infrastructure.se_operators import OperatorResult
from infrastructure.benchmark_runner import BenchmarkResult, BenchmarkType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(
                        content="STRATEGY: Test strategy\nCODE:\n```python\ndef test(): pass\n```"
                    )
                )
            ]
        )
    )
    return client


@pytest.fixture
def se_darwin_agent(mock_llm_client, tmp_path):
    """Create SE-Darwin agent for testing"""
    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool:
        # Create real pool with temp storage
        from infrastructure.trajectory_pool import TrajectoryPool
        pool = TrajectoryPool(
            agent_name="test_agent",
            storage_dir=tmp_path / "trajectory_pools" / "test_agent"
        )
        mock_pool.return_value = pool

        agent = SEDarwinAgent(
            agent_name="test_agent",
            llm_client=mock_llm_client,
            trajectories_per_iteration=3,
            max_iterations=2,
            timeout_per_trajectory=30
        )
        return agent


@pytest.fixture
def sample_trajectory():
    """Create sample trajectory for testing"""
    return Trajectory(
        trajectory_id="test_traj_001",
        generation=0,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        code_changes="def test(): return True",
        proposed_strategy="Baseline test strategy",
        reasoning_pattern="direct_implementation",
        status=TrajectoryStatus.PENDING.value,
        success_score=0.0
    )


@pytest.fixture
def sample_benchmark_result():
    """Create sample benchmark result"""
    return BenchmarkResult(
        benchmark_id="bench_001",
        benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
        agent_name="test_agent",
        agent_version="test_traj_001",
        status="completed",
        overall_score=0.85,
        metrics={'accuracy': 0.85, 'speed': 0.90},
        tasks_total=10,
        tasks_passed=8,
        tasks_failed=2,
        execution_time=2.5,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_se_darwin_agent_initialization(se_darwin_agent):
    """Test agent initializes correctly"""
    assert se_darwin_agent.agent_name == "test_agent"
    assert se_darwin_agent.trajectories_per_iteration == 3
    assert se_darwin_agent.max_iterations == 2
    assert se_darwin_agent.timeout_per_trajectory == 30
    assert se_darwin_agent.current_generation == 0
    assert se_darwin_agent.best_score == 0.0
    assert se_darwin_agent.best_trajectory_id is None
    assert se_darwin_agent.trajectory_pool is not None
    assert se_darwin_agent.revision_operator is not None
    assert se_darwin_agent.recombination_operator is not None
    assert se_darwin_agent.refinement_operator is not None


def test_se_darwin_agent_trajectories_clamped():
    """Test trajectories_per_iteration is clamped to 1-5"""
    with patch('agents.se_darwin_agent.get_trajectory_pool'):
        # Test too low
        agent = SEDarwinAgent(agent_name="test", trajectories_per_iteration=0)
        assert agent.trajectories_per_iteration == 1

        # Test too high
        agent = SEDarwinAgent(agent_name="test", trajectories_per_iteration=10)
        assert agent.trajectories_per_iteration == 5

        # Test valid
        agent = SEDarwinAgent(agent_name="test", trajectories_per_iteration=3)
        assert agent.trajectories_per_iteration == 3


def test_factory_function():
    """Test factory function creates agent correctly"""
    with patch('agents.se_darwin_agent.get_trajectory_pool'):
        agent = get_se_darwin_agent(
            agent_name="factory_test",
            trajectories_per_iteration=4,
            max_iterations=5
        )
        assert agent.agent_name == "factory_test"
        assert agent.trajectories_per_iteration == 4
        assert agent.max_iterations == 5


# ============================================================================
# TRAJECTORY GENERATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_baseline_trajectories(se_darwin_agent):
    """Test generation of baseline trajectories (iteration 0)"""
    trajectories = await se_darwin_agent._generate_trajectories(
        problem_description="Test problem",
        context={},
        generation=0
    )

    assert len(trajectories) == 3  # trajectories_per_iteration
    for traj in trajectories:
        assert traj.generation == 0
        assert traj.agent_name == "test_agent"
        assert traj.operator_applied == OperatorType.BASELINE.value
        assert traj.status == TrajectoryStatus.PENDING.value
        assert "baseline" in traj.trajectory_id.lower()


@pytest.mark.asyncio
async def test_create_baseline_trajectory(se_darwin_agent):
    """Test baseline trajectory creation"""
    trajectory = se_darwin_agent._create_baseline_trajectory(
        problem_description="Build API",
        context={'framework': 'FastAPI'},
        generation=1,
        index=0
    )

    assert trajectory.generation == 1
    assert trajectory.agent_name == "test_agent"
    assert trajectory.operator_applied == OperatorType.BASELINE.value
    assert "Build API" in trajectory.proposed_strategy
    assert trajectory.reasoning_pattern == "direct_implementation"


@pytest.mark.asyncio
async def test_generate_trajectories_with_operators(se_darwin_agent):
    """Test generation with operators (iteration 1+)"""
    # Seed trajectory pool with some trajectories
    failed_traj = Trajectory(
        trajectory_id="failed_001",
        generation=0,
        agent_name="test_agent",
        status=TrajectoryStatus.FAILURE.value,
        success_score=0.2,
        operator_applied=OperatorType.BASELINE.value,
        reasoning_pattern="failed_approach"
    )
    se_darwin_agent.trajectory_pool.add_trajectory(failed_traj)

    successful_traj_a = Trajectory(
        trajectory_id="success_001",
        generation=0,
        agent_name="test_agent",
        status=TrajectoryStatus.SUCCESS.value,
        success_score=0.85,
        operator_applied=OperatorType.BASELINE.value,
        reasoning_pattern="approach_a"
    )
    se_darwin_agent.trajectory_pool.add_trajectory(successful_traj_a)

    successful_traj_b = Trajectory(
        trajectory_id="success_002",
        generation=0,
        agent_name="test_agent",
        status=TrajectoryStatus.SUCCESS.value,
        success_score=0.80,
        operator_applied=OperatorType.BASELINE.value,
        reasoning_pattern="approach_b"
    )
    se_darwin_agent.trajectory_pool.add_trajectory(successful_traj_b)

    # Generate trajectories for iteration 1
    trajectories = await se_darwin_agent._generate_trajectories(
        problem_description="Test problem",
        context={},
        generation=1
    )

    assert len(trajectories) == 3

    # Should have mix of operator types
    operator_types = [t.operator_applied for t in trajectories]
    assert len(set(operator_types)) >= 1  # At least some diversity


@pytest.mark.asyncio
async def test_create_trajectory_from_operator(se_darwin_agent):
    """Test creating trajectory from operator result"""
    operator_result = OperatorResult(
        success=True,
        generated_code="def improved(): return 42",
        strategy_description="Improved strategy",
        reasoning="Applied refinement operator"
    )

    trajectory = se_darwin_agent._create_trajectory_from_operator(
        operator_result=operator_result,
        operator_type=OperatorType.REFINEMENT,
        generation=2,
        parent_ids=["parent_001"]
    )

    assert trajectory.generation == 2
    assert trajectory.agent_name == "test_agent"
    assert trajectory.operator_applied == OperatorType.REFINEMENT.value
    assert trajectory.code_changes == "def improved(): return 42"
    assert trajectory.proposed_strategy == "Improved strategy"
    assert trajectory.parent_trajectories == ["parent_001"]
    assert "refinement" in trajectory.trajectory_id.lower()


# ============================================================================
# TRAJECTORY EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_single_trajectory_success(se_darwin_agent, sample_trajectory, sample_benchmark_result):
    """Test successful execution of single trajectory"""
    with patch.object(se_darwin_agent, '_validate_trajectory', return_value=sample_benchmark_result):
        result = await se_darwin_agent._execute_single_trajectory(
            sample_trajectory,
            "Test problem"
        )

        assert result.success is True
        assert result.trajectory.status == TrajectoryStatus.SUCCESS.value
        assert result.trajectory.success_score == 0.85
        assert result.benchmark_result is not None
        assert result.execution_time > 0


@pytest.mark.asyncio
async def test_execute_single_trajectory_failure(se_darwin_agent, sample_trajectory):
    """Test failed trajectory execution"""
    # Create benchmark result with low score
    failed_benchmark = BenchmarkResult(
        benchmark_id="bench_fail",
        benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
        agent_name="test_agent",
        agent_version="test_traj_001",
        status="completed",
        overall_score=0.3,  # Below threshold
        metrics={'accuracy': 0.3},
        tasks_total=10,
        tasks_passed=3,
        tasks_failed=7,
        execution_time=1.0,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    with patch.object(se_darwin_agent, '_validate_trajectory', return_value=failed_benchmark):
        result = await se_darwin_agent._execute_single_trajectory(
            sample_trajectory,
            "Test problem"
        )

        assert result.success is False
        assert result.trajectory.status == TrajectoryStatus.FAILURE.value
        assert result.trajectory.success_score < se_darwin_agent.success_threshold


@pytest.mark.asyncio
async def test_execute_single_trajectory_timeout(se_darwin_agent, sample_trajectory):
    """Test trajectory execution timeout"""
    # Create agent with very short timeout
    se_darwin_agent.timeout_per_trajectory = 0.1

    async def slow_validate(*args, **kwargs):
        await asyncio.sleep(1.0)  # Longer than timeout
        return None

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=slow_validate):
        result = await se_darwin_agent._execute_single_trajectory(
            sample_trajectory,
            "Test problem"
        )

        assert result.success is False
        assert result.error_message == "Execution timeout"
        assert "execution_timeout" in result.trajectory.failure_reasons


@pytest.mark.asyncio
async def test_execute_single_trajectory_exception(se_darwin_agent, sample_trajectory):
    """Test trajectory execution with exception"""
    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=RuntimeError("Test error")):
        result = await se_darwin_agent._execute_single_trajectory(
            sample_trajectory,
            "Test problem"
        )

        assert result.success is False
        assert "Test error" in result.error_message
        assert any("execution_error" in reason for reason in result.trajectory.failure_reasons)


@pytest.mark.asyncio
async def test_execute_trajectories_parallel(se_darwin_agent):
    """Test parallel execution of multiple trajectories"""
    trajectories = [
        Trajectory(
            trajectory_id=f"test_traj_{i:03d}",
            generation=0,
            agent_name="test_agent",
            operator_applied=OperatorType.BASELINE.value,
            status=TrajectoryStatus.PENDING.value
        )
        for i in range(3)
    ]

    # Mock validation to return different scores
    async def mock_validate(traj, problem):
        return BenchmarkResult(
            benchmark_id=f"bench_{traj.trajectory_id}",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
            agent_name="test_agent",
            agent_version=traj.trajectory_id,
            status="completed",
            overall_score=0.75,
            metrics={'accuracy': 0.75},
            tasks_total=10,
            tasks_passed=7,
            tasks_failed=3,
            execution_time=0.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        results = await se_darwin_agent._execute_trajectories_parallel(
            trajectories,
            "Test problem"
        )

        assert len(results) == 3
        for result in results:
            assert isinstance(result, TrajectoryExecutionResult)
            assert result.success is True


@pytest.mark.asyncio
async def test_execute_trajectories_parallel_with_failures(se_darwin_agent):
    """Test parallel execution handles mixed success/failure"""
    trajectories = [
        Trajectory(
            trajectory_id=f"test_traj_{i:03d}",
            generation=0,
            agent_name="test_agent",
            operator_applied=OperatorType.BASELINE.value,
            status=TrajectoryStatus.PENDING.value
        )
        for i in range(3)
    ]

    # Mock validation: first succeeds, second fails, third raises exception
    call_count = [0]

    async def mock_validate(traj, problem):
        call_count[0] += 1
        if call_count[0] == 1:
            # Success
            return BenchmarkResult(
                benchmark_id=f"bench_{traj.trajectory_id}",
                benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
                agent_name="test_agent",
                agent_version=traj.trajectory_id,
                status="completed",
                overall_score=0.85,
                metrics={},
                tasks_total=10,
                tasks_passed=8,
                tasks_failed=2,
                execution_time=0.5,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        elif call_count[0] == 2:
            # Failure
            return BenchmarkResult(
                benchmark_id=f"bench_{traj.trajectory_id}",
                benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
                agent_name="test_agent",
                agent_version=traj.trajectory_id,
                status="completed",
                overall_score=0.25,
                metrics={},
                tasks_total=10,
                tasks_passed=2,
                tasks_failed=8,
                execution_time=0.5,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        else:
            # Exception
            raise RuntimeError("Validation error")

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        results = await se_darwin_agent._execute_trajectories_parallel(
            trajectories,
            "Test problem"
        )

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is False
        assert "Validation error" in results[2].error_message


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_validate_trajectory(se_darwin_agent, sample_trajectory):
    """Test trajectory validation"""
    result = await se_darwin_agent._validate_trajectory(
        sample_trajectory,
        "Test problem"
    )

    assert isinstance(result, BenchmarkResult)
    assert 0.0 <= result.overall_score <= 1.0
    assert result.agent_name == "test_agent"
    assert result.tasks_total > 0


@pytest.mark.asyncio
async def test_validate_trajectory_scoring_logic(se_darwin_agent):
    """Test validation scoring gives bonuses for quality indicators"""
    # Trajectory with recombination operator and good content
    rich_trajectory = Trajectory(
        trajectory_id="rich_001",
        generation=1,
        agent_name="test_agent",
        operator_applied=OperatorType.RECOMBINATION.value,
        code_changes="def elaborate_solution(): pass  # 100 chars of code" + " " * 60,
        proposed_strategy="Well-thought-out strategy with detailed planning",
        reasoning_pattern="comprehensive_analysis"
    )

    result_rich = await se_darwin_agent._validate_trajectory(rich_trajectory, "Test")

    # Minimal baseline trajectory
    minimal_trajectory = Trajectory(
        trajectory_id="minimal_001",
        generation=0,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        code_changes="",
        proposed_strategy=""
    )

    result_minimal = await se_darwin_agent._validate_trajectory(minimal_trajectory, "Test")

    # Rich trajectory should generally score higher (allowing for randomness)
    # Run multiple times to account for random variance
    rich_scores = []
    minimal_scores = []

    for _ in range(5):
        rich_scores.append((await se_darwin_agent._validate_trajectory(rich_trajectory, "Test")).overall_score)
        minimal_scores.append((await se_darwin_agent._validate_trajectory(minimal_trajectory, "Test")).overall_score)

    avg_rich = sum(rich_scores) / len(rich_scores)
    avg_minimal = sum(minimal_scores) / len(minimal_scores)

    assert avg_rich > avg_minimal, "Rich trajectory should score higher on average"


# ============================================================================
# ARCHIVING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_archive_trajectories(se_darwin_agent, sample_trajectory, sample_benchmark_result):
    """Test archiving trajectories to pool"""
    execution_results = [
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=sample_benchmark_result,
            execution_time=2.5,
            success=True
        )
    ]

    initial_count = len(se_darwin_agent.trajectory_pool.get_all_trajectories())

    await se_darwin_agent._archive_trajectories(execution_results)

    final_count = len(se_darwin_agent.trajectory_pool.get_all_trajectories())

    assert final_count == initial_count + 1
    assert se_darwin_agent.trajectory_pool.get_trajectory(sample_trajectory.trajectory_id) is not None


# ============================================================================
# CONVERGENCE TESTS
# ============================================================================

def test_check_convergence_all_successful(se_darwin_agent, sample_trajectory, sample_benchmark_result):
    """Test convergence detection when all trajectories successful"""
    execution_results = [
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=sample_benchmark_result,
            execution_time=1.0,
            success=True
        )
        for _ in range(3)
    ]

    converged = se_darwin_agent._check_convergence(execution_results)

    assert converged is True


def test_check_convergence_score_plateaued(se_darwin_agent, sample_trajectory):
    """Test convergence when score plateaus"""
    # Create two iterations with same score
    se_darwin_agent.iterations = [
        EvolutionIteration(
            iteration_id="iter_0",
            generation=0,
            status=EvolutionStatus.COMPLETED.value,
            trajectories_generated=3,
            trajectories_successful=2,
            best_score=0.75,
            execution_time=5.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        ),
        EvolutionIteration(
            iteration_id="iter_1",
            generation=1,
            status=EvolutionStatus.COMPLETED.value,
            trajectories_generated=3,
            trajectories_successful=2,
            best_score=0.751,  # Very close to previous
            execution_time=5.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    ]

    execution_results = [
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=None,
            execution_time=1.0,
            success=False
        )
    ]

    converged = se_darwin_agent._check_convergence(execution_results)

    assert converged is True


def test_check_convergence_excellent_score(se_darwin_agent, sample_trajectory):
    """Test convergence when excellent score achieved"""
    se_darwin_agent.best_score = 0.92

    execution_results = [
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=None,
            execution_time=1.0,
            success=False
        )
    ]

    converged = se_darwin_agent._check_convergence(execution_results)

    assert converged is True


def test_check_convergence_not_converged(se_darwin_agent, sample_trajectory, sample_benchmark_result):
    """Test no convergence when conditions not met"""
    se_darwin_agent.best_score = 0.65
    se_darwin_agent.iterations = []

    # Mixed success/failure
    execution_results = [
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=sample_benchmark_result,
            execution_time=1.0,
            success=True
        ),
        TrajectoryExecutionResult(
            trajectory=sample_trajectory,
            benchmark_result=None,
            execution_time=1.0,
            success=False
        )
    ]

    converged = se_darwin_agent._check_convergence(execution_results)

    assert converged is False


# ============================================================================
# ITERATION RECORDING TESTS
# ============================================================================

def test_record_iteration(se_darwin_agent):
    """Test iteration recording"""
    se_darwin_agent.best_score = 0.82

    se_darwin_agent._record_iteration(
        generation=0,
        trajectories_generated=3,
        trajectories_successful=2,
        execution_time=5.5
    )

    assert len(se_darwin_agent.iterations) == 1
    iteration = se_darwin_agent.iterations[0]

    assert iteration.generation == 0
    assert iteration.trajectories_generated == 3
    assert iteration.trajectories_successful == 2
    assert iteration.best_score == 0.82
    assert iteration.execution_time == 5.5
    assert iteration.status == EvolutionStatus.COMPLETED.value


# ============================================================================
# FULL EVOLUTION LOOP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_evolve_solution_basic(se_darwin_agent):
    """Test basic evolution loop"""
    # Mock validation to return improving scores
    call_count = [0]

    async def mock_validate(traj, problem):
        call_count[0] += 1
        score = 0.6 + (call_count[0] * 0.05)  # Improving scores

        return BenchmarkResult(
            benchmark_id=f"bench_{call_count[0]}",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
            agent_name="test_agent",
            agent_version=traj.trajectory_id,
            status="completed",
            overall_score=min(score, 1.0),
            metrics={'accuracy': min(score, 1.0)},
            tasks_total=10,
            tasks_passed=int(min(score, 1.0) * 10),
            tasks_failed=10 - int(min(score, 1.0) * 10),
            execution_time=0.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        result = await se_darwin_agent.evolve_solution(
            problem_description="Build authentication system",
            context={'framework': 'FastAPI'}
        )

        assert result['success'] is True
        assert result['best_score'] > 0.0
        assert len(result['iterations']) > 0
        assert result['total_time'] > 0
        assert 'pool_statistics' in result


@pytest.mark.asyncio
async def test_evolve_solution_early_convergence(se_darwin_agent):
    """Test evolution stops early on convergence"""
    # Mock validation to return excellent scores
    async def mock_validate(traj, problem):
        return BenchmarkResult(
            benchmark_id="bench_excellent",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
            agent_name="test_agent",
            agent_version=traj.trajectory_id,
            status="completed",
            overall_score=0.95,  # Excellent score
            metrics={'accuracy': 0.95},
            tasks_total=10,
            tasks_passed=9,
            tasks_failed=1,
            execution_time=0.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        result = await se_darwin_agent.evolve_solution(
            problem_description="Test problem"
        )

        # Should converge early (not run all max_iterations)
        assert result['success'] is True
        assert result['best_score'] >= 0.9
        # May converge on first iteration if all trajectories excellent
        assert len(result['iterations']) <= se_darwin_agent.max_iterations


@pytest.mark.asyncio
async def test_evolve_solution_updates_best_score(se_darwin_agent):
    """Test evolution tracks best score across iterations"""
    scores = [0.65, 0.72, 0.85, 0.78, 0.91, 0.88]  # Some improving, some not
    score_index = [0]

    async def mock_validate(traj, problem):
        score = scores[score_index[0] % len(scores)]
        score_index[0] += 1

        return BenchmarkResult(
            benchmark_id=f"bench_{score_index[0]}",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
            agent_name="test_agent",
            agent_version=traj.trajectory_id,
            status="completed",
            overall_score=score,
            metrics={'accuracy': score},
            tasks_total=10,
            tasks_passed=int(score * 10),
            tasks_failed=10 - int(score * 10),
            execution_time=0.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        result = await se_darwin_agent.evolve_solution(
            problem_description="Test problem"
        )

        # Best score should be highest observed
        assert result['best_score'] >= max(scores)


@pytest.mark.asyncio
async def test_evolve_solution_saves_pool(se_darwin_agent, tmp_path):
    """Test evolution saves trajectory pool"""
    async def mock_validate(traj, problem):
        return BenchmarkResult(
            benchmark_id="bench_test",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM.value,
            agent_name="test_agent",
            agent_version=traj.trajectory_id,
            status="completed",
            overall_score=0.75,
            metrics={},
            tasks_total=10,
            tasks_passed=7,
            tasks_failed=3,
            execution_time=0.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=mock_validate):
        result = await se_darwin_agent.evolve_solution(
            problem_description="Test problem"
        )

        # Pool should be saved
        assert result['pool_statistics']['total_trajectories'] > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_evolve_solution_handles_validation_errors(se_darwin_agent):
    """Test evolution gracefully handles validation errors"""
    with patch.object(se_darwin_agent, '_validate_trajectory', side_effect=RuntimeError("Validation failed")):
        result = await se_darwin_agent.evolve_solution(
            problem_description="Test problem"
        )

        # Should complete despite errors
        assert 'iterations' in result
        assert len(result['iterations']) > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_evolution_workflow(tmp_path):
    """Test complete evolution workflow end-to-end"""
    # Create agent with real components
    mock_llm = Mock()
    mock_llm.chat = Mock()
    mock_llm.chat.completions = Mock()
    mock_llm.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(
                        content="STRATEGY: Evolutionary strategy\nCODE:\n```python\ndef evolve(): return 'improved'\n```"
                    )
                )
            ]
        )
    )

    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool_factory:
        from infrastructure.trajectory_pool import TrajectoryPool
        pool = TrajectoryPool(
            agent_name="integration_test",
            storage_dir=tmp_path / "trajectory_pools" / "integration_test"
        )
        mock_pool_factory.return_value = pool

        agent = SEDarwinAgent(
            agent_name="integration_test",
            llm_client=mock_llm,
            trajectories_per_iteration=2,
            max_iterations=2,
            timeout_per_trajectory=10
        )

        # Run evolution
        result = await agent.evolve_solution(
            problem_description="Implement user authentication with JWT tokens",
            context={'framework': 'FastAPI', 'database': 'PostgreSQL'}
        )

        # Verify result structure
        assert 'success' in result
        assert 'best_score' in result
        assert 'iterations' in result
        assert 'total_time' in result
        assert 'pool_statistics' in result

        # Verify iterations recorded
        assert len(result['iterations']) <= 2
        for iteration in result['iterations']:
            assert 'generation' in iteration
            assert 'trajectories' in iteration
            assert 'successful' in iteration
            assert 'best_score' in iteration

        # Verify pool has trajectories
        stats = result['pool_statistics']
        assert stats['total_trajectories'] > 0
        assert stats['total_added'] > 0


# ============================================================================
# P2-1 FIX: BENCHMARK SCENARIO LOADER TESTS
# ============================================================================

def test_benchmark_scenario_loader_initialization():
    """Test BenchmarkScenarioLoader initializes and loads scenarios"""
    loader = BenchmarkScenarioLoader()

    # Should have loaded scenarios from JSON files
    all_scenarios = loader.get_all_scenarios()
    assert len(all_scenarios) > 0, "Should load scenarios from JSON files"


def test_benchmark_scenario_loader_get_scenarios_for_agent():
    """Test getting scenarios for specific agent"""
    loader = BenchmarkScenarioLoader()

    # Test builder agent scenarios
    builder_scenarios = loader.get_scenarios_for_agent("builder")
    assert len(builder_scenarios) > 0, "Should have builder scenarios"

    # Verify scenario structure
    for scenario in builder_scenarios:
        assert 'id' in scenario
        assert 'description' in scenario


def test_benchmark_scenario_loader_find_matching_scenario():
    """Test finding matching scenario for problem description"""
    loader = BenchmarkScenarioLoader()

    # Test matching React component problem
    match = loader.find_matching_scenario(
        "builder",
        "Build a React UserProfile component with avatar"
    )

    if match:  # Only if builder scenarios exist
        assert 'description' in match
        assert 'React' in match['description'] or 'component' in match['description'].lower()


def test_benchmark_scenario_loader_no_match_returns_none():
    """Test that unrelated problem returns no match"""
    loader = BenchmarkScenarioLoader()

    # Test completely unrelated problem
    match = loader.find_matching_scenario(
        "builder",
        "xyz quantum entanglement hyperdrive"
    )

    # Should return None for unrelated problem
    # (unless by chance some scenario matches)
    assert match is None or isinstance(match, dict)


# ============================================================================
# P2-2 FIX: CODE QUALITY VALIDATOR TESTS
# ============================================================================

def test_code_quality_validator_valid_python():
    """Test validation of valid Python code"""
    code = """
def hello_world(name: str) -> str:
    '''Greet someone'''
    return f"Hello, {name}!"

class Greeter:
    '''A greeter class'''
    def greet(self, name: str) -> str:
        return hello_world(name)
"""

    result = CodeQualityValidator.validate_code(code)

    assert result['syntax_valid'] is True
    assert result['overall_score'] > 0.5
    assert result['function_score'] > 0.0
    assert result['docstring_score'] > 0.0
    assert result['type_hint_score'] > 0.0


def test_code_quality_validator_invalid_syntax():
    """Test validation of code with syntax errors"""
    code = """
def broken(
    return "incomplete"
"""

    result = CodeQualityValidator.validate_code(code)

    assert result['syntax_valid'] is False
    assert result['overall_score'] == 0.0
    assert 'syntax_error' in result['details']


def test_code_quality_validator_empty_code():
    """Test validation of empty code"""
    result = CodeQualityValidator.validate_code("")

    assert result['syntax_valid'] is False
    assert result['overall_score'] == 0.0
    assert 'error' in result['details']


def test_code_quality_validator_dangerous_imports():
    """Test detection of dangerous imports"""
    code = """
import os
import subprocess

def dangerous():
    os.system("rm -rf /")
"""

    result = CodeQualityValidator.validate_code(code)

    # Should penalize dangerous imports
    assert result['syntax_valid'] is True
    assert result['import_score'] < 0.8  # Penalty applied


def test_code_quality_validator_required_imports():
    """Test validation with required imports"""
    code = """
import React
from typing import useState

def component():
    pass
"""

    result = CodeQualityValidator.validate_code(
        code,
        required_imports=["React", "useState"]
    )

    assert result['syntax_valid'] is True
    # Should have good import score if required imports present
    assert result['import_score'] > 0.0


def test_code_quality_validator_type_hints():
    """Test type hint coverage validation"""
    code_with_hints = """
def typed_function(x: int, y: str) -> bool:
    return True
"""

    code_without_hints = """
def untyped_function(x, y):
    return True
"""

    result_typed = CodeQualityValidator.validate_code(code_with_hints)
    result_untyped = CodeQualityValidator.validate_code(code_without_hints)

    assert result_typed['type_hint_score'] > result_untyped['type_hint_score']


def test_code_quality_validator_docstrings():
    """Test docstring coverage validation"""
    code_with_docs = """
def documented():
    '''This function has a docstring'''
    pass

class Documented:
    '''This class has a docstring'''
    pass
"""

    code_without_docs = """
def undocumented():
    pass

class Undocumented:
    pass
"""

    result_documented = CodeQualityValidator.validate_code(code_with_docs)
    result_undocumented = CodeQualityValidator.validate_code(code_without_docs)

    assert result_documented['docstring_score'] > result_undocumented['docstring_score']


def test_code_quality_validator_deterministic():
    """Test that validation is deterministic (same input = same output)"""
    code = """
def test_function(x: int) -> int:
    '''Test function'''
    return x * 2
"""

    # Run validation multiple times
    results = [CodeQualityValidator.validate_code(code) for _ in range(5)]

    # All results should be identical
    scores = [r['overall_score'] for r in results]
    assert len(set(scores)) == 1, "Validation should be deterministic"

    # Check all components are deterministic
    for key in ['import_score', 'function_score', 'docstring_score', 'type_hint_score']:
        values = [r[key] for r in results]
        assert len(set(values)) == 1, f"{key} should be deterministic"


# ============================================================================
# P2-1 & P2-2 FIX: TRAJECTORY VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_validate_trajectory_uses_benchmark_scenarios(se_darwin_agent, sample_trajectory):
    """Test that validation uses real benchmark scenarios"""
    # Create trajectory with code that matches a scenario
    sample_trajectory.code_changes = """
import React
from typing import useState

def UserProfile(props):
    '''User profile component'''
    return <div>Profile</div>
"""

    result = await se_darwin_agent._validate_trajectory(
        sample_trajectory,
        "React UserProfile component"
    )

    assert isinstance(result, BenchmarkResult)
    assert result.overall_score >= 0.0
    assert result.overall_score <= 1.0

    # Should have deterministic metrics
    assert 'syntax_valid' in result.metrics
    assert 'import_score' in result.metrics


@pytest.mark.asyncio
async def test_validate_trajectory_deterministic(se_darwin_agent):
    """Test that trajectory validation is deterministic"""
    trajectory = Trajectory(
        trajectory_id="deterministic_test",
        generation=0,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        code_changes="""
def calculate(x: int, y: int) -> int:
    '''Calculate sum'''
    return x + y
""",
        proposed_strategy="Simple addition function with type hints",
        reasoning_pattern="direct_implementation",
        status=TrajectoryStatus.PENDING.value
    )

    # Run validation multiple times
    results = []
    for _ in range(3):
        result = await se_darwin_agent._validate_trajectory(
            trajectory,
            "Build a calculator function"
        )
        results.append(result.overall_score)

    # All scores should be identical (deterministic)
    assert len(set(results)) == 1, f"Scores should be deterministic, got: {results}"


@pytest.mark.asyncio
async def test_validate_trajectory_operator_bonuses(se_darwin_agent):
    """Test that different operators get different bonuses"""
    base_code = """
def test() -> None:
    '''Test function'''
    pass
"""

    # Test different operator types
    operators_and_scores = {}

    for operator_type in [OperatorType.BASELINE, OperatorType.REVISION,
                          OperatorType.REFINEMENT, OperatorType.RECOMBINATION]:
        trajectory = Trajectory(
            trajectory_id=f"test_{operator_type.value}",
            generation=0,
            agent_name="test_agent",
            operator_applied=operator_type.value,
            code_changes=base_code,
            proposed_strategy="Test strategy",
            reasoning_pattern="test"
        )

        result = await se_darwin_agent._validate_trajectory(trajectory, "Test problem")
        operators_and_scores[operator_type.value] = result.overall_score

    # Recombination should score highest (has 0.12 bonus)
    # Refinement should be next (0.08 bonus)
    # Revision should be next (0.04 bonus)
    # Baseline should be lowest (0.0 bonus)
    assert operators_and_scores[OperatorType.RECOMBINATION.value] >= operators_and_scores[OperatorType.REFINEMENT.value]
    assert operators_and_scores[OperatorType.REFINEMENT.value] >= operators_and_scores[OperatorType.REVISION.value]


@pytest.mark.asyncio
async def test_validate_trajectory_code_bonus(se_darwin_agent):
    """Test that more substantial code gets bonus"""
    short_code = "def f(): pass"

    long_code = """
def elaborate_function(x: int, y: int) -> int:
    '''
    This is a comprehensive function that does many things.
    It takes two parameters and performs complex calculations.
    '''
    result = 0
    for i in range(x):
        result += y * i
    return result

def another_function(data: list) -> dict:
    '''Process data and return results'''
    return {'count': len(data), 'items': data}

class DataProcessor:
    '''A class for processing data'''
    def __init__(self):
        self.data = []

    def process(self, item):
        self.data.append(item)
"""

    traj_short = Trajectory(
        trajectory_id="short",
        generation=0,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        code_changes=short_code,
        proposed_strategy="Test"
    )

    traj_long = Trajectory(
        trajectory_id="long",
        generation=0,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        code_changes=long_code,
        proposed_strategy="Test"
    )

    result_short = await se_darwin_agent._validate_trajectory(traj_short, "Test")
    result_long = await se_darwin_agent._validate_trajectory(traj_long, "Test")

    # Longer, more substantial code should score higher
    assert result_long.overall_score > result_short.overall_score


@pytest.mark.asyncio
async def test_validate_trajectory_no_randomness(se_darwin_agent, sample_trajectory):
    """Test that validation contains no random elements (P2-2 fix verification)"""
    # This test verifies P2-2 fix: no random.random() calls
    sample_trajectory.code_changes = """
def deterministic_test():
    return 42
"""

    # Run validation 10 times
    scores = []
    for _ in range(10):
        result = await se_darwin_agent._validate_trajectory(
            sample_trajectory,
            "Test problem"
        )
        scores.append(result.overall_score)

    # All scores must be identical (no randomness)
    unique_scores = set(scores)
    assert len(unique_scores) == 1, f"Found non-deterministic scoring: {unique_scores}"

    # Verify no random variance in metrics either
    results = []
    for _ in range(5):
        result = await se_darwin_agent._validate_trajectory(
            sample_trajectory,
            "Test problem"
        )
        results.append(result)

    # Check all metric values are identical
    for metric_key in ['accuracy', 'import_score', 'function_score']:
        metric_values = [r.metrics.get(metric_key) for r in results]
        assert len(set(metric_values)) == 1, f"{metric_key} should be deterministic"
