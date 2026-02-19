"""NEXUS IMS — Warehouse schemas (Block 2)."""
from uuid import UUID

from pydantic import BaseModel


class WarehouseCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    timezone: str = "UTC"


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None


class WarehouseResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    address: str | None
    timezone: str
    is_active: bool

    model_config = {"from_attributes": True}


class TransactionRequest(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    quantity: float
    location_id: UUID | None = None
    reference_id: UUID | None = None
    notes: str | None = None


class ReceiveRequest(TransactionRequest):
    pass


class PickRequest(TransactionRequest):
    reference_id: UUID | None = None  # order reference


class AdjustRequest(TransactionRequest):
    reason_code: str  # DAMAGE, THEFT, FOUND, DATA_ERROR, CYCLE_COUNT, OTHER


class ReturnRequest(TransactionRequest):
    disposition: str  # resaleable | damaged | quarantine
