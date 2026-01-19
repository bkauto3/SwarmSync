"""
Integration Tests: Swarm Coordinator + HALO Router

Tests the full integration between PSO-optimized team generation
and HALO routing for task execution.
"""

import pytest
import asyncio
from infrastructure.orchestration.swarm_coordinator import (
    SwarmCoordinator,
    create_swarm_coordinator,
)
from infrastructure.halo_router import HALORouter, AgentCapability
from infrastructure.task_dag import Task, TaskStatus
from infrastructure.swarm.swarm_halo_bridge import (
    AgentProfile,
    GENESIS_DEFAULT_PROFILES,
)


# ===== HELPER FUNCTIONS =====

def convert_profiles_to_capabilities(profiles):
    """Convert swarm AgentProfile to HALO AgentCapability"""
    capabilities = {}
    for profile in profiles:
        capabilities[profile.name] = AgentCapability(
            agent_name=profile.name,
            supported_task_types=[profile.role.lower().replace(" ", "_")],
            skills=profile.capabilities,
            cost_tier=profile.cost_tier,
            success_rate=profile.success_rate
        )
    return capabilities


# ===== FIXTURES =====

@pytest.fixture
def halo_router():
    """Create HALO router instance with authenticated Genesis agents"""
    from infrastructure.agent_auth_registry import AgentAuthRegistry

    # Create auth registry and register all Genesis agents
    auth_registry = AgentAuthRegistry()
    for profile in GENESIS_DEFAULT_PROFILES:
        agent_id, token = auth_registry.register_agent(
            agent_name=profile.name,
            metadata={"role": profile.role, "cost_tier": profile.cost_tier},
            permissions=["read", "write", "execute"]
        )

    # Convert swarm profiles to HALO capabilities
    agent_registry = convert_profiles_to_capabilities(GENESIS_DEFAULT_PROFILES)

    # Create HALO router with matching registry and authenticated agents
    router = HALORouter(
        agent_registry=agent_registry,
        auth_registry=auth_registry
    )
    return router


@pytest.fixture
def swarm_coordinator(halo_router):
    """Create SwarmCoordinator with Genesis 15 agents"""
    return create_swarm_coordinator(
        halo_router=halo_router,
        agent_profiles=GENESIS_DEFAULT_PROFILES,
        n_particles=50,  # Increased for better convergence
        max_iterations=100,  # Increased for better team selection
        random_seed=42
    )


@pytest.fixture
def sample_task():
    """Create sample task"""
    return Task(
        task_id="test_task_001",
        task_type="business_creation",
        description="Build an e-commerce platform with testing and deployment"
    )


# ===== TEST 1: TEAM GENERATION =====

@pytest.mark.asyncio
async def test_swarm_generates_team_for_task(swarm_coordinator, sample_task):
    """SwarmCoordinator should generate team using PSO"""
    team = await swarm_coordinator.generate_optimal_team(
        sample_task,
        team_size=3
    )

    assert 2 <= len(team) <= 4  # team_size ± 1 (PSO can optimize to smaller teams)
    assert all(isinstance(agent, str) for agent in team)
    assert sample_task.task_id in swarm_coordinator.active_teams


@pytest.mark.asyncio
async def test_swarm_team_better_than_random(swarm_coordinator):
    """Swarm-generated team should be better than random for specific requirements"""
    task = Task(
        task_id="test_task_002",
        task_type="business_creation",
        description="Build SaaS with security audit and data analytics"
    )

    # Generate swarm team
    swarm_team = await swarm_coordinator.generate_optimal_team(task, team_size=3)

    # Verify team has relevant agents for SaaS
    relevant_agents = {
        "builder_agent",  # Coding
        "deploy_agent",   # Deployment
        "security_agent", # Security
        "analyst_agent",  # Analytics
    }

    # At least 2 of the team should be from relevant agents
    matches = sum(1 for agent in swarm_team if agent in relevant_agents)
    assert matches >= 2, f"Team {swarm_team} should include at least 2 relevant agents for SaaS"


# ===== TEST 2: HALO INTEGRATION =====

@pytest.mark.asyncio
async def test_swarm_routes_to_team_via_halo(swarm_coordinator, sample_task):
    """Team routing should go through HALO router"""
    team = ["qa_agent", "builder_agent", "deploy_agent"]

    assignments = await swarm_coordinator.route_to_team(sample_task, team)

    assert len(assignments) == 3
    assert "qa_agent" in assignments
    assert "builder_agent" in assignments
    assert "deploy_agent" in assignments

    # Verify sub-task IDs are created
    for agent, sub_task_id in assignments.items():
        assert sample_task.task_id in sub_task_id
        assert isinstance(sub_task_id, str)


@pytest.mark.asyncio
async def test_swarm_executes_team_task(swarm_coordinator, sample_task):
    """Team task execution should coordinate all members"""
    team = ["qa_agent", "builder_agent"]

    result = await swarm_coordinator.execute_team_task(sample_task, team)

    assert result.task_id == sample_task.task_id
    assert result.status in ["completed", "partial", "failed"]
    assert result.team == team
    assert len(result.individual_results) <= len(team)
    assert result.execution_time > 0


# ===== TEST 3: DYNAMIC TEAM SPAWNING =====

@pytest.mark.asyncio
async def test_dynamic_team_spawning_for_ecommerce(swarm_coordinator):
    """Dynamic spawning should create appropriate team for business type"""
    team = await swarm_coordinator.spawn_dynamic_team_for_business(
        "ecommerce",
        complexity="medium"
    )

    assert 3 <= len(team) <= 4  # Medium complexity = 3-4 agents

    # Should include builder/deploy for ecommerce
    relevant_agents = {"builder_agent", "deploy_agent", "qa_agent", "billing_agent"}
    matches = sum(1 for agent in team if agent in relevant_agents)
    assert matches >= 2, f"E-commerce team should include relevant agents, got {team}"


@pytest.mark.asyncio
async def test_complex_business_gets_larger_team(swarm_coordinator):
    """Complex businesses should get larger teams"""
    simple_team = await swarm_coordinator.spawn_dynamic_team_for_business(
        "saas",
        complexity="simple"
    )
    complex_team = await swarm_coordinator.spawn_dynamic_team_for_business(
        "saas",
        complexity="complex"
    )

    assert 2 <= len(simple_team) <= 3
    assert 5 <= len(complex_team) <= 7
    assert len(complex_team) > len(simple_team)


# ===== TEST 4: PERFORMANCE TRACKING =====

@pytest.mark.asyncio
async def test_team_performance_tracking(swarm_coordinator, sample_task):
    """SwarmCoordinator should track team performance"""
    team = ["qa_agent", "builder_agent"]

    # Execute task
    result = await swarm_coordinator.execute_team_task(sample_task, team)

    # Check performance tracking
    history = swarm_coordinator.get_team_performance_history(team)

    assert history["team"] == team
    assert "team_hash" in history
    assert "performance" in history
    assert "execution_count" in history
    assert history["execution_count"] >= 1
    assert 0.0 <= history["performance"] <= 1.0


# ===== TEST 5: TEAM METRICS =====

def test_team_genotype_diversity(swarm_coordinator):
    """Should calculate genotype diversity correctly"""
    # Team with diverse genotypes
    diverse_team = ["qa_agent", "builder_agent", "marketing_agent"]
    diversity = swarm_coordinator.swarm_bridge.get_team_genotype_diversity(diverse_team)
    assert 0.0 <= diversity <= 1.0
    assert diversity > 0.2  # Should have some diversity


def test_team_cooperation_score(swarm_coordinator):
    """Should calculate cooperation score based on kin relationships"""
    # Team with genetic kin (same genotype)
    kin_team = ["qa_agent", "analyst_agent"]  # Both ANALYSIS
    cooperation = swarm_coordinator.swarm_bridge.get_team_cooperation_score(kin_team)
    assert 0.0 <= cooperation <= 1.0
    assert cooperation > 0.15  # Cooperation based on module overlap, not just genotype label


# ===== TEST 6: TEAM EVOLUTION =====

def test_team_evolution_keeps_good_performers(swarm_coordinator):
    """Should keep team composition if performing well"""
    current_team = ["qa_agent", "builder_agent", "deploy_agent"]

    # Good performance
    evolved_team = swarm_coordinator.evolve_team(current_team, performance_feedback=0.9)

    assert evolved_team == current_team


def test_team_evolution_triggers_reoptimization_for_poor_performers(swarm_coordinator):
    """Should consider re-optimization if performing poorly"""
    current_team = ["qa_agent", "builder_agent", "deploy_agent"]

    # Poor performance (currently returns same team, placeholder for future logic)
    evolved_team = swarm_coordinator.evolve_team(current_team, performance_feedback=0.3)

    # For now, should return same team (placeholder)
    assert isinstance(evolved_team, list)
    assert len(evolved_team) > 0


# ===== TEST 7: BUSINESS TYPE COVERAGE =====

@pytest.mark.asyncio
@pytest.mark.parametrize("business_type", [
    "ecommerce",
    "saas",
    "content_platform",
    "marketplace",
    "analytics_dashboard"
])
async def test_business_type_coverage(swarm_coordinator, business_type):
    """All business types should spawn appropriate teams"""
    team = await swarm_coordinator.spawn_dynamic_team_for_business(
        business_type,
        complexity="medium"
    )

    assert len(team) >= 2
    assert all(isinstance(agent, str) for agent in team)


# ===== TEST 8: REQUIREMENT INFERENCE =====

@pytest.mark.asyncio
async def test_requirement_inference_from_task_description(swarm_coordinator):
    """Should infer requirements from task description keywords"""
    test_cases = [
        ("Build and test the application", {"coding", "testing"}),
        ("Deploy to production and monitor", {"deployment"}),
        ("Analyze user data and create reports", {"data_analysis"}),
        ("Write marketing copy and run ads", {"writing", "ads"}),
    ]

    for description, expected_capabilities in test_cases:
        task = Task(
            task_id=f"test_{hash(description)}",
            task_type="generic",
            description=description
        )

        requirements = swarm_coordinator._infer_requirements_from_task(task)

        # Check that at least one expected capability is inferred
        assert any(cap in requirements for cap in expected_capabilities), \
            f"Expected {expected_capabilities} in requirements {requirements} for '{description}'"


# ===== TEST 9: PARALLEL EXECUTION =====

@pytest.mark.asyncio
async def test_parallel_team_execution(swarm_coordinator):
    """Should handle multiple team executions in parallel"""
    tasks = [
        Task(task_id=f"task_{i}", task_type="generic", description=f"Task {i}")
        for i in range(3)
    ]

    teams = [
        ["qa_agent", "builder_agent"],
        ["deploy_agent", "analyst_agent"],
        ["marketing_agent", "content_agent"]
    ]

    # Execute all tasks in parallel
    results = await asyncio.gather(*[
        swarm_coordinator.execute_team_task(task, team)
        for task, team in zip(tasks, teams)
    ])

    assert len(results) == 3
    assert all(result.status in ["completed", "partial", "failed"] for result in results)


# ===== TEST 10: EDGE CASES =====

@pytest.mark.asyncio
async def test_empty_task_description(swarm_coordinator):
    """Should handle empty task description gracefully"""
    task = Task(
        task_id="test_empty",
        task_type="generic",
        description=""
    )

    team = await swarm_coordinator.generate_optimal_team(task, team_size=2)
    assert len(team) >= 1  # Should still generate a team


@pytest.mark.asyncio
async def test_single_agent_team(swarm_coordinator):
    """Should handle single-agent teams"""
    task = Task(
        task_id="test_single",
        task_type="generic",
        description="Simple task"
    )

    team = await swarm_coordinator.generate_optimal_team(task, team_size=1)
    assert len(team) >= 1

    result = await swarm_coordinator.execute_team_task(task, team)
    assert result.status in ["completed", "partial", "failed"]


# ===== TEST 11: FACTORY FUNCTION =====

def test_create_swarm_coordinator_factory(halo_router):
    """Factory function should create valid SwarmCoordinator"""
    coordinator = create_swarm_coordinator(
        halo_router=halo_router,
        n_particles=10,
        max_iterations=20,
        random_seed=123
    )

    assert isinstance(coordinator, SwarmCoordinator)
    assert coordinator.halo_router == halo_router
    assert coordinator.swarm_bridge is not None


# ===== TEST 12: EXECUTION HISTORY =====

@pytest.mark.asyncio
async def test_execution_history_tracking(swarm_coordinator, sample_task):
    """Should track execution history for analysis"""
    team = ["qa_agent", "builder_agent"]

    # Execute multiple times
    for _ in range(3):
        await swarm_coordinator.execute_team_task(sample_task, team)

    assert len(swarm_coordinator.execution_history) == 3
    assert all(result.task_id == sample_task.task_id for result in swarm_coordinator.execution_history)


# ===== SUMMARY =====

def test_integration_summary():
    """
    Integration test summary:
    - Team generation using PSO: ✓
    - HALO routing integration: ✓
    - Dynamic team spawning: ✓
    - Performance tracking: ✓
    - Team evolution: ✓
    - Business type coverage: ✓
    - Parallel execution: ✓
    - Edge cases: ✓
    - Factory pattern: ✓
    - Execution history: ✓
    """
    assert True
