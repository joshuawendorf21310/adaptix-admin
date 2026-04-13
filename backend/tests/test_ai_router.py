"""Tests for AI policy router (Feature 169)."""
import pytest
from fastapi.testclient import TestClient

from core_app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def founder_token(client):
    """Get a founder token for testing."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-founder", "tenant_id": "test-tenant", "role": "founder"},
    )
    return response.json()["access_token"]


@pytest.fixture
def policy_manager_token(client):
    """Get a policy manager token for testing."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-policy", "tenant_id": "test-tenant", "role": "policy_manager"},
    )
    return response.json()["access_token"]


def test_ai_policy_dashboard(client, founder_token):
    """Test AI policy dashboard."""
    response = client.get(
        "/api/v1/ai/dashboard",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_rules" in data
    assert "active_rules" in data
    assert "total_violations" in data


def test_create_ai_policy_rule(client, policy_manager_token):
    """Test creating an AI policy rule."""
    response = client.post(
        "/api/v1/ai/policies",
        json={
            "name": "Test Safety Rule",
            "rule_type": "output_safety",
            "description": "Ensure safe outputs",
            "config": {"max_toxicity": 0.1},
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Safety Rule"
    assert data["rule_type"] == "output_safety"
    assert data["status"] == "draft"


def test_list_ai_policy_rules(client, policy_manager_token):
    """Test listing AI policy rules."""
    response = client.get(
        "/api/v1/ai/policies",
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_simulate_ai_policy_rule(client, policy_manager_token):
    """Test simulating an AI policy rule."""
    # Create rule
    create_response = client.post(
        "/api/v1/ai/policies",
        json={
            "name": "Simulation Test",
            "rule_type": "model_allowlist",
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    rule_id = create_response.json()["id"]

    # Simulate rule
    response = client.post(
        f"/api/v1/ai/policies/{rule_id}/simulate",
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "simulation_complete"


def test_activate_ai_policy_rule(client, founder_token):
    """Test activating an AI policy rule (founder only)."""
    # Create rule
    create_response = client.post(
        "/api/v1/ai/policies",
        json={
            "name": "Activation Test",
            "rule_type": "redaction",
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    rule_id = create_response.json()["id"]

    # Activate rule
    response = client.post(
        f"/api/v1/ai/policies/{rule_id}/activate",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


def test_add_ai_model(client, policy_manager_token):
    """Test adding an AI model to allowlist."""
    response = client.post(
        "/api/v1/ai/models",
        json={
            "model_id": "gpt-4",
            "model_name": "GPT-4",
            "provider": "OpenAI",
            "allowed": True,
            "requires_human_review": False,
        },
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["model_id"] == "gpt-4"
    assert data["allowed"] is True


def test_list_ai_violations(client, policy_manager_token):
    """Test listing AI policy violations."""
    response = client.get(
        "/api/v1/ai/violations",
        headers={"Authorization": f"Bearer {policy_manager_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_ai_policy_permissions(client):
    """Test AI policy requires proper permissions."""
    # Get viewer token
    viewer_response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-viewer", "tenant_id": "test-tenant", "role": "viewer"},
    )
    viewer_token = viewer_response.json()["access_token"]

    # Viewer should not access AI policies
    response = client.get(
        "/api/v1/ai/dashboard",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
