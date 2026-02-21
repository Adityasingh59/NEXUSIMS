"""NEXUS IMS — Sales Order schemas (Block 8)."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.sku import SKUResponse

# --- Lines ---

class SalesOrderLineCreate(BaseModel):
    sku_id: UUID
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(default=0, ge=0)


class SalesOrderLineResponse(BaseModel):
    id: UUID
    sales_order_id: UUID
    sku_id: UUID
    quantity: Decimal
    unit_price: Decimal
    fulfilled_qty: Decimal
    sku: SKUResponse | None = None

    class Config:
        from_attributes = True


# --- Orders ---

class SalesOrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    order_reference: str | None = Field(default=None, max_length=100)
    shipping_address: str | None = None
    lines: list[SalesOrderLineCreate] = Field(..., min_items=1)


class SalesOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_name: str
    order_reference: str | None
    status: Literal["PENDING", "PROCESSING", "SHIPPED", "CANCELLED"] | str
    shipping_address: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    lines: list[SalesOrderLineResponse] = []

    class Config:
        from_attributes = True


class SalesOrderAllocateRequest(BaseModel):
    warehouse_id: UUID


class SalesOrderShipRequest(BaseModel):
    warehouse_id: UUID


class SalesOrderCancelRequest(BaseModel):
    warehouse_id: UUID
