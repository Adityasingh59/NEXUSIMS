"""NEXUS IMS — BOM schemas (Block 5)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BOMLineCreate(BaseModel):
    component_sku_id: UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity of component per finished unit")
    unit_cost_snapshot: Decimal = Field(..., ge=0, description="Cost per component unit")


class BOMCreate(BaseModel):
    sku_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    lines: list[BOMLineCreate] = Field(..., min_length=1)


class BOMUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    lines: list[BOMLineCreate] | None = None


class BOMLineResponse(BaseModel):
    id: UUID
    component_sku_id: UUID
    quantity: Decimal
    unit_cost_snapshot: Decimal

    class Config:
        from_attributes = True


class BOMResponse(BaseModel):
    id: UUID
    sku_id: UUID
    name: str
    is_active: bool
    lines: list[BOMLineResponse]
    created_at: str

    class Config:
        from_attributes = True


class ExplodeResponse(BaseModel):
    bom_id: UUID
    quantity: Decimal
    components: dict[str, Decimal]  # component_sku_id (str) → total_quantity
