"""Adaptix Admin alias router."""
from core_app.api.adaptix_domain_router_common import build_adaptix_domain_router

router = build_adaptix_domain_router(
    module="admin",
    tag="Adaptix Admin",
    prefix="/api/admin",
    legacy_routes=["/api/v1/feature-flags", "/api/v1/templates", "/api/v1/audit"],
    legacy_modules=["feature_flag_router", "template_router", "audit_router"],
)
