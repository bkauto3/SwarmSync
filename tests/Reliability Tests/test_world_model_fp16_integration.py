"""Integration checks for WorldModel FP16 toggle."""

import pytest

torch = pytest.importorskip("torch")

from infrastructure import OutcomeTag
from infrastructure.world_model import WorldModel


class DummyReplayBuffer:
    def __init__(self, trajectories):
        self._trajectories = trajectories

    def sample(self, limit=1000):
        return self._trajectories[:limit]


@pytest.mark.asyncio
async def test_world_model_fp16_toggle_without_cuda(monkeypatch):
    monkeypatch.setenv("ENABLE_FP16_TRAINING", "true")

    trajectories = [
        {
            "initial_state": {"metrics": {"overall_score": 0.6, "correctness": 0.7}},
            "actions": ["edit"],
            "final_outcome": OutcomeTag.SUCCESS.value,
            "final_reward": 0.4,
        }
        for _ in range(4)
    ]

    model = WorldModel()
    model.replay_buffer = DummyReplayBuffer(trajectories)

    await model.train(num_epochs=1, batch_size=2)

    # On CPU-only environments fp16 should gracefully fall back
    assert isinstance(model.fp16_enabled, bool)
    if not torch.cuda.is_available():
        assert model.fp16_enabled is False

    assert model.training_history, "WorldModel training history should not be empty"
    assert "fp16_overflow_batches" in model.training_history[-1]
    assert model.training_history[-1]["fp16_overflow_batches"] >= 0

    # No FP16 stats when training ran in FP32 mode
    if not torch.cuda.is_available():
        assert model._fp16_stats is None
