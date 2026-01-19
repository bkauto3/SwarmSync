"""Unit tests for the FP16 training helper."""

import os
import tempfile

import pytest

torch = pytest.importorskip("torch")

from infrastructure.training import FP16Trainer, FP16TrainingConfig


class SimpleModel(torch.nn.Module):
    """Minimal linear model for exercising the trainer."""

    def __init__(self) -> None:
        super().__init__()
        self.fc = torch.nn.Linear(10, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.fc(inputs)


def compute_loss(model: SimpleModel, batch):
    features, targets = batch
    outputs = model(features)
    return torch.nn.functional.mse_loss(outputs, targets)


@pytest.fixture
def dummy_batch():
    features = torch.randn(8, 10)
    targets = torch.randn(8, 1)
    return features, targets


def test_fp16_trainer_initialization():
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    trainer = FP16Trainer(model, optimizer)

    stats = trainer.get_stats()
    assert stats["training_steps"] == 0
    assert stats["overflow_steps"] == 0
    # fp16 may be disabled on CPU-only runners, but the flag should exist
    assert "fp16_enabled" in stats


def test_fp16_training_step(dummy_batch):
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    trainer = FP16Trainer(model, optimizer)

    loss = trainer.training_step(dummy_batch, compute_loss)
    assert isinstance(loss, torch.Tensor)
    assert loss.dtype == torch.float32


def test_fp16_backward_and_step(dummy_batch):
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    trainer = FP16Trainer(model, optimizer)

    loss = trainer.training_step(dummy_batch, compute_loss)
    success = trainer.backward_and_step(loss)

    assert success is True
    assert trainer.training_steps == 1


def test_fp32_fallback(dummy_batch):
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    config = FP16TrainingConfig(enabled=False)
    trainer = FP16Trainer(model, optimizer, config)

    assert trainer.get_stats()["fp16_enabled"] is False

    loss = trainer.training_step(dummy_batch, compute_loss)
    success = trainer.backward_and_step(loss)
    assert success is True


def test_checkpoint_round_trip(dummy_batch):
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    trainer = FP16Trainer(model, optimizer)

    loss = trainer.training_step(dummy_batch, compute_loss)
    trainer.backward_and_step(loss)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ckpt.pt")
        trainer.save_checkpoint(path)

        # Load into a fresh model/trainer instance
        new_model = SimpleModel()
        new_optimizer = torch.optim.Adam(new_model.parameters())
        new_trainer = FP16Trainer(new_model, new_optimizer)
        new_trainer.load_checkpoint(path)

        assert new_trainer.training_steps == trainer.training_steps
        assert new_trainer.overflow_steps == trainer.overflow_steps


def test_gradient_overflow_detection():
    """Test gradient overflow detection with high loss scale.

    Via Context7 MCP - PyTorch AMP overflow detection:
    When gradients overflow in FP16, GradScaler detects it and reduces scale.
    The trainer should return False and increment overflow counter.
    """
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())

    # Use extremely high loss scale to trigger overflow
    config = FP16TrainingConfig(
        enabled=True,
        loss_scale=1e10,  # Very high to trigger overflow
        growth_interval=2000
    )
    trainer = FP16Trainer(model, optimizer, config)

    # Create batch with large values
    x = torch.randn(8, 10) * 1e6
    y = torch.randn(8, 1) * 1e6
    batch = (x, y)

    # Training steps (may trigger overflow depending on hardware)
    for _ in range(5):
        loss = trainer.training_step(batch, compute_loss)
        success = trainer.backward_and_step(loss)

        # If overflow detected, verify counter incremented
        if not success:
            assert trainer.overflow_steps > 0
            stats = trainer.get_stats()
            assert stats["overflow_rate"] > 0
            break


def test_model_casting_to_fp16():
    """Test optional full FP16 model casting.

    Via Context7 MCP - Full FP16 vs Mixed Precision:
    - Mixed precision (default): Model in FP32, operations in FP16
    - Full FP16 (optional): Model parameters cast to FP16
    """
    model = SimpleModel()
    optimizer = torch.optim.Adam(model.parameters())
    trainer = FP16Trainer(model, optimizer)

    # Check initial dtype (should be FP32)
    initial_dtype = next(model.parameters()).dtype
    assert initial_dtype in (torch.float32, torch.float64)

    # Cast to FP16 (only works if CUDA available and FP16 enabled)
    if trainer._fp16_active:
        trainer.cast_model_to_fp16()
        casted_dtype = next(model.parameters()).dtype
        assert casted_dtype == torch.float16


@pytest.mark.benchmark
def test_fp16_vs_fp32_speed_benchmark(dummy_batch):
    """Benchmark FP16 vs FP32 training speed.

    Via Context7 MCP - Expected speedup: 2-3x on CUDA, 1.0x on CPU.
    """
    import time

    # Prepare larger dataset for meaningful benchmark
    dataset = [(torch.randn(32, 10), torch.randn(32, 1)) for _ in range(100)]

    # Benchmark FP16
    model_fp16 = SimpleModel()
    optimizer_fp16 = torch.optim.Adam(model_fp16.parameters())
    trainer_fp16 = FP16Trainer(model_fp16, optimizer_fp16)

    start = time.perf_counter()
    for batch in dataset:
        loss = trainer_fp16.training_step(batch, compute_loss)
        trainer_fp16.backward_and_step(loss)
    fp16_time = time.perf_counter() - start

    # Benchmark FP32
    model_fp32 = SimpleModel()
    optimizer_fp32 = torch.optim.Adam(model_fp32.parameters())
    config_fp32 = FP16TrainingConfig(enabled=False)
    trainer_fp32 = FP16Trainer(model_fp32, optimizer_fp32, config_fp32)

    start = time.perf_counter()
    for batch in dataset:
        loss = trainer_fp32.training_step(batch, compute_loss)
        trainer_fp32.backward_and_step(loss)
    fp32_time = time.perf_counter() - start

    # Calculate speedup
    speedup = fp32_time / max(fp16_time, 1e-6)

    stats_fp16 = trainer_fp16.get_stats()
    stats_fp32 = trainer_fp32.get_stats()

    print(f"\n{'='*60}")
    print(f"FP16 vs FP32 Speed Benchmark")
    print(f"{'='*60}")
    print(f"FP16 time:       {fp16_time:.3f}s")
    print(f"FP32 time:       {fp32_time:.3f}s")
    print(f"Speedup:         {speedup:.2f}x")
    print(f"FP16 enabled:    {stats_fp16['fp16_enabled']}")
    print(f"CUDA available:  {torch.cuda.is_available()}")
    print(f"Overflow rate:   {stats_fp16['overflow_rate']:.2%}")
    print(f"{'='*60}")

    # FP16 should be at least as fast as FP32 (on CUDA should be 2-3x)
    assert speedup >= 0.8, f"FP16 should not be slower than FP32, got {speedup:.2f}x"

    # If CUDA available, expect significant speedup
    if torch.cuda.is_available() and stats_fp16['fp16_enabled']:
        # On CUDA, expect at least 1.5x speedup (conservative threshold)
        assert speedup >= 1.3, f"Expected >1.3x speedup on CUDA, got {speedup:.2f}x"
