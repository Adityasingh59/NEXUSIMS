"""NEXUS IMS — BOM schemas (Block 7)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BOMLineCreate(BaseModel):
    component_sku_id: UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity of component per finished unit")
    unit: str | None = Field(None, max_length=50)


class BOMCreate(BaseModel):
    finished_sku_id: UUID
    landed_cost: Decimal = Field(Decimal("0"), ge=0, description="Fixed overhead cost for BOM")
    landed_cost_description: str | None = Field(None, max_length=255)
    lines: list[BOMLineCreate] = Field(..., min_length=1)


class BOMLineResponse(BaseModel):
    id: UUID
    component_sku_id: UUID
    quantity: Decimal
    unit: str | None

    class Config:
        from_attributes = True


class BOMResponse(BaseModel):
    id: UUID
    finished_sku_id: UUID
    version: int
    is_active: bool
    landed_cost: Decimal
    landed_cost_description: str | None
    lines: list[BOMLineResponse]
    created_at: str

    class Config:
        from_attributes = True


class BOMAvailabilityResponse(BaseModel):
    is_available: bool
    shortages: dict[UUID, dict] # component_sku_id -> {required, available, shortage}
