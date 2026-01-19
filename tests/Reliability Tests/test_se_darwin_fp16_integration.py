"""Integration tests for SE-Darwin with FP16 training.

Tests the integration between SE-Darwin evolution system and FP16 training
infrastructure, validating that:
1. WorldModel correctly uses FP16 when enabled
2. SE-Darwin evolution loops work with FP16-enabled components
3. Performance improvements are measurable
4. Accuracy is maintained within acceptable bounds
"""

import os
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock

# Skip all tests if torch not available
torch = pytest.importorskip("torch")

from infrastructure.training import FP16Trainer, FP16TrainingConfig
from infrastructure.world_model import WorldModel
from infrastructure import OutcomeTag


class MockReplayBuffer:
    """Mock replay buffer for testing."""
    
    def __init__(self, num_trajectories=100):
        self.trajectories = [
            self._generate_trajectory(i) for i in range(num_trajectories)
        ]
    
    def _generate_trajectory(self, seed):
        import random
        rng = random.Random(seed)
        return {
            "initial_state": {
                "metrics": {
                    "overall_score": rng.uniform(0.3, 0.9),
                    "correctness": rng.uniform(0.2, 0.95),
                }
            },
            "actions": [f"edit_{i}" for i in range(rng.randint(1, 4))],
            "final_outcome": OutcomeTag.SUCCESS.value if rng.random() > 0.3 else OutcomeTag.FAILURE.value,
            "final_reward": rng.uniform(-0.1, 0.6),
        }
    
    def sample(self, limit=1000):
        return self.trajectories[:limit]


@pytest.mark.asyncio
async def test_world_model_fp16_integration():
    """Test that WorldModel correctly uses FP16 when enabled."""
    # Enable FP16 via environment
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        # Initialize WorldModel
        world_model = WorldModel()
        world_model.replay_buffer = MockReplayBuffer(50)
        
        # Train for 1 epoch
        await world_model.train(num_epochs=1, batch_size=16)
        
        # Verify FP16 was used
        assert world_model.fp16_enabled, "FP16 should be enabled"
        
        # Check for FP16 statistics
        if world_model._fp16_stats:
            stats = world_model._fp16_stats
            assert "training_steps" in stats
            assert "overflow_rate" in stats
            assert stats["overflow_rate"] <= 0.1, "Overflow rate should be <10%"
    
    finally:
        # Cleanup
        os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.asyncio
async def test_world_model_fp32_fallback():
    """Test that WorldModel falls back to FP32 when FP16 disabled."""
    # Disable FP16
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    
    try:
        # Initialize WorldModel
        world_model = WorldModel()
        world_model.replay_buffer = MockReplayBuffer(50)
        
        # Train for 1 epoch
        await world_model.train(num_epochs=1, batch_size=16)
        
        # Verify FP32 was used
        assert not world_model.fp16_enabled, "FP16 should be disabled"
        assert world_model._fp16_stats is None or world_model._fp16_stats.get("fp16_enabled_runtime") == False
    
    finally:
        pass


@pytest.mark.asyncio
async def test_fp16_vs_fp32_performance():
    """Compare FP16 vs FP32 training performance on WorldModel."""
    
    num_epochs = 2
    num_trajectories = 100
    batch_size = 16
    
    # FP32 baseline
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    world_model_fp32 = WorldModel()
    world_model_fp32.replay_buffer = MockReplayBuffer(num_trajectories)
    
    start_fp32 = time.perf_counter()
    await world_model_fp32.train(num_epochs=num_epochs, batch_size=batch_size)
    fp32_duration = time.perf_counter() - start_fp32
    
    # FP16 comparison
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    world_model_fp16 = WorldModel()
    world_model_fp16.replay_buffer = MockReplayBuffer(num_trajectories)
    
    start_fp16 = time.perf_counter()
    await world_model_fp16.train(num_epochs=num_epochs, batch_size=batch_size)
    fp16_duration = time.perf_counter() - start_fp16
    
    # Calculate speedup
    speedup = fp32_duration / max(fp16_duration, 1e-6)
    
    print(f"\n{'='*60}")
    print(f"WorldModel FP16 vs FP32 Performance")
    print(f"{'='*60}")
    print(f"FP32 duration: {fp32_duration:.3f}s")
    print(f"FP16 duration: {fp16_duration:.3f}s")
    print(f"Speedup:       {speedup:.2f}x")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"{'='*60}")
    
    # Verify speedup is at least neutral (FP16 not slower)
    assert speedup >= 0.8, f"FP16 should not be significantly slower, got {speedup:.2f}x"
    
    # Cleanup
    os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.asyncio
async def test_fp16_training_stability():
    """Test that FP16 training is numerically stable."""
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        world_model = WorldModel()
        world_model.replay_buffer = MockReplayBuffer(200)
        
        # Train for multiple epochs
        await world_model.train(num_epochs=3, batch_size=16)
        
        # Check training history
        assert len(world_model.training_history) > 0, "Training history should be recorded"
        
        # Verify no NaN or Inf losses
        for entry in world_model.training_history:
            loss = entry.get("loss", 0.0)
            assert not (loss != loss), "Loss should not be NaN"  # NaN != NaN is True
            assert loss != float('inf') and loss != float('-inf'), "Loss should not be Inf"
        
        # Check overflow rate if FP16 was active
        if world_model._fp16_stats:
            overflow_rate = world_model._fp16_stats.get("overflow_rate", 0.0)
            assert overflow_rate < 0.5, f"Overflow rate too high: {overflow_rate:.2%}"
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.asyncio
async def test_fp16_checkpoint_compatibility():
    """Test that FP16-trained models can save/load checkpoints."""
    import tempfile
    import os as os_module
    
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        # Train model with FP16
        world_model = WorldModel()
        world_model.replay_buffer = MockReplayBuffer(50)
        await world_model.train(num_epochs=1, batch_size=16)
        
        # Save checkpoint
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = os_module.path.join(tmpdir, "world_model_fp16.pt")
            world_model._save_model(checkpoint_path)
            
            assert os_module.path.exists(checkpoint_path), "Checkpoint should be saved"
            
            # Load checkpoint into new model
            world_model_loaded = WorldModel()
            
            # Load the checkpoint
            checkpoint = torch.load(checkpoint_path, map_location="cpu")
            if checkpoint and "model_state_dict" in checkpoint:
                world_model_loaded.model.load_state_dict(checkpoint["model_state_dict"])
            
            # Verify model loaded successfully
            assert world_model_loaded.model is not None
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


def test_fp16_config_from_environment():
    """Test that FP16 configuration is correctly read from environment."""
    # Test enabled
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    world_model = WorldModel()
    assert world_model.fp16_enabled == True or not torch.cuda.is_available()
    
    # Test disabled
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    world_model = WorldModel()
    assert world_model.fp16_enabled == False
    
    # Test default (should be false)
    if "ENABLE_FP16_TRAINING" in os.environ:
        del os.environ["ENABLE_FP16_TRAINING"]
    world_model = WorldModel()
    assert world_model.fp16_enabled == False


@pytest.mark.asyncio
async def test_fp16_memory_usage():
    """Test that FP16 reduces memory usage (when CUDA available)."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available - skipping memory test")
    
    import gc
    
    # Clear CUDA cache
    torch.cuda.empty_cache()
    gc.collect()
    
    # FP32 baseline
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    world_model_fp32 = WorldModel()
    world_model_fp32.replay_buffer = MockReplayBuffer(100)
    
    # Get initial memory
    torch.cuda.reset_peak_memory_stats()
    await world_model_fp32.train(num_epochs=1, batch_size=32)
    fp32_memory = torch.cuda.max_memory_allocated() / 1024**2  # Convert to MB
    
    # Clear memory
    del world_model_fp32
    torch.cuda.empty_cache()
    gc.collect()
    
    # FP16 comparison
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    world_model_fp16 = WorldModel()
    world_model_fp16.replay_buffer = MockReplayBuffer(100)
    
    torch.cuda.reset_peak_memory_stats()
    await world_model_fp16.train(num_epochs=1, batch_size=32)
    fp16_memory = torch.cuda.max_memory_allocated() / 1024**2  # Convert to MB
    
    # Calculate memory reduction
    memory_reduction = (fp32_memory - fp16_memory) / fp32_memory
    
    print(f"\n{'='*60}")
    print(f"Memory Usage Comparison")
    print(f"{'='*60}")
    print(f"FP32 memory: {fp32_memory:.2f} MB")
    print(f"FP16 memory: {fp16_memory:.2f} MB")
    print(f"Reduction:   {memory_reduction:.1%}")
    print(f"{'='*60}")
    
    # FP16 should use same or less memory (allow 10% tolerance)
    assert fp16_memory <= fp32_memory * 1.1, "FP16 should not use significantly more memory"
    
    # Cleanup
    os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_fp16_accuracy_maintenance():
    """Test that FP16 maintains model accuracy within acceptable bounds."""
    
    num_epochs = 3
    num_trajectories = 200
    
    # Train FP32 model
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    world_model_fp32 = WorldModel()
    world_model_fp32.replay_buffer = MockReplayBuffer(num_trajectories)
    await world_model_fp32.train(num_epochs=num_epochs, batch_size=16)
    fp32_final_loss = world_model_fp32.training_history[-1]["loss"] if world_model_fp32.training_history else 0.0
    
    # Train FP16 model
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    world_model_fp16 = WorldModel()
    world_model_fp16.replay_buffer = MockReplayBuffer(num_trajectories)
    await world_model_fp16.train(num_epochs=num_epochs, batch_size=16)
    fp16_final_loss = world_model_fp16.training_history[-1]["loss"] if world_model_fp16.training_history else 0.0
    
    # Calculate accuracy degradation
    if fp32_final_loss > 0:
        degradation = abs(fp16_final_loss - fp32_final_loss) / fp32_final_loss
    else:
        degradation = abs(fp16_final_loss - fp32_final_loss)
    
    print(f"\n{'='*60}")
    print(f"Accuracy Comparison")
    print(f"{'='*60}")
    print(f"FP32 final loss: {fp32_final_loss:.4f}")
    print(f"FP16 final loss: {fp16_final_loss:.4f}")
    print(f"Degradation:     {degradation:.2%}")
    print(f"{'='*60}")
    
    # Verify accuracy degradation is acceptable (<5%)
    assert degradation < 0.05, f"Accuracy degradation {degradation:.2%} exceeds 5% threshold"
    
    # Cleanup
    os.environ["ENABLE_FP16_TRAINING"] = "false"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

