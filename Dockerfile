# Feature 187: Docker support for Adaptix Admin
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend application
COPY backend/pyproject.toml backend/setup.py* ./
COPY backend/core_app ./core_app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /app/data && chmod 777 /app/data

# Non-root user for security
RUN useradd -m -u 1000 adaptix && chown -R adaptix:adaptix /app
USER adaptix

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8012/health').raise_for_status()"

# Feature 188: ECS-compatible runtime
# Expose port
EXPOSE 8012

# Environment variables documented in feature 189
ENV ADAPTIX_ADMIN_APP_NAME=adaptix-admin \
    ADAPTIX_ADMIN_ENV=production \
    ADAPTIX_ADMIN_ALLOW_DEV_AUTH=false \
    PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "core_app.main:app", "--host", "0.0.0.0", "--port", "8012"]
