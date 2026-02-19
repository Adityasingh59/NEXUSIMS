"""NEXUS IMS — Location and Transfer schemas (Block 3)."""
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class LocationCreate(BaseModel):
    warehouse_id: UUID
    name: str
    code: str
    location_type: str  # ZONE | AISLE | BIN
    parent_id: UUID | None = None


class LocationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    parent_id: UUID | None
    name: str
    code: str
    location_type: str
    is_active: bool

    model_config = {"from_attributes": True}


class TransferLineCreate(BaseModel):
    sku_id: UUID
    quantity_requested: Decimal | float


class TransferCreate(BaseModel):
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    lines: list[TransferLineCreate]


class TransferLineResponse(BaseModel):
    id: UUID
    sku_id: UUID
    quantity_requested: Decimal
    quantity_received: Decimal | None

    model_config = {"from_attributes": True}


class TransferResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    status: str
    created_at: str | None
    received_at: str | None
    lines: list[TransferLineResponse] = []

    model_config = {"from_attributes": True}


class TransferReceiveRequest(BaseModel):
    line_quantities: dict[str, float] | None = None  # line_id -> qty_received
