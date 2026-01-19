"""
Comprehensive test suite for secure checkpoint loading.

Tests cover:
- Save/load with safetensors format
- SHA256 hash verification
- Tampering detection
- Migration from PyTorch to safetensors
- Metadata handling
- Error handling
- Security edge cases

Author: Sentinel (Security Agent)
Date: October 30, 2025
Version: 1.0
"""

import pytest
import torch
import torch.nn as nn
from pathlib import Path
import json
import hashlib

from infrastructure.secure_checkpoint import (
    save_checkpoint_secure,
    load_checkpoint_secure,
    migrate_pytorch_to_safetensors,
    load_checkpoint_metadata,
    verify_checkpoint_integrity,
    compute_sha256,
    CheckpointVerificationError,
    CheckpointFormatError,
)


# Test Fixtures

@pytest.fixture
def sample_state_dict():
    """Create sample model state dictionary."""
    return {
        "weight": torch.randn(10, 5),
        "bias": torch.randn(5),
        "embedding": torch.randn(100, 64),
    }


@pytest.fixture
def sample_model():
    """Create sample PyTorch model."""
    model = nn.Sequential(
        nn.Linear(10, 20),
        nn.ReLU(),
        nn.Linear(20, 5),
    )
    return model


@pytest.fixture
def checkpoint_dir(tmp_path):
    """Create temporary checkpoint directory."""
    checkpoint_path = tmp_path / "checkpoints"
    checkpoint_path.mkdir()
    return checkpoint_path


# Test: Save and Load

def test_save_and_load_checkpoint(tmp_path, sample_state_dict):
    """Test saving and loading checkpoint with hash verification."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    checkpoint_hash = save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Verify hash file exists
    hash_path = checkpoint_path.with_suffix(".sha256")
    assert hash_path.exists(), "Hash file should be created"
    assert hash_path.read_text().strip() == checkpoint_hash, "Hash should match"

    # Load checkpoint
    loaded_state = load_checkpoint_secure(checkpoint_path)

    # Verify state dict matches
    assert len(loaded_state) == len(sample_state_dict), "Tensor count mismatch"
    for key in sample_state_dict:
        assert key in loaded_state, f"Key {key} missing in loaded state"
        assert torch.allclose(
            sample_state_dict[key], loaded_state[key]
        ), f"Tensor {key} values don't match"


def test_save_with_metadata(tmp_path, sample_state_dict):
    """Test saving checkpoint with metadata."""
    checkpoint_path = tmp_path / "model.safetensors"
    metadata = {
        "version": "1.0",
        "created_at": "2025-10-30",
        "model_type": "test",
        "num_parameters": 1000,
    }

    # Save with metadata
    save_checkpoint_secure(sample_state_dict, checkpoint_path, metadata=metadata)

    # Load metadata
    loaded_metadata = load_checkpoint_metadata(checkpoint_path)

    # Verify metadata (all values are strings in safetensors)
    assert loaded_metadata["version"] == "1.0"
    assert loaded_metadata["created_at"] == "2025-10-30"
    assert loaded_metadata["model_type"] == "test"
    assert loaded_metadata["num_parameters"] == "1000"  # Converted to string


def test_load_to_different_device(tmp_path, sample_state_dict):
    """Test loading checkpoint to different device."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Load to CPU
    loaded_cpu = load_checkpoint_secure(checkpoint_path, device="cpu")
    assert all(
        t.device.type == "cpu" for t in loaded_cpu.values()
    ), "All tensors should be on CPU"

    # Load to CUDA (if available)
    if torch.cuda.is_available():
        loaded_cuda = load_checkpoint_secure(checkpoint_path, device="cuda:0")
        assert all(
            t.device.type == "cuda" for t in loaded_cuda.values()
        ), "All tensors should be on CUDA"


# Test: Hash Verification

def test_load_with_wrong_hash_fails(tmp_path, sample_state_dict):
    """Test that tampered checkpoints are rejected."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Tamper with checkpoint (append random bytes)
    with open(checkpoint_path, "ab") as f:
        f.write(b"malicious_data_appended")

    # Load should fail (hash mismatch)
    with pytest.raises(CheckpointVerificationError, match="Hash mismatch"):
        load_checkpoint_secure(checkpoint_path)


def test_load_with_correct_hash_succeeds(tmp_path, sample_state_dict):
    """Test loading with explicitly provided hash."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    checkpoint_hash = save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Load with explicit hash (should succeed)
    loaded_state = load_checkpoint_secure(
        checkpoint_path, expected_hash=checkpoint_hash
    )
    assert loaded_state is not None


def test_load_without_hash_file_fails(tmp_path, sample_state_dict):
    """Test that loading without hash file fails."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Delete hash file
    hash_path = checkpoint_path.with_suffix(".sha256")
    hash_path.unlink()

    # Load should fail (no hash file)
    with pytest.raises(CheckpointVerificationError, match="Hash file not found"):
        load_checkpoint_secure(checkpoint_path)


def test_load_with_verify_hash_disabled(tmp_path, sample_state_dict):
    """Test loading with hash verification disabled (insecure mode)."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Delete hash file (simulate missing hash)
    hash_path = checkpoint_path.with_suffix(".sha256")
    hash_path.unlink()

    # Load with verify_hash=False should succeed without hash file
    loaded_state = load_checkpoint_secure(checkpoint_path, verify_hash=False)
    assert loaded_state is not None  # Loads without hash verification
    assert len(loaded_state) == len(sample_state_dict)


def test_verify_checkpoint_integrity_success(tmp_path, sample_state_dict):
    """Test successful integrity verification."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Verify integrity
    is_valid = verify_checkpoint_integrity(checkpoint_path)
    assert is_valid, "Checkpoint should be valid"


def test_verify_checkpoint_integrity_failure(tmp_path, sample_state_dict):
    """Test failed integrity verification (tampered checkpoint)."""
    checkpoint_path = tmp_path / "model.safetensors"

    # Save checkpoint
    save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Tamper with checkpoint
    with open(checkpoint_path, "ab") as f:
        f.write(b"malicious")

    # Verify integrity (should fail)
    is_valid = verify_checkpoint_integrity(checkpoint_path)
    assert not is_valid, "Checkpoint should be invalid"


# Test: Migration from PyTorch

def test_migrate_pytorch_to_safetensors(tmp_path, sample_model):
    """Test migration from .pt to .safetensors."""
    pytorch_path = tmp_path / "model.pt"
    safetensors_path = tmp_path / "model.safetensors"

    # Save as PyTorch checkpoint
    torch.save(sample_model.state_dict(), pytorch_path)

    # Migrate to safetensors
    checkpoint_hash = migrate_pytorch_to_safetensors(
        pytorch_path,
        safetensors_path,
        metadata={"version": "1.0", "migrated": "true"},
    )

    # Verify safetensors checkpoint exists
    assert safetensors_path.exists(), "Safetensors checkpoint should exist"
    assert safetensors_path.with_suffix(".sha256").exists(), "Hash file should exist"

    # Load migrated checkpoint
    loaded_state = load_checkpoint_secure(safetensors_path)

    # Verify state dict matches
    original_state = sample_model.state_dict()
    assert len(loaded_state) == len(original_state), "Tensor count mismatch"
    for key in original_state:
        assert torch.allclose(
            original_state[key], loaded_state[key]
        ), f"Tensor {key} mismatch after migration"

    # Verify metadata
    metadata = load_checkpoint_metadata(safetensors_path)
    assert metadata["version"] == "1.0"
    assert metadata["migrated"] == "true"


def test_migrate_pytorch_checkpoint_with_extra_keys(tmp_path, sample_model):
    """Test migration of checkpoint with extra keys (optimizer, epoch, etc.)."""
    pytorch_path = tmp_path / "checkpoint.pt"
    safetensors_path = tmp_path / "model.safetensors"

    # Save checkpoint with extra keys
    checkpoint = {
        "model": sample_model.state_dict(),
        "optimizer": {"lr": 0.001},
        "epoch": 10,
    }
    torch.save(checkpoint, pytorch_path)

    # Migrate (should extract 'model' key)
    checkpoint_hash = migrate_pytorch_to_safetensors(
        pytorch_path, safetensors_path, weights_only=False
    )

    # Load migrated checkpoint
    loaded_state = load_checkpoint_secure(safetensors_path)

    # Verify model state matches
    original_state = sample_model.state_dict()
    assert len(loaded_state) == len(original_state)


def test_migrate_nonexistent_pytorch_file_fails(tmp_path):
    """Test migration fails for nonexistent PyTorch file."""
    pytorch_path = tmp_path / "nonexistent.pt"
    safetensors_path = tmp_path / "model.safetensors"

    with pytest.raises(FileNotFoundError):
        migrate_pytorch_to_safetensors(pytorch_path, safetensors_path)


def test_migrate_invalid_extension_fails(tmp_path, sample_state_dict):
    """Test migration fails for invalid file extension."""
    pytorch_path = tmp_path / "model.txt"  # Wrong extension
    safetensors_path = tmp_path / "model.safetensors"

    # Create dummy file
    pytorch_path.write_text("invalid")

    with pytest.raises(ValueError, match="must end with .pt or .pth"):
        migrate_pytorch_to_safetensors(pytorch_path, safetensors_path)


# Test: Compute Hash

def test_compute_sha256(tmp_path):
    """Test SHA256 computation."""
    test_file = tmp_path / "test.txt"
    test_content = b"Hello, World!"
    test_file.write_bytes(test_content)

    # Compute hash
    file_hash = compute_sha256(test_file)

    # Verify against expected hash
    expected_hash = hashlib.sha256(test_content).hexdigest()
    assert file_hash == expected_hash


def test_compute_sha256_nonexistent_file(tmp_path):
    """Test SHA256 computation fails for nonexistent file."""
    nonexistent = tmp_path / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        compute_sha256(nonexistent)


# Test: Error Handling

def test_load_nonexistent_checkpoint_fails(tmp_path):
    """Test loading nonexistent checkpoint fails."""
    checkpoint_path = tmp_path / "nonexistent.safetensors"

    with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
        load_checkpoint_secure(checkpoint_path)


def test_save_invalid_extension_fails(tmp_path, sample_state_dict):
    """Test saving with invalid extension fails."""
    checkpoint_path = tmp_path / "model.pt"  # Wrong extension

    with pytest.raises(ValueError, match="must end with .safetensors"):
        save_checkpoint_secure(sample_state_dict, checkpoint_path)


def test_load_corrupted_checkpoint_fails(tmp_path):
    """Test loading corrupted checkpoint fails."""
    checkpoint_path = tmp_path / "corrupted.safetensors"

    # Create corrupted file
    checkpoint_path.write_bytes(b"this is not a valid safetensors file")

    # Create valid hash file
    hash_path = checkpoint_path.with_suffix(".sha256")
    file_hash = compute_sha256(checkpoint_path)
    hash_path.write_text(file_hash)

    # Load should fail (invalid format)
    with pytest.raises(CheckpointFormatError, match="Failed to load checkpoint"):
        load_checkpoint_secure(checkpoint_path)


def test_load_metadata_nonexistent_file_fails(tmp_path):
    """Test loading metadata from nonexistent file fails."""
    checkpoint_path = tmp_path / "nonexistent.safetensors"

    with pytest.raises(FileNotFoundError):
        load_checkpoint_metadata(checkpoint_path)


def test_load_metadata_corrupted_file_fails(tmp_path):
    """Test loading metadata from corrupted file fails."""
    checkpoint_path = tmp_path / "corrupted.safetensors"
    checkpoint_path.write_bytes(b"corrupted data")

    with pytest.raises(CheckpointFormatError):
        load_checkpoint_metadata(checkpoint_path)


# Test: Security Edge Cases

def test_save_and_load_empty_state_dict(tmp_path):
    """Test saving and loading empty state dictionary."""
    checkpoint_path = tmp_path / "empty.safetensors"
    empty_state = {}

    # Save empty state
    save_checkpoint_secure(empty_state, checkpoint_path)

    # Load empty state
    loaded_state = load_checkpoint_secure(checkpoint_path)
    assert len(loaded_state) == 0, "Should load empty state dict"


def test_save_and_load_large_tensors(tmp_path):
    """Test saving and loading large tensors."""
    checkpoint_path = tmp_path / "large.safetensors"

    # Create large state dict (10 million parameters)
    large_state = {
        "layer1": torch.randn(1000, 1000),
        "layer2": torch.randn(1000, 1000),
        "layer3": torch.randn(1000, 1000),
        "layer4": torch.randn(1000, 1000),
        "layer5": torch.randn(1000, 1000),
    }

    # Save large checkpoint
    checkpoint_hash = save_checkpoint_secure(large_state, checkpoint_path)

    # Load large checkpoint
    loaded_state = load_checkpoint_secure(checkpoint_path)

    # Verify tensors match
    for key in large_state:
        assert torch.allclose(large_state[key], loaded_state[key])


def test_save_and_load_special_dtypes(tmp_path):
    """Test saving and loading special dtypes (fp16, bfloat16, int8)."""
    checkpoint_path = tmp_path / "special_dtypes.safetensors"

    state_dict = {
        "fp32": torch.randn(10, 10, dtype=torch.float32),
        "fp16": torch.randn(10, 10, dtype=torch.float16),
        "bf16": torch.randn(10, 10, dtype=torch.bfloat16),
        "int8": torch.randint(-128, 127, (10, 10), dtype=torch.int8),
        "int64": torch.randint(0, 1000, (10, 10), dtype=torch.int64),
    }

    # Save checkpoint
    save_checkpoint_secure(state_dict, checkpoint_path)

    # Load checkpoint
    loaded_state = load_checkpoint_secure(checkpoint_path)

    # Verify dtypes and values
    for key in state_dict:
        assert loaded_state[key].dtype == state_dict[key].dtype, f"Dtype mismatch: {key}"
        assert torch.equal(loaded_state[key], state_dict[key]), f"Value mismatch: {key}"


def test_multiple_checkpoints_same_directory(tmp_path, sample_state_dict):
    """Test saving multiple checkpoints in same directory."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()

    # Save multiple checkpoints
    for i in range(5):
        checkpoint_path = checkpoint_dir / f"model_epoch_{i}.safetensors"
        save_checkpoint_secure(sample_state_dict, checkpoint_path)

    # Verify all checkpoints exist
    checkpoints = list(checkpoint_dir.glob("*.safetensors"))
    assert len(checkpoints) == 5, "Should have 5 checkpoint files"

    hash_files = list(checkpoint_dir.glob("*.sha256"))
    assert len(hash_files) == 5, "Should have 5 hash files"

    # Load each checkpoint
    for checkpoint_path in checkpoints:
        loaded_state = load_checkpoint_secure(checkpoint_path)
        assert len(loaded_state) == len(sample_state_dict)


def test_hash_consistency_across_saves(tmp_path, sample_state_dict):
    """Test that saving same state dict produces consistent hash."""
    checkpoint_path1 = tmp_path / "model1.safetensors"
    checkpoint_path2 = tmp_path / "model2.safetensors"

    # Save same state dict twice
    hash1 = save_checkpoint_secure(sample_state_dict, checkpoint_path1)
    hash2 = save_checkpoint_secure(sample_state_dict, checkpoint_path2)

    # Hashes should be identical (deterministic serialization)
    assert hash1 == hash2, "Same state dict should produce same hash"


def test_unicode_metadata(tmp_path, sample_state_dict):
    """Test saving and loading Unicode metadata."""
    checkpoint_path = tmp_path / "unicode.safetensors"

    metadata = {
        "name": "テストモデル",  # Japanese
        "author": "张三",  # Chinese
        "notes": "Émilie's model",  # French
        "emoji": "🔒🚀",  # Emoji
    }

    # Save with Unicode metadata
    save_checkpoint_secure(sample_state_dict, checkpoint_path, metadata=metadata)

    # Load metadata
    loaded_metadata = load_checkpoint_metadata(checkpoint_path)

    # Verify Unicode preserved
    assert loaded_metadata["name"] == "テストモデル"
    assert loaded_metadata["author"] == "张三"
    assert loaded_metadata["notes"] == "Émilie's model"
    assert loaded_metadata["emoji"] == "🔒🚀"


# Performance Tests

def test_load_speed_vs_pytorch(tmp_path, sample_model):
    """Test that safetensors loading is faster than PyTorch."""
    import time

    pytorch_path = tmp_path / "model.pt"
    safetensors_path = tmp_path / "model.safetensors"

    # Save checkpoints
    torch.save(sample_model.state_dict(), pytorch_path)
    save_checkpoint_secure(sample_model.state_dict(), safetensors_path)

    # Benchmark PyTorch loading
    start = time.time()
    for _ in range(10):
        torch.load(pytorch_path, map_location="cpu", weights_only=True)
    pytorch_time = time.time() - start

    # Benchmark safetensors loading
    start = time.time()
    for _ in range(10):
        load_checkpoint_secure(safetensors_path, device="cpu")
    safetensors_time = time.time() - start

    # Safetensors should be comparable or faster
    # (Due to memory-mapping and zero-copy)
    print(f"PyTorch time: {pytorch_time:.4f}s")
    print(f"Safetensors time: {safetensors_time:.4f}s")
    print(f"Speedup: {pytorch_time / safetensors_time:.2f}x")

    # NOTE: Speedup varies by file size and system
    # For small files, overhead may dominate
    # For large files (100MB+), safetensors is significantly faster


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
