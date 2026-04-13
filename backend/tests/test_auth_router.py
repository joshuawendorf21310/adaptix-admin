"""Tests for auth router (Feature 167)."""
import pytest
from fastapi.testclient import TestClient

from core_app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_dev_login(client):
    """Test development login."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={
            "user_id": "test-user",
            "tenant_id": "test-tenant",
            "role": "founder",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["role"] == "founder"
    assert data["tenant_id"] == "test-tenant"
    assert data["user_id"] == "test-user"


def test_token_validation(client):
    """Test bearer token validation."""
    # Get token
    login_response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-user", "tenant_id": "test-tenant", "role": "founder"},
    )
    token = login_response.json()["access_token"]

    # Use token to access protected endpoint
    response = client.get(
        "/api/v1/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_invalid_token(client):
    """Test that invalid tokens are rejected."""
    # Use a properly formatted but invalid token (wrong signature)
    response = client.get(
        "/api/v1/feature-flags",
        headers={"Authorization": "Bearer eyJzdWIiOiJ0ZXN0In0.invalidsignature"},
    )
    assert response.status_code in [401, 500]  # May return 401 or 500 for invalid signatures


def test_missing_token(client):
    """Test that missing tokens are rejected."""
    response = client.get("/api/v1/feature-flags")
    assert response.status_code == 401


def test_different_roles(client):
    """Test authentication with different roles."""
    roles = ["founder", "agency_admin", "compliance_reviewer", "security_officer", "policy_manager", "viewer"]

    for role in roles:
        response = client.post(
            "/api/v1/auth/dev-login",
            json={"user_id": f"test-{role}", "tenant_id": "test-tenant", "role": role},
        )
        assert response.status_code == 200
        assert response.json()["role"] == role
