"""Tests for health router and startup checks (Feature 164)."""
import pytest
from fastapi.testclient import TestClient

from core_app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test basic health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["service"] == "adaptix-admin"
    assert "timestamp" in data


def test_startup_health(client):
    """Test startup health checks."""
    response = client.get("/health/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["mode"] == "standalone-shell"
    assert "services" in data
    assert "checks" in data


def test_readiness_probe(client):
    """Test Kubernetes readiness probe."""
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "services" in data


def test_liveness_probe(client):
    """Test Kubernetes liveness probe."""
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True
    assert "timestamp" in data


def test_service_checks(client):
    """Test individual service health checks."""
    response = client.get("/health/startup")
    data = response.json()

    services = data["services"]
    assert "feature_flags" in services
    assert "audit" in services
    assert "ai_policy" in services
    assert "personnel" in services
