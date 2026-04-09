"""Feature flag model for tenant-scoped and global feature toggles."""

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from core_app.models.base import BaseModel


class FeatureFlag(BaseModel):
    """Feature flag with support for global, tenant-scoped, role, and percentage rollouts."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "flag_key", name="uq_feature_flags_tenant_key"),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    flag_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
