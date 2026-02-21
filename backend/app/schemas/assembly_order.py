"""NEXUS IMS — Assembly Order schemas (Block 7)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AssemblyOrderCreate(BaseModel):
    bom_id: UUID
    warehouse_id: UUID
    planned_qty: Decimal = Field(..., gt=0, description="Planned production quantity")


class AssemblyOrderComplete(BaseModel):
    produced_qty: Decimal = Field(..., ge=0, description="Actual produced quantity")
    waste_qty: Decimal = Field(Decimal("0"), ge=0, description="Quantity wasted during production")
    waste_reason: str | None = Field(None, max_length=1000)


class AssemblyOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    bom_id: UUID
    bom_version: int
    warehouse_id: UUID
    planned_qty: Decimal
    produced_qty: Decimal | None
    waste_qty: Decimal | None
    waste_reason: str | None
    cogs_per_unit: Decimal | None
    status: str
    started_at: str
    completed_at: str | None

    class Config:
        from_attributes = True
