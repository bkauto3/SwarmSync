"""
Tests for Socratic-Zero Fine-Tuning

Tests the fine-tuning integration for Analyst agent.
"""

import json
import pytest
import sys
from pathlib import Path

# Add scripts to path
SCRIPTS_PATH = Path(__file__).parent.parent / "scripts" / "socratic_zero"
sys.path.insert(0, str(SCRIPTS_PATH))

from fine_tune_analyst import AnalystFineTuner


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "models"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_training_data(temp_data_dir):
    """Create sample training data."""
    data_file = temp_data_dir / "analyst_seeds.jsonl"
    
    examples = [
        {
            "id": "train_001",
            "instruction": "Analyze revenue trends",
            "input": "Q3 revenue data",
            "output": "Revenue increased 15% YoY"
        },
        {
            "id": "train_002",
            "instruction": "Estimate market size",
            "input": "SaaS product data",
            "output": "$5B addressable market"
        }
    ]
    
    with open(data_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    
    return data_file


class TestAnalystFineTuner:
    """Test suite for AnalystFineTuner class."""
    
    def test_fine_tuner_initialization(self, temp_data_dir, temp_output_dir):
        """Test fine-tuner initialization."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        assert fine_tuner.data_dir == temp_data_dir
        assert fine_tuner.output_dir == temp_output_dir
        assert fine_tuner.output_dir.exists()
    
    def test_convert_to_alpaca_format(self, temp_data_dir, temp_output_dir, sample_training_data):
        """Test conversion to Alpaca format."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        output_file = temp_output_dir / "alpaca_format.jsonl"
        
        fine_tuner.convert_to_unsloth_format(
            sample_training_data,
            output_file,
            format_type="alpaca"
        )
        
        assert output_file.exists()
        
        # Verify format
        with open(output_file, 'r') as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    assert "instruction" in example
                    assert "input" in example
                    assert "output" in example
    
    def test_convert_to_sharegpt_format(self, temp_data_dir, temp_output_dir, sample_training_data):
        """Test conversion to ShareGPT format."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        output_file = temp_output_dir / "sharegpt_format.jsonl"
        
        fine_tuner.convert_to_unsloth_format(
            sample_training_data,
            output_file,
            format_type="sharegpt"
        )
        
        assert output_file.exists()
        
        # Verify format
        with open(output_file, 'r') as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    assert "conversations" in example
                    assert len(example["conversations"]) >= 2
                    assert example["conversations"][0]["from"] == "human"
                    assert example["conversations"][1]["from"] == "gpt"
    
    def test_fine_tune_baseline_creates_metadata(self, temp_data_dir, temp_output_dir, sample_training_data):
        """Test baseline fine-tuning creates metadata."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        model_output = fine_tuner.fine_tune_baseline(
            baseline_file=sample_training_data,
            epochs=1,
            batch_size=2,
            learning_rate=1e-4
        )
        
        assert model_output.exists()
        
        # Check metadata file
        metadata_file = model_output / "training_metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["epochs"] == 1
        assert metadata["batch_size"] == 2
        assert metadata["learning_rate"] == 1e-4
    
    def test_fine_tune_socratic_zero_creates_metadata(self, temp_data_dir, temp_output_dir):
        """Test Socratic-Zero fine-tuning creates metadata."""
        # Create Socratic-Zero data
        socratic_file = temp_data_dir / "analyst_bootstrap.jsonl"
        examples = [
            {
                "id": "socratic_001",
                "question": "Analyze revenue",
                "answer": "Revenue analysis result"
            }
        ]
        
        with open(socratic_file, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        model_output = fine_tuner.fine_tune_socratic_zero(
            socratic_file=socratic_file,
            epochs=1,
            batch_size=2
        )
        
        assert model_output.exists()
        
        # Check metadata
        metadata_file = model_output / "training_metadata.json"
        assert metadata_file.exists()
    
    def test_conversion_preserves_data_count(self, temp_data_dir, temp_output_dir, sample_training_data):
        """Test that conversion preserves example count."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        # Count original examples
        original_count = 0
        with open(sample_training_data, 'r') as f:
            original_count = sum(1 for line in f if line.strip())
        
        # Convert
        output_file = temp_output_dir / "converted.jsonl"
        fine_tuner.convert_to_unsloth_format(
            sample_training_data,
            output_file,
            format_type="alpaca"
        )
        
        # Count converted examples
        converted_count = 0
        with open(output_file, 'r') as f:
            converted_count = sum(1 for line in f if line.strip())
        
        assert converted_count == original_count
    
    def test_unsloth_availability_detection(self, temp_data_dir, temp_output_dir):
        """Test Unsloth availability detection."""
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir
        )
        
        # Should detect whether Unsloth is available
        assert isinstance(fine_tuner.unsloth_available, bool)
    
    def test_output_directory_creation(self, temp_data_dir, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_models_dir"
        
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=output_dir
        )
        
        assert output_dir.exists()
    
    def test_model_name_configuration(self, temp_data_dir, temp_output_dir):
        """Test custom model name configuration."""
        custom_model = "custom/model-name"
        
        fine_tuner = AnalystFineTuner(
            data_dir=temp_data_dir,
            output_dir=temp_output_dir,
            model_name=custom_model
        )
        
        assert fine_tuner.model_name == custom_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

