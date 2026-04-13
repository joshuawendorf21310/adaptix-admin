# Upstream Evidence Integration Documentation (Feature 192)

## Overview

Adaptix Admin is designed as a standalone governance system that can optionally connect to upstream evidence sources for real audit data, compliance tracking, and cross-tenant governance.

## Current State: Standalone Mode

The system currently operates in **standalone-shell mode**:

- ✅ Feature flags: Stored locally in `data/feature_flags_extended.json`
- ✅ AI policies: Stored locally in `data/ai_policy_rules.json`
- ✅ Personnel: Stored locally in `data/admin_accounts.json`
- ⚠️ Audit events: Returns truthful empty state (no fabricated evidence)
- ⚠️ Legal holds: Local tracking only, no upstream enforcement
- ⚠️ Replay requests: Local queueing, no upstream execution

## Integration Architecture

```
┌─────────────────────────────────────────────┐
│         Adaptix Admin (This System)         │
│                                             │
│  ┌─────────────┐  ┌────────────────────┐   │
│  │ Feature     │  │ AI Policy          │   │
│  │ Flags       │  │ Management         │   │
│  │ (Local)     │  │ (Local)            │   │
│  └─────────────┘  └────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │   Audit & Evidence Integration      │   │
│  │   (Upstream Connection Required)    │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                     ↓
         ┌───────────────────────┐
         │  Upstream Services    │
         ├───────────────────────┤
         │ • Audit Database      │
         │ • Event Stream        │
         │ • Compliance Store    │
         │ • Evidence Vault      │
         └───────────────────────┘
```

## Integration Points

### 1. Audit Evidence Source

**Purpose**: Real-time audit event ingestion and query

**Required Changes**:

1. Update `core_app/services/audit_service.py`:

```python
class AuditService:
    def __init__(self, upstream_db_url: str | None = None):
        self._upstream_db = None
        if upstream_db_url:
            # Connect to upstream audit database
            from sqlalchemy import create_engine
            self._upstream_db = create_engine(upstream_db_url)

    def list_events(self, ...):
        if self._upstream_db:
            # Query upstream database
            return self._query_upstream_events(...)
        else:
            # Truthful standalone mode
            return self._empty_standalone_response()
```

2. Add database models for audit events:

```python
# core_app/models/audit_db.py
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AuditEventDB(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    actor_user_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    details = Column(JSON)
```

3. Configure connection:

```bash
ADAPTIX_ADMIN_AUDIT_DB_URL=postgresql://user:pass@host:5432/audit
```

### 2. Event Stream Integration

**Purpose**: Real-time event ingestion from message queue

**Supported Sources**:
- Kafka
- AWS Kinesis
- Azure Event Hubs
- RabbitMQ

**Implementation**:

```python
# core_app/services/event_stream.py
from kafka import KafkaConsumer

class EventStreamConsumer:
    def __init__(self, bootstrap_servers: str, topic: str):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

    async def consume_events(self):
        for message in self.consumer:
            event = message.value
            await audit_service.create_event_local(
                event_type=event['event_type'],
                action=event['action'],
                ...
            )
```

### 3. Legal Hold Enforcement

**Purpose**: Upstream legal hold enforcement and evidence preservation

**Integration Steps**:

1. Implement legal hold webhook:

```python
@router.post("/legal-holds/{hold_id}/enforce")
async def enforce_legal_hold_upstream(hold_id: str):
    hold = audit_service.get_legal_hold(hold_id)

    # Call upstream enforcement API
    response = await upstream_client.post(
        f"{upstream_url}/legal-holds/enforce",
        json={
            "hold_id": hold_id,
            "custodians": hold["custodian_user_ids"],
            "scope": hold["scope"]
        }
    )

    return response.json()
```

2. Configure upstream endpoint:

```bash
ADAPTIX_ADMIN_UPSTREAM_LEGAL_HOLD_URL=https://compliance-api.example.com
```

### 4. Replay Execution

**Purpose**: Execute audit event replays against upstream systems

**Integration Steps**:

1. Implement replay executor:

```python
async def execute_replay(replay_id: str):
    replay = audit_service.get_replay_request(replay_id)

    if replay["dry_run"]:
        # Simulate without execution
        return await simulate_replay(replay)

    if replay["status"] != "authorized":
        raise ValueError("Replay not authorized")

    # Execute against upstream
    results = []
    for event_id in replay["event_ids"]:
        event = await upstream_client.get_event(event_id)
        result = await upstream_client.replay_event(event)
        results.append(result)

    return results
```

## Migration Checklist

When connecting upstream evidence sources:

- [ ] Configure database connection
- [ ] Test database connectivity
- [ ] Migrate existing local data (if needed)
- [ ] Update health checks to verify upstream connection
- [ ] Update API responses to remove "standalone-shell" mode indicators
- [ ] Enable real-time event ingestion
- [ ] Configure legal hold enforcement
- [ ] Enable replay execution
- [ ] Update monitoring and alerting
- [ ] Verify audit trail completeness
- [ ] Test failover to standalone mode if upstream is unavailable

## Graceful Degradation

The system must gracefully degrade if upstream is unavailable:

```python
def list_events(self, ...):
    try:
        if self._upstream_db:
            return self._query_upstream_events(...)
    except Exception as e:
        logger.warning(f"Upstream unavailable, falling back to standalone: {e}")

    # Fall back to standalone mode
    return {
        "items": [],
        "mode": "degraded-standalone",
        "message": "Upstream temporarily unavailable"
    }
```

## Testing Integration

1. **Unit Tests**: Mock upstream connections
2. **Integration Tests**: Use test database
3. **Load Tests**: Verify performance with real data volume
4. **Failover Tests**: Simulate upstream outages

## Security Considerations

- Use mutual TLS for upstream connections
- Rotate database credentials regularly
- Encrypt data in transit and at rest
- Audit all upstream API calls
- Implement rate limiting
- Use least-privilege database accounts
