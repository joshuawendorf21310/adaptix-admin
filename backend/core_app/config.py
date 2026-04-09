from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("ADAPTIX_ADMIN_APP_NAME", "adaptix-admin")
    app_env: str = os.getenv("ADAPTIX_ADMIN_ENV", "development")
    dev_secret: str = os.getenv("ADAPTIX_ADMIN_DEV_SECRET", "adaptix-admin-dev-secret")
    allow_dev_auth: bool = os.getenv("ADAPTIX_ADMIN_ALLOW_DEV_AUTH", "true").lower() == "true"
    default_tenant_id: str = os.getenv(
        "ADAPTIX_ADMIN_DEFAULT_TENANT_ID",
        "00000000-0000-0000-0000-000000000001",
    )
    cors_origins: str = os.getenv("ADAPTIX_ADMIN_CORS_ORIGINS", "*")


settings = Settings()