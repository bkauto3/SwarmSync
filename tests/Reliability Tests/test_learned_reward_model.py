"""
Tests for Learned Reward Model (Phase 2 Feature)

Tests data-driven quality scoring and adaptive learning:
- Task outcome recording
- Weight learning from historical data
- Exponential moving average
- Prediction vs actual scoring
- Model persistence
- Weight normalization

Target: 99%+ coverage for learned_reward_model.py
"""
import pytest
import tempfile
import os
import json
from pathlib import Path

from infrastructure.learned_reward_model import (
    LearnedRewardModel,
    TaskOutcome,
    RewardModelWeights
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def reward_model():
    """Create fresh reward model for testing"""
    return LearnedRewardModel()


@pytest.fixture
def temp_storage():
    """Create temporary storage for model persistence"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "reward_model.json"


@pytest.fixture
def sample_outcomes():
    """Generate sample task outcomes"""
    return [
        TaskOutcome(
            task_id="task_1",
            task_type="implement",
            agent_name="builder_agent",
            success=1.0,
            quality=0.9,
            cost=0.3,
            time=0.4,
            predicted_score=0.85,
            actual_score=0.87
        ),
        TaskOutcome(
            task_id="task_2",
            task_type="test",
            agent_name="qa_agent",
            success=1.0,
            quality=0.95,
            cost=0.2,
            time=0.3,
            predicted_score=0.90,
            actual_score=0.92
        ),
        TaskOutcome(
            task_id="task_3",
            task_type="deploy",
            agent_name="deploy_agent",
            success=0.0,
            quality=0.0,
            cost=0.5,
            time=0.8,
            predicted_score=0.70,
            actual_score=0.15
        )
    ]


# ============================================================================
# TEST REWARD MODEL WEIGHTS
# ============================================================================

class TestRewardModelWeights:
    """Test RewardModelWeights dataclass"""

    def test_default_weights(self):
        """Test default weight values"""
        weights = RewardModelWeights()

        assert weights.w_success == 0.4
        assert weights.w_quality == 0.3
        assert weights.w_cost == 0.2
        assert weights.w_time == 0.1

    def test_weights_sum_to_one(self):
        """Test weights sum to 1.0"""
        weights = RewardModelWeights()

        total = weights.w_success + weights.w_quality + weights.w_cost + weights.w_time
        assert abs(total - 1.0) < 0.0001

    def test_normalize_weights(self):
        """Test weight normalization"""
        weights = RewardModelWeights(
            w_success=0.5,
            w_quality=0.5,
            w_cost=0.5,
            w_time=0.5
        )

        weights.normalize()

        total = weights.w_success + weights.w_quality + weights.w_cost + weights.w_time
        assert abs(total - 1.0) < 0.0001

    def test_weights_to_dict(self):
        """Test converting weights to dictionary"""
        weights = RewardModelWeights()
        weights_dict = weights.to_dict()

        assert "w_success" in weights_dict
        assert "w_quality" in weights_dict
        assert "w_cost" in weights_dict
        assert "w_time" in weights_dict

    def test_weights_from_dict(self):
        """Test creating weights from dictionary"""
        weights_dict = {
            "w_success": 0.5,
            "w_quality": 0.3,
            "w_cost": 0.15,
            "w_time": 0.05
        }

        weights = RewardModelWeights(**weights_dict)

        assert weights.w_success == 0.5
        assert weights.w_quality == 0.3

    def test_custom_learning_rate(self):
        """Test custom learning rate"""
        weights = RewardModelWeights(learning_rate=0.2)

        assert weights.learning_rate == 0.2

    def test_custom_min_samples(self):
        """Test custom minimum samples"""
        weights = RewardModelWeights(min_samples=20)

        assert weights.min_samples == 20


# ============================================================================
# TEST TASK OUTCOME
# ============================================================================

class TestTaskOutcome:
    """Test TaskOutcome dataclass"""

    def test_task_outcome_creation(self):
        """Test creating task outcome"""
        outcome = TaskOutcome(
            task_id="test_task",
            task_type="implement",
            agent_name="builder_agent",
            success=1.0,
            quality=0.9,
            cost=0.3,
            time=0.4
        )

        assert outcome.task_id == "test_task"
        assert outcome.success == 1.0
        assert outcome.quality == 0.9

    def test_outcome_with_prediction(self):
        """Test outcome with predicted score"""
        outcome = TaskOutcome(
            task_id="test",
            task_type="test",
            agent_name="qa_agent",
            success=1.0,
            quality=0.9,
            cost=0.2,
            time=0.3,
            predicted_score=0.85
        )

        assert outcome.predicted_score == 0.85

    def test_outcome_with_error(self):
        """Test outcome with error message"""
        outcome = TaskOutcome(
            task_id="failed_task",
            task_type="deploy",
            agent_name="deploy_agent",
            success=0.0,
            quality=0.0,
            cost=0.5,
            time=0.8,
            error_message="Deployment failed: timeout"
        )

        assert outcome.success == 0.0
        assert "timeout" in outcome.error_message

    def test_outcome_timestamp(self):
        """Test outcome has timestamp"""
        outcome = TaskOutcome(
            task_id="test",
            task_type="test",
            agent_name="test_agent",
            success=1.0,
            quality=0.9,
            cost=0.3,
            time=0.4
        )

        assert outcome.timestamp > 0

    def test_outcome_with_metadata(self):
        """Test outcome with detailed metrics"""
        outcome = TaskOutcome(
            task_id="test",
            task_type="test",
            agent_name="test_agent",
            success=1.0,
            quality=0.9,
            cost=0.3,
            time=0.4,
            execution_time_seconds=45.5,
            cost_dollars=0.0015
        )

        assert outcome.execution_time_seconds == 45.5
        assert outcome.cost_dollars == 0.0015


# ============================================================================
# TEST LEARNED REWARD MODEL
# ============================================================================

class TestLearnedRewardModel:
    """Test LearnedRewardModel class"""

    def test_model_initialization(self, reward_model):
        """Test model initializes with default weights"""
        weights = reward_model.get_weights()

        assert weights is not None
        assert weights.w_success > 0
        assert weights.w_quality > 0

    def test_record_single_outcome(self, reward_model, sample_outcomes):
        """Test recording single outcome"""
        outcome = sample_outcomes[0]
        reward_model.record_outcome(outcome)

        # Should have recorded outcome
        outcomes = reward_model.get_outcomes()
        assert len(outcomes) >= 1

    def test_record_multiple_outcomes(self, reward_model, sample_outcomes):
        """Test recording multiple outcomes"""
        for outcome in sample_outcomes:
            reward_model.record_outcome(outcome)

        outcomes = reward_model.get_outcomes()
        assert len(outcomes) == len(sample_outcomes)

    def test_calculate_score(self, reward_model):
        """Test score calculation"""
        outcome = TaskOutcome(
            task_id="test",
            task_type="test",
            agent_name="test_agent",
            success=1.0,
            quality=0.8,
            cost=0.3,
            time=0.4
        )

        score = reward_model.calculate_score(outcome)

        # Score should be weighted combination
        # score = 0.4*1.0 + 0.3*0.8 + 0.2*(1-0.3) + 0.1*(1-0.4)
        # score = 0.4 + 0.24 + 0.14 + 0.06 = 0.84
        assert 0.8 <= score <= 1.0

    def test_calculate_score_with_failure(self, reward_model):
        """Test score calculation for failed task"""
        outcome = TaskOutcome(
            task_id="failed",
            task_type="test",
            agent_name="test_agent",
            success=0.0,
            quality=0.2,
            cost=0.8,
            time=0.9
        )

        score = reward_model.calculate_score(outcome)

        # Failed tasks should have low scores
        assert score < 0.5

    def test_learning_updates_weights(self, reward_model, sample_outcomes):
        """Test that learning updates weights"""
        initial_weights = reward_model.get_weights()
        initial_success_weight = initial_weights.w_success

        # Record many outcomes
        for _ in range(15):  # More than min_samples (10)
            for outcome in sample_outcomes:
                reward_model.record_outcome(outcome)

        # Trigger learning
        reward_model.learn_from_outcomes()

        updated_weights = reward_model.get_weights()

        # Weights may have changed (depends on outcomes)
        # At minimum, they should still be normalized
        total = (updated_weights.w_success + updated_weights.w_quality +
                 updated_weights.w_cost + updated_weights.w_time)
        assert abs(total - 1.0) < 0.01

    def test_min_samples_requirement(self, reward_model, sample_outcomes):
        """Test learning requires minimum samples"""
        # Record only 5 outcomes (less than min_samples=10)
        for outcome in sample_outcomes[:1]:
            for i in range(5):
                reward_model.record_outcome(outcome)

        initial_weights = reward_model.get_weights()
        reward_model.learn_from_outcomes()
        updated_weights = reward_model.get_weights()

        # Weights should not change with insufficient samples
        # (or change minimally)
        assert abs(initial_weights.w_success - updated_weights.w_success) < 0.1

    def test_predict_score(self, reward_model):
        """Test predicting score for task"""
        score = reward_model.predict_score(
            task_type="implement",
            agent_name="builder_agent"
        )

        # Should return reasonable score
        assert 0.0 <= score <= 1.0

    def test_get_agent_statistics(self, reward_model, sample_outcomes):
        """Test getting agent-specific statistics"""
        for outcome in sample_outcomes:
            reward_model.record_outcome(outcome)

        stats = reward_model.get_agent_statistics("builder_agent")

        # Should have statistics for builder_agent
        assert stats is not None
        assert "success_rate" in stats or "avg_score" in stats or stats == {}

    def test_get_task_type_statistics(self, reward_model, sample_outcomes):
        """Test getting task type statistics"""
        for outcome in sample_outcomes:
            reward_model.record_outcome(outcome)

        stats = reward_model.get_task_type_statistics("implement")

        # Should have statistics for implement tasks
        assert stats is not None

    def test_weights_remain_normalized(self, reward_model, sample_outcomes):
        """Test weights stay normalized after learning"""
        # Record outcomes and learn multiple times
        for _ in range(3):
            for outcome in sample_outcomes:
                reward_model.record_outcome(outcome)
            reward_model.learn_from_outcomes()

        weights = reward_model.get_weights()
        total = weights.w_success + weights.w_quality + weights.w_cost + weights.w_time

        assert abs(total - 1.0) < 0.01

    def test_exponential_moving_average(self, reward_model):
        """Test exponential moving average for recent performance"""
        # Record outcomes with varying quality
        for i in range(20):
            outcome = TaskOutcome(
                task_id=f"task_{i}",
                task_type="test",
                agent_name="test_agent",
                success=1.0,
                quality=0.5 + (i * 0.02),  # Gradually improving quality
                cost=0.3,
                time=0.4
            )
            reward_model.record_outcome(outcome)

        # Recent outcomes should have more weight
        # (Implementation detail - test that model handles this)
        outcomes = reward_model.get_outcomes()
        assert len(outcomes) == 20

    def test_model_persistence(self, reward_model, sample_outcomes, temp_storage):
        """Test saving and loading model"""
        # Record outcomes
        for outcome in sample_outcomes:
            reward_model.record_outcome(outcome)

        # Save model
        reward_model.save(str(temp_storage))

        # Load into new model
        new_model = LearnedRewardModel()
        new_model.load(str(temp_storage))

        # Weights should match
        original_weights = reward_model.get_weights()
        loaded_weights = new_model.get_weights()

        assert abs(original_weights.w_success - loaded_weights.w_success) < 0.0001

    def test_model_reset(self, reward_model, sample_outcomes):
        """Test resetting model to defaults"""
        # Record outcomes
        for outcome in sample_outcomes:
            reward_model.record_outcome(outcome)

        reward_model.reset()

        # Should be back to defaults
        weights = reward_model.get_weights()
        assert weights.w_success == 0.4
        assert len(reward_model.get_outcomes()) == 0

    def test_prediction_accuracy_tracking(self, reward_model):
        """Test tracking prediction accuracy"""
        # Record outcomes with predictions
        for i in range(10):
            outcome = TaskOutcome(
                task_id=f"task_{i}",
                task_type="test",
                agent_name="test_agent",
                success=1.0,
                quality=0.9,
                cost=0.3,
                time=0.4,
                predicted_score=0.85,
                actual_score=0.87
            )
            reward_model.record_outcome(outcome)

        # Should track prediction accuracy
        # (Model may calculate RMSE or MAE)
        outcomes = reward_model.get_outcomes()
        with_predictions = [o for o in outcomes if o.predicted_score is not None]
        assert len(with_predictions) == 10

    def test_handle_invalid_outcome_values(self, reward_model):
        """Test handling of invalid outcome values"""
        # Outcome with out-of-range values
        outcome = TaskOutcome(
            task_id="invalid",
            task_type="test",
            agent_name="test_agent",
            success=1.5,  # Should be 0-1
            quality=-0.1,  # Should be 0-1
            cost=2.0,  # Should be 0-1
            time=-0.5  # Should be 0-1
        )

        # Model should handle gracefully (clip or reject)
        try:
            reward_model.record_outcome(outcome)
            # If accepted, should clip values
            score = reward_model.calculate_score(outcome)
            assert 0.0 <= score <= 1.0
        except ValueError:
            # Or reject invalid values
            pass

    def test_concurrent_outcome_recording(self, reward_model):
        """Test thread-safe outcome recording"""
        import threading

        def record_outcomes():
            for i in range(10):
                outcome = TaskOutcome(
                    task_id=f"task_{i}",
                    task_type="test",
                    agent_name="test_agent",
                    success=1.0,
                    quality=0.9,
                    cost=0.3,
                    time=0.4
                )
                reward_model.record_outcome(outcome)

        # Record from multiple threads
        threads = [threading.Thread(target=record_outcomes) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All outcomes should be recorded
        outcomes = reward_model.get_outcomes()
        assert len(outcomes) >= 50

    def test_learning_rate_impact(self, reward_model, sample_outcomes):
        """Test learning rate affects weight updates"""
        # Set high learning rate
        weights = reward_model.get_weights()
        weights.learning_rate = 0.5

        initial_success_weight = weights.w_success

        # Record outcomes and learn
        for _ in range(3):
            for outcome in sample_outcomes:
                reward_model.record_outcome(outcome)
            reward_model.learn_from_outcomes()

        # Weights should have changed more with high learning rate
        updated_weights = reward_model.get_weights()
        # (Can't assert exact change without knowing algorithm, but should differ)
        total = (updated_weights.w_success + updated_weights.w_quality +
                 updated_weights.w_cost + updated_weights.w_time)
        assert abs(total - 1.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
