"""NEXUS IMS — BOM and BOMLine models (Block 5)."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BOM(Base):
    """Bill of Materials — defines the component recipe for a finished SKU."""

    __tablename__ = "boms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skus.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    lines: Mapped[list["BOMLine"]] = relationship("BOMLine", back_populates="bom", cascade="all, delete-orphan", lazy="selectin")


class BOMLine(Base):
    """A single component line within a BOM."""

    __tablename__ = "bom_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"))
    component_sku_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skus.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    bom: Mapped["BOM"] = relationship("BOM", back_populates="lines")
