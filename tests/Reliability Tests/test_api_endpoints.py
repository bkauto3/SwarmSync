"""
Backend API Endpoint Tests for SHADCN/UI Dashboard.

Tests all 6 REST API endpoints:
- /api/health
- /api/agents
- /api/halo/routes
- /api/casebank
- /api/traces
- /api/approvals
"""

import pytest
import requests
from typing import Dict, Any


# Configuration
API_BASE_URL = "http://localhost:8000"  # FastAPI backend
TIMEOUT = 5  # seconds


@pytest.fixture
def api_client():
    """Create API client session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""
    
    def test_health_check_success(self, api_client):
        """Test health check returns 200 OK."""
        response = api_client.get(f"{API_BASE_URL}/api/health", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_check_response_time(self, api_client):
        """Test health check responds within 1 second."""
        import time
        start = time.time()
        response = api_client.get(f"{API_BASE_URL}/api/health", timeout=TIMEOUT)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check took {elapsed:.2f}s (should be <1s)"


class TestAgentsEndpoint:
    """Tests for /api/agents endpoint."""
    
    def test_get_all_agents(self, api_client):
        """Test retrieving all agents."""
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 15, "Should have at least 15 agents"
    
    def test_agent_structure(self, api_client):
        """Test agent object structure."""
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        data = response.json()
        
        if len(data) > 0:
            agent = data[0]
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent
            assert "type" in agent
    
    def test_agent_status_values(self, api_client):
        """Test agent status values are valid."""
        response = api_client.get(f"{API_BASE_URL}/api/agents", timeout=TIMEOUT)
        data = response.json()
        
        valid_statuses = ["active", "idle", "busy", "error", "offline"]
        for agent in data:
            assert agent["status"] in valid_statuses


class TestHALORoutesEndpoint:
    """Tests for /api/halo/routes endpoint."""
    
    def test_get_halo_routes(self, api_client):
        """Test retrieving HALO routing data."""
        response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_halo_route_structure(self, api_client):
        """Test HALO route object structure."""
        response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        data = response.json()
        
        if len(data) > 0:
            route = data[0]
            assert "task_id" in route
            assert "selected_agent" in route
            assert "routing_time_ms" in route
            assert "confidence_score" in route
    
    def test_halo_routing_time(self, api_client):
        """Test HALO routing time is reasonable."""
        response = api_client.get(f"{API_BASE_URL}/api/halo/routes", timeout=TIMEOUT)
        data = response.json()
        
        for route in data:
            routing_time = route.get("routing_time_ms", 0)
            assert routing_time < 200, f"Routing time {routing_time}ms should be <200ms"


class TestCaseBankEndpoint:
    """Tests for /api/casebank endpoint."""
    
    def test_get_casebank_entries(self, api_client):
        """Test retrieving CaseBank memory entries."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_casebank_entry_structure(self, api_client):
        """Test CaseBank entry structure."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank", timeout=TIMEOUT)
        data = response.json()
        
        if len(data) > 0:
            entry = data[0]
            assert "id" in entry
            assert "task" in entry
            assert "solution" in entry
            assert "success_rate" in entry
    
    def test_casebank_pagination(self, api_client):
        """Test CaseBank pagination."""
        response = api_client.get(f"{API_BASE_URL}/api/casebank?limit=10", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10, "Should respect limit parameter"


class TestOTELTracesEndpoint:
    """Tests for /api/traces endpoint."""
    
    def test_get_otel_traces(self, api_client):
        """Test retrieving OTEL traces."""
        response = api_client.get(f"{API_BASE_URL}/api/traces", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_otel_trace_structure(self, api_client):
        """Test OTEL trace structure."""
        response = api_client.get(f"{API_BASE_URL}/api/traces", timeout=TIMEOUT)
        data = response.json()
        
        if len(data) > 0:
            trace = data[0]
            assert "trace_id" in trace
            assert "span_id" in trace
            assert "operation_name" in trace
            assert "duration_ms" in trace
    
    def test_otel_trace_filtering(self, api_client):
        """Test OTEL trace filtering by time range."""
        response = api_client.get(
            f"{API_BASE_URL}/api/traces?start_time=2025-11-04T00:00:00Z",
            timeout=TIMEOUT
        )
        assert response.status_code == 200


class TestHumanApprovalsEndpoint:
    """Tests for /api/approvals endpoint."""
    
    def test_get_pending_approvals(self, api_client):
        """Test retrieving pending human approvals."""
        response = api_client.get(f"{API_BASE_URL}/api/approvals", timeout=TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_approval_structure(self, api_client):
        """Test approval object structure."""
        response = api_client.get(f"{API_BASE_URL}/api/approvals", timeout=TIMEOUT)
        data = response.json()
        
        if len(data) > 0:
            approval = data[0]
            assert "id" in approval
            assert "task" in approval
            assert "agent" in approval
            assert "status" in approval
            assert "priority" in approval
    
    def test_approval_status_filter(self, api_client):
        """Test filtering approvals by status."""
        response = api_client.get(
            f"{API_BASE_URL}/api/approvals?status=pending",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        
        data = response.json()
        for approval in data:
            assert approval["status"] == "pending"


class TestAPIErrorHandling:
    """Tests for API error handling."""
    
    def test_invalid_endpoint_404(self, api_client):
        """Test invalid endpoint returns 404."""
        response = api_client.get(f"{API_BASE_URL}/api/invalid", timeout=TIMEOUT)
        assert response.status_code == 404
    
    def test_invalid_query_params(self, api_client):
        """Test invalid query parameters are handled gracefully."""
        response = api_client.get(
            f"{API_BASE_URL}/api/casebank?limit=invalid",
            timeout=TIMEOUT
        )
        # Should either return 400 or default to valid limit
        assert response.status_code in [200, 400]
    
    def test_cors_headers(self, api_client):
        """Test CORS headers are present."""
        response = api_client.options(f"{API_BASE_URL}/api/health", timeout=TIMEOUT)
        assert "Access-Control-Allow-Origin" in response.headers


class TestAPIPerformance:
    """Tests for API performance."""
    
    def test_all_endpoints_respond_within_5s(self, api_client):
        """Test all endpoints respond within 5 seconds."""
        import time
        
        endpoints = [
            "/api/health",
            "/api/agents",
            "/api/halo/routes",
            "/api/casebank",
            "/api/traces",
            "/api/approvals",
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = api_client.get(f"{API_BASE_URL}{endpoint}", timeout=TIMEOUT)
            elapsed = time.time() - start
            
            assert response.status_code == 200, f"{endpoint} failed"
            assert elapsed < 5.0, f"{endpoint} took {elapsed:.2f}s (should be <5s)"
    
    def test_concurrent_requests(self, api_client):
        """Test API handles concurrent requests."""
        import concurrent.futures
        
        def make_request():
            response = api_client.get(f"{API_BASE_URL}/api/health", timeout=TIMEOUT)
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert all(status == 200 for status in results), "All concurrent requests should succeed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

