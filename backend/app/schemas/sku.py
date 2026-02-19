"""NEXUS IMS — SKU schemas (Block 1.3)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SKUCreate(BaseModel):
    sku_code: str
    name: str
    item_type_id: UUID
    attributes: dict = Field(default_factory=dict)
    reorder_point: Decimal | None = None
    unit_cost: Decimal | None = None


class SKUUpdate(BaseModel):
    name: str | None = None
    attributes: dict | None = None
    reorder_point: Decimal | None = None
    unit_cost: Decimal | None = None


class SKUResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sku_code: str
    name: str
    item_type_id: UUID
    attributes: dict
    reorder_point: Decimal | None
    unit_cost: Decimal | None
    is_archived: bool

    model_config = {"from_attributes": True}
