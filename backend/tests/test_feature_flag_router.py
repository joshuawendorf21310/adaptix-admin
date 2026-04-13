"""Tests for feature flag router (Feature 165)."""
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
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    """Get an admin token for testing."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-admin", "tenant_id": "test-tenant", "role": "agency_admin"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_feature_flag(client, founder_token):
    """Test feature flag creation."""
    response = client.post(
        "/api/v1/feature-flags",
        json={
            "flag_key": "test_flag",
            "description": "Test flag",
            "enabled": False,
            "tenant_id": None,
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["flag_key"] == "test_flag"
    assert data["enabled"] is False
    assert "id" in data


def test_list_feature_flags(client, founder_token):
    """Test listing feature flags."""
    response = client.get(
        "/api/v1/feature-flags",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_toggle_feature_flag(client, founder_token):
    """Test toggling a feature flag."""
    # Create flag
    create_response = client.post(
        "/api/v1/feature-flags",
        json={"flag_key": "toggle_test", "enabled": False},
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    flag_id = create_response.json()["id"]

    # Toggle flag
    toggle_response = client.post(
        f"/api/v1/feature-flags/{flag_id}/toggle",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json()["enabled"] is True


def test_evaluate_feature_flag(client, founder_token):
    """Test feature flag evaluation."""
    # Create flag
    client.post(
        "/api/v1/feature-flags",
        json={"flag_key": "eval_test", "enabled": True, "config": {"max_users": 100}},
        headers={"Authorization": f"Bearer {founder_token}"},
    )

    # Evaluate flag
    response = client.get(
        "/api/v1/feature-flags/evaluate/eval_test",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["config"]["max_users"] == 100


def test_feature_flag_audit_trail(client, founder_token):
    """Test feature flag audit trail."""
    # Create flag
    create_response = client.post(
        "/api/v1/feature-flags",
        json={"flag_key": "audit_test", "enabled": False},
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    flag_id = create_response.json()["id"]

    # Get audit trail
    response = client.get(
        f"/api/v1/feature-flags/{flag_id}/audit",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    audit = response.json()
    assert len(audit) > 0
    assert audit[0]["action"] == "created"


def test_unauthorized_access(client):
    """Test that endpoints require authentication."""
    response = client.get("/api/v1/feature-flags")
    assert response.status_code == 401


def test_permission_boundary(client, admin_token):
    """Test permission boundaries for admin vs founder."""
    # Admin should not be able to create global flags
    response = client.post(
        "/api/v1/feature-flags",
        json={"flag_key": "global_flag", "enabled": False, "tenant_id": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403
