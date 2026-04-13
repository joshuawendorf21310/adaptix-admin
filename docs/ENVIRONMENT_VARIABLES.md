# Environment Variables Documentation (Feature 189)

## Required Environment Variables

### Application Configuration

- `ADAPTIX_ADMIN_APP_NAME` (default: `adaptix-admin`)
  - Application identifier for logging and monitoring
  - Example: `adaptix-admin`

- `ADAPTIX_ADMIN_ENV` (default: `development`)
  - Environment name: `development`, `staging`, `production`
  - Controls behavior and safety checks

### Authentication Configuration

- `ADAPTIX_ADMIN_ALLOW_DEV_AUTH` (default: `true`)
  - **CRITICAL**: Must be `false` in production
  - Enables `/api/v1/auth/dev-login` endpoint for local development
  - **Production**: Set to `false` and use proper OAuth/OIDC integration

- `ADAPTIX_ADMIN_DEV_SECRET` (default: `adaptix-admin-dev-secret`)
  - **DEV ONLY**: Secret for signing development JWTs
  - **Production**: Replace with production secret management
  - Should be stored in secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

### Tenant Configuration

- `ADAPTIX_ADMIN_DEFAULT_TENANT_ID` (default: `00000000-0000-0000-0000-000000000001`)
  - Default tenant ID for development authentication
  - Example: `00000000-0000-0000-0000-000000000001`

### CORS Configuration

- `ADAPTIX_ADMIN_CORS_ORIGINS` (default: `*`)
  - Comma-separated list of allowed origins
  - **Production**: Specify exact origins, do not use `*`
  - Example: `https://admin.adaptix.example.com,https://app.adaptix.example.com`

## Optional Environment Variables

### Database Configuration (Future)

When connecting to upstream evidence sources:

- `ADAPTIX_ADMIN_DATABASE_URL`
  - Connection string for audit evidence database
  - Example: `postgresql://user:pass@host:5432/adaptix_audit`

- `ADAPTIX_ADMIN_REDIS_URL`
  - Redis connection for caching and session management
  - Example: `redis://localhost:6379/0`

### Observability

- `ADAPTIX_ADMIN_LOG_LEVEL` (default: `INFO`)
  - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

- `ADAPTIX_ADMIN_OTEL_ENDPOINT`
  - OpenTelemetry collector endpoint for traces
  - Example: `http://otel-collector:4318`

### Feature Flags

- `ADAPTIX_ADMIN_FEATURE_FLAGS_PATH` (default: `data/feature_flags_extended.json`)
  - Path to feature flags storage

### Security

- `ADAPTIX_ADMIN_JWT_ALGORITHM` (default: `HS256`)
  - JWT signing algorithm for production auth

- `ADAPTIX_ADMIN_JWT_EXPIRY_SECONDS` (default: `3600`)
  - JWT token expiry time in seconds

## Docker Environment

When running in Docker/ECS:

```bash
docker run -p 8012:8012 \
  -e ADAPTIX_ADMIN_ENV=production \
  -e ADAPTIX_ADMIN_ALLOW_DEV_AUTH=false \
  -e ADAPTIX_ADMIN_DEV_SECRET="${SECRET}" \
  -e ADAPTIX_ADMIN_CORS_ORIGINS="https://admin.example.com" \
  adaptix-admin:latest
```

## ECS Task Definition Example

```json
{
  "family": "adaptix-admin",
  "containerDefinitions": [{
    "name": "admin-backend",
    "image": "adaptix-admin:latest",
    "environment": [
      {"name": "ADAPTIX_ADMIN_ENV", "value": "production"},
      {"name": "ADAPTIX_ADMIN_ALLOW_DEV_AUTH", "value": "false"}
    ],
    "secrets": [
      {"name": "ADAPTIX_ADMIN_DEV_SECRET", "valueFrom": "arn:aws:secretsmanager:..."}
    ],
    "portMappings": [{
      "containerPort": 8012,
      "protocol": "tcp"
    }],
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8012/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 10
    }
  }]
}
```
