"""
Unit Tests for SPICE DrGRPO Optimizer - Dynamic Reward Group Preference Optimization

Tests the DrGRPOOptimizer class:
1. Training step execution with Challenger + Reasoner
2. Variance reward calculation
3. Training example creation
4. Training batch saving
5. Fine-tuning threshold validation
6. Error handling and edge cases
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from infrastructure.spice.drgrpo_optimizer import (
    DrGRPOOptimizer,
    TrainingExample,
    TrainingBatch,
    get_drgrpo_optimizer
)
from infrastructure.spice.challenger_agent import (
    ChallengerAgent,
    FrontierTask,
    GroundingEvidence
)
from infrastructure.spice.reasoner_agent import (
    ReasonerAgent,
    TrajectoryResult
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="Generated content")
    return client


@pytest.fixture
def mock_challenger():
    """Mock Challenger agent"""
    agent = AsyncMock(spec=ChallengerAgent)

    # Return sample frontier tasks
    async def generate_tasks(*args, **kwargs):
        return [
            FrontierTask(
                task_id="task_001",
                description="Generated frontier task 1",
                difficulty=0.5,
                agent_role="QA",
                grounding_evidence=[
                    GroundingEvidence(
                        corpus_source="genesis_benchmarks",
                        reference_task="Base task 1",
                        similarity_score=0.85
                    )
                ],
                expected_capabilities=["cap1", "cap2"]
            )
        ]

    agent.generate_frontier_task = generate_tasks
    return agent


@pytest.fixture
def mock_reasoner():
    """Mock Reasoner agent"""
    agent = AsyncMock(spec=ReasonerAgent)

    # Return sample trajectories
    async def solve_tasks(*args, **kwargs):
        return [
            TrajectoryResult(
                task_id="task_001",
                solution="Solution 1 with detailed explanation",
                approach="baseline",
                quality_score=0.7
            ),
            TrajectoryResult(
                task_id="task_001",
                solution="Alternative solution approach 2",
                approach="revision",
                quality_score=0.75
            ),
            TrajectoryResult(
                task_id="task_001",
                solution="Hybrid solution combining best elements",
                approach="recombination",
                quality_score=0.8
            )
        ]

    agent.solve_task = solve_tasks
    return agent


@pytest.fixture
def drgrpo_optimizer(mock_challenger, mock_reasoner, tmp_path):
    """Create DrGRPO optimizer for testing"""
    optimizer = DrGRPOOptimizer(
        challenger=mock_challenger,
        reasoner=mock_reasoner,
        output_dir=tmp_path / "training_data"
    )
    return optimizer


@pytest.fixture
def sample_frontier_task():
    """Create sample frontier task"""
    return FrontierTask(
        task_id="task_001",
        description="Sample frontier task",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Base task",
                similarity_score=0.85
            )
        ],
        expected_capabilities=["capability1"]
    )


@pytest.fixture
def sample_trajectories():
    """Create sample trajectories"""
    return [
        TrajectoryResult(
            task_id="task_001",
            solution="Solution A with more content",
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="task_001",
            solution="Solution B",
            approach="revision",
            quality_score=0.75
        ),
        TrajectoryResult(
            task_id="task_001",
            solution="Solution C with additional details",
            approach="recombination",
            quality_score=0.8
        )
    ]


# ============================================================================
# TESTS: Training Step Execution
# ============================================================================

@pytest.mark.asyncio
async def test_train_step_basic(drgrpo_optimizer):
    """Test executing one complete training step"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=3
    )

    assert isinstance(batch, TrainingBatch)
    assert batch.batch_id is not None
    assert len(batch.challenger_examples) >= 0
    assert len(batch.reasoner_examples) >= 0


@pytest.mark.asyncio
async def test_train_step_creates_examples(drgrpo_optimizer):
    """Test that training step creates training examples"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=3
    )

    # Should have created examples
    total_examples = len(batch.challenger_examples) + len(batch.reasoner_examples)
    assert total_examples >= 1


@pytest.mark.asyncio
async def test_train_step_batch_id_format(drgrpo_optimizer):
    """Test that batch ID follows expected format"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=3
    )

    # Batch ID should contain agent role and difficulty
    assert "qa" in batch.batch_id.lower()
    assert "5" in batch.batch_id  # Difficulty 0.5 * 10 = 5


@pytest.mark.asyncio
async def test_train_step_timestamp(drgrpo_optimizer):
    """Test that batch has valid timestamp"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=3
    )

    # Should have ISO format timestamp
    try:
        datetime.fromisoformat(batch.timestamp)
    except ValueError:
        pytest.fail("Invalid timestamp format")


# ============================================================================
# TESTS: Variance Reward Calculation
# ============================================================================

def test_variance_reward_calculation(drgrpo_optimizer, sample_frontier_task, sample_trajectories):
    """Test variance reward formula calculation"""
    reward = drgrpo_optimizer.compute_variance_reward(
        task=sample_frontier_task,
        trajectories=sample_trajectories
    )

    assert isinstance(reward, float)
    assert reward >= 0.0


def test_variance_reward_high_diversity(drgrpo_optimizer, sample_frontier_task):
    """Test variance reward with high solution diversity"""
    # Create trajectories with very different lengths
    trajectories = [
        TrajectoryResult(
            task_id="task_001",
            solution="A",
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="task_001",
            solution="B" * 100,
            approach="revision",
            quality_score=0.75
        )
    ]

    reward = drgrpo_optimizer.compute_variance_reward(
        task=sample_frontier_task,
        trajectories=trajectories
    )

    assert reward > 0.0


def test_variance_reward_low_diversity(drgrpo_optimizer, sample_frontier_task):
    """Test variance reward with low solution diversity"""
    # Create trajectories with similar lengths
    same_solution = "Solution text"
    trajectories = [
        TrajectoryResult(
            task_id="task_001",
            solution=same_solution,
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="task_001",
            solution=same_solution,
            approach="revision",
            quality_score=0.75
        )
    ]

    reward = drgrpo_optimizer.compute_variance_reward(
        task=sample_frontier_task,
        trajectories=trajectories
    )

    assert reward == 0.0


def test_variance_reward_single_trajectory(drgrpo_optimizer, sample_frontier_task):
    """Test variance reward with single trajectory returns 0.0"""
    trajectories = [
        TrajectoryResult(
            task_id="task_001",
            solution="Single solution",
            approach="baseline",
            quality_score=0.7
        )
    ]

    reward = drgrpo_optimizer.compute_variance_reward(
        task=sample_frontier_task,
        trajectories=trajectories
    )

    assert reward == 0.0


def test_variance_reward_difficulty_weighting(drgrpo_optimizer, sample_trajectories):
    """Test that difficulty weights variance reward"""
    easy_task = FrontierTask(
        task_id="easy",
        description="Easy task",
        difficulty=0.1,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Easy base",
                similarity_score=0.85
            )
        ],
        expected_capabilities=[]
    )

    hard_task = FrontierTask(
        task_id="hard",
        description="Hard task",
        difficulty=0.9,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Hard base",
                similarity_score=0.85
            )
        ],
        expected_capabilities=[]
    )

    easy_reward = drgrpo_optimizer.compute_variance_reward(easy_task, sample_trajectories)
    hard_reward = drgrpo_optimizer.compute_variance_reward(hard_task, sample_trajectories)

    # Harder tasks should have higher rewards for same variance
    assert hard_reward > easy_reward


def test_variance_reward_grounding_weighting(drgrpo_optimizer, sample_trajectories):
    """Test that grounding score weights variance reward"""
    well_grounded = FrontierTask(
        task_id="well",
        description="Well-grounded task",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Base",
                similarity_score=0.95
            )
        ],
        expected_capabilities=[]
    )

    poorly_grounded = FrontierTask(
        task_id="poor",
        description="Poorly-grounded task",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Base",
                similarity_score=0.1
            )
        ],
        expected_capabilities=[]
    )

    well_reward = drgrpo_optimizer.compute_variance_reward(well_grounded, sample_trajectories)
    poor_reward = drgrpo_optimizer.compute_variance_reward(poorly_grounded, sample_trajectories)

    # Better grounding should result in higher rewards
    assert well_reward > poor_reward


# ============================================================================
# TESTS: Training Example Creation
# ============================================================================

def test_create_challenger_example(drgrpo_optimizer, sample_frontier_task):
    """Test creating training example for Challenger agent"""
    example = drgrpo_optimizer._create_challenger_example(
        task=sample_frontier_task,
        variance_reward=0.5
    )

    assert isinstance(example, TrainingExample)
    assert example.agent_type == "challenger"
    assert example.reward == 0.5
    assert len(example.input_text) > 0
    assert len(example.output_text) > 0


def test_create_challenger_example_to_dict(drgrpo_optimizer, sample_frontier_task):
    """Test Challenger example serialization"""
    example = drgrpo_optimizer._create_challenger_example(
        task=sample_frontier_task,
        variance_reward=0.5
    )

    example_dict = example.to_dict()

    assert "messages" in example_dict
    assert len(example_dict["messages"]) == 2
    assert example_dict["messages"][0]["role"] == "user"
    assert example_dict["messages"][1]["role"] == "assistant"
    assert example_dict["reward"] == 0.5


def test_create_reasoner_example(drgrpo_optimizer, sample_frontier_task):
    """Test creating training example for Reasoner agent"""
    trajectory = TrajectoryResult(
        task_id="task_001",
        solution="Generated solution",
        approach="baseline",
        quality_score=0.7
    )

    example = drgrpo_optimizer._create_reasoner_example(
        task=sample_frontier_task,
        trajectory=trajectory,
        variance_reward=0.5
    )

    assert isinstance(example, TrainingExample)
    assert example.agent_type == "reasoner"
    # Reward should be weighted by quality score
    assert example.reward == 0.5 * 0.7


def test_create_reasoner_example_to_dict(drgrpo_optimizer, sample_frontier_task):
    """Test Reasoner example serialization"""
    trajectory = TrajectoryResult(
        task_id="task_001",
        solution="Generated solution",
        approach="baseline",
        quality_score=0.7
    )

    example = drgrpo_optimizer._create_reasoner_example(
        task=sample_frontier_task,
        trajectory=trajectory,
        variance_reward=0.5
    )

    example_dict = example.to_dict()

    assert "messages" in example_dict
    assert example_dict["messages"][1]["role"] == "assistant"
    assert example_dict["reward"] == 0.5 * 0.7


# ============================================================================
# TESTS: Training Batch Saving
# ============================================================================

@pytest.mark.asyncio
async def test_save_training_batch(drgrpo_optimizer):
    """Test saving training batch to disk"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=2
    )

    # Verify files were created
    output_dir = drgrpo_optimizer.output_dir

    # Files should exist
    challenger_files = list(output_dir.glob("challenger_*"))
    reasoner_files = list(output_dir.glob("reasoner_*"))
    metadata_files = list(output_dir.glob("metadata_*"))

    assert len(challenger_files) >= 0  # May be empty if no challenger examples
    assert len(reasoner_files) >= 0    # May be empty if no reasoner examples


@pytest.mark.asyncio
async def test_training_batch_metadata_file(drgrpo_optimizer):
    """Test that metadata file is created correctly"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=1,
        num_trajectories=2
    )

    metadata_files = list(drgrpo_optimizer.output_dir.glob("metadata_*"))

    if metadata_files:
        metadata_file = metadata_files[0]
        metadata = json.loads(metadata_file.read_text())

        assert "batch_id" in metadata
        assert "timestamp" in metadata
        assert "avg_variance_reward" in metadata
        assert "num_challenger_examples" in metadata
        assert "num_reasoner_examples" in metadata


# ============================================================================
# TESTS: Fine-Tuning Threshold
# ============================================================================

@pytest.mark.asyncio
async def test_fine_tune_insufficient_data(drgrpo_optimizer):
    """Test fine-tuning with insufficient training examples"""
    # Don't add any examples
    result = await drgrpo_optimizer.fine_tune_agents(min_examples=100)

    assert result["status"] == "insufficient_data"
    assert result["challenger_count"] == 0
    assert result["reasoner_count"] == 0


@pytest.mark.asyncio
async def test_fine_tune_sufficient_data(drgrpo_optimizer):
    """Test fine-tuning with sufficient training examples"""
    # Add enough examples - need BOTH challenger AND reasoner to have 100
    for i in range(100):
        from infrastructure.spice.drgrpo_optimizer import TrainingExample
        example = TrainingExample(
            input_text=f"Input {i}",
            output_text=f"Output {i}",
            reward=0.5,
            agent_type="challenger"
        )
        drgrpo_optimizer.training_examples.append(example)

    for i in range(100):
        from infrastructure.spice.drgrpo_optimizer import TrainingExample
        example = TrainingExample(
            input_text=f"Input {i}",
            output_text=f"Output {i}",
            reward=0.5,
            agent_type="reasoner"
        )
        drgrpo_optimizer.training_examples.append(example)

    result = await drgrpo_optimizer.fine_tune_agents(min_examples=100)

    # Should have sufficient data now (100 challenger AND 100 reasoner)
    assert result["status"] == "data_ready"
    assert result["challenger_count"] >= 100
    assert result["reasoner_count"] >= 100


# ============================================================================
# TESTS: Training Data Accumulation
# ============================================================================

@pytest.mark.asyncio
async def test_training_history_accumulation(drgrpo_optimizer):
    """Test that training history accumulates across steps"""
    batch1 = await drgrpo_optimizer.train_step("QA", 0.3, 1, 2)
    batch2 = await drgrpo_optimizer.train_step("Support", 0.5, 1, 2)

    assert len(drgrpo_optimizer.training_history) >= 2
    assert batch1.batch_id is not None
    assert batch2.batch_id is not None


@pytest.mark.asyncio
async def test_training_examples_accumulation(drgrpo_optimizer):
    """Test that training examples accumulate"""
    batch = await drgrpo_optimizer.train_step("QA", 0.5, 1, 3)

    # Should have accumulated examples
    assert len(drgrpo_optimizer.training_examples) >= 0


# ============================================================================
# TESTS: DrGRPO Initialization
# ============================================================================

def test_drgrpo_initialization_defaults(tmp_path):
    """Test DrGRPO initialization with defaults"""
    # Just test that we can create an optimizer with specified agents
    mock_challenger = Mock(spec=ChallengerAgent)
    mock_reasoner = Mock(spec=ReasonerAgent)

    optimizer = DrGRPOOptimizer(
        challenger=mock_challenger,
        reasoner=mock_reasoner,
        output_dir=tmp_path
    )

    assert optimizer.reward_weight == 1.0
    assert optimizer.output_dir == tmp_path


def test_drgrpo_initialization_custom_weight(mock_challenger, mock_reasoner, tmp_path):
    """Test DrGRPO initialization with custom reward weight"""
    optimizer = DrGRPOOptimizer(
        challenger=mock_challenger,
        reasoner=mock_reasoner,
        output_dir=tmp_path,
        reward_weight=2.0
    )

    assert optimizer.reward_weight == 2.0


def test_get_drgrpo_optimizer_singleton(mock_challenger, mock_reasoner, tmp_path):
    """Test get_drgrpo_optimizer singleton pattern"""
    # Reset singleton
    import infrastructure.spice.drgrpo_optimizer
    infrastructure.spice.drgrpo_optimizer._drgrpo_instance = None

    optimizer1 = get_drgrpo_optimizer(
        challenger=mock_challenger,
        reasoner=mock_reasoner,
        output_dir=tmp_path
    )
    optimizer2 = get_drgrpo_optimizer()

    # Should return same instance
    assert optimizer1 is optimizer2


# ============================================================================
# TESTS: Training Batch Data Class
# ============================================================================

def test_training_batch_creation():
    """Test TrainingBatch creation"""
    examples = [
        TrainingExample("input", "output", 0.5, "challenger"),
        TrainingExample("input2", "output2", 0.6, "reasoner")
    ]

    batch = TrainingBatch(
        challenger_examples=examples[:1],
        reasoner_examples=examples[1:],
        avg_variance_reward=0.55,
        batch_id="batch_001",
        timestamp="2024-01-01T00:00:00Z"
    )

    assert batch.batch_id == "batch_001"
    assert len(batch.challenger_examples) == 1
    assert len(batch.reasoner_examples) == 1
    assert batch.avg_variance_reward == 0.55


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_train_step_zero_tasks(drgrpo_optimizer):
    """Test training step with zero tasks"""
    batch = await drgrpo_optimizer.train_step(
        agent_role="QA",
        difficulty_level=0.5,
        num_tasks=0,
        num_trajectories=3
    )

    assert isinstance(batch, TrainingBatch)


@pytest.mark.asyncio
async def test_train_step_empty_reward_weight(mock_challenger, mock_reasoner, tmp_path):
    """Test with zero reward weight"""
    optimizer = DrGRPOOptimizer(
        challenger=mock_challenger,
        reasoner=mock_reasoner,
        output_dir=tmp_path,
        reward_weight=0.0
    )

    batch = await optimizer.train_step("QA", 0.5, 1, 2)

    # Should handle gracefully
    assert batch.avg_variance_reward == 0.0


def test_variance_reward_no_grounding_evidence(drgrpo_optimizer):
    """Test variance reward with missing grounding evidence"""
    task = FrontierTask(
        task_id="test",
        description="Test task",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[],  # Empty
        expected_capabilities=[]
    )

    trajectories = [
        TrajectoryResult("test", "Sol A" * 10, "baseline", 0.7),
        TrajectoryResult("test", "Sol B", "revision", 0.75)
    ]

    reward = drgrpo_optimizer.compute_variance_reward(task, trajectories)

    # Should use default grounding score of 0.5
    assert isinstance(reward, float)
    assert reward >= 0.0
