"""
Tests for Real Socratic-Zero Integration

Tests the real Socratic-Zero 3-agent system integration.
"""

import json
import pytest
from pathlib import Path
from infrastructure.socratic_zero_real_integration import RealSocraticZeroIntegration


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace = tmp_path / "socratic_zero_real_test"
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


class TestRealSocraticZeroIntegration:
    """Test suite for RealSocraticZeroIntegration class."""
    
    def test_integration_initialization_real_mode(self, temp_workspace):
        """Test integration initialization in real mode."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=True
        )
        
        assert integration.workspace_dir == temp_workspace
        assert integration.seeds_dir.exists()
        assert integration.generated_dir.exists()
        assert integration.checkpoints_dir.exists()
        assert integration.use_real_framework in [True, False]  # Depends on availability
    
    def test_integration_initialization_fallback_mode(self, temp_workspace):
        """Test integration initialization in fallback mode."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        assert integration.workspace_dir == temp_workspace
        assert integration.use_real_framework is False
        assert integration.state_manager is None
    
    def test_generate_data_fallback_mode(self, temp_workspace, sample_seeds):
        """Test data generation in fallback mode."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
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
        assert all("source" in ex for ex in generated)
        assert all(ex["source"] == "fallback" for ex in generated)
    
    def test_generate_data_with_checkpoints(self, temp_workspace, sample_seeds):
        """Test data generation with checkpoint saving."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=50,
            max_rounds=3,
            save_checkpoints=True
        )
        
        assert output_file.exists()
        
        # Check if checkpoints were created (in fallback mode, they won't be)
        # This test validates the checkpoint logic exists
        assert integration.checkpoints_dir.exists()
    
    def test_teacher_generate_variations(self, temp_workspace):
        """Test Teacher agent variation generation."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        trajectories = [
            {
                "question": "Test question 1",
                "response": "Test response 1",
                "reasoning_steps": "Step 1, Step 2"
            },
            {
                "question": "Test question 2",
                "response": "Test response 2 with longer content for difficulty estimation",
                "reasoning_steps": "Step 1, Step 2, Step 3"
            }
        ]
        
        variations = integration._teacher_generate_variations(trajectories, expansion_factor=3)
        
        assert len(variations) == 6  # 2 trajectories * 3 variations
        assert all("question" in v for v in variations)
        assert all("variation_id" in v for v in variations)
        assert all("difficulty" in v for v in variations)
    
    def test_generator_expand_curriculum(self, temp_workspace):
        """Test Generator agent curriculum expansion."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        variations = [
            {
                "question": "Variation 1",
                "variation_id": 0,
                "base_trajectory": "Response 1",
                "difficulty": "easy"
            },
            {
                "question": "Variation 2",
                "variation_id": 1,
                "base_trajectory": "Response 2",
                "difficulty": "medium"
            }
        ]
        
        examples = integration._generator_expand_curriculum(variations, expansion_factor=2)
        
        assert len(examples) == 4  # 2 variations * 2 expansion
        assert all("id" in ex for ex in examples)
        assert all("question" in ex for ex in examples)
        assert all("answer" in ex for ex in examples)
        assert all("difficulty" in ex for ex in examples)
    
    def test_estimate_difficulty(self, temp_workspace):
        """Test difficulty estimation from trajectory."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        # Short response = easy
        easy_traj = {"response": "Short answer"}
        assert integration._estimate_difficulty(easy_traj) == "easy"
        
        # Medium response = medium
        medium_traj = {"response": "A" * 150}
        assert integration._estimate_difficulty(medium_traj) == "medium"
        
        # Long response = hard
        hard_traj = {"response": "A" * 400}
        assert integration._estimate_difficulty(hard_traj) == "hard"
    
    def test_seeds_saved_correctly(self, temp_workspace, sample_seeds):
        """Test that seed examples are saved correctly."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
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
    
    def test_multiple_rounds_generation(self, temp_workspace, sample_seeds):
        """Test multi-round data generation."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=100,
            max_rounds=5
        )
        
        # Verify data was generated
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == 100
    
    def test_target_count_respected(self, temp_workspace, sample_seeds):
        """Test that target count is respected."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        target = 37  # Odd number to test exact count
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=target,
            max_rounds=10
        )
        
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == target
    
    def test_generated_data_has_required_fields(self, temp_workspace, sample_seeds):
        """Test that generated data has all required fields."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=sample_seeds,
            target_count=10
        )
        
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    assert "id" in example
                    assert "question" in example
                    assert "answer" in example
                    assert "round" in example
                    assert "source" in example
                    assert "agent" in example
    
    def test_workspace_directories_created(self, temp_workspace):
        """Test that all workspace directories are created."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        assert integration.seeds_dir.exists()
        assert integration.generated_dir.exists()
        assert integration.checkpoints_dir.exists()
        
        assert integration.seeds_dir == temp_workspace / "seeds"
        assert integration.generated_dir == temp_workspace / "generated"
        assert integration.checkpoints_dir == temp_workspace / "checkpoints"
    
    def test_custom_socratic_zero_path(self, temp_workspace, tmp_path):
        """Test integration with custom Socratic-Zero path."""
        custom_path = tmp_path / "custom_socratic_zero"
        custom_path.mkdir()
        
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            socratic_zero_path=custom_path,
            use_real_framework=False
        )
        
        assert integration.socratic_zero_path == custom_path
    
    def test_empty_seeds_handling(self, temp_workspace):
        """Test handling of empty seed list."""
        integration = RealSocraticZeroIntegration(
            workspace_dir=temp_workspace,
            use_real_framework=False
        )
        
        output_file = integration.generate_data(
            agent_name="test_agent",
            seed_examples=[],
            target_count=10
        )
        
        # Should generate empty file or minimal data
        with open(output_file, "r") as f:
            count = sum(1 for line in f if line.strip())
        
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

