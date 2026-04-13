"""Tests for personnel router (Feature 168)."""
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
def admin_token(client):
    """Get an admin token for testing."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-admin", "tenant_id": "test-tenant", "role": "agency_admin"},
    )
    return response.json()["access_token"]


def test_list_personnel(client, founder_token):
    """Test listing personnel."""
    response = client.get(
        "/api/v1/personnel/",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_personnel_account(client, founder_token):
    """Test creating personnel account."""
    response = client.post(
        "/api/v1/personnel/",
        json={
            "user_id": "new-user",
            "tenant_id": "test-tenant",
            "primary_role": "viewer",
            "account_type": "user",
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "new-user"
    assert data["primary_role"] == "viewer"


def test_access_review_summary(client, admin_token):
    """Test access review summary."""
    response = client.get(
        "/api/v1/personnel/access/review",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_accounts" in data
    assert "privileged_accounts" in data
    assert "inactive_accounts" in data


def test_list_privileged_accounts(client, founder_token):
    """Test listing privileged accounts."""
    response = client.get(
        "/api/v1/personnel/access/privileged",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_assign_role(client, founder_token):
    """Test role assignment."""
    response = client.post(
        "/api/v1/personnel/roles/assign",
        json={
            "user_id": "test-user",
            "tenant_id": "test-tenant",
            "role": "viewer",
            "reason": "New team member",
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "viewer"
    assert data["reason"] == "New team member"


def test_create_recertification_campaign(client, founder_token):
    """Test creating access recertification campaign."""
    from datetime import datetime, timedelta

    due_date = (datetime.now() + timedelta(days=30)).isoformat()

    response = client.post(
        "/api/v1/personnel/recertification",
        json={
            "campaign_name": "Q2 2026 Recertification",
            "target_roles": ["agency_admin", "security_officer"],
            "due_at": due_date,
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_name"] == "Q2 2026 Recertification"


def test_detect_inactive_admins(client, founder_token):
    """Test detecting inactive admin accounts."""
    response = client.get(
        "/api/v1/personnel/detection/inactive?days=90",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_personnel_permissions(client):
    """Test personnel requires admin permissions."""
    # Get viewer token
    viewer_response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-viewer", "tenant_id": "test-tenant", "role": "viewer"},
    )
    viewer_token = viewer_response.json()["access_token"]

    # Viewer should not access personnel
    response = client.get(
        "/api/v1/personnel/",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
