"""Tests for founder security router (Feature 180)."""
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


def test_security_dashboard(client, founder_token):
    """Test founder security dashboard."""
    response = client.get(
        "/api/v1/founder/security/dashboard",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "security_posture" in data
    assert "auth_summary" in data
    assert "feature_flag_summary" in data
    assert "audit_summary" in data


def test_security_posture(client, founder_token):
    """Test security posture summary."""
    response = client.get(
        "/api/v1/founder/security/posture",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "operational"
    assert "recommendations" in data


def test_auth_config(client, founder_token):
    """Test auth configuration summary."""
    response = client.get(
        "/api/v1/founder/security/auth-config",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "dev_auth_enabled" in data
    assert "bearer_token_validation" in data


def test_feature_flag_risks(client, founder_token):
    """Test feature flag risk summary."""
    response = client.get(
        "/api/v1/founder/security/feature-flag-risks",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_flags" in data
    assert "stale_flags" in data
    assert "risk_level" in data


def test_audit_evidence_summary(client, founder_token):
    """Test audit evidence summary."""
    response = client.get(
        "/api/v1/founder/security/audit-evidence",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "standalone-shell"
    assert data["upstream_connected"] is False


def test_legal_hold_summary(client, founder_token):
    """Test legal hold summary."""
    response = client.get(
        "/api/v1/founder/security/legal-holds",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_holds" in data
    assert "active_holds" in data


def test_privileged_user_summary(client, founder_token):
    """Test privileged user summary."""
    response = client.get(
        "/api/v1/founder/security/privileged-users",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_privileged" in data


def test_stale_session_summary(client, founder_token):
    """Test stale session summary."""
    response = client.get(
        "/api/v1/founder/security/stale-sessions",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "inactive_accounts_90_days" in data


def test_suspicious_auth_summary(client, founder_token):
    """Test suspicious auth summary."""
    response = client.get(
        "/api/v1/founder/security/suspicious-auth",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data


def test_founder_only_access(client):
    """Test that security dashboard is founder-only."""
    # Get admin token
    admin_response = client.post(
        "/api/v1/auth/dev-login",
        json={"user_id": "test-admin", "tenant_id": "test-tenant", "role": "agency_admin"},
    )
    admin_token = admin_response.json()["access_token"]

    # Admin should not access founder security
    response = client.get(
        "/api/v1/founder/security/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403
