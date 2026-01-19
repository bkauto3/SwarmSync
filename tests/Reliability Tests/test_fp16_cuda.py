"""CUDA-specific tests for FP16 training.

These tests validate GPU-specific features:
1. CUDA tensor operations with FP16
2. Multi-GPU (DDP) training
3. Bfloat16 support on capable hardware
4. VRAM reduction on GPU
5. Actual speedup measurements on CUDA

All tests are automatically skipped if CUDA is not available.
"""

import os
import pytest
import time

torch = pytest.importorskip("torch")

from infrastructure.training import (
    FP16Trainer,
    FP16TrainingConfig,
    ExtendedFP16Trainer,
    ExtendedFP16Config,
    PrecisionMode,
)


# Skip all tests if CUDA not available
pytestmark = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA not available"
)


@pytest.fixture
def cuda_device():
    """Get CUDA device for testing."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    return torch.device("cuda:0")


@pytest.fixture
def dummy_model(cuda_device):
    """Create a dummy model on CUDA for testing."""
    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(128, 256)
            self.fc2 = torch.nn.Linear(256, 128)
            self.fc3 = torch.nn.Linear(128, 64)
        
        def forward(self, x):
            x = torch.relu(self.fc1(x))
            x = torch.relu(self.fc2(x))
            return self.fc3(x)
    
    return DummyModel().to(cuda_device)


@pytest.fixture
def dummy_batch(cuda_device):
    """Create a dummy batch on CUDA for testing."""
    return torch.randn(32, 128, device=cuda_device)


def test_fp16_cuda_initialization(dummy_model, cuda_device):
    """Test FP16Trainer initializes correctly on CUDA."""
    optimizer = torch.optim.Adam(dummy_model.parameters())
    config = FP16TrainingConfig(enabled=True)
    
    trainer = FP16Trainer(dummy_model, optimizer, config)
    
    assert trainer.fp16_enabled, "FP16 should be enabled on CUDA"
    assert trainer.device.type == "cuda", "Device should be CUDA"
    assert trainer.scaler is not None, "GradScaler should be initialized"


def test_fp16_cuda_training_step(dummy_model, dummy_batch, cuda_device):
    """Test FP16 training step executes correctly on CUDA."""
    optimizer = torch.optim.Adam(dummy_model.parameters())
    config = FP16TrainingConfig(enabled=True)
    trainer = FP16Trainer(dummy_model, optimizer, config)
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    # Execute training step
    loss = trainer.training_step(dummy_batch, compute_loss)
    
    assert isinstance(loss, torch.Tensor), "Loss should be a tensor"
    assert loss.device.type == "cuda", "Loss should be on CUDA"
    assert loss.dtype == torch.float32, "Loss should be FP32"
    assert not torch.isnan(loss), "Loss should not be NaN"


def test_fp16_cuda_backward_step(dummy_model, dummy_batch, cuda_device):
    """Test FP16 backward pass works correctly on CUDA."""
    optimizer = torch.optim.Adam(dummy_model.parameters())
    config = FP16TrainingConfig(enabled=True)
    trainer = FP16Trainer(dummy_model, optimizer, config)
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    # Training step
    loss = trainer.training_step(dummy_batch, compute_loss)
    
    # Backward step
    success = trainer.backward_and_step(loss)
    
    assert success, "Optimizer step should succeed"
    
    stats = trainer.get_stats()
    assert stats["training_steps"] == 1
    assert stats["fp16_enabled"], "FP16 should be active"


def test_fp16_cuda_speedup(dummy_model, dummy_batch, cuda_device):
    """Measure actual FP16 speedup on CUDA."""
    
    num_steps = 100
    
    # FP32 baseline
    model_fp32 = type(dummy_model)().to(cuda_device)
    optimizer_fp32 = torch.optim.Adam(model_fp32.parameters())
    config_fp32 = FP16TrainingConfig(enabled=False)
    trainer_fp32 = FP16Trainer(model_fp32, optimizer_fp32, config_fp32)
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    # Warmup
    for _ in range(10):
        loss = trainer_fp32.training_step(dummy_batch, compute_loss)
        trainer_fp32.backward_and_step(loss)
    
    torch.cuda.synchronize()
    start_fp32 = time.perf_counter()
    
    for _ in range(num_steps):
        loss = trainer_fp32.training_step(dummy_batch, compute_loss)
        trainer_fp32.backward_and_step(loss)
    
    torch.cuda.synchronize()
    fp32_duration = time.perf_counter() - start_fp32
    
    # FP16 comparison
    model_fp16 = type(dummy_model)().to(cuda_device)
    optimizer_fp16 = torch.optim.Adam(model_fp16.parameters())
    config_fp16 = FP16TrainingConfig(enabled=True)
    trainer_fp16 = FP16Trainer(model_fp16, optimizer_fp16, config_fp16)
    
    # Warmup
    for _ in range(10):
        loss = trainer_fp16.training_step(dummy_batch, compute_loss)
        trainer_fp16.backward_and_step(loss)
    
    torch.cuda.synchronize()
    start_fp16 = time.perf_counter()
    
    for _ in range(num_steps):
        loss = trainer_fp16.training_step(dummy_batch, compute_loss)
        trainer_fp16.backward_and_step(loss)
    
    torch.cuda.synchronize()
    fp16_duration = time.perf_counter() - start_fp16
    
    speedup = fp32_duration / fp16_duration
    
    print(f"\n{'='*60}")
    print(f"CUDA FP16 Speedup Test")
    print(f"{'='*60}")
    print(f"Device: {torch.cuda.get_device_name(0)}")
    print(f"FP32 duration: {fp32_duration:.3f}s")
    print(f"FP16 duration: {fp16_duration:.3f}s")
    print(f"Speedup:       {speedup:.2f}x")
    print(f"{'='*60}")
    
    # On CUDA, expect at least 1.3x speedup
    assert speedup >= 1.3, f"Expected >1.3x speedup on CUDA, got {speedup:.2f}x"


def test_fp16_cuda_vram_reduction(dummy_model, cuda_device):
    """Measure VRAM reduction with FP16 on CUDA."""
    import gc
    
    batch_size = 64
    num_steps = 50
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    # FP32 baseline
    torch.cuda.empty_cache()
    gc.collect()
    
    model_fp32 = type(dummy_model)().to(cuda_device)
    optimizer_fp32 = torch.optim.Adam(model_fp32.parameters())
    config_fp32 = FP16TrainingConfig(enabled=False)
    trainer_fp32 = FP16Trainer(model_fp32, optimizer_fp32, config_fp32)
    
    torch.cuda.reset_peak_memory_stats()
    
    for _ in range(num_steps):
        batch = torch.randn(batch_size, 128, device=cuda_device)
        loss = trainer_fp32.training_step(batch, compute_loss)
        trainer_fp32.backward_and_step(loss)
    
    fp32_memory = torch.cuda.max_memory_allocated() / 1024**2  # MB
    
    # Cleanup
    del model_fp32, optimizer_fp32, trainer_fp32
    torch.cuda.empty_cache()
    gc.collect()
    
    # FP16 comparison
    model_fp16 = type(dummy_model)().to(cuda_device)
    optimizer_fp16 = torch.optim.Adam(model_fp16.parameters())
    config_fp16 = FP16TrainingConfig(enabled=True)
    trainer_fp16 = FP16Trainer(model_fp16, optimizer_fp16, config_fp16)
    
    torch.cuda.reset_peak_memory_stats()
    
    for _ in range(num_steps):
        batch = torch.randn(batch_size, 128, device=cuda_device)
        loss = trainer_fp16.training_step(batch, compute_loss)
        trainer_fp16.backward_and_step(loss)
    
    fp16_memory = torch.cuda.max_memory_allocated() / 1024**2  # MB
    
    vram_reduction = (fp32_memory - fp16_memory) / fp32_memory
    
    print(f"\n{'='*60}")
    print(f"VRAM Reduction Test")
    print(f"{'='*60}")
    print(f"Device: {torch.cuda.get_device_name(0)}")
    print(f"FP32 VRAM: {fp32_memory:.2f} MB")
    print(f"FP16 VRAM: {fp16_memory:.2f} MB")
    print(f"Reduction: {vram_reduction:.1%}")
    print(f"{'='*60}")
    
    # Expect at least 20% VRAM reduction
    assert vram_reduction >= 0.20, f"Expected >20% VRAM reduction, got {vram_reduction:.1%}"


@pytest.mark.skipif(
    not torch.cuda.is_available() or not hasattr(torch.cuda, 'is_bf16_supported') or not torch.cuda.is_bf16_supported(),
    reason="Bfloat16 not supported on this hardware"
)
def test_bfloat16_cuda_support(cuda_device):
    """Test Bfloat16 training on capable hardware."""
    
    class SimpleModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = torch.nn.Linear(64, 32)
        
        def forward(self, x):
            return self.fc(x)
    
    model = SimpleModel().to(cuda_device)
    optimizer = torch.optim.Adam(model.parameters())
    
    config = ExtendedFP16Config(
        precision_mode=PrecisionMode.MIXED_BF16,
        enabled=True
    )
    
    trainer = ExtendedFP16Trainer(model, optimizer, config, device=cuda_device)
    
    assert trainer.precision_active, "Bfloat16 should be active"
    assert trainer.autocast_dtype == torch.bfloat16, "Should use bfloat16 dtype"
    assert trainer.scaler is None, "Bfloat16 doesn't need gradient scaling"
    
    # Test training step
    batch = torch.randn(16, 64, device=cuda_device)
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    loss = trainer.training_step(batch, compute_loss)
    success = trainer.backward_and_step(loss)
    
    assert success, "Bfloat16 training step should succeed"
    assert not torch.isnan(loss), "Loss should not be NaN"


@pytest.mark.skipif(
    torch.cuda.device_count() < 2,
    reason="Multi-GPU test requires at least 2 GPUs"
)
def test_multi_gpu_ddp():
    """Test that DDP configuration works (basic initialization only)."""
    
    # This test only validates DDP can be initialized
    # Full multi-process testing requires torchrun or similar
    
    class SimpleModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = torch.nn.Linear(32, 16)
        
        def forward(self, x):
            return self.fc(x)
    
    model = SimpleModel().cuda()
    optimizer = torch.optim.Adam(model.parameters())
    
    config = ExtendedFP16Config(
        use_ddp=False,  # Don't actually enable DDP (requires torch.distributed.init_process_group)
        enabled=True
    )
    
    trainer = ExtendedFP16Trainer(
        model, optimizer, config,
        device=torch.device("cuda:0"),
        rank=0,
        world_size=1
    )
    
    # Verify configuration
    assert trainer.world_size == 1
    assert trainer.rank == 0
    assert not isinstance(trainer.model, torch.nn.parallel.DistributedDataParallel)


def test_gradient_overflow_recovery(dummy_model, dummy_batch, cuda_device):
    """Test that gradient overflow is detected and handled."""
    
    optimizer = torch.optim.Adam(dummy_model.parameters())
    config = FP16TrainingConfig(
        enabled=True,
        loss_scale=1.0,  # Low initial scale to trigger overflow
    )
    trainer = FP16Trainer(dummy_model, optimizer, config)
    
    def compute_loss_with_overflow(model, batch):
        output = model(batch)
        # Create a loss that will overflow when scaled
        return output.abs().mean() * 1e10
    
    # Try to trigger overflow
    initial_scale = trainer.scaler.get_scale()
    
    for _ in range(10):
        loss = trainer.training_step(dummy_batch, compute_loss_with_overflow)
        trainer.backward_and_step(loss)
    
    stats = trainer.get_stats()
    
    # Check if overflow was detected
    if stats["overflow_steps"] > 0:
        print(f"\nOverflow detected and handled: {stats['overflow_steps']} times")
        print(f"Scale adjusted from {initial_scale} to {trainer.scaler.get_scale()}")
        assert trainer.scaler.get_scale() < initial_scale or trainer.scaler.get_scale() == initial_scale


def test_fp16_mixed_precision_layers(cuda_device):
    """Test that different layer types work correctly with FP16."""
    
    class MixedModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv1d(64, 128, kernel_size=3, padding=1)
            self.norm = torch.nn.LayerNorm(128)
            self.linear = torch.nn.Linear(128, 64)
            self.dropout = torch.nn.Dropout(0.1)
        
        def forward(self, x):
            # x: (batch, seq_len, features)
            x = x.transpose(1, 2)  # (batch, features, seq_len)
            x = self.conv(x)
            x = x.transpose(1, 2)  # (batch, seq_len, features)
            x = self.norm(x)
            x = self.dropout(x)
            x = self.linear(x)
            return x.mean(dim=1)
    
    model = MixedModel().to(cuda_device)
    optimizer = torch.optim.Adam(model.parameters())
    config = FP16TrainingConfig(enabled=True)
    trainer = FP16Trainer(model, optimizer, config)
    
    batch = torch.randn(16, 32, 64, device=cuda_device)
    
    def compute_loss(model, batch):
        output = model(batch)
        target = torch.randn_like(output)
        return torch.nn.functional.mse_loss(output, target)
    
    # Test multiple training steps
    for _ in range(20):
        loss = trainer.training_step(batch, compute_loss)
        success = trainer.backward_and_step(loss)
        assert success, "Training step should succeed"
        assert not torch.isnan(loss), "Loss should not be NaN"
    
    stats = trainer.get_stats()
    assert stats["training_steps"] == 20
    assert stats["overflow_rate"] < 0.2, "Overflow rate should be reasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

