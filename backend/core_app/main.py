from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core_app.api.adaptix_admin_router import router as adaptix_admin_router
from core_app.api.ai_router import router as ai_router
from core_app.api.ai_router_extended import router as ai_router_extended
from core_app.api.audit_router import router as audit_router
from core_app.api.audit_router_extended import router as audit_router_extended
from core_app.api.auth_router import router as auth_router
from core_app.api.feature_flag_router import router as feature_flag_router
from core_app.api.feature_flag_router_extended import router as feature_flag_router_extended
from core_app.api.founder_security_router import router as founder_security_router
from core_app.api.health_router import router as health_router
from core_app.api.personnel_router import router as personnel_router
from core_app.api.personnel_router_extended import router as personnel_router_extended
from core_app.config import settings

app = FastAPI(
    title="Adaptix Admin",
    version="1.0.0",
    description="Production-grade Adaptix Admin governance, feature-flag, audit, legal-hold, and AI policy system",
)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core infrastructure
app.include_router(health_router)
app.include_router(auth_router)

# Extended feature routers (production-grade governance)
app.include_router(feature_flag_router_extended)
app.include_router(audit_router_extended)
app.include_router(ai_router_extended)
app.include_router(personnel_router_extended)
app.include_router(founder_security_router)

# Legacy routers (kept for backward compatibility)
app.include_router(feature_flag_router)
app.include_router(audit_router)
app.include_router(personnel_router)
app.include_router(ai_router)
app.include_router(adaptix_admin_router)