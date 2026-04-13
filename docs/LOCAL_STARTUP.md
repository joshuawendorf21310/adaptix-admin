# Local Startup Documentation (Feature 191)

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- npm or yarn

## Backend Setup

### 1. Navigate to backend directory

```bash
cd backend
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

Using pip:
```bash
pip install -e .
```

Or with pyproject.toml:
```bash
pip install fastapi uvicorn pydantic
```

### 4. Configure environment (optional)

Create `.env` file in backend directory:

```bash
ADAPTIX_ADMIN_APP_NAME=adaptix-admin
ADAPTIX_ADMIN_ENV=development
ADAPTIX_ADMIN_ALLOW_DEV_AUTH=true
ADAPTIX_ADMIN_DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
ADAPTIX_ADMIN_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
ADAPTIX_ADMIN_DEV_SECRET=your-dev-secret-here
```

### 5. Start the backend server

```bash
uvicorn core_app.main:app --reload --port 8012
```

The backend will be available at: `http://127.0.0.1:8012`

### 6. Verify startup

Check health endpoint:
```bash
curl http://127.0.0.1:8012/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2026-04-13T...",
  "version": "1.0.0",
  "service": "adaptix-admin",
  "environment": "development"
}
```

Check startup health:
```bash
curl http://127.0.0.1:8012/health/startup
```

## Frontend Setup

### 1. Navigate to frontend directory

```bash
cd frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment

Create `.env.local` file:

```bash
NEXT_PUBLIC_ADMIN_API_BASE=http://127.0.0.1:8012
```

### 4. Start the development server

```bash
npm run dev
```

The frontend will be available at: `http://localhost:3000`

## Using Docker (Recommended)

### Build and run with Docker Compose

```bash
docker-compose up --build
```

This will start:
- Backend at `http://localhost:8012`
- Frontend at `http://localhost:3001`

### Stop services

```bash
docker-compose down
```

## Development Authentication

### Get a development token

```bash
curl -X POST http://127.0.0.1:8012/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000201",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "role": "founder"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "role": "founder",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "user_id": "00000000-0000-0000-0000-000000000201"
}
```

### Use token in requests

```bash
TOKEN="your-token-here"
curl -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8012/api/v1/feature-flags
```

## Available Roles

- `founder` - Full system access
- `agency_admin` - Admin access within tenant
- `compliance_officer` - Compliance and audit access
- `security_officer` - Security monitoring access
- `policy_manager` - AI policy management
- `legal_hold_operator` - Legal hold management
- `viewer` - Read-only access

## API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://127.0.0.1:8012/docs
- **ReDoc**: http://127.0.0.1:8012/redoc

## Troubleshooting

### Port already in use

Backend:
```bash
# Change port in uvicorn command
uvicorn core_app.main:app --reload --port 8013
```

Frontend:
```bash
# Change port in package.json or:
PORT=3002 npm run dev
```

### Data directory permissions

```bash
mkdir -p backend/data
chmod 755 backend/data
```

### Module not found errors

```bash
# Reinstall dependencies
pip install --force-reinstall -e .
```

### CORS errors

Ensure `ADAPTIX_ADMIN_CORS_ORIGINS` includes your frontend URL.
