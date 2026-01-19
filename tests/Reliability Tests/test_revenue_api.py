from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Ensure backend package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "genesis-dashboard"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.api import app  # type: ignore  # noqa: E402


client = TestClient(app)


def test_revenue_metrics_endpoint():
    response = client.get("/api/revenue/metrics")
    assert response.status_code == 200
    payload = response.json()

    assert "metrics" in payload
    assert "businesses" in payload
    assert "trends" in payload

    metrics = payload["metrics"]
    assert metrics["total_revenue"] >= 0
    assert metrics["mrr"] >= 0
    assert isinstance(metrics["last_updated"], str)

    businesses = payload["businesses"]
    assert businesses, "expected at least one business entry"
    required_keys = {
        "business_id",
        "business_name",
        "business_type",
        "revenue_total",
        "revenue_current_month",
        "projected_mrr",
        "confidence_score",
        "payment_count",
        "status",
    }
    for entry in businesses:
        assert required_keys.issubset(entry.keys())


def test_revenue_analytics_endpoint():
    response = client.get("/api/revenue/analytics")
    assert response.status_code == 200
    payload = response.json()

    assert "roi_by_business" in payload
    assert payload["roi_by_business"], "expected ROI entries"
    assert "revenue_forecast" in payload
    assert payload["revenue_forecast"], "expected forecast entries"

    churn = payload["churn_analysis"]
    assert churn["total_businesses"] >= churn["active_businesses"]
    assert 0 <= churn["retention_rate"] <= 100
