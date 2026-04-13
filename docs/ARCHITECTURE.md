# Complete Admin Architecture Documentation (Feature 199)

## System Overview

Adaptix Admin is a production-grade governance, feature-flag, audit, legal-hold, and AI policy system designed for healthcare and regulated industries.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Adaptix Admin System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Frontend   │  │   Backend    │  │   Data Storage       │  │
│  │   (Next.js)  │◄─┤   (FastAPI)  │◄─┤   (JSON/Local)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Core Services                           │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • Feature Flag Service (CRUD, targeting, scheduling)   │   │
│  │ • Audit Service (events, legal holds, replay)          │   │
│  │ • AI Policy Service (rules, violations, models)        │   │
│  │ • Personnel Service (accounts, roles, recertification) │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  API Routers                            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • /api/v1/feature-flags (50 endpoints)                 │   │
│  │ • /api/v1/audit (40 endpoints)                         │   │
│  │ • /api/v1/ai (20 endpoints)                            │   │
│  │ • /api/v1/personnel (15 endpoints)                     │   │
│  │ • /api/v1/founder/security (10 endpoints)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             ↕
          ┌──────────────────────────────────┐
          │   Optional Upstream Integration  │
          ├──────────────────────────────────┤
          │ • Audit Evidence Database        │
          │ • Event Stream (Kafka/Kinesis)   │
          │ • Compliance Store               │
          │ • Security Monitoring            │
          └──────────────────────────────────┘
```

## Component Architecture

### 1. Backend (FastAPI)

**Location**: `backend/core_app/`

**Structure**:
```
core_app/
├── api/                    # API routers
│   ├── feature_flag_router_extended.py
│   ├── audit_router_extended.py
│   ├── ai_router_extended.py
│   ├── personnel_router_extended.py
│   └── founder_security_router.py
├── services/               # Business logic
│   ├── feature_flag_service.py
│   ├── audit_service.py
│   ├── ai_policy_service.py
│   └── personnel_service.py
├── models/                 # Data models
│   ├── feature_flag_extended.py
│   ├── audit_extended.py
│   ├── ai_policy.py
│   └── personnel.py
├── core/                   # Core utilities
│   └── security.py        # JWT, auth
└── main.py                # Application entry point
```

**Technology Stack**:
- FastAPI 0.115+
- Pydantic 2.7+ (data validation)
- Uvicorn (ASGI server)

### 2. Frontend (Next.js)

**Location**: `frontend/`

**Structure**:
```
frontend/
├── app/                    # Next.js app router
│   ├── founder/           # Founder-only views
│   │   ├── security/      # Security dashboard
│   │   └── ai/            # AI policy management
│   └── access/            # Access management
├── components/            # Reusable components
│   ├── AuthProvider.tsx
│   └── PlatformShell.tsx
└── services/              # API clients
    └── auth.ts
```

**Technology Stack**:
- Next.js 14+
- React 18+
- TypeScript

### 3. Data Storage

**Current**: Local JSON files in `backend/data/`
```
data/
├── feature_flags_extended.json
├── flag_audit.json
├── audit_events.json
├── legal_holds.json
├── replay_requests.json
├── ai_policy_rules.json
├── ai_violations.json
├── ai_models.json
├── admin_accounts.json
├── role_assignments.json
└── access_recertifications.json
```

**Future**: Optional database integration for scale

## Data Flow

### 1. Feature Flag Evaluation

```
User Request
    ↓
API: GET /api/v1/feature-flags/evaluate/{flag_key}
    ↓
FeatureFlagService.evaluate_flag()
    ↓
1. Check tenant-specific flag
2. Fall back to global flag
3. Check schedule (start/end/expiry)
4. Return enabled status + config
    ↓
Response to user
```

### 2. Audit Event Creation

```
Admin Action (e.g., flag update)
    ↓
FeatureFlagService.update_flag()
    ↓
Internal: _audit_action()
    ↓
AuditService.create_event_local()
    ↓
Write to flag_audit.json
    ↓
Audit trail persisted
```

### 3. Legal Hold Workflow

```
POST /api/v1/audit/legal-holds
    ↓
Check permissions (founder/compliance)
    ↓
AuditService.create_legal_hold()
    ↓
Store in legal_holds.json
    ↓
(Future) Enforce upstream
    ↓
Return hold ID
```

## Security Architecture

### Authentication Flow

```
1. Dev Mode (local):
   POST /api/v1/auth/dev-login
   → Create JWT with user_id, tenant_id, role
   → Return bearer token

2. Production Mode (future):
   OAuth/OIDC flow
   → Exchange code for token
   → Validate with identity provider
   → Create session
```

### Authorization Model

**Role Hierarchy**:
```
founder
  ↓
agency_admin
  ↓
security_officer / compliance_officer / policy_manager
  ↓
legal_hold_operator
  ↓
viewer
```

**Permission Matrix**:
| Feature | Founder | Agency Admin | Security Officer | Compliance | Viewer |
|---------|---------|--------------|------------------|------------|--------|
| Feature Flags (CRUD) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Flag Approval | ✅ | ❌ | ❌ | ❌ | ❌ |
| Audit Export | ✅ | ✅ | ❌ | ✅ | ❌ |
| Legal Holds | ✅ | ✅ | ❌ | ✅ | ❌ |
| AI Policies | ✅ | ❌ | ✅ | ❌ | ❌ |
| Personnel | ✅ | ✅ | ❌ | ❌ | ❌ |
| Security Dashboard | ✅ | ❌ | ❌ | ❌ | ❌ |

## Deployment Architecture

### Docker Deployment

```
┌─────────────────────────────────────┐
│         Load Balancer               │
└─────────────────┬───────────────────┘
                  │
     ┌────────────┴───────────┐
     │                        │
┌────▼────┐            ┌─────▼─────┐
│ Backend │            │ Backend   │
│ (8012)  │            │ (8012)    │
└─────────┘            └───────────┘
     │                        │
     └────────────┬───────────┘
                  │
         ┌────────▼─────────┐
         │  Shared Volume   │
         │  (Feature Flags) │
         └──────────────────┘
```

### ECS Deployment

```yaml
Task Definition:
  - Container: admin-backend
    Port: 8012
    Health Check: /health
    CPU: 256
    Memory: 512
    Secrets:
      - JWT_SECRET
      - DATABASE_URL (when connected)
```

## Scaling Considerations

### Current (Standalone)

- **Concurrent Users**: 100-500
- **Feature Flags**: < 1000
- **Requests/sec**: < 100

### With Database

- **Concurrent Users**: 10,000+
- **Feature Flags**: Unlimited
- **Requests/sec**: 1000+
- **Audit Events**: Millions

### Bottlenecks

1. **JSON File I/O**: Switch to database for > 1000 flags
2. **Concurrent Writes**: Implement locking or use DB transactions
3. **Audit Query Performance**: Index by timestamp, tenant_id, event_type

## Monitoring & Observability

### Health Checks

- `/health` - Basic health
- `/health/startup` - Startup validation
- `/health/readiness` - Kubernetes readiness
- `/health/liveness` - Kubernetes liveness

### Metrics (Future)

- Feature flag evaluations/sec
- API request latency
- Error rates by endpoint
- Auth success/failure rates

### Logging

- Structured JSON logging
- Trace IDs for request correlation
- Audit trail for all admin actions

## Disaster Recovery

### Backup Strategy

1. **Data Files**: Daily backup of `backend/data/`
2. **Configuration**: Version control all config
3. **Secrets**: Stored in secrets manager

### Recovery

1. Restore data files from backup
2. Restart application
3. Verify health checks
4. Validate feature flags load correctly

## Performance Characteristics

- **Cold Start**: < 2 seconds
- **Health Check**: < 50ms
- **Feature Flag Evaluation**: < 10ms
- **Audit Query (local)**: < 100ms
- **API Response (avg)**: < 100ms
