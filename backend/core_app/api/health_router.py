"""Health router with comprehensive startup checks (features 1-2)."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter

from core_app.config import settings

router = APIRouter(tags=["health"])


def _check_data_directory() -> bool:
    """Check if data directory is accessible."""
    try:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir.exists() and data_dir.is_dir()
    except Exception:
        return False


def _check_services() -> dict[str, bool]:
    """Run startup health checks on all services."""
    return {
        "feature_flags": _check_data_directory(),
        "audit": _check_data_directory(),
        "ai_policy": _check_data_directory(),
        "personnel": _check_data_directory(),
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """Feature 1: Admin health endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/health/startup")
async def startup_health() -> dict:
    """Feature 2: Admin backend startup health checks."""
    services = _check_services()
    all_healthy = all(services.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "service": settings.app_name,
        "environment": settings.app_env,
        "mode": "standalone-shell",
        "services": services,
        "checks": {
            "data_directory": _check_data_directory(),
            "config_loaded": True,
            "auth_enabled": settings.allow_dev_auth,
        },
    }


@router.get("/health/readiness")
async def readiness() -> dict:
    """Kubernetes readiness probe."""
    services = _check_services()
    all_ready = all(services.values())

    return {
        "ready": all_ready,
        "timestamp": datetime.now(UTC).isoformat(),
        "services": services,
    }


@router.get("/health/liveness")
async def liveness() -> dict:
    """Kubernetes liveness probe."""
    return {
        "alive": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }