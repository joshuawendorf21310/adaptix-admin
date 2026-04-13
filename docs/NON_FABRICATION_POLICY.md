# Non-Fabrication Runtime Documentation (Feature 193)

## Core Principle: Truthful Standalone Behavior

**Adaptix Admin does NOT fabricate audit evidence, security events, or cross-domain business records.**

This is a foundational architectural principle that ensures the system maintains integrity and trustworthiness in all operating modes.

## What This Means

### ✅ What IS Stored Locally

1. **Feature Flags** - Full local storage and management
   - Flags can be created, read, updated, deleted locally
   - Targeting, variants, schedules are stored locally
   - Audit trail of flag changes is maintained locally

2. **AI Policy Rules** - Full local storage and enforcement
   - Policy rules and configurations stored locally
   - Violations tracked locally
   - Model allowlists/denylists managed locally

3. **Personnel/Admin Accounts** - Local access management
   - Admin accounts and roles tracked locally
   - Role assignments managed locally
   - Access recertification campaigns stored locally

4. **Local Admin Actions** - Admin operations within this system
   - Changes to feature flags
   - AI policy rule modifications
   - Personnel account updates

### ❌ What is NOT Fabricated

1. **Cross-Tenant Audit Evidence**
   - The system returns **truthful empty state** when no upstream source is connected
   - It does NOT generate fake audit events to appear functional
   - API responses clearly indicate `"mode": "standalone-shell"`

2. **Upstream Security Events**
   - No fake login attempts
   - No fabricated suspicious auth events
   - No synthetic security findings

3. **Business Domain Events**
   - No fake patient records
   - No synthetic clinical events
   - No fabricated compliance violations from upstream systems

4. **Legal Hold Evidence**
   - Legal holds are tracked locally for admin purposes
   - Actual evidence preservation requires upstream connection
   - No fake evidence packets are generated

## API Response Patterns

### Truthful Empty State

When no upstream evidence source is connected:

```json
{
  "items": [],
  "total": 0,
  "mode": "standalone-shell",
  "message": "No upstream audit evidence source connected. Connect for full audit trail."
}
```

### Connected State

When upstream is connected:

```json
{
  "items": [...],
  "total": 1234,
  "mode": "connected",
  "upstream": {
    "source": "audit-db",
    "last_sync": "2026-04-13T12:00:00Z"
  }
}
```

### Degraded State

When upstream becomes unavailable:

```json
{
  "items": [],
  "total": 0,
  "mode": "degraded-standalone",
  "message": "Upstream temporarily unavailable. Falling back to standalone mode.",
  "upstream": {
    "source": "audit-db",
    "status": "unavailable",
    "last_successful_sync": "2026-04-13T11:00:00Z"
  }
}
```

## Enforcement Mechanisms

### 1. Service Layer Guards

```python
class AuditService:
    def list_events(self, ...):
        if not self._upstream_connected:
            # Return truthful empty state
            return self._empty_standalone_response()

        # Only query upstream if connected
        return self._query_upstream(...)
```

### 2. API Documentation

All endpoints that require upstream connectivity are documented with:

```python
@router.get("/api/v1/audit/events")
async def list_audit_events(...) -> dict:
    """
    List audit events with filtering.

    **Mode: Standalone Shell**
    Returns empty state when no upstream audit source is connected.
    This endpoint does NOT fabricate audit evidence.
    """
```

### 3. Health Checks

```python
@router.get("/health/startup")
async def startup_health():
    return {
        "mode": "standalone-shell",
        "upstream_connected": False,
        "capabilities": {
            "local_admin_audit": True,
            "upstream_tenant_audit": False,
        }
    }
```

## Testing Non-Fabrication

### Unit Tests

```python
def test_audit_events_truthful_empty_state():
    """Verify audit service returns empty state without upstream."""
    service = AuditService(upstream_db_url=None)
    result = service.list_events()

    assert result["items"] == []
    assert result["mode"] == "standalone-shell"
    assert "fabricated" not in str(result).lower()
```

### Integration Tests

```python
def test_no_fake_audit_evidence():
    """Verify no audit events exist without upstream connection."""
    response = client.get("/api/v1/audit/events")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["mode"] == "standalone-shell"
```

## Compliance and Audit

This non-fabrication policy supports:

1. **SOC 2 Type II**: Accurate representation of system capabilities
2. **HIPAA**: No fabrication of PHI or clinical records
3. **GDPR**: No synthetic personal data
4. **Internal Audits**: Truthful system state for auditors

## Why This Matters

1. **Trust**: Users can trust the data they see is real
2. **Compliance**: Auditors can rely on accurate system state
3. **Safety**: No risk of acting on fabricated data
4. **Integrity**: System maintains honesty about its capabilities

## Violations of This Policy

The following would violate the non-fabrication policy:

❌ Generating fake audit events to make the system "look active"
❌ Returning sample/demo data without clear indicators
❌ Fabricating compliance metrics to appear compliant
❌ Creating synthetic security events for demonstration
❌ Generating fake user data or business records

## Allowed Demo/Test Data

✅ Explicitly marked sample data in development mode
✅ Test data in dedicated test environments
✅ Fixtures in automated tests
✅ Documentation examples clearly marked as examples

All test/demo data must:
- Be clearly labeled as non-production
- Never mix with real data
- Be isolated to development environments
- Include mode indicators in API responses
