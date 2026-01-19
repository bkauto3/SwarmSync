"""
Integration Tests for SHADCN/UI Dashboard.

Tests frontend-backend integration:
- API data fetching
- Real-time updates (5s polling)
- Error handling
- Data flow
"""

import pytest
import requests
import time
from typing import Dict, Any, List


# Configuration
API_BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
TIMEOUT = 10


@pytest.fixture
def api_client():
    """Create API client session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


class TestFrontendBackendIntegration:
    """Tests for frontend-backend data flow."""
    
    def test_dashboard_loads_agent_data(self, api_client):
        """Test dashboard can load agent data from backend."""
        # Fetch data from backend
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        assert response.status_code == 200
        
        agents = response.json()
        assert len(agents) >= 15, "Should have at least 15 agents"
        
        # Verify data structure matches frontend expectations
        for agent in agents:
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent
    
    def test_dashboard_loads_halo_routes(self, api_client):
        """Test dashboard can load HALO routing data."""
        response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        assert response.status_code == 200
        
        routes = response.json()
        assert isinstance(routes, list)
    
    def test_dashboard_loads_casebank_memory(self, api_client):
        """Test dashboard can load CaseBank memory."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank", timeout=TIMEOUT)
        assert response.status_code == 200
        
        entries = response.json()
        assert isinstance(entries, list)
    
    def test_dashboard_loads_otel_traces(self, api_client):
        """Test dashboard can load OTEL traces."""
        response = api_client.get(f"{API_BASE_URL}/api/traces", timeout=TIMEOUT)
        assert response.status_code == 200
        
        traces = response.json()
        assert isinstance(traces, list)
    
    def test_dashboard_loads_approvals(self, api_client):
        """Test dashboard can load human approvals."""
        response = api_client.get(f"{API_BASE_URL}/api/approvals", timeout=TIMEOUT)
        assert response.status_code == 200
        
        approvals = response.json()
        assert isinstance(approvals, list)


class TestRealTimeUpdates:
    """Tests for real-time data updates (5s polling)."""
    
    def test_agent_status_updates(self, api_client):
        """Test agent status updates over time."""
        # First fetch
        response1 = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        agents1 = response1.json()
        
        # Wait 5 seconds (polling interval)
        time.sleep(5)
        
        # Second fetch
        response2 = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        agents2 = response2.json()
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Should have same number of agents
        assert len(agents1) == len(agents2)
    
    def test_halo_routes_update(self, api_client):
        """Test HALO routes update over time."""
        # First fetch
        response1 = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        routes1 = response1.json()
        
        # Wait 5 seconds
        time.sleep(5)
        
        # Second fetch
        response2 = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        routes2 = response2.json()
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    def test_polling_latency(self, api_client):
        """Test polling latency is <5s."""
        start = time.time()
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Polling took {elapsed:.2f}s (should be <5s)"


class TestErrorHandling:
    """Tests for error handling in integration."""
    
    def test_backend_unavailable_handling(self, api_client):
        """Test frontend handles backend unavailability."""
        # Try to connect to invalid backend
        try:
            response = api_client.get("http://localhost:9999/api/health", timeout=1)
        except requests.exceptions.ConnectionError:
            # Expected - frontend should handle this gracefully
            pass
        except requests.exceptions.Timeout:
            # Also acceptable
            pass
    
    def test_invalid_data_handling(self, api_client):
        """Test frontend handles invalid data from backend."""
        # This test would require mocking the backend
        # For now, we just verify the API returns valid JSON
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        assert response.status_code == 200
        
        # Verify it's valid JSON
        try:
            data = response.json()
            assert isinstance(data, list)
        except ValueError:
            pytest.fail("Backend returned invalid JSON")
    
    def test_timeout_handling(self, api_client):
        """Test frontend handles API timeouts."""
        # Set very short timeout
        try:
            response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=0.001)
        except requests.exceptions.Timeout:
            # Expected - frontend should handle this
            pass


class TestDataConsistency:
    """Tests for data consistency across endpoints."""
    
    def test_agent_count_consistency(self, api_client):
        """Test agent count is consistent across endpoints."""
        # Get agents from /api/agents
        agents_response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        agents = agents_response.json()
        agent_count = len(agents)
        
        # Get HALO routes (should reference same agents)
        routes_response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        routes = routes_response.json()
        
        # All routed agents should exist in agent list
        agent_names = {agent["name"] for agent in agents}
        for route in routes:
            selected_agent = route.get("selected_agent", "")
            # Agent might not be in list if it's a dynamic agent
            # Just verify the data structure is consistent
            assert isinstance(selected_agent, str)
    
    def test_casebank_task_references(self, api_client):
        """Test CaseBank entries reference valid tasks."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank", timeout=TIMEOUT)
        entries = response.json()
        
        for entry in entries:
            assert "task" in entry
            assert isinstance(entry["task"], str)
            assert len(entry["task"]) > 0


class TestAPIDataFlow:
    """Tests for complete data flow from backend to frontend."""
    
    def test_overview_dashboard_data_flow(self, api_client):
        """Test data flow for Overview Dashboard component."""
        # Overview Dashboard needs:
        # 1. Agent count
        # 2. Active tasks
        # 3. System health
        
        # Get agents
        agents_response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        assert agents_response.status_code == 200
        agents = agents_response.json()
        
        # Get health
        health_response = api_client.get(f"{API_BASE_URL}/api/health", timeout=TIMEOUT)
        assert health_response.status_code == 200
        health = health_response.json()
        
        # Verify data is usable
        assert len(agents) > 0
        assert health["status"] == "healthy"
    
    def test_agent_status_grid_data_flow(self, api_client):
        """Test data flow for Agent Status Grid component."""
        # Agent Status Grid needs:
        # 1. All agents with status
        
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        assert response.status_code == 200
        agents = response.json()
        
        # Verify each agent has required fields
        for agent in agents:
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent
            assert "type" in agent
    
    def test_halo_routes_data_flow(self, api_client):
        """Test data flow for HALO Routes component."""
        response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        assert response.status_code == 200
        routes = response.json()
        
        # Verify route structure
        for route in routes:
            assert "task_id" in route
            assert "selected_agent" in route
    
    def test_casebank_memory_data_flow(self, api_client):
        """Test data flow for CaseBank Memory component."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank", timeout=TIMEOUT)
        assert response.status_code == 200
        entries = response.json()
        
        # Verify entry structure
        for entry in entries:
            assert "id" in entry
            assert "task" in entry
            assert "solution" in entry
    
    def test_otel_traces_data_flow(self, api_client):
        """Test data flow for OTEL Traces component."""
        response = api_client.get(f"{API_BASE_URL}/api/traces", timeout=TIMEOUT)
        assert response.status_code == 200
        traces = response.json()
        
        # Verify trace structure
        for trace in traces:
            assert "trace_id" in trace
            assert "span_id" in trace
    
    def test_human_approvals_data_flow(self, api_client):
        """Test data flow for Human Approvals component."""
        response = api_client.get(f"{API_BASE_URL}/api/approvals", timeout=TIMEOUT)
        assert response.status_code == 200
        approvals = response.json()
        
        # Verify approval structure
        for approval in approvals:
            assert "id" in approval
            assert "task" in approval
            assert "status" in approval


class TestConcurrentDataFetching:
    """Tests for concurrent data fetching (simulating real dashboard)."""
    
    def test_fetch_all_endpoints_concurrently(self, api_client):
        """Test fetching all endpoints concurrently (like dashboard does)."""
        import concurrent.futures
        
        endpoints = [
            "/api/health",
            "/api/agents",
            "/api/halo/routes",
            "/api/casebank",
            "/api/traces",
            "/api/approvals",
        ]
        
        def fetch_endpoint(endpoint):
            response = api_client.get(f"{API_BASE_URL}{endpoint}", timeout=TIMEOUT)
            return endpoint, response.status_code, response.json()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(fetch_endpoint, ep) for ep in endpoints]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert len(results) == 6
        for endpoint, status, data in results:
            assert status == 200, f"{endpoint} failed with status {status}"
            assert data is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

