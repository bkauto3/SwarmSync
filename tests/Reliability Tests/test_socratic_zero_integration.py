"""
Tests for Socratic-Zero Integration

Tests the integration wrapper for Socratic-Zero data bootstrapping.
"""

import json
import pytest
from pathlib import Path
from infrastructure.socratic_zero_integration import SocraticZeroIntegration


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace = tmp_path / "socratic_zero_test"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_seeds():
    """Create sample seed examples for testing."""
    return [
        {
            "id": "seed_001",
            "category": "Financial Analysis",
            "topic": "Revenue analysis",
            "question": "Analyze Q3 revenue trends",
            "answer": "Revenue increased 15% YoY",
            "reasoning": "Growth driven by new product launches"
        },
        {
            "id": "seed_002",
            "category": "Market Analysis",
            "topic": "Market size",
            "question": "Estimate TAM for SaaS product",
            "answer": "$5B addressable market",
            "reasoning": "Based on industry reports and competitor analysis"
        }
    ]


class TestSocraticZeroIntegration:
    """Test suite for SocraticZeroIntegration class."""
    
    def test_integration_initialization(self, temp_workspace):
        """Test integration initialization creates workspace directories."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        assert integration.workspace_dir == temp_workspace
        assert integration.seeds_dir.exists()
        assert integration.generated_dir.exists()
        assert integration.seeds_dir == temp_workspace / "seeds"
        assert integration.generated_dir == temp_workspace / "generated"
    
    def test_integration_with_custom_socratic_zero_path(self, temp_workspace, tmp_path):
        """Test integration with custom Socratic-Zero path."""
        custom_path = tmp_path / "custom_socratic_zero"
        custom_path.mkdir()
        
        integration = SocraticZeroIntegration(
            workspace_dir=temp_workspace,
            socratic_zero_path=custom_path
        )
        
        assert integration.socratic_zero_path == custom_path
    
    def test_generate_data_basic(self, temp_workspace, sample_seeds):
        """Test basic data generation."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=20,
            max_rounds=2
        )
        
        assert output_file.exists()
        assert output_file.name == "test_agent_bootstrapped.jsonl"
        
        # Verify generated data
        generated = []
        with open(output_file, "r") as f:
            for line in f:
                generated.append(json.loads(line))
        
        assert len(generated) == 20
        assert all("id" in ex for ex in generated)
        assert all("source" in ex for ex in generated)
        assert all(ex["source"] == "socratic_zero" for ex in generated)
    
    def test_generate_data_with_custom_count(self, temp_workspace, sample_seeds):
        """Test data generation with custom target count."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=50,
            max_rounds=5
        )
        
        # Count generated examples
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == 50
    
    def test_generate_data_saves_seeds(self, temp_workspace, sample_seeds):
        """Test that seed examples are saved to seeds directory."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        seeds_file = integration.seeds_dir / "test_agent_seeds.json"
        assert seeds_file.exists()
        
        with open(seeds_file, "r") as f:
            saved_seeds = json.load(f)
        
        assert len(saved_seeds) == len(sample_seeds)
        assert saved_seeds[0]["id"] == "seed_001"
    
    def test_validate_quality_basic(self, temp_workspace, sample_seeds):
        """Test basic quality validation."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=100
        )
        
        metrics = integration.validate_quality(output_file, sample_size=50)
        
        assert "total_examples" in metrics
        assert "sample_size" in metrics
        assert "quality_score" in metrics
        assert metrics["total_examples"] == 100
        assert metrics["sample_size"] == 50
    
    def test_validate_quality_with_small_sample(self, temp_workspace, sample_seeds):
        """Test quality validation with small sample size."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=20
        )
        
        metrics = integration.validate_quality(output_file, sample_size=10)
        
        assert metrics["sample_size"] == 10
        assert metrics["total_examples"] == 20
    
    def test_workspace_creation_idempotent(self, temp_workspace):
        """Test that workspace creation is idempotent."""
        integration1 = SocraticZeroIntegration(workspace_dir=temp_workspace)
        integration2 = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        assert integration1.workspace_dir == integration2.workspace_dir
        assert integration1.seeds_dir.exists()
        assert integration2.seeds_dir.exists()
    
    def test_generate_data_with_empty_seeds(self, temp_workspace):
        """Test data generation with empty seed list."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=[],
            target_count=10
        )
        
        # Should generate empty file or minimal data
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == 0
    
    def test_generate_data_preserves_agent_name(self, temp_workspace, sample_seeds):
        """Test that agent name is preserved in generated data."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="analyst_agent",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    assert example["agent"] == "analyst_agent"
    
    def test_generate_data_includes_round_info(self, temp_workspace, sample_seeds):
        """Test that generated data includes round information."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=20,
            max_rounds=2
        )
        
        rounds_found = set()
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    rounds_found.add(example["round"])
        
        assert len(rounds_found) > 0
        assert all(isinstance(r, int) for r in rounds_found)
    
    def test_generate_data_stops_at_target_count(self, temp_workspace, sample_seeds):
        """Test that generation stops at target count."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=15,
            max_rounds=10  # More rounds than needed
        )
        
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == 15
    
    def test_validate_quality_handles_missing_file(self, temp_workspace):
        """Test quality validation with missing file."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        missing_file = temp_workspace / "missing.jsonl"
        
        with pytest.raises(FileNotFoundError):
            integration.validate_quality(missing_file)
    
    def test_generate_data_creates_valid_jsonl(self, temp_workspace, sample_seeds):
        """Test that generated data is valid JSONL format."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        # Verify each line is valid JSON
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON line: {line}")
    
    def test_multiple_agents_separate_files(self, temp_workspace, sample_seeds):
        """Test that multiple agents generate separate files."""
        integration = SocraticZeroIntegration(workspace_dir=temp_workspace)
        
        output1 = integration.generate_data(
            agent_name="agent1",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        output2 = integration.generate_data(
            agent_name="agent2",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        assert output1 != output2
        assert output1.name == "agent1_bootstrapped.jsonl"
        assert output2.name == "agent2_bootstrapped.jsonl"
        assert output1.exists()
        assert output2.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

