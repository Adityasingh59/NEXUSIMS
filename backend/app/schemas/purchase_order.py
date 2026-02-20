"""NEXUS IMS — Purchase Order schemas (Block 5)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class POLineCreate(BaseModel):
    sku_id: UUID
    quantity_ordered: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)


class POCreate(BaseModel):
    supplier_name: str = Field(..., min_length=1, max_length=255)
    warehouse_id: UUID
    notes: str | None = None
    lines: list[POLineCreate] = Field(..., min_length=1)


class POReceiveLine(BaseModel):
    po_line_id: UUID
    quantity_received: Decimal = Field(..., gt=0)


class POReceiveRequest(BaseModel):
    lines: list[POReceiveLine] = Field(..., min_length=1)


class POLineResponse(BaseModel):
    id: UUID
    sku_id: UUID
    quantity_ordered: Decimal
    quantity_received: Decimal
    unit_cost: Decimal

    class Config:
        from_attributes = True


class POResponse(BaseModel):
    id: UUID
    supplier_name: str
    status: str
    warehouse_id: UUID
    notes: str | None
    lines: list[POLineResponse]
    created_at: str

    class Config:
        from_attributes = True
