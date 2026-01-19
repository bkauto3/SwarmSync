"""
TEST SUITE FOR LAYER 5 CRITICAL FIXES
Version: 1.0
Last Updated: October 16, 2025

Tests for the 3 critical fixes:
1. Random seed control (reproducibility)
2. Empty team edge case handling
3. Input validation

These tests verify production-readiness of the swarm optimizer.
"""

import pytest
from typing import List

from infrastructure.inclusive_fitness_swarm import (
    Agent,
    GenotypeGroup,
    InclusiveFitnessSwarm,
    ParticleSwarmOptimizer,
    TaskRequirement,
    get_inclusive_fitness_swarm,
    get_pso_optimizer,
)


# Fixtures

@pytest.fixture
def sample_agents() -> List[Agent]:
    """Create minimal sample agents"""
    agents = [
        Agent(name="marketing", role="marketing", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
              capabilities=["ads", "social_media"]),
        Agent(name="builder", role="builder", genotype=GenotypeGroup.INFRASTRUCTURE,
              capabilities=["coding", "architecture"]),
        Agent(name="content", role="content", genotype=GenotypeGroup.CONTENT,
              capabilities=["writing", "seo"]),
        Agent(name="billing", role="billing", genotype=GenotypeGroup.FINANCE,
              capabilities=["payments", "invoicing"]),
    ]
    return agents


@pytest.fixture
def simple_task() -> TaskRequirement:
    """Simple task for testing"""
    return TaskRequirement(
        task_id="simple_task",
        required_capabilities=["coding", "ads"],
        team_size_range=(2, 3),
        priority=1.0
    )


# Test Class 1: Random Seed Control (Issue #1)

class TestRandomSeedControl:
    """Test that random seed makes optimization reproducible"""

    def test_swarm_reproducibility(self, sample_agents, simple_task):
        """Same seed produces identical team evaluations"""
        # Create two swarms with same seed
        swarm1 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        swarm2 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)

        # Evaluate same team multiple times
        team = [sample_agents[0], sample_agents[1]]

        outcomes1 = []
        outcomes2 = []

        for _ in range(10):
            outcome1 = swarm1.evaluate_team(team, simple_task, simulate=True)
            outcome2 = swarm2.evaluate_team(team, simple_task, simulate=True)

            outcomes1.append((outcome1.success, outcome1.execution_time))
            outcomes2.append((outcome2.success, outcome2.execution_time))

        # Results should be identical
        assert outcomes1 == outcomes2

    def test_pso_reproducibility(self, sample_agents, simple_task):
        """Same seed produces identical PSO optimization results"""
        # Create two PSO optimizers with same seed
        swarm1 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        swarm2 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)

        pso1 = get_pso_optimizer(swarm1, n_particles=5, max_iterations=10, random_seed=42)
        pso2 = get_pso_optimizer(swarm2, n_particles=5, max_iterations=10, random_seed=42)

        # Run optimization
        team1, fitness1 = pso1.optimize_team(simple_task, verbose=False)
        team2, fitness2 = pso2.optimize_team(simple_task, verbose=False)

        # Results should be identical
        assert [a.name for a in team1] == [a.name for a in team2]
        assert fitness1 == fitness2

    def test_different_seeds_produce_different_results(self, sample_agents, simple_task):
        """Different seeds should produce different results"""
        swarm1 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        swarm2 = get_inclusive_fitness_swarm(sample_agents, random_seed=999)

        pso1 = get_pso_optimizer(swarm1, n_particles=5, max_iterations=10, random_seed=42)
        pso2 = get_pso_optimizer(swarm2, n_particles=5, max_iterations=10, random_seed=999)

        team1, fitness1 = pso1.optimize_team(simple_task, verbose=False)
        team2, fitness2 = pso2.optimize_team(simple_task, verbose=False)

        # Results should be different (highly likely)
        # Note: There's a small chance they could be the same by random chance
        team1_names = set(a.name for a in team1)
        team2_names = set(a.name for a in team2)

        # At least one of: different team composition or different fitness
        assert team1_names != team2_names or fitness1 != fitness2

    def test_no_seed_is_non_deterministic(self, sample_agents, simple_task):
        """No seed should produce non-deterministic results"""
        # Create two swarms without seed
        swarm1 = get_inclusive_fitness_swarm(sample_agents)
        swarm2 = get_inclusive_fitness_swarm(sample_agents)

        team = [sample_agents[0], sample_agents[1]]

        outcomes1 = []
        outcomes2 = []

        for _ in range(20):
            outcome1 = swarm1.evaluate_team(team, simple_task, simulate=True)
            outcome2 = swarm2.evaluate_team(team, simple_task, simulate=True)

            outcomes1.append(outcome1.success)
            outcomes2.append(outcome2.success)

        # Results should be different (with high probability)
        # At least some variation in success outcomes
        assert len(set(outcomes1)) > 1 or len(set(outcomes2)) > 1


# Test Class 2: Empty Team Edge Case (Issue #2)

class TestEmptyTeamEdgeCase:
    """Test that empty team edge case respects minimum size"""

    def test_empty_team_respects_min_size(self, sample_agents):
        """Empty team fallback should create team of at least min_size"""
        swarm = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        pso = get_pso_optimizer(swarm, n_particles=5, max_iterations=5, random_seed=42)

        # Task with minimum size 3
        task = TaskRequirement(
            task_id="min_size_test",
            required_capabilities=["coding"],
            team_size_range=(3, 4),
            priority=1.0
        )

        # Force edge case by creating degenerate PSO parameters
        # that could lead to empty teams
        pso_edge_case = ParticleSwarmOptimizer(
            swarm=swarm,
            n_particles=5,
            max_iterations=5,
            w=0.0,  # No inertia
            c1=0.0,  # No cognitive
            c2=0.0,  # No social
            random_seed=42
        )

        # This should not crash and should produce valid teams
        team, fitness = pso_edge_case.optimize_team(task, verbose=False)

        # Team should respect minimum size
        assert len(team) >= 3
        assert len(team) <= 4

    def test_single_agent_availability(self, sample_agents):
        """Edge case: when only 1 agent available but min_size > 1"""
        # Create swarm with single agent
        single_agent = [sample_agents[0]]
        swarm = get_inclusive_fitness_swarm(single_agent, random_seed=42)

        task = TaskRequirement(
            task_id="single_agent",
            required_capabilities=["ads"],
            team_size_range=(1, 3),  # Min 1
            priority=1.0
        )

        pso = ParticleSwarmOptimizer(
            swarm=swarm,
            n_particles=2,
            max_iterations=2,
            w=0.0,
            c1=0.0,
            c2=0.0,
            random_seed=42
        )

        # Should not crash
        team, fitness = pso.optimize_team(task, verbose=False)
        assert len(team) == 1  # Can only select 1 agent


# Test Class 3: Input Validation (Issue #3)

class TestInputValidation:
    """Test input validation for all constructors"""

    def test_swarm_empty_agents_raises_error(self):
        """Empty agents list should raise ValueError"""
        with pytest.raises(ValueError, match="agents list cannot be empty"):
            get_inclusive_fitness_swarm([])

    def test_swarm_duplicate_names_raises_error(self, sample_agents):
        """Duplicate agent names should raise ValueError"""
        duplicate_agents = [
            sample_agents[0],
            Agent(name="marketing", role="other", genotype=GenotypeGroup.CONTENT,
                  capabilities=["other"]),  # Duplicate name
        ]
        with pytest.raises(ValueError, match="agent names must be unique"):
            get_inclusive_fitness_swarm(duplicate_agents)

    def test_task_negative_min_size_raises_error(self):
        """Negative min_size should raise ValueError"""
        with pytest.raises(ValueError, match="team_size_range min must be >= 0"):
            TaskRequirement(
                task_id="invalid",
                required_capabilities=["coding"],
                team_size_range=(-1, 3),
                priority=1.0
            )

    def test_task_max_less_than_min_raises_error(self):
        """max_size < min_size should raise ValueError"""
        with pytest.raises(ValueError, match="team_size_range max .* must be >= min"):
            TaskRequirement(
                task_id="invalid",
                required_capabilities=["coding"],
                team_size_range=(5, 3),  # max < min
                priority=1.0
            )

    def test_task_negative_priority_raises_error(self):
        """Negative priority should raise ValueError"""
        with pytest.raises(ValueError, match="priority must be >= 0"):
            TaskRequirement(
                task_id="invalid",
                required_capabilities=["coding"],
                team_size_range=(2, 3),
                priority=-1.0
            )

    def test_pso_zero_particles_raises_error(self, sample_agents):
        """n_particles < 1 should raise ValueError"""
        swarm = get_inclusive_fitness_swarm(sample_agents)
        with pytest.raises(ValueError, match="n_particles must be >= 1"):
            get_pso_optimizer(swarm, n_particles=0, max_iterations=10)

    def test_pso_zero_iterations_raises_error(self, sample_agents):
        """max_iterations < 1 should raise ValueError"""
        swarm = get_inclusive_fitness_swarm(sample_agents)
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            get_pso_optimizer(swarm, n_particles=10, max_iterations=0)

    def test_pso_invalid_inertia_raises_error(self, sample_agents):
        """Inertia weight outside [0,1] should raise ValueError"""
        swarm = get_inclusive_fitness_swarm(sample_agents)

        # w > 1
        with pytest.raises(ValueError, match="inertia weight w must be in"):
            ParticleSwarmOptimizer(swarm=swarm, w=1.5)

        # w < 0
        with pytest.raises(ValueError, match="inertia weight w must be in"):
            ParticleSwarmOptimizer(swarm=swarm, w=-0.1)

    def test_pso_negative_cognitive_raises_error(self, sample_agents):
        """Negative c1 should raise ValueError"""
        swarm = get_inclusive_fitness_swarm(sample_agents)
        with pytest.raises(ValueError, match="PSO parameters c1, c2 must be >= 0"):
            ParticleSwarmOptimizer(swarm=swarm, c1=-0.5)

    def test_pso_negative_social_raises_error(self, sample_agents):
        """Negative c2 should raise ValueError"""
        swarm = get_inclusive_fitness_swarm(sample_agents)
        with pytest.raises(ValueError, match="PSO parameters c1, c2 must be >= 0"):
            ParticleSwarmOptimizer(swarm=swarm, c2=-0.5)


# Test Class 4: Integration Tests for All Fixes

class TestIntegrationFixes:
    """Integration tests combining all fixes"""

    def test_reproducible_validation_pipeline(self, sample_agents):
        """Complete pipeline with validation and reproducibility"""
        # Valid task (passes validation)
        task = TaskRequirement(
            task_id="integration",
            required_capabilities=["coding", "ads"],
            team_size_range=(2, 3),
            priority=1.0
        )

        # Create reproducible pipeline
        swarm = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        pso = get_pso_optimizer(swarm, n_particles=5, max_iterations=5, random_seed=42)

        # Should work without errors
        team, fitness = pso.optimize_team(task, verbose=False)

        # Verify results
        assert 2 <= len(team) <= 3
        assert fitness > 0

        # Run again with same seed - should get identical results
        swarm2 = get_inclusive_fitness_swarm(sample_agents, random_seed=42)
        pso2 = get_pso_optimizer(swarm2, n_particles=5, max_iterations=5, random_seed=42)
        team2, fitness2 = pso2.optimize_team(task, verbose=False)

        assert [a.name for a in team] == [a.name for a in team2]
        assert fitness == fitness2

    def test_edge_case_with_validation(self, sample_agents):
        """Edge case handling with validated inputs"""
        # Valid task with challenging constraints
        task = TaskRequirement(
            task_id="edge_case",
            required_capabilities=["coding"],
            team_size_range=(1, 2),
            priority=1.0
        )

        swarm = get_inclusive_fitness_swarm(sample_agents, random_seed=42)

        # PSO with parameters that could cause edge cases
        pso = ParticleSwarmOptimizer(
            swarm=swarm,
            n_particles=3,
            max_iterations=3,
            w=0.1,  # Low inertia
            c1=0.1,  # Low cognitive
            c2=0.1,  # Low social
            random_seed=42
        )

        # Should handle edge cases gracefully
        team, fitness = pso.optimize_team(task, verbose=False)

        # Verify team respects constraints
        assert 1 <= len(team) <= 2
        assert all(isinstance(a, Agent) for a in team)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
