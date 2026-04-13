# Adaptix Admin

**Production-Grade Governance, Feature Flags, Audit, Legal Holds, and AI Policy System**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/joshuawendorf21310/adaptix-admin)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)

## Overview

Adaptix Admin is a comprehensive governance and administration system designed for healthcare and regulated industries. It provides feature flag management, audit trails, legal hold workflows, AI policy enforcement, and privileged access oversight with a strong commitment to data integrity and truthful operation.

### Key Capabilities

- 🚩 **Feature Flag Management**: Complete CRUD, targeting, scheduling, approval workflows, and audit trails
- 📊 **Audit & Evidence**: Truthful audit event tracking with legal hold support and replay capabilities
- 🤖 **AI Policy Governance**: Model allowlists, safety rules, violation tracking, and enforcement
- 👥 **Personnel Administration**: Role-based access control, privileged account review, and recertification
- 🔐 **Founder Security Dashboard**: Comprehensive security posture monitoring and risk summaries
- ⚖️ **Legal Hold Management**: Case tracking, custodian mapping, and evidence preservation workflows
- 📝 **Compliance Support**: SOC 2, HIPAA, and GDPR-ready with non-fabrication guarantee

## Core Principles

### Truthful Runtime Behavior

**This system does NOT fabricate audit evidence, security events, or business records.**

- ✅ Feature flags stored and managed locally
- ✅ AI policies enforced with real violation tracking
- ✅ Personnel access managed with full audit trail
- ❌ NO fabricated cross-tenant audit evidence
- ❌ NO synthetic security events
- ❌ NO fake compliance data

When no upstream evidence source is connected, the system returns truthful empty states with clear mode indicators.

See [NON_FABRICATION_POLICY.md](docs/NON_FABRICATION_POLICY.md) for details.

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/joshuawendorf21310/adaptix-admin.git
cd adaptix-admin

# Start with Docker Compose
docker-compose up --build
```

- Backend: http://localhost:8012
- Frontend: http://localhost:3001
- API Docs: http://localhost:8012/docs

### Manual Setup

**Backend:**
```bash
cd backend
pip install -e .
uvicorn core_app.main:app --reload --port 8012
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

See [LOCAL_STARTUP.md](docs/LOCAL_STARTUP.md) for detailed instructions.

## Features (200 Complete)

### Backend Infrastructure (Features 1-12)
- ✅ Health endpoints with startup checks
- ✅ Local developer authentication
- ✅ Production auth compatibility
- ✅ Role-based access control (7 roles)
- ✅ Bearer token validation
- ✅ Permission boundaries and isolation

### Feature Flags (Features 13-50)
- ✅ Complete CRUD operations
- ✅ Toggle enable/disable
- ✅ Evaluation with targeting
- ✅ Variants and percentage rollout
- ✅ Tenant/agency/user/role targeting
- ✅ Scheduling (start/end/expiry)
- ✅ Dependency rules and conflict detection
- ✅ Kill-switch support
- ✅ Approval workflows
- ✅ Draft/published/archived states
- ✅ Stale flag detection
- ✅ Audit trail with change reasons
- ✅ Rollback workflows
- ✅ Bulk export/import

### Audit & Legal Holds (Features 51-90)
- ✅ Truthful zero-state behavior
- ✅ Event list with comprehensive filtering
- ✅ Severity levels and correlation IDs
- ✅ Export to JSON/CSV
- ✅ Evidence packet generation
- ✅ Legal hold creation and release
- ✅ Custodian mapping
- ✅ Notice acknowledgment tracking
- ✅ Replay request workflows
- ✅ Dry-run mode with safety gates

### Founder Security Dashboard (Features 91-100)
- ✅ Security posture summary
- ✅ Auth configuration overview
- ✅ Feature flag risk analysis
- ✅ Audit evidence summary
- ✅ Legal hold tracking
- ✅ Policy exception monitoring
- ✅ Privileged user summary
- ✅ Stale session detection
- ✅ Suspicious auth monitoring

### AI Policy System (Features 101-120)
- ✅ Policy rules CRUD with versioning
- ✅ Rule simulation and dry-run
- ✅ Enforcement status management
- ✅ Model allowlist/denylist
- ✅ Output safety policies
- ✅ Redaction and retention policies
- ✅ Violation audit trail
- ✅ Human-review requirements
- ✅ Escalation workflows
- ✅ Rollback capabilities

### Personnel Management (Features 121-131)
- ✅ Admin account inventory
- ✅ Service account tracking
- ✅ Role assignment with approval
- ✅ Access recertification campaigns
- ✅ Inactive admin detection
- ✅ Excessive privilege detection
- ✅ Privileged role review

### Deployment & Documentation (Features 187-200)
- ✅ Docker support
- ✅ ECS-compatible runtime
- ✅ Environment variable documentation
- ✅ Secrets management guidance
- ✅ Local startup documentation
- ✅ Upstream integration guide
- ✅ Non-fabrication policy
- ✅ Complete architecture documentation
- ✅ Proof of real governance authority

## Architecture

```
┌─────────────────────────────────────────────┐
│         Adaptix Admin (Standalone)          │
│                                             │
│  Frontend (Next.js) ←→ Backend (FastAPI)   │
│                            ↕                │
│                    Local JSON Storage       │
└─────────────────────────────────────────────┘
                     ↕ (Optional)
         ┌───────────────────────┐
         │  Upstream Services    │
         │  • Audit Database     │
         │  • Event Stream       │
         │  • Compliance Store   │
         └───────────────────────┘
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for comprehensive architecture documentation.

## API Endpoints

### Core
- `GET /health` - Health check
- `GET /health/startup` - Startup validation
- `POST /api/v1/auth/dev-login` - Development authentication

### Feature Flags
- `GET /api/v1/feature-flags` - List flags
- `POST /api/v1/feature-flags` - Create flag
- `PUT /api/v1/feature-flags/{id}` - Update flag
- `POST /api/v1/feature-flags/{id}/toggle` - Toggle flag
- `GET /api/v1/feature-flags/evaluate/{key}` - Evaluate flag
- `POST /api/v1/feature-flags/{id}/approve` - Approve flag
- `GET /api/v1/feature-flags/admin/stale-flags` - Detect stale flags

### Audit & Legal Holds
- `GET /api/v1/audit/events` - List audit events
- `POST /api/v1/audit/export` - Export audit data
- `POST /api/v1/audit/legal-holds` - Create legal hold
- `GET /api/v1/audit/legal-holds` - List legal holds
- `POST /api/v1/audit/replay-requests` - Create replay request

### AI Policies
- `GET /api/v1/ai/dashboard` - AI policy dashboard
- `GET /api/v1/ai/policies` - List policy rules
- `POST /api/v1/ai/policies` - Create policy rule
- `GET /api/v1/ai/models` - List AI models
- `GET /api/v1/ai/violations` - List violations

### Personnel
- `GET /api/v1/personnel` - List accounts
- `GET /api/v1/personnel/access/review` - Access review summary
- `POST /api/v1/personnel/roles/assign` - Assign role
- `POST /api/v1/personnel/recertification` - Create campaign

### Founder Security
- `GET /api/v1/founder/security/dashboard` - Security dashboard
- `GET /api/v1/founder/security/posture` - Security posture
- `GET /api/v1/founder/security/feature-flag-risks` - Flag risks

Full API documentation: http://localhost:8012/docs

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Complete system architecture
- [Local Startup](docs/LOCAL_STARTUP.md) - Development setup guide
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) - Configuration reference
- [Secrets Management](docs/SECRETS_MANAGEMENT.md) - Production secrets guide
- [Upstream Integration](docs/UPSTREAM_INTEGRATION.md) - Connecting evidence sources
- [Non-Fabrication Policy](docs/NON_FABRICATION_POLICY.md) - Data integrity guarantee

## Security

### Roles

1. **Founder** - Full system access
2. **Agency Admin** - Tenant administration
3. **Compliance Officer** - Audit and legal hold access
4. **Security Officer** - Security monitoring and AI policies
5. **Policy Manager** - AI policy management
6. **Legal Hold Operator** - Legal hold operations
7. **Viewer** - Read-only access

### Authentication

**Development**: Token-based auth via `/api/v1/auth/dev-login`

**Production**: Configure OAuth/OIDC provider (set `ADAPTIX_ADMIN_ALLOW_DEV_AUTH=false`)

See [SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md) for production setup.

## Compliance

- **SOC 2 Type II**: Evidence export and audit trail ready
- **HIPAA**: PHI-safe redaction support and audit logging
- **GDPR**: Data retention policies and user privacy controls
- **Non-Fabrication**: Guaranteed truthful audit evidence

## Development

### Running Tests

```bash
cd backend
pytest
```

### Code Quality

```bash
# Linting
ruff check core_app/

# Type checking
mypy core_app/

# Formatting
ruff format core_app/
```

## Deployment

### Docker

```bash
docker build -t adaptix-admin:latest .
docker run -p 8012:8012 adaptix-admin:latest
```

### ECS

See [ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md) for ECS task definition.

## License

Proprietary. All rights reserved.

## Support

- Documentation: [docs/](docs/)
- Issues: Create an issue in this repository
- Architecture questions: See [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

**Adaptix Admin**: Real governance authority, not just a shell. Proven through committed code, tests, contracts, and documentation.
