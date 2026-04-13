# Secrets Management (Feature 190)

## Production Secrets Expectation

### **CRITICAL: Never commit secrets to source code**

This system requires proper secrets management in production. All sensitive values must be stored in a secrets manager.

## Secrets Required

### 1. JWT Signing Secret

**Secret Name**: `adaptix-admin/jwt-secret`

**Purpose**: Sign and verify JWT tokens for authentication

**Requirements**:
- Minimum 32 characters
- Cryptographically random
- Rotated every 90 days

**Example Generation**:
```bash
openssl rand -base64 32
```

### 2. Database Credentials (when upstream connected)

**Secret Name**: `adaptix-admin/database-url`

**Purpose**: Connect to audit evidence database

**Format**:
```
postgresql://username:password@host:port/database
```

### 3. Redis Connection (when upstream connected)

**Secret Name**: `adaptix-admin/redis-url`

**Purpose**: Session management and caching

**Format**:
```
redis://username:password@host:port/db
```

## Secrets Manager Integration

### AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In config.py:
# dev_secret = get_secret('adaptix-admin/jwt-secret')['secret']
```

### Azure Key Vault

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret(vault_url, secret_name):
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    return client.get_secret(secret_name).value

# In config.py:
# dev_secret = get_secret('https://myvault.vault.azure.net/', 'jwt-secret')
```

### Google Secret Manager

```python
from google.cloud import secretmanager

def get_secret(project_id, secret_name, version='latest'):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

# In config.py:
# dev_secret = get_secret('my-project', 'jwt-secret')
```

## Docker Secrets

When using Docker Swarm:

```yaml
version: '3.8'

services:
  admin-backend:
    image: adaptix-admin:latest
    secrets:
      - jwt_secret
    environment:
      - ADAPTIX_ADMIN_DEV_SECRET_FILE=/run/secrets/jwt_secret

secrets:
  jwt_secret:
    external: true
```

## Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: adaptix-admin-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adaptix-admin
spec:
  template:
    spec:
      containers:
      - name: admin-backend
        image: adaptix-admin:latest
        env:
        - name: ADAPTIX_ADMIN_DEV_SECRET
          valueFrom:
            secretKeyRef:
              name: adaptix-admin-secrets
              key: jwt-secret
```

## Secret Rotation

1. **Create new secret version**
2. **Update secret reference** in environment
3. **Rolling restart** of application
4. **Verify** new secret is working
5. **Delete old secret version** after grace period

## Security Best Practices

1. **Never log secrets** - Sanitize logs before output
2. **Use short-lived credentials** - Rotate frequently
3. **Principle of least privilege** - Grant minimal access
4. **Audit secret access** - Monitor who accesses secrets
5. **Encrypt secrets at rest** - Use secrets manager encryption
6. **Separate secrets per environment** - Dev, staging, prod
