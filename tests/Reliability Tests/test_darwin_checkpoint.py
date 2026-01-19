"""
Test Darwin checkpoint methods
Verifies save_checkpoint, load_checkpoint, and resume_evolution functionality
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path

from agents.darwin_agent import DarwinAgent


class TestDarwinCheckpoint:
    """Test checkpoint functionality in DarwinAgent"""

    def test_save_checkpoint(self):
        """Test saving evolution state to checkpoint"""
        # Create dummy agent code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        try:
            # Initialize Darwin agent with dummy API keys
            darwin = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                max_generations=10,
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Set some evolution state
            darwin.current_generation = 3
            darwin.best_score = 0.75
            darwin.best_version = "gen2_attempt1"
            darwin.archive = ["initial", "gen1_attempt0", "gen2_attempt1"]

            # Save checkpoint
            checkpoint_path = tempfile.mktemp(suffix=".json")
            success = darwin.save_checkpoint(checkpoint_path)

            assert success is True
            assert Path(checkpoint_path).exists()

            # Verify checkpoint content
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)

            assert checkpoint_data["agent_name"] == "test_agent"
            assert checkpoint_data["current_generation"] == 3
            assert checkpoint_data["best_score"] == 0.75
            assert checkpoint_data["best_version"] == "gen2_attempt1"
            assert len(checkpoint_data["archive"]) == 3

            # Cleanup
            Path(checkpoint_path).unlink()

        finally:
            if dummy_code.exists():
                dummy_code.unlink()

    def test_load_checkpoint(self):
        """Test loading evolution state from checkpoint"""
        # Create dummy agent code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        try:
            # Initialize Darwin agent with dummy API keys
            darwin = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Set initial state
            darwin.current_generation = 3
            darwin.best_score = 0.75
            darwin.best_version = "gen2_attempt1"
            darwin.archive = ["initial", "gen1_attempt0", "gen2_attempt1"]

            # Save checkpoint
            checkpoint_path = tempfile.mktemp(suffix=".json")
            darwin.save_checkpoint(checkpoint_path)

            # Create new Darwin agent with dummy API keys
            darwin2 = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Verify initial state is different
            assert darwin2.current_generation == 0
            assert darwin2.best_score == 0.0

            # Load checkpoint
            success = darwin2.load_checkpoint(checkpoint_path)

            assert success is True
            assert darwin2.current_generation == 3
            assert darwin2.best_score == 0.75
            assert darwin2.best_version == "gen2_attempt1"
            assert len(darwin2.archive) == 3

            # Cleanup
            Path(checkpoint_path).unlink()

        finally:
            if dummy_code.exists():
                dummy_code.unlink()

    def test_load_checkpoint_file_not_found(self):
        """Test loading from non-existent checkpoint file"""
        # Create dummy agent code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        try:
            darwin = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Try to load non-existent checkpoint
            success = darwin.load_checkpoint("/tmp/nonexistent_checkpoint.json")

            assert success is False

        finally:
            if dummy_code.exists():
                dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_resume_evolution(self):
        """Test resuming evolution from checkpoint"""
        # Create dummy agent code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        try:
            # Initialize Darwin agent with dummy API keys
            darwin = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                max_generations=10,
                population_size=2,  # Small for fast test
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Set initial state (simulating previous evolution)
            darwin.current_generation = 2
            darwin.best_score = 0.65
            darwin.best_version = "gen1_attempt0"
            darwin.archive = ["initial", "gen1_attempt0"]

            # Save checkpoint
            checkpoint_path = tempfile.mktemp(suffix=".json")
            darwin.save_checkpoint(checkpoint_path)

            # Create new Darwin agent to resume with dummy API keys
            darwin2 = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                max_generations=10,
                population_size=2,
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Resume evolution for 2 more generations
            archive = await darwin2.resume_evolution(
                path=checkpoint_path,
                additional_generations=2
            )

            # Verify state
            assert darwin2.current_generation >= 2  # Should have progressed
            assert archive.agent_name == "test_agent"
            assert archive.total_attempts > 0

            # Cleanup
            Path(checkpoint_path).unlink()

        finally:
            if dummy_code.exists():
                dummy_code.unlink()

    @pytest.mark.asyncio
    async def test_resume_evolution_invalid_checkpoint(self):
        """Test resume_evolution with invalid checkpoint"""
        # Create dummy agent code
        dummy_code = Path(tempfile.mktemp(suffix=".py"))
        dummy_code.write_text("def agent(): return 'initial'")

        try:
            darwin = DarwinAgent(
                agent_name="test_agent",
                initial_code_path=str(dummy_code),
                openai_api_key="sk-dummy-key-for-testing",
                anthropic_api_key="sk-ant-dummy-key",
            )

            # Try to resume from non-existent checkpoint
            with pytest.raises(ValueError, match="Failed to load checkpoint"):
                await darwin.resume_evolution(
                    path="/tmp/nonexistent_checkpoint.json",
                    additional_generations=2
                )

        finally:
            if dummy_code.exists():
                dummy_code.unlink()
