"""Tests for audit router (Feature 166)."""
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
def compliance_token(client):
    """Get a compliance officer token for testing."""
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-compliance", "tenant_id": "test-tenant", "role": "compliance_reviewer"},
    )
    return response.json()["access_token"]


def test_audit_health(client, founder_token):
    """Test audit service health check."""
    response = client.get(
        "/api/v1/audit/health",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "standalone-shell"


def test_audit_status(client, founder_token):
    """Test audit connection status."""
    response = client.get(
        "/api/v1/audit/status",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "standalone-shell"
    assert data["upstream_connected"] is False


def test_list_audit_events_truthful_empty_state(client, founder_token):
    """Test that audit events return truthful empty state (Feature 172)."""
    response = client.get(
        "/api/v1/audit/events",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["mode"] == "standalone-shell"
    assert "No upstream audit evidence source connected" in data["message"]


def test_create_legal_hold(client, founder_token):
    """Test legal hold creation (Feature 174)."""
    response = client.post(
        "/api/v1/audit/legal-holds",
        json={
            "case_id": "CASE-001",
            "scope": "tenant-wide",
            "reason": "Regulatory investigation",
            "custodian_user_ids": ["user1", "user2"],
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"] == "CASE-001"
    assert data["status"] == "active"
    assert "id" in data


def test_list_legal_holds(client, founder_token):
    """Test listing legal holds."""
    response = client.get(
        "/api/v1/audit/legal-holds",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_release_legal_hold(client, founder_token):
    """Test releasing a legal hold."""
    # Create hold
    create_response = client.post(
        "/api/v1/audit/legal-holds",
        json={"case_id": "CASE-002", "scope": "user", "reason": "Test"},
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    hold_id = create_response.json()["id"]

    # Release hold
    response = client.post(
        f"/api/v1/audit/legal-holds/{hold_id}/release",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "released"


def test_create_replay_request(client, founder_token):
    """Test replay request creation (Feature 175)."""
    response = client.post(
        "/api/v1/audit/replay-requests",
        json={
            "reason": "Test replay",
            "webhook_id": "webhook-123",
            "dry_run": True,
        },
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["reason"] == "Test replay"
    assert data["dry_run"] is True
    assert data["status"] == "pending"


def test_audit_export(client, compliance_token):
    """Test audit export (Feature 178)."""
    response = client.post(
        "/api/v1/audit/export?format=json",
        headers={"Authorization": f"Bearer {compliance_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "json"
    assert data["mode"] == "standalone-shell"


def test_legal_hold_permissions(client):
    """Test legal hold requires proper permissions."""
    # Get viewer token
    viewer_response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-viewer", "tenant_id": "test-tenant", "role": "viewer"},
    )
    viewer_token = viewer_response.json()["access_token"]

    # Viewer should not be able to create legal holds
    response = client.post(
        "/api/v1/audit/legal-holds",
        json={"case_id": "CASE-003", "scope": "test", "reason": "Test"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
