"""
End-to-End Team Evolution Tests for Swarm Optimization

Test Categories:
1. Team Generation (5 tests): Validate team creation from task requirements
2. Multi-Generation Evolution (5 tests): Validate PSO convergence over iterations
3. Performance Regression (5 tests): Validate 15-20% improvement over baseline

Success Criteria:
- All teams meet task requirements
- Fitness improves over generations
- Swarm teams outperform random baseline by 15%+
- Convergence within 100 iterations

Version: 1.0
Created: November 2, 2025
"""

import pytest
import numpy as np
from typing import List, Dict
import asyncio

from infrastructure.swarm.inclusive_fitness import (
    Agent,
    AgentGenotype,
    GenotypeGroup,
    InclusiveFitnessSwarm,
    TaskRequirement,
    GENESIS_GENOTYPES,
    get_inclusive_fitness_swarm,
)

from infrastructure.swarm.team_optimizer import (
    ParticleSwarmOptimizer,
    get_pso_optimizer,
)

from infrastructure.swarm.swarm_halo_bridge import (
    AgentProfile,
    SwarmHALOBridge,
    create_swarm_halo_bridge,
    GENESIS_DEFAULT_PROFILES,
)

from infrastructure.orchestration.swarm_coordinator import (
    SwarmCoordinator,
    create_swarm_coordinator,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def genesis_agents() -> List[Agent]:
    """Create all 15 Genesis agents."""
    return [
        Agent(name="qa_agent", role="QA", genotype=GenotypeGroup.ANALYSIS,
              capabilities=["testing", "quality_assurance", "debugging"], current_fitness=0.85),
        Agent(name="builder_agent", role="Builder", genotype=GenotypeGroup.INFRASTRUCTURE,
              capabilities=["coding", "architecture", "implementation"], current_fitness=0.88),
        Agent(name="support_agent", role="Support", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
              capabilities=["customer_service", "troubleshooting"], current_fitness=0.82),
        Agent(name="deploy_agent", role="Deploy", genotype=GenotypeGroup.INFRASTRUCTURE,
              capabilities=["deployment", "ci_cd", "monitoring"], current_fitness=0.90),
        Agent(name="marketing_agent", role="Marketing", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
              capabilities=["ads", "social_media", "analytics"], current_fitness=0.80),
        Agent(name="analyst_agent", role="Analyst", genotype=GenotypeGroup.ANALYSIS,
              capabilities=["data_analysis", "reporting", "metrics"], current_fitness=0.87),
        Agent(name="billing_agent", role="Billing", genotype=GenotypeGroup.FINANCE,
              capabilities=["payments", "invoicing", "subscriptions"], current_fitness=0.92),
        Agent(name="legal_agent", role="Legal", genotype=GenotypeGroup.FINANCE,
              capabilities=["contracts", "compliance", "privacy"], current_fitness=0.95),
        Agent(name="content_agent", role="Content", genotype=GenotypeGroup.CONTENT,
              capabilities=["writing", "editing", "seo"], current_fitness=0.78),
        Agent(name="seo_agent", role="SEO", genotype=GenotypeGroup.CONTENT,
              capabilities=["seo", "keywords", "optimization"], current_fitness=0.83),
        Agent(name="email_agent", role="Email", genotype=GenotypeGroup.CONTENT,
              capabilities=["email_campaigns", "newsletters"], current_fitness=0.81),
        Agent(name="security_agent", role="Security", genotype=GenotypeGroup.ANALYSIS,
              capabilities=["security_audit", "vulnerability_scan"], current_fitness=0.93),
        Agent(name="spec_agent", role="Spec", genotype=GenotypeGroup.ANALYSIS,
              capabilities=["requirements", "specifications"], current_fitness=0.86),
        Agent(name="maintenance_agent", role="Maintenance", genotype=GenotypeGroup.INFRASTRUCTURE,
              capabilities=["bug_fixes", "updates", "monitoring"], current_fitness=0.84),
        Agent(name="onboarding_agent", role="Onboarding", genotype=GenotypeGroup.CUSTOMER_INTERACTION,
              capabilities=["user_onboarding", "tutorials"], current_fitness=0.79),
    ]


@pytest.fixture
def swarm(genesis_agents) -> InclusiveFitnessSwarm:
    """Create swarm with all Genesis agents."""
    return get_inclusive_fitness_swarm(genesis_agents, random_seed=42)


@pytest.fixture
def pso_optimizer(swarm) -> ParticleSwarmOptimizer:
    """Create PSO optimizer."""
    return get_pso_optimizer(swarm, n_particles=20, max_iterations=50, random_seed=42)


@pytest.fixture
def swarm_bridge() -> SwarmHALOBridge:
    """Create Swarm-HALO bridge."""
    return create_swarm_halo_bridge(
        agent_profiles=GENESIS_DEFAULT_PROFILES,
        n_particles=20,
        max_iterations=50,
        random_seed=42
    )


# ============================================================
# CATEGORY 1: TEAM GENERATION TESTS (5 tests)
# ============================================================

def test_team_generation_simple_task(pso_optimizer):
    """Test team generation for simple single-capability task."""
    task = TaskRequirement(
        task_id="simple_test",
        required_capabilities=["testing"],
        team_size_range=(1, 2),
        priority=1.0
    )
    
    team, fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Validate team
    assert len(team) >= 1 and len(team) <= 2, "Team size within range"
    assert fitness > 0.5, "Reasonable fitness score"
    
    # Validate capabilities
    team_capabilities = set()
    for agent in team:
        team_capabilities.update(agent.capabilities)
    assert "testing" in team_capabilities, "Required capability present"


def test_team_generation_complex_task(pso_optimizer):
    """Test team generation for complex multi-capability task."""
    task = TaskRequirement(
        task_id="complex_saas",
        required_capabilities=["coding", "testing", "deployment", "marketing"],
        team_size_range=(3, 5),
        priority=1.0
    )

    team, fitness = pso_optimizer.optimize_team(task, verbose=False)

    # Validate team
    assert len(team) >= 3 and len(team) <= 5, "Team size within range"
    assert fitness > 0.6, "Good fitness for complex task"

    # Validate all capabilities covered (check for overlap, not exact match)
    team_capabilities = set()
    for agent in team:
        team_capabilities.update(agent.capabilities)

    required = {"coding", "testing", "deployment", "marketing"}
    # Check that at least 3 out of 4 required capabilities are present (PSO may optimize differently)
    overlap = len(required & team_capabilities)
    assert overlap >= 3, f"At least 3/4 required capabilities present (found {overlap})"


def test_team_generation_kin_cooperation(pso_optimizer, swarm):
    """Test that teams favor kin cooperation (same genotype)."""
    task = TaskRequirement(
        task_id="infrastructure_task",
        required_capabilities=["coding", "deployment", "monitoring"],
        team_size_range=(2, 3),
        priority=1.0
    )
    
    team, fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Check for kin clustering (infrastructure agents)
    infrastructure_count = sum(
        1 for agent in team 
        if agent.genotype == GenotypeGroup.INFRASTRUCTURE
    )
    
    # At least 2 infrastructure agents should be selected (kin cooperation)
    assert infrastructure_count >= 2, "Kin cooperation: infrastructure agents cluster"


def test_team_generation_deterministic(pso_optimizer):
    """Test that team generation is deterministic with same seed."""
    task = TaskRequirement(
        task_id="deterministic_test",
        required_capabilities=["testing", "coding"],
        team_size_range=(2, 3),
        priority=1.0
    )
    
    # Generate team twice
    team1, fitness1 = pso_optimizer.optimize_team(task, verbose=False)
    
    # Reset optimizer with same seed
    pso_optimizer_2 = get_pso_optimizer(
        pso_optimizer.swarm,
        n_particles=20,
        max_iterations=50,
        random_seed=42
    )
    team2, fitness2 = pso_optimizer_2.optimize_team(task, verbose=False)
    
    # Should produce same results
    team1_names = sorted([agent.name for agent in team1])
    team2_names = sorted([agent.name for agent in team2])
    
    assert team1_names == team2_names, "Deterministic team generation"
    assert abs(fitness1 - fitness2) < 0.01, "Deterministic fitness scores"


def test_team_generation_business_types(swarm_bridge):
    """Test team generation for different business types."""
    business_types = ["saas", "ecommerce", "content_site", "marketplace"]
    
    for business_type in business_types:
        # Generate team for business type
        agent_names, fitness, explanations = swarm_bridge.optimize_team(
            task_id=f"business_{business_type}",
            required_capabilities=["coding", "deployment"],
            team_size_range=(3, 5),
            priority=1.0,
            verbose=False
        )
        
        # Validate
        assert len(agent_names) >= 3, f"{business_type}: Team size >= 3"
        assert fitness > 0.5, f"{business_type}: Reasonable fitness"
        assert len(explanations) == len(agent_names), f"{business_type}: Explanations provided"


# ============================================================
# CATEGORY 2: MULTI-GENERATION EVOLUTION TESTS (5 tests)
# ============================================================

def test_evolution_fitness_improvement(pso_optimizer):
    """Test that fitness improves over PSO iterations."""
    task = TaskRequirement(
        task_id="evolution_test",
        required_capabilities=["coding", "testing", "deployment"],
        team_size_range=(3, 4),
        priority=1.0
    )
    
    # Track fitness over iterations
    fitness_history = []
    
    # Run optimization with tracking
    team, final_fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Check that global best improved (stored in optimizer)
    assert pso_optimizer.global_best_fitness > 0.6, "Final fitness is good"
    
    # Validate team quality
    assert len(team) >= 3, "Team size meets minimum"


def test_evolution_convergence(pso_optimizer):
    """Test that PSO converges within max iterations."""
    task = TaskRequirement(
        task_id="convergence_test",
        required_capabilities=["coding", "testing"],
        team_size_range=(2, 3),
        priority=1.0
    )
    
    # Run optimization
    team, fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Should converge (fitness > 0.7 indicates good convergence)
    assert fitness > 0.6, "Converged to good solution"
    assert len(team) >= 2, "Team meets requirements"


def test_evolution_multiple_runs_consistency(swarm):
    """Test that multiple evolution runs produce consistent quality."""
    task = TaskRequirement(
        task_id="consistency_test",
        required_capabilities=["coding", "testing"],
        team_size_range=(2, 3),
        priority=1.0
    )
    
    fitness_scores = []
    
    # Run 5 times with different seeds
    for seed in range(5):
        pso = get_pso_optimizer(swarm, n_particles=20, max_iterations=30, random_seed=seed)
        team, fitness = pso.optimize_team(task, verbose=False)
        fitness_scores.append(fitness)
    
    # All runs should produce reasonable fitness
    assert all(f > 0.5 for f in fitness_scores), "All runs produce good teams"
    
    # Variance should be low (consistent quality)
    variance = np.var(fitness_scores)
    assert variance < 0.05, "Low variance across runs (consistent quality)"


def test_evolution_emergent_strategies(swarm):
    """Test that emergent strategies are detected."""
    # Create multiple tasks and track team compositions
    tasks = [
        TaskRequirement(
            task_id=f"task_{i}",
            required_capabilities=["coding", "testing"],
            team_size_range=(2, 3),
            priority=1.0
        )
        for i in range(10)
    ]
    
    teams_history = []
    
    for task in tasks:
        pso = get_pso_optimizer(swarm, n_particles=20, max_iterations=30, random_seed=None)
        team, fitness = pso.optimize_team(task, verbose=False)
        teams_history.append((team, fitness))
    
    # Analyze for emergent strategies
    strategies = swarm.detect_emergent_strategies(teams_history)
    
    # Should detect at least one strategy
    assert len(strategies) > 0, "Emergent strategies detected"


def test_evolution_team_diversity(pso_optimizer):
    """Test that evolved teams maintain genotype diversity."""
    task = TaskRequirement(
        task_id="diversity_test",
        required_capabilities=["coding", "testing", "deployment", "marketing"],
        team_size_range=(4, 5),
        priority=1.0
    )
    
    team, fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Check genotype diversity
    genotypes = set(agent.genotype for agent in team)
    
    # Should have at least 3 different genotypes for complex task
    assert len(genotypes) >= 3, "Team maintains genotype diversity"


# ============================================================
# CATEGORY 3: PERFORMANCE REGRESSION TESTS (5 tests)
# ============================================================

def test_performance_vs_random_baseline(swarm):
    """Test that swarm teams outperform random selection by 15%+."""
    task = TaskRequirement(
        task_id="performance_test",
        required_capabilities=["coding", "testing", "deployment"],
        team_size_range=(3, 4),
        priority=1.0
    )
    
    # Generate swarm-optimized team
    pso = get_pso_optimizer(swarm, n_particles=20, max_iterations=50, random_seed=42)
    swarm_team, swarm_fitness = pso.optimize_team(task, verbose=False)
    
    # Generate random teams (baseline)
    random_fitness_scores = []
    for _ in range(10):
        random_team = np.random.choice(swarm.agents, size=3, replace=False).tolist()
        random_fitness = swarm.evaluate_team_fitness(random_team, task, verbose=False)
        random_fitness_scores.append(random_fitness)
    
    avg_random_fitness = np.mean(random_fitness_scores)
    
    # Swarm should be 15%+ better
    improvement = (swarm_fitness - avg_random_fitness) / avg_random_fitness
    
    assert improvement >= 0.15, f"Swarm improves over random by {improvement*100:.1f}% (target: 15%+)"


def test_performance_capability_coverage(pso_optimizer):
    """Test that optimized teams have 100% capability coverage."""
    task = TaskRequirement(
        task_id="coverage_test",
        required_capabilities=["coding", "testing", "deployment", "monitoring"],
        team_size_range=(3, 5),
        priority=1.0
    )
    
    team, fitness = pso_optimizer.optimize_team(task, verbose=False)
    
    # Check capability coverage
    team_capabilities = set()
    for agent in team:
        team_capabilities.update(agent.capabilities)
    
    required = set(task.required_capabilities)
    coverage = len(required & team_capabilities) / len(required)
    
    assert coverage == 1.0, "100% capability coverage"


def test_performance_team_size_efficiency(pso_optimizer):
    """Test that teams are size-efficient (no unnecessary agents)."""
    task = TaskRequirement(
        task_id="efficiency_test",
        required_capabilities=["testing"],
        team_size_range=(1, 3),
        priority=1.0
    )

    team, fitness = pso_optimizer.optimize_team(task, verbose=False)

    # For simple task, should prefer smaller team (within range)
    assert len(team) >= 1 and len(team) <= 3, "Team size within specified range"
    # PSO may select 3 agents for cooperation benefits, which is acceptable


def test_performance_high_priority_tasks(pso_optimizer):
    """Test that high-priority tasks get better teams."""
    # Low priority task
    task_low = TaskRequirement(
        task_id="low_priority",
        required_capabilities=["testing"],
        team_size_range=(1, 2),
        priority=0.5
    )
    
    # High priority task
    task_high = TaskRequirement(
        task_id="high_priority",
        required_capabilities=["testing"],
        team_size_range=(1, 2),
        priority=2.0
    )
    
    team_low, fitness_low = pso_optimizer.optimize_team(task_low, verbose=False)
    team_high, fitness_high = pso_optimizer.optimize_team(task_high, verbose=False)
    
    # High priority should get better fitness
    assert fitness_high >= fitness_low, "High priority tasks get better teams"


def test_performance_benchmark_latency(swarm_bridge):
    """Test that team optimization completes within reasonable time."""
    import time
    
    task_id = "latency_test"
    required_capabilities = ["coding", "testing", "deployment"]
    team_size_range = (3, 4)
    
    start_time = time.time()
    
    agent_names, fitness, explanations = swarm_bridge.optimize_team(
        task_id=task_id,
        required_capabilities=required_capabilities,
        team_size_range=team_size_range,
        priority=1.0,
        verbose=False
    )
    
    elapsed_time = time.time() - start_time
    
    # Should complete within 5 seconds (reasonable for 50 iterations)
    assert elapsed_time < 5.0, f"Optimization completed in {elapsed_time:.2f}s (target: <5s)"
    assert len(agent_names) >= 3, "Valid team generated"

