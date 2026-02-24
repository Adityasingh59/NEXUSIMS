"""NEXUS IMS — Returns Management (RMA) models."""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RMAStatus(str, Enum):
    PENDING = "PENDING"
    INSPECTING = "INSPECTING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESTOCKED = "RESTOCKED"


class RMA(Base):
    """Return Merchandise Authorization (RMA) header."""
    __tablename__ = "rmas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"))
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=RMAStatus.PENDING.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    lines: Mapped[list["RMALine"]] = relationship("RMALine", back_populates="rma", cascade="all, delete-orphan")


class RMALine(Base):
    """Line items for an RMA ticket."""
    __tablename__ = "rma_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rma_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rmas.id", ondelete="CASCADE"))
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skus.id", ondelete="RESTRICT"))
    quantity_expected: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "NEW", "DAMAGED"
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    rma: Mapped["RMA"] = relationship("RMA", back_populates="lines")
