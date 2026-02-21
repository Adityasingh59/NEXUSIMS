"""NEXUS IMS — Assembly Order models (Block 7)."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssemblyOrder(Base):
    """Represents a job to assemble a finished SKU from its BOM components."""

    __tablename__ = "assembly_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="RESTRICT"))
    bom_version: Mapped[int] = mapped_column(nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"))
    planned_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    produced_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    waste_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    waste_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cogs_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
