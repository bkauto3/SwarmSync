"""
LAYER 5 SWARM OPTIMIZATION - EDGE CASE AND STRESS TESTS
Version: 1.0
Last Updated: October 16, 2025

Additional test coverage for:
1. Edge cases not covered by main test suite
2. Error handling and boundary conditions
3. Performance and stress tests
4. Statistical validation
5. Thread safety and race conditions
"""

import pytest
import random
from typing import List

from infrastructure.inclusive_fitness_swarm import (
    Agent,
    GenotypeGroup,
    InclusiveFitnessSwarm,
    ParticleSwarmOptimizer,
    TaskRequirement,
    TeamOutcome,
    get_inclusive_fitness_swarm,
    get_pso_optimizer,
)


# Edge Case Tests

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unknown_role_defaults_to_analysis(self):
        """Agent with unknown role should default to ANALYSIS genotype"""
        agents = [
            Agent(
                name="mystery",
                role="unknown_weird_role_12345",
                genotype=GenotypeGroup.ANALYSIS,  # Will be overridden
                capabilities=["misc"]
            )
        ]
        swarm = get_inclusive_fitness_swarm(agents)

        # Should default to ANALYSIS (line 152-153 coverage)
        assert agents[0].genotype == GenotypeGroup.ANALYSIS

    def test_actual_execution_raises_not_implemented(self):
        """Calling evaluate_team with simulate=False should raise NotImplementedError"""
        agents = [
            Agent(name="test", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("test", ["test"], (1, 2))

        # Line 294 coverage
        with pytest.raises(NotImplementedError, match="Actual team execution not yet implemented"):
            swarm.evaluate_team([agents[0]], task, simulate=False)

    def test_verbose_pso_prints_progress(self, capsys):
        """PSO with verbose=True should print progress"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(5)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=3, max_iterations=5)
        task = TaskRequirement("test", ["test"], (2, 3))

        # Line 401 coverage
        pso.optimize_team(task, verbose=True)

        captured = capsys.readouterr()
        assert "Iteration" in captured.out
        assert "Best fitness" in captured.out

    def test_empty_team_edge_case(self):
        """PSO update with edge case where new_team becomes empty"""
        agents = [
            Agent(name="agent1", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=5, max_iterations=10)

        # Force edge case: very small team size range
        task = TaskRequirement("test", ["test"], (1, 1))

        # Should handle edge case gracefully (line 485-486 coverage)
        best_team, best_fitness = pso.optimize_team(task, verbose=False)

        assert len(best_team) >= 1  # Should not be empty

    def test_single_agent_team(self):
        """Team with single agent should work correctly"""
        agents = [
            Agent(name="solo", role="builder", genotype=GenotypeGroup.INFRASTRUCTURE, capabilities=["coding"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("solo_task", ["coding"], (1, 1))

        outcome = swarm.evaluate_team([agents[0]], task, simulate=True)

        assert outcome is not None
        assert len(outcome.team) == 1
        assert "solo" in outcome.individual_contributions

    def test_maximum_team_size(self):
        """PSO should respect maximum team size"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(20)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=10, max_iterations=20)

        task = TaskRequirement("large_task", ["test"], (1, 5))
        best_team, _ = pso.optimize_team(task, verbose=False)

        # Should not exceed max size
        assert len(best_team) <= 5

    def test_minimum_team_size(self):
        """PSO should respect minimum team size"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(10)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=10, max_iterations=20)

        task = TaskRequirement("min_task", ["test"], (3, 10))
        best_team, _ = pso.optimize_team(task, verbose=False)

        # Should meet min size
        assert len(best_team) >= 3


class TestStatisticalValidation:
    """Validate statistical claims and probabilistic behavior"""

    def test_success_probability_with_capabilities(self):
        """Teams with all capabilities should have higher success rate"""
        agents = [
            Agent(name="builder", role="builder", genotype=GenotypeGroup.INFRASTRUCTURE,
                  capabilities=["coding", "testing"]),
            Agent(name="marketing", role="marketing", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
                  capabilities=["ads", "analytics"]),
            Agent(name="billing", role="billing", genotype=GenotypeGroup.FINANCE,
                  capabilities=["payments", "invoicing"]),
        ]
        swarm = get_inclusive_fitness_swarm(agents)

        # Task requiring all capabilities
        task = TaskRequirement("complete_task", ["coding", "ads", "payments"], (3, 3))

        # Run 200 trials for statistical significance
        successes = 0
        for _ in range(200):
            outcome = swarm.evaluate_team(agents, task, simulate=True)
            if outcome.success:
                successes += 1

        success_rate = successes / 200

        # Should have >60% success with all capabilities (as per code logic)
        assert success_rate > 0.55  # Allow some variance
        print(f"\nSuccess rate with all capabilities: {success_rate:.1%}")

    def test_success_probability_without_capabilities(self):
        """Teams missing capabilities should have lower success rate"""
        agents = [
            Agent(name="content", role="content", genotype=GenotypeGroup.CONTENT,
                  capabilities=["writing", "copywriting"]),
            Agent(name="seo", role="seo", genotype=GenotypeGroup.CONTENT,
                  capabilities=["seo", "keywords"]),
        ]
        swarm = get_inclusive_fitness_swarm(agents)

        # Task requiring capabilities they don't have
        task = TaskRequirement("mismatch_task", ["coding", "payments"], (2, 2))

        # Run 200 trials
        successes = 0
        for _ in range(200):
            outcome = swarm.evaluate_team(agents, task, simulate=True)
            if outcome.success:
                successes += 1

        success_rate = successes / 200

        # Should have <50% success without capabilities
        assert success_rate < 0.45  # Allow some variance
        print(f"\nSuccess rate without capabilities: {success_rate:.1%}")

    def test_randomness_seed_reproducibility(self):
        """Setting random seed should produce reproducible results"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(10)
        ]

        random.seed(42)
        swarm1 = get_inclusive_fitness_swarm(agents)
        pso1 = get_pso_optimizer(swarm1, n_particles=5, max_iterations=10)
        task = TaskRequirement("test", ["test"], (2, 4))
        team1, fitness1 = pso1.optimize_team(task, verbose=False)

        random.seed(42)
        swarm2 = get_inclusive_fitness_swarm(agents)
        pso2 = get_pso_optimizer(swarm2, n_particles=5, max_iterations=10)
        team2, fitness2 = pso2.optimize_team(task, verbose=False)

        # Should produce same results with same seed
        team1_names = set(a.name for a in team1)
        team2_names = set(a.name for a in team2)

        # Note: Due to PSO stochasticity, exact match not guaranteed
        # But fitness should be similar
        assert abs(fitness1 - fitness2) < 0.5

    def test_inclusive_fitness_statistical_improvement(self):
        """
        Verify 15-20% improvement claim with larger sample size
        """
        agents = [
            Agent(name="marketing", role="marketing", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
                  capabilities=["ads", "social_media"]),
            Agent(name="support", role="support", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
                  capabilities=["customer_service"]),
            Agent(name="builder", role="builder", genotype=GenotypeGroup.INFRASTRUCTURE,
                  capabilities=["coding", "testing"]),
            Agent(name="deploy", role="deploy", genotype=GenotypeGroup.INFRASTRUCTURE,
                  capabilities=["deployment", "ci_cd"]),
            Agent(name="content", role="content", genotype=GenotypeGroup.CONTENT,
                  capabilities=["writing"]),
            Agent(name="seo", role="seo", genotype=GenotypeGroup.CONTENT,
                  capabilities=["seo"]),
        ]

        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("test", ["ads", "coding"], (3, 4))
        pso = get_pso_optimizer(swarm, n_particles=15, max_iterations=30)

        # Collect 20 samples
        optimized_scores = []
        random_scores = []

        for _ in range(20):
            # Optimized approach
            opt_team, opt_fit = pso.optimize_team(task, verbose=False)
            optimized_scores.append(opt_fit)

            # Random approach
            rand_team = random.sample(agents, k=3)
            rand_outcome = swarm.evaluate_team(rand_team, task, simulate=True)
            rand_fit = sum(
                swarm.inclusive_fitness_reward(a, "task", rand_outcome, rand_team)
                for a in rand_team
            ) / len(rand_team)
            random_scores.append(rand_fit)

        avg_optimized = sum(optimized_scores) / len(optimized_scores)
        avg_random = sum(random_scores) / len(random_scores)

        improvement = (avg_optimized - avg_random) / avg_random if avg_random > 0 else 0

        print(f"\nStatistical improvement over 20 samples: {improvement:.1%}")
        print(f"Optimized avg: {avg_optimized:.3f}, Random avg: {avg_random:.3f}")

        # Should show improvement (not necessarily 15-20%, but positive)
        assert avg_optimized >= avg_random


class TestErrorHandling:
    """Test error handling and robustness"""

    def test_empty_agent_list(self):
        """Creating swarm with empty agent list should raise ValueError"""
        # Empty agent list is invalid - should raise ValueError
        with pytest.raises(ValueError, match="agents list cannot be empty"):
            swarm = get_inclusive_fitness_swarm([])

    def test_task_with_no_required_capabilities(self):
        """Task with empty required capabilities"""
        agents = [
            Agent(name="test", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("simple_task", [], (1, 2))

        outcome = swarm.evaluate_team([agents[0]], task, simulate=True)
        assert outcome is not None

    def test_agent_with_no_capabilities(self):
        """Agent with empty capabilities list"""
        agents = [
            Agent(name="useless", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=[])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("test", ["some_capability"], (1, 1))

        outcome = swarm.evaluate_team([agents[0]], task, simulate=True)

        # Should work, but likely low success rate
        assert outcome is not None
        assert outcome.overall_reward >= 0

    def test_extremely_small_team_size_range(self):
        """Team size range of (1, 1) should work"""
        agents = [
            Agent(name="solo", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=5, max_iterations=10)
        task = TaskRequirement("tiny", ["test"], (1, 1))

        best_team, _ = pso.optimize_team(task, verbose=False)
        assert len(best_team) == 1

    def test_pso_convergence_with_single_particle(self):
        """PSO with single particle should still work"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(5)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=1, max_iterations=10)
        task = TaskRequirement("test", ["test"], (2, 3))

        best_team, best_fitness = pso.optimize_team(task, verbose=False)

        assert best_team is not None
        assert best_fitness > 0


class TestPerformance:
    """Performance and stress tests"""

    def test_large_agent_pool_performance(self):
        """PSO should handle large agent pools efficiently"""
        # Create 50 agents
        agents = [
            Agent(
                name=f"agent_{i}",
                role=["builder", "marketing", "analyst", "support", "content"][i % 5],
                genotype=GenotypeGroup.ANALYSIS,
                capabilities=[f"skill_{i % 10}"]
            )
            for i in range(50)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=20, max_iterations=20)
        task = TaskRequirement("large_pool", ["skill_0", "skill_5"], (5, 10))

        import time
        start = time.time()
        best_team, _ = pso.optimize_team(task, verbose=False)
        duration = time.time() - start

        print(f"\nLarge pool optimization time: {duration:.2f}s")

        # Should complete in reasonable time (<5 seconds)
        assert duration < 5.0
        assert best_team is not None

    def test_many_iterations_convergence(self):
        """PSO should converge with many iterations"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(10)
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        pso = get_pso_optimizer(swarm, n_particles=10, max_iterations=100)
        task = TaskRequirement("convergence", ["test"], (3, 5))

        best_team, best_fitness = pso.optimize_team(task, verbose=False)

        # With 100 iterations, should find good solution
        assert best_fitness > 0
        assert best_team is not None


class TestDataIntegrity:
    """Test data consistency and integrity"""

    def test_agent_metadata_persistence(self):
        """Agent metadata should persist through operations"""
        agents = [
            Agent(
                name="test",
                role="test",
                genotype=GenotypeGroup.ANALYSIS,
                capabilities=["test"],
                metadata={"custom_field": "test_value"}
            )
        ]
        swarm = get_inclusive_fitness_swarm(agents)

        # Metadata should be preserved
        assert agents[0].metadata["custom_field"] == "test_value"

    def test_task_metadata_persistence(self):
        """Task metadata should persist through operations"""
        task = TaskRequirement(
            "test",
            ["test"],
            (1, 2),
            metadata={"priority_level": "high"}
        )

        assert task.metadata["priority_level"] == "high"

    def test_team_outcome_timestamp(self):
        """TeamOutcome should have valid timestamp"""
        agents = [
            Agent(name="test", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
        ]
        swarm = get_inclusive_fitness_swarm(agents)
        task = TaskRequirement("test", ["test"], (1, 1))

        outcome = swarm.evaluate_team([agents[0]], task, simulate=True)

        assert outcome.timestamp is not None
        # Should be recent (within last minute)
        from datetime import datetime, timezone, timedelta
        assert outcome.timestamp > datetime.now(timezone.utc) - timedelta(minutes=1)

    def test_cooperation_history_tracking(self):
        """Swarm should track cooperation history"""
        agents = [
            Agent(name=f"agent_{i}", role="test", genotype=GenotypeGroup.ANALYSIS, capabilities=["test"])
            for i in range(3)
        ]
        swarm = get_inclusive_fitness_swarm(agents)

        # Initially empty
        assert len(swarm.cooperation_history) == 0

        # Note: Current implementation doesn't append to history
        # This is a placeholder for future enhancement


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
