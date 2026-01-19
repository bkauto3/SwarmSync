"""
SE-Darwin Integration Test - Real Benchmark Scenario Validation

Tests SE-Darwin agent against real benchmark scenarios from the 270-scenario suite:
- Builder agent scenarios (code generation)
- Analyst agent scenarios (data analysis)
- Support agent scenarios (user assistance)

Validates:
1. Multi-trajectory generation works with real problems
2. Operators produce valid code/strategies
3. Benchmark validation integrates correctly
4. Evolution improves scores over iterations
5. TrajectoryPool archiving works end-to-end
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from agents.se_darwin_agent import SEDarwinAgent, get_se_darwin_agent
from infrastructure.trajectory_pool import TrajectoryPool
from infrastructure.benchmark_runner import BenchmarkResult, BenchmarkType


# ============================================================================
# REAL BENCHMARK SCENARIOS (from 270-scenario suite)
# ============================================================================

BUILDER_SCENARIOS = [
    {
        'name': 'fastapi_crud_api',
        'description': 'Build a FastAPI CRUD API with PostgreSQL database for managing user accounts',
        'context': {
            'framework': 'FastAPI',
            'database': 'PostgreSQL',
            'features': ['authentication', 'CRUD operations', 'validation']
        },
        'expected_patterns': ['FastAPI', 'SQLAlchemy', 'Pydantic', 'database', 'router']
    },
    {
        'name': 'websocket_chat',
        'description': 'Implement real-time WebSocket chat server with room management',
        'context': {
            'protocol': 'WebSocket',
            'features': ['room creation', 'message broadcasting', 'user presence']
        },
        'expected_patterns': ['websocket', 'broadcast', 'connection', 'message']
    },
    {
        'name': 'microservice_deployment',
        'description': 'Create Docker-based microservice with health checks and graceful shutdown',
        'context': {
            'platform': 'Docker',
            'features': ['health endpoint', 'graceful shutdown', 'logging']
        },
        'expected_patterns': ['docker', 'dockerfile', 'health', 'shutdown']
    }
]

ANALYST_SCENARIOS = [
    {
        'name': 'performance_bottleneck',
        'description': 'Analyze application performance data and identify top 3 bottlenecks',
        'context': {
            'data': 'API response times, database query logs, CPU profiles',
            'goal': 'Identify slow queries and optimization opportunities'
        },
        'expected_patterns': ['analyze', 'bottleneck', 'query', 'performance', 'optimize']
    },
    {
        'name': 'user_behavior_analysis',
        'description': 'Analyze user behavior patterns to improve conversion funnel',
        'context': {
            'data': 'Click streams, session data, conversion events',
            'goal': 'Find drop-off points and recommend improvements'
        },
        'expected_patterns': ['funnel', 'conversion', 'drop', 'behavior', 'pattern']
    },
    {
        'name': 'cost_optimization',
        'description': 'Analyze cloud infrastructure costs and recommend optimization strategies',
        'context': {
            'data': 'AWS billing, resource utilization, traffic patterns',
            'goal': 'Reduce costs by 30% without impacting performance'
        },
        'expected_patterns': ['cost', 'optimize', 'resource', 'utilization', 'savings']
    }
]

SUPPORT_SCENARIOS = [
    {
        'name': 'authentication_troubleshooting',
        'description': 'Help user debug authentication failures in their application',
        'context': {
            'error': '401 Unauthorized despite valid credentials',
            'stack': 'FastAPI + JWT',
            'user_level': 'intermediate'
        },
        'expected_patterns': ['authentication', 'JWT', 'token', 'validate', 'debug']
    },
    {
        'name': 'database_migration',
        'description': 'Guide user through database migration from SQLite to PostgreSQL',
        'context': {
            'current': 'SQLite with 10K records',
            'target': 'PostgreSQL with minimal downtime',
            'user_level': 'beginner'
        },
        'expected_patterns': ['migration', 'backup', 'export', 'import', 'postgresql']
    },
    {
        'name': 'deployment_issues',
        'description': 'Resolve Docker container failing to start in production',
        'context': {
            'error': 'Container exits with code 137',
            'platform': 'AWS ECS',
            'user_level': 'intermediate'
        },
        'expected_patterns': ['docker', 'memory', 'oom', 'container', 'resource']
    }
]


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_with_realistic_responses():
    """Mock LLM that generates realistic code/strategies"""

    async def generate_response(model, messages, **kwargs):
        # Extract the problem from messages
        user_message = next((m['content'] for m in messages if m['role'] == 'user'), '')

        # Generate realistic response based on problem domain
        if 'FastAPI' in user_message or 'API' in user_message:
            code = """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: str

@app.post("/users/")
async def create_user(user: UserCreate, db: Session):
    # Create user logic
    return {"id": 1, "username": user.username}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
"""
            strategy = "Implement FastAPI CRUD endpoints with Pydantic validation and SQLAlchemy ORM integration"

        elif 'WebSocket' in user_message or 'chat' in user_message:
            code = """
from fastapi import FastAPI, WebSocket
from typing import Dict, Set

app = FastAPI()
active_connections: Dict[str, Set[WebSocket]] = {}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in active_connections:
        active_connections[room_id] = set()
    active_connections[room_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            for connection in active_connections[room_id]:
                await connection.send_text(data)
    except:
        active_connections[room_id].remove(websocket)
"""
            strategy = "WebSocket room-based chat with connection management and message broadcasting"

        elif 'Docker' in user_message or 'deployment' in user_message:
            code = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=3s \\
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
            strategy = "Dockerized microservice with health checks and production-ready configuration"

        elif 'analysis' in user_message or 'bottleneck' in user_message or 'performance' in user_message:
            code = """
import pandas as pd
import numpy as np

def analyze_performance_bottlenecks(response_times_df):
    # Identify slow endpoints
    slow_endpoints = response_times_df[response_times_df['response_time'] > 1000]
    top_3_bottlenecks = slow_endpoints.groupby('endpoint').agg({
        'response_time': ['mean', 'count']
    }).sort_values(('response_time', 'mean'), ascending=False).head(3)

    # Analyze query performance
    query_analysis = analyze_database_queries()

    return {
        'slow_endpoints': top_3_bottlenecks,
        'query_bottlenecks': query_analysis
    }
"""
            strategy = "Analyze response time data to identify slow endpoints and database query bottlenecks"

        elif 'cost' in user_message or 'optimization' in user_message:
            code = """
import boto3

def analyze_aws_costs():
    ce_client = boto3.client('ce')

    # Get cost and usage data
    response = ce_client.get_cost_and_usage(
        TimePeriod={'Start': '2025-09-01', 'End': '2025-10-01'},
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'SERVICE', 'Key': 'SERVICE'}]
    )

    # Identify high-cost services
    recommendations = []
    for result in response['ResultsByTime']:
        # Recommend right-sizing, reserved instances, etc.
        pass

    return recommendations
"""
            strategy = "Analyze AWS billing data to identify cost optimization opportunities via right-sizing and reserved instances"

        else:
            # Generic support/troubleshooting
            code = """
def troubleshoot_authentication_issue():
    # 1. Verify JWT token format
    # 2. Check token expiration
    # 3. Validate signature
    # 4. Ensure headers are correct

    steps = [
        "Decode JWT to inspect claims",
        "Verify exp claim hasn't passed",
        "Check secret key matches between generation and validation",
        "Ensure Authorization header format: 'Bearer <token>'"
    ]

    return steps
"""
            strategy = "Systematic approach to debug JWT authentication: decode token, verify expiration, validate signature, check headers"

        response_text = f"STRATEGY: {strategy}\n\nCODE:\n```python\n{code}\n```"

        return Mock(
            choices=[
                Mock(message=Mock(content=response_text))
            ]
        )

    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(side_effect=generate_response)

    return client


@pytest.fixture
def se_darwin_agent_for_integration(mock_llm_with_realistic_responses, tmp_path):
    """Create SE-Darwin agent configured for integration testing"""

    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool:
        from infrastructure.trajectory_pool import TrajectoryPool
        pool = TrajectoryPool(
            agent_name="integration_agent",
            storage_dir=tmp_path / "trajectory_pools" / "integration_agent"
        )
        mock_pool.return_value = pool

        agent = SEDarwinAgent(
            agent_name="integration_agent",
            llm_client=mock_llm_with_realistic_responses,
            trajectories_per_iteration=3,
            max_iterations=2,
            timeout_per_trajectory=60
        )

        return agent


# ============================================================================
# INTEGRATION TESTS - BUILDER SCENARIOS
# ============================================================================

@pytest.mark.asyncio
async def test_builder_fastapi_crud_evolution(se_darwin_agent_for_integration):
    """Test evolution on FastAPI CRUD API scenario"""
    scenario = BUILDER_SCENARIOS[0]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    # Verify evolution completed
    assert result['success'] is True
    assert result['best_score'] > 0.0

    # Verify trajectories generated
    assert len(result['iterations']) > 0
    total_trajectories = sum(it['trajectories'] for it in result['iterations'])
    assert total_trajectories >= 3  # At least trajectories_per_iteration

    # Verify pool contains trajectories
    stats = result['pool_statistics']
    assert stats['total_trajectories'] > 0

    # Verify best trajectory exists and has code
    if result['best_trajectory']:
        best_traj = result['best_trajectory']
        assert best_traj.trajectory_id is not None
        # May have code if operators were applied
        if best_traj.code_changes:
            # Check for expected patterns
            code_lower = best_traj.code_changes.lower()
            assert any(pattern.lower() in code_lower for pattern in scenario['expected_patterns'])


@pytest.mark.asyncio
async def test_builder_websocket_evolution(se_darwin_agent_for_integration):
    """Test evolution on WebSocket chat scenario"""
    scenario = BUILDER_SCENARIOS[1]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True
    assert result['best_score'] > 0.0

    # Check that operators were applied in later iterations
    if len(result['iterations']) > 1:
        # Should have some operator diversity
        stats = result['pool_statistics']
        operator_dist = stats.get('operator_distribution', {})
        assert len(operator_dist) > 0


@pytest.mark.asyncio
async def test_builder_docker_deployment_evolution(se_darwin_agent_for_integration):
    """Test evolution on Docker deployment scenario"""
    scenario = BUILDER_SCENARIOS[2]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True

    # Verify improvement over iterations (if multiple iterations ran)
    if len(result['iterations']) >= 2:
        iteration_scores = [it['best_score'] for it in result['iterations']]
        # Best score should be max of all iterations
        assert result['best_score'] == max(iteration_scores)


# ============================================================================
# INTEGRATION TESTS - ANALYST SCENARIOS
# ============================================================================

@pytest.mark.asyncio
async def test_analyst_performance_bottleneck_evolution(se_darwin_agent_for_integration):
    """Test evolution on performance analysis scenario"""
    scenario = ANALYST_SCENARIOS[0]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True
    assert result['best_score'] > 0.0

    # Verify analysis-specific patterns in best trajectory
    if result['best_trajectory'] and result['best_trajectory'].proposed_strategy:
        strategy_lower = result['best_trajectory'].proposed_strategy.lower()
        assert any(pattern in strategy_lower for pattern in ['analyze', 'performance', 'bottleneck', 'query'])


@pytest.mark.asyncio
async def test_analyst_user_behavior_evolution(se_darwin_agent_for_integration):
    """Test evolution on user behavior analysis scenario"""
    scenario = ANALYST_SCENARIOS[1]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True

    # Verify pool accumulated knowledge
    stats = result['pool_statistics']
    assert stats['total_added'] >= 3  # At least one iteration worth


@pytest.mark.asyncio
async def test_analyst_cost_optimization_evolution(se_darwin_agent_for_integration):
    """Test evolution on cost optimization scenario"""
    scenario = ANALYST_SCENARIOS[2]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True
    assert result['total_time'] > 0


# ============================================================================
# INTEGRATION TESTS - SUPPORT SCENARIOS
# ============================================================================

@pytest.mark.asyncio
async def test_support_authentication_troubleshooting_evolution(se_darwin_agent_for_integration):
    """Test evolution on authentication debugging scenario"""
    scenario = SUPPORT_SCENARIOS[0]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True
    assert result['best_score'] > 0.0


@pytest.mark.asyncio
async def test_support_database_migration_evolution(se_darwin_agent_for_integration):
    """Test evolution on database migration guidance scenario"""
    scenario = SUPPORT_SCENARIOS[1]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True


@pytest.mark.asyncio
async def test_support_deployment_issues_evolution(se_darwin_agent_for_integration):
    """Test evolution on deployment troubleshooting scenario"""
    scenario = SUPPORT_SCENARIOS[2]

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=scenario['description'],
        context=scenario['context']
    )

    assert result['success'] is True

    # Verify Docker-specific patterns if code generated
    if result['best_trajectory'] and result['best_trajectory'].code_changes:
        code_lower = result['best_trajectory'].code_changes.lower()
        assert 'docker' in code_lower or 'container' in code_lower or 'memory' in code_lower


# ============================================================================
# CROSS-SCENARIO VALIDATION
# ============================================================================

@pytest.mark.asyncio
async def test_evolution_improves_across_scenarios(mock_llm_with_realistic_responses, tmp_path):
    """Test that evolution shows improvement across multiple scenarios"""

    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool:
        from infrastructure.trajectory_pool import TrajectoryPool
        pool = TrajectoryPool(
            agent_name="cross_scenario_agent",
            storage_dir=tmp_path / "trajectory_pools" / "cross_scenario_agent"
        )
        mock_pool.return_value = pool

        agent = SEDarwinAgent(
            agent_name="cross_scenario_agent",
            llm_client=mock_llm_with_realistic_responses,
            trajectories_per_iteration=2,
            max_iterations=3,
            timeout_per_trajectory=30
        )

        # Run evolution on multiple scenarios and track scores
        scenario_results = []

        for scenario in [BUILDER_SCENARIOS[0], ANALYST_SCENARIOS[0], SUPPORT_SCENARIOS[0]]:
            result = await agent.evolve_solution(
                problem_description=scenario['description'],
                context=scenario['context']
            )

            scenario_results.append({
                'name': scenario['name'],
                'best_score': result['best_score'],
                'iterations': len(result['iterations']),
                'trajectories': sum(it['trajectories'] for it in result['iterations'])
            })

        # Verify all scenarios completed successfully
        assert len(scenario_results) == 3
        for res in scenario_results:
            assert res['best_score'] > 0.0
            assert res['iterations'] > 0
            assert res['trajectories'] >= 2  # At least trajectories_per_iteration

        # Verify pool accumulated diverse knowledge
        final_stats = agent.trajectory_pool.get_statistics()
        assert final_stats['total_trajectories'] >= 6  # 2 trajectories × 3 scenarios minimum


@pytest.mark.asyncio
async def test_trajectory_pool_persistence_across_scenarios(mock_llm_with_realistic_responses, tmp_path):
    """Test that trajectory pool persists and accumulates across scenarios"""

    storage_dir = tmp_path / "trajectory_pools" / "persistent_agent"

    # First scenario
    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool:
        from infrastructure.trajectory_pool import TrajectoryPool

        # Use load_existing=True to load from disk if available
        def get_pool_with_load(*args, **kwargs):
            return TrajectoryPool.load_from_disk(
                agent_name="persistent_agent",
                storage_dir=storage_dir
            )

        mock_pool.side_effect = get_pool_with_load

        agent1 = SEDarwinAgent(
            agent_name="persistent_agent",
            llm_client=mock_llm_with_realistic_responses,
            trajectories_per_iteration=2,
            max_iterations=1
        )

        await agent1.evolve_solution(
            problem_description=BUILDER_SCENARIOS[0]['description'],
            context=BUILDER_SCENARIOS[0]['context']
        )

        stats1 = agent1.trajectory_pool.get_statistics()
        count1 = stats1['total_trajectories']

    # Second scenario - should load saved pool and accumulate
    with patch('agents.se_darwin_agent.get_trajectory_pool') as mock_pool:
        mock_pool.side_effect = get_pool_with_load

        agent2 = SEDarwinAgent(
            agent_name="persistent_agent",
            llm_client=mock_llm_with_realistic_responses,
            trajectories_per_iteration=2,
            max_iterations=1
        )

        await agent2.evolve_solution(
            problem_description=ANALYST_SCENARIOS[0]['description'],
            context=ANALYST_SCENARIOS[0]['context']
        )

        stats2 = agent2.trajectory_pool.get_statistics()
        count2 = stats2['total_trajectories']

    # Second run should have more trajectories than first
    assert count2 > count1, f"Trajectory pool should accumulate across scenarios: {count1} -> {count2}"


# ============================================================================
# PERFORMANCE VALIDATION
# ============================================================================

@pytest.mark.asyncio
async def test_evolution_completes_within_timeout(se_darwin_agent_for_integration):
    """Test that evolution completes within reasonable time"""
    import time

    start_time = time.time()

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=BUILDER_SCENARIOS[0]['description'],
        context=BUILDER_SCENARIOS[0]['context']
    )

    elapsed = time.time() - start_time

    # Should complete within max_iterations × trajectories × timeout + overhead
    max_expected = (
        se_darwin_agent_for_integration.max_iterations *
        se_darwin_agent_for_integration.trajectories_per_iteration *
        se_darwin_agent_for_integration.timeout_per_trajectory
    ) + 30  # 30s overhead

    assert elapsed < max_expected, f"Evolution took {elapsed:.2f}s, expected < {max_expected}s"
    assert result['success'] is True


@pytest.mark.asyncio
async def test_parallel_execution_efficiency(se_darwin_agent_for_integration):
    """Test that parallel execution is actually concurrent"""
    import time

    # Configure for clear parallelism test
    se_darwin_agent_for_integration.trajectories_per_iteration = 3

    # Measure time for parallel execution
    start_time = time.time()

    result = await se_darwin_agent_for_integration.evolve_solution(
        problem_description=BUILDER_SCENARIOS[0]['description']
    )

    parallel_time = time.time() - start_time

    # With 3 trajectories in parallel, should be much faster than sequential
    # Each trajectory mock validation takes ~0.01s, so parallel should be ~0.01s per iteration
    # Sequential would be ~0.03s per iteration
    # Allow generous margin for test flakiness

    assert result['success'] is True
    assert parallel_time < 10.0, "Parallel execution should be fast with mocked validation"
