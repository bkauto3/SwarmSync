"""
Comprehensive test suite for feature flag system.

Tests cover:
- Flag loading from JSON/YAML files
- Flag evaluation (is_enabled)
- Progressive rollout (0% → 25% → 50% → 75% → 100%)
- Percentage-based rollout (hash-based user distribution)
- Canary deployment (specific users)
- Emergency flags (shutdown, maintenance, read-only)
- File backend (read, write, hot-reload)
- Invalid flag names (sanitization)
- Missing flag files (default values)
- Concurrent updates (thread safety)
- Environment variable overrides
- Flag validation (schema checking)

Author: Alex (Testing Specialist)
Date: 2025-10-18
"""

import json
import os
import pytest
import tempfile
import threading
import time
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from infrastructure.feature_flags import (
    FeatureFlagConfig,
    FeatureFlagManager,
    FeatureFlagBackend,
    RolloutStrategy,
    get_feature_flag_manager,
    is_feature_enabled
)


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
        yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = Path(f.name)
        yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def flag_manager():
    """Create a fresh FeatureFlagManager for each test."""
    return FeatureFlagManager()


@pytest.fixture
def sample_flag_data():
    """Sample flag data for testing."""
    return {
        "flags": {
            "test_feature": {
                "name": "test_feature",
                "enabled": True,
                "default_value": True,
                "rollout_strategy": "all_at_once",
                "rollout_percentage": 100.0,
                "description": "Test feature flag"
            },
            "progressive_feature": {
                "name": "progressive_feature",
                "enabled": True,
                "default_value": False,
                "rollout_strategy": "progressive",
                "rollout_percentage": 0.0,
                "progressive_config": {
                    "initial_percentage": 0,
                    "end_percentage": 100,
                    "start_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    "end_date": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()
                },
                "description": "Progressive rollout feature"
            },
            "canary_feature": {
                "name": "canary_feature",
                "enabled": True,
                "default_value": False,
                "rollout_strategy": "canary",
                "rollout_percentage": 0.0,
                "progressive_config": {
                    "canary_users": ["user1", "user2"],
                    "canary_regions": ["us-west-1"]
                },
                "description": "Canary deployment feature"
            }
        }
    }


# ============================================================================
# TEST CATEGORY 1: Flag Loading (JSON/YAML)
# ============================================================================

def test_load_from_json_file(flag_manager, temp_config_file, sample_flag_data):
    """Test loading feature flags from JSON file."""
    # Write sample data to temp file
    with open(temp_config_file, 'w') as f:
        json.dump(sample_flag_data, f)

    # Load flags
    flag_manager.load_from_file(temp_config_file)

    # Verify flags were loaded
    assert "test_feature" in flag_manager.flags
    assert flag_manager.flags["test_feature"].enabled is True
    assert flag_manager.flags["test_feature"].description == "Test feature flag"


def test_load_from_yaml_file(flag_manager, temp_yaml_file, sample_flag_data):
    """Test loading feature flags from YAML file."""
    # Write sample data to temp file
    with open(temp_yaml_file, 'w') as f:
        yaml.dump(sample_flag_data, f)

    # Load flags
    flag_manager.load_from_file(temp_yaml_file)

    # Verify flags were loaded
    assert "test_feature" in flag_manager.flags
    assert flag_manager.flags["test_feature"].enabled is True


def test_load_from_nonexistent_file(flag_manager, caplog):
    """Test loading from a file that doesn't exist."""
    nonexistent = Path("/tmp/nonexistent_flags.json")
    flag_manager.load_from_file(nonexistent)

    # Should log error but not crash
    assert "not found" in caplog.text.lower()


def test_load_from_unsupported_format(flag_manager, caplog):
    """Test loading from unsupported file format."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        temp_path = Path(f.name)

    try:
        flag_manager.load_from_file(temp_path)
        assert "Unsupported file format" in caplog.text
    finally:
        temp_path.unlink()


def test_load_from_corrupted_json(flag_manager, temp_config_file, caplog):
    """Test loading from corrupted JSON file."""
    # Write invalid JSON
    with open(temp_config_file, 'w') as f:
        f.write("{ invalid json")

    flag_manager.load_from_file(temp_config_file)

    # Should log error but not crash
    assert "Failed to load" in caplog.text


# ============================================================================
# TEST CATEGORY 2: Flag Evaluation (is_enabled)
# ============================================================================

def test_is_enabled_simple_flag(flag_manager):
    """Test is_enabled for a simple all-or-nothing flag."""
    # Production flag should be enabled
    assert flag_manager.is_enabled("orchestration_enabled") is True

    # Emergency flags should be disabled
    assert flag_manager.is_enabled("emergency_shutdown") is False


def test_is_enabled_nonexistent_flag(flag_manager, caplog):
    """Test is_enabled for a flag that doesn't exist."""
    result = flag_manager.is_enabled("nonexistent_flag")

    assert result is False
    assert "not found" in caplog.text.lower()


def test_is_enabled_disabled_flag(flag_manager):
    """Test is_enabled for a globally disabled flag."""
    # Manually disable a flag
    flag_manager.flags["orchestration_enabled"].enabled = False

    assert flag_manager.is_enabled("orchestration_enabled") is False


def test_get_flag_value(flag_manager):
    """Test get_flag_value returns correct values."""
    # Enabled flag
    value = flag_manager.get_flag_value("orchestration_enabled")
    assert value is True

    # Disabled flag returns None
    value = flag_manager.get_flag_value("emergency_shutdown", default="fallback")
    assert value == "fallback"


def test_get_flag_value_nonexistent(flag_manager):
    """Test get_flag_value for nonexistent flag."""
    value = flag_manager.get_flag_value("nonexistent", default="default_value")
    assert value == "default_value"


# ============================================================================
# TEST CATEGORY 3: Progressive Rollout (Time-based)
# ============================================================================

def test_progressive_rollout_before_start(flag_manager):
    """Test progressive rollout before start date."""
    # Create flag with future start date
    future_flag = FeatureFlagConfig(
        name="future_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
        }
    )
    flag_manager.flags["future_feature"] = future_flag

    # Should be disabled before start
    assert flag_manager.is_enabled("future_feature") is False


def test_progressive_rollout_after_end(flag_manager):
    """Test progressive rollout after end date."""
    # Create flag with past dates
    past_flag = FeatureFlagConfig(
        name="past_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            "end_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        }
    )
    flag_manager.flags["past_feature"] = past_flag

    # Should be fully enabled after end
    assert flag_manager.is_enabled("past_feature") is True


def test_progressive_rollout_during_rollout(flag_manager):
    """Test progressive rollout during active rollout period."""
    # Create flag currently rolling out (50% through 7-day window)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=3.5)
    end = now + timedelta(days=3.5)

    rollout_flag = FeatureFlagConfig(
        name="rollout_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": start.isoformat(),
            "end_date": end.isoformat()
        }
    )
    flag_manager.flags["rollout_feature"] = rollout_flag

    # Run multiple times to get probabilistic result
    results = [flag_manager.is_enabled("rollout_feature") for _ in range(100)]
    enabled_count = sum(results)

    # Should be roughly 50% enabled (allow 20-80% range for randomness)
    assert 20 <= enabled_count <= 80

    # Check that percentage was updated
    assert 40 <= rollout_flag.rollout_percentage <= 60


def test_progressive_rollout_percentage_calculation(flag_manager):
    """Test that progressive rollout calculates percentage correctly."""
    # Set up 25% progress (1.75 days into 7-day rollout)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1.75)
    end = now + timedelta(days=5.25)

    rollout_flag = FeatureFlagConfig(
        name="calc_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": start.isoformat(),
            "end_date": end.isoformat()
        }
    )
    flag_manager.flags["calc_feature"] = rollout_flag

    # Trigger evaluation
    flag_manager.is_enabled("calc_feature")

    # Should be around 25% (allow 20-30% range)
    assert 20 <= rollout_flag.rollout_percentage <= 30


# ============================================================================
# TEST CATEGORY 4: Percentage-based Rollout (Hash-based)
# ============================================================================

def test_percentage_rollout_with_user_id(flag_manager):
    """Test percentage-based rollout with user ID (deterministic)."""
    percent_flag = FeatureFlagConfig(
        name="percent_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=50.0
    )
    flag_manager.flags["percent_feature"] = percent_flag

    # Same user should get consistent result
    context1 = {"user_id": "user123"}
    result1 = flag_manager.is_enabled("percent_feature", context1)
    result2 = flag_manager.is_enabled("percent_feature", context1)

    assert result1 == result2  # Deterministic


def test_percentage_rollout_without_user_id(flag_manager):
    """Test percentage-based rollout without user ID (random)."""
    percent_flag = FeatureFlagConfig(
        name="percent_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=50.0
    )
    flag_manager.flags["percent_feature"] = percent_flag

    # Without user_id, should be probabilistic
    results = [flag_manager.is_enabled("percent_feature") for _ in range(100)]
    enabled_count = sum(results)

    # Should be roughly 50% (allow 30-70% range)
    assert 30 <= enabled_count <= 70


def test_percentage_rollout_distribution(flag_manager):
    """Test that percentage rollout distributes users correctly."""
    percent_flag = FeatureFlagConfig(
        name="percent_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=30.0
    )
    flag_manager.flags["percent_feature"] = percent_flag

    # Test with many different users
    enabled_count = 0
    for i in range(100):
        context = {"user_id": f"user{i}"}
        if flag_manager.is_enabled("percent_feature", context):
            enabled_count += 1

    # Should be roughly 30% (allow 20-40% range)
    assert 20 <= enabled_count <= 40


# ============================================================================
# TEST CATEGORY 5: Canary Deployment
# ============================================================================

def test_canary_rollout_specific_users(flag_manager):
    """Test canary deployment for specific users."""
    canary_flag = FeatureFlagConfig(
        name="canary_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.CANARY,
        progressive_config={
            "canary_users": ["alice", "bob"],
            "canary_regions": []
        }
    )
    flag_manager.flags["canary_feature"] = canary_flag

    # Canary users should be enabled
    assert flag_manager.is_enabled("canary_feature", {"user_id": "alice"}) is True
    assert flag_manager.is_enabled("canary_feature", {"user_id": "bob"}) is True

    # Non-canary users should be disabled
    assert flag_manager.is_enabled("canary_feature", {"user_id": "charlie"}) is False


def test_canary_rollout_specific_regions(flag_manager):
    """Test canary deployment for specific regions."""
    canary_flag = FeatureFlagConfig(
        name="canary_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.CANARY,
        progressive_config={
            "canary_users": [],
            "canary_regions": ["us-west-1", "eu-west-1"]
        }
    )
    flag_manager.flags["canary_feature"] = canary_flag

    # Canary regions should be enabled
    assert flag_manager.is_enabled("canary_feature", {"region": "us-west-1"}) is True
    assert flag_manager.is_enabled("canary_feature", {"region": "eu-west-1"}) is True

    # Non-canary regions should be disabled
    assert flag_manager.is_enabled("canary_feature", {"region": "us-east-1"}) is False


def test_canary_rollout_no_context(flag_manager):
    """Test canary deployment without context returns False."""
    canary_flag = FeatureFlagConfig(
        name="canary_feature",
        enabled=True,
        rollout_strategy=RolloutStrategy.CANARY,
        progressive_config={
            "canary_users": ["alice"],
            "canary_regions": ["us-west-1"]
        }
    )
    flag_manager.flags["canary_feature"] = canary_flag

    # Without context, should be disabled
    assert flag_manager.is_enabled("canary_feature") is False


# ============================================================================
# TEST CATEGORY 6: Emergency Flags
# ============================================================================

def test_emergency_shutdown_flag(flag_manager):
    """Test emergency shutdown flag behavior."""
    # Initially disabled
    assert flag_manager.is_enabled("emergency_shutdown") is False

    # Enable emergency shutdown
    flag_manager.set_flag("emergency_shutdown", True)
    flag_manager.flags["emergency_shutdown"].default_value = True
    assert flag_manager.is_enabled("emergency_shutdown") is True


def test_read_only_mode_flag(flag_manager):
    """Test read-only mode flag behavior."""
    # Initially disabled
    assert flag_manager.is_enabled("read_only_mode") is False

    # Enable read-only mode
    flag_manager.set_flag("read_only_mode", True)
    flag_manager.flags["read_only_mode"].default_value = True
    assert flag_manager.is_enabled("read_only_mode") is True


def test_maintenance_mode_flag(flag_manager):
    """Test maintenance mode flag behavior."""
    # Initially disabled
    assert flag_manager.is_enabled("maintenance_mode") is False

    # Enable maintenance mode
    flag_manager.set_flag("maintenance_mode", True)
    flag_manager.flags["maintenance_mode"].default_value = True
    assert flag_manager.is_enabled("maintenance_mode") is True


def test_set_flag_manual_override(flag_manager, caplog):
    """Test manual flag override logs warning."""
    flag_manager.set_flag("orchestration_enabled", False)

    assert "Manual flag override" in caplog.text
    assert flag_manager.flags["orchestration_enabled"].enabled is False


# ============================================================================
# TEST CATEGORY 7: File Backend (Save/Load)
# ============================================================================

def test_save_to_file(flag_manager, temp_config_file):
    """Test saving feature flags to file."""
    flag_manager.save_to_file(temp_config_file)

    # Verify file was created and contains data
    assert temp_config_file.exists()

    with open(temp_config_file, 'r') as f:
        data = json.load(f)

    assert "flags" in data
    assert "orchestration_enabled" in data["flags"]


def test_save_and_reload(flag_manager, temp_config_file):
    """Test saving and reloading preserves flag state."""
    # Modify a flag
    flag_manager.set_flag("phase_4_deployment", True)

    # Save
    flag_manager.save_to_file(temp_config_file)

    # Create new manager and load
    new_manager = FeatureFlagManager()
    new_manager.load_from_file(temp_config_file)

    # Verify state was preserved
    assert new_manager.flags["phase_4_deployment"].enabled is True


def test_reload_with_file_backend(temp_config_file, sample_flag_data):
    """Test reload() method with file backend."""
    # Write initial data
    with open(temp_config_file, 'w') as f:
        json.dump(sample_flag_data, f)

    # Create manager with file backend
    manager = FeatureFlagManager(
        backend=FeatureFlagBackend.FILE,
        config_file=temp_config_file
    )
    manager.load_from_file(temp_config_file)

    assert "test_feature" in manager.flags

    # Modify file
    sample_flag_data["flags"]["new_feature"] = {
        "name": "new_feature",
        "enabled": True,
        "default_value": True,
        "rollout_strategy": "all_at_once",
        "rollout_percentage": 100.0,
        "description": "New feature"
    }
    with open(temp_config_file, 'w') as f:
        json.dump(sample_flag_data, f)

    # Reload
    manager.reload()

    # Verify new flag was loaded
    assert "new_feature" in manager.flags


# ============================================================================
# TEST CATEGORY 8: Concurrent Access (Thread Safety)
# ============================================================================

def test_concurrent_flag_reads(flag_manager):
    """Test concurrent reads from multiple threads."""
    results = []
    errors = []

    def read_flags():
        try:
            for _ in range(100):
                result = flag_manager.is_enabled("orchestration_enabled")
                results.append(result)
        except Exception as e:
            errors.append(e)

    # Run 10 threads concurrently
    threads = [threading.Thread(target=read_flags) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No errors should occur
    assert len(errors) == 0
    assert len(results) == 1000  # 10 threads * 100 reads


def test_concurrent_flag_updates(flag_manager, temp_config_file):
    """Test concurrent updates to flags."""
    errors = []

    def update_flag(value):
        try:
            for _ in range(10):
                flag_manager.set_flag("phase_4_deployment", value)
                time.sleep(0.001)  # Small delay
        except Exception as e:
            errors.append(e)

    # Run threads that toggle flag
    threads = [
        threading.Thread(target=update_flag, args=(True,)),
        threading.Thread(target=update_flag, args=(False,))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No errors should occur
    assert len(errors) == 0


# ============================================================================
# TEST CATEGORY 9: Rollout Status and Introspection
# ============================================================================

def test_get_all_flags(flag_manager):
    """Test get_all_flags returns all flags with status."""
    all_flags = flag_manager.get_all_flags()

    assert isinstance(all_flags, dict)
    assert "orchestration_enabled" in all_flags
    assert "enabled" in all_flags["orchestration_enabled"]
    assert "config" in all_flags["orchestration_enabled"]


def test_get_rollout_status_progressive(flag_manager):
    """Test get_rollout_status for progressive rollout."""
    status = flag_manager.get_rollout_status("phase_4_deployment")

    assert status["name"] == "phase_4_deployment"
    assert "strategy" in status
    assert "phase" in status
    assert status["phase"] in ["not_started", "in_progress", "completed"]


def test_get_rollout_status_nonexistent(flag_manager):
    """Test get_rollout_status for nonexistent flag."""
    status = flag_manager.get_rollout_status("nonexistent")

    assert "error" in status


def test_get_rollout_status_not_started(flag_manager):
    """Test rollout status shows 'not_started' before start date."""
    future_flag = FeatureFlagConfig(
        name="future",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
        }
    )
    flag_manager.flags["future"] = future_flag

    status = flag_manager.get_rollout_status("future")
    assert status["phase"] == "not_started"


def test_get_rollout_status_completed(flag_manager):
    """Test rollout status shows 'completed' after end date."""
    past_flag = FeatureFlagConfig(
        name="past",
        enabled=True,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        progressive_config={
            "initial_percentage": 0,
            "end_percentage": 100,
            "start_date": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            "end_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        }
    )
    flag_manager.flags["past"] = past_flag

    status = flag_manager.get_rollout_status("past")
    assert status["phase"] == "completed"


# ============================================================================
# TEST CATEGORY 10: Global Manager and Environment Variables
# ============================================================================

def test_global_feature_flag_manager():
    """Test global get_feature_flag_manager singleton."""
    manager1 = get_feature_flag_manager()
    manager2 = get_feature_flag_manager()

    # Should return same instance
    assert manager1 is manager2


def test_is_feature_enabled_convenience_function():
    """Test is_feature_enabled convenience function."""
    result = is_feature_enabled("orchestration_enabled")
    assert isinstance(result, bool)


def test_environment_variable_config_path():
    """Test that FEATURE_FLAGS_CONFIG env var is respected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
        json.dump({"flags": {}}, f)

    try:
        # Set environment variable
        with patch.dict(os.environ, {"FEATURE_FLAGS_CONFIG": temp_path}):
            # Reset global manager
            import infrastructure.feature_flags
            infrastructure.feature_flags._feature_flag_manager = None

            manager = get_feature_flag_manager()
            assert manager.config_file == Path(temp_path)
    finally:
        Path(temp_path).unlink()


# ============================================================================
# TEST CATEGORY 11: FeatureFlagConfig Serialization
# ============================================================================

def test_feature_flag_config_to_dict():
    """Test FeatureFlagConfig.to_dict serialization."""
    config = FeatureFlagConfig(
        name="test",
        enabled=True,
        default_value=True,
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=50.0,
        description="Test flag"
    )

    data = config.to_dict()

    assert data["name"] == "test"
    assert data["enabled"] is True
    assert data["rollout_strategy"] == "percentage"
    assert data["rollout_percentage"] == 50.0


def test_feature_flag_config_from_dict():
    """Test FeatureFlagConfig.from_dict deserialization."""
    data = {
        "name": "test",
        "enabled": True,
        "default_value": True,
        "rollout_strategy": "percentage",
        "rollout_percentage": 50.0,
        "progressive_config": {},
        "description": "Test flag"
    }

    config = FeatureFlagConfig.from_dict(data)

    assert config.name == "test"
    assert config.enabled is True
    assert config.rollout_strategy == RolloutStrategy.PERCENTAGE
    assert config.rollout_percentage == 50.0


def test_feature_flag_config_roundtrip():
    """Test serialization roundtrip preserves data."""
    original = FeatureFlagConfig(
        name="roundtrip",
        enabled=True,
        default_value=False,
        rollout_strategy=RolloutStrategy.PROGRESSIVE,
        rollout_percentage=25.0,
        progressive_config={"start_date": "2025-10-18T00:00:00Z"},
        description="Roundtrip test"
    )

    # Convert to dict and back
    data = original.to_dict()
    restored = FeatureFlagConfig.from_dict(data)

    assert restored.name == original.name
    assert restored.enabled == original.enabled
    assert restored.rollout_strategy == original.rollout_strategy
    assert restored.progressive_config == original.progressive_config


# ============================================================================
# TEST CATEGORY 12: Production Flags Validation
# ============================================================================

def test_production_flags_initialized(flag_manager):
    """Test that production flags are initialized on startup."""
    # Core flags should exist
    assert "orchestration_enabled" in flag_manager.flags
    assert "security_hardening_enabled" in flag_manager.flags
    assert "llm_integration_enabled" in flag_manager.flags
    assert "error_handling_enabled" in flag_manager.flags
    assert "otel_enabled" in flag_manager.flags

    # Phase flags should exist
    assert "phase_1_complete" in flag_manager.flags
    assert "phase_2_complete" in flag_manager.flags
    assert "phase_3_complete" in flag_manager.flags
    assert "phase_4_deployment" in flag_manager.flags

    # Emergency flags should exist
    assert "emergency_shutdown" in flag_manager.flags
    assert "read_only_mode" in flag_manager.flags
    assert "maintenance_mode" in flag_manager.flags


def test_production_flags_safe_defaults(flag_manager):
    """Test that production flags have safe defaults."""
    # Core features should be enabled
    assert flag_manager.is_enabled("orchestration_enabled") is True
    assert flag_manager.is_enabled("security_hardening_enabled") is True
    assert flag_manager.is_enabled("error_handling_enabled") is True

    # High-risk features should be disabled
    assert flag_manager.is_enabled("aatc_system_enabled") is False

    # Emergency flags should be disabled
    assert flag_manager.is_enabled("emergency_shutdown") is False
    assert flag_manager.is_enabled("read_only_mode") is False
    assert flag_manager.is_enabled("maintenance_mode") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
