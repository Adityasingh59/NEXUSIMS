"""NEXUS IMS — Serial Numbers API Endpoints (Phase 3B)."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_auth
from app.models.item_type import SKU
from app.models.serial import SerialNumber, SerialStatus
from app.models.module import ModuleInstall

router = APIRouter()


class RegisterSerialRequest(BaseModel):
    sku_id: uuid.UUID
    warehouse_id: uuid.UUID
    serial_number: str


class SerialNumberResponse(BaseModel):
    id: uuid.UUID
    sku_id: uuid.UUID
    warehouse_id: uuid.UUID
    serial_number: str
    status: str

    class Config:
        from_attributes = True


class UpdateSerialStatusRequest(BaseModel):
    status: SerialStatus


async def _check_module_active(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Helper to verify the module is actually installed and active."""
    result = await db.execute(
        select(ModuleInstall).where(
            ModuleInstall.tenant_id == tenant_id,
            ModuleInstall.module_slug == "serial-numbers",
            ModuleInstall.is_active == True
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The 'serial-numbers' module is not installed or active."
        )


@router.post("/register", response_model=SerialNumberResponse)
async def register_serial_number(
    req: RegisterSerialRequest,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new serial number for a SKU."""
    await _check_module_active(db, user.tenant_id)

    # Verify SKU exists and has is_serialized attribute
    result = await db.execute(select(SKU).where(SKU.id == req.sku_id, SKU.tenant_id == user.tenant_id))
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found.")
        
    if not sku.attributes.get("is_serialized"):
        raise HTTPException(
            status_code=400, 
            detail="Cannot register serial number: This SKU does not have the 'is_serialized' attribute set to true."
        )

    # Check for duplicate serial on this SKU
    dup_check = await db.execute(
        select(SerialNumber).where(
            SerialNumber.tenant_id == user.tenant_id,
            SerialNumber.sku_id == req.sku_id,
            SerialNumber.serial_number == req.serial_number
        )
    )
    if dup_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Serial number already exists for this SKU.")

    serial = SerialNumber(
        tenant_id=user.tenant_id,
        sku_id=req.sku_id,
        warehouse_id=req.warehouse_id,
        serial_number=req.serial_number,
        status=SerialStatus.IN_STOCK.value
    )
    db.add(serial)
    await db.commit()
    await db.refresh(serial)
    return serial


@router.get("/", response_model=list[SerialNumberResponse])
async def list_serial_numbers(
    sku_id: uuid.UUID = Query(..., description="Filter by SKU"),
    warehouse_id: uuid.UUID | None = None,
    serial_status: SerialStatus | None = None,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List serial numbers for a specific SKU."""
    await _check_module_active(db, user.tenant_id)
    
    stmt = select(SerialNumber).where(
        SerialNumber.tenant_id == user.tenant_id,
        SerialNumber.sku_id == sku_id
    )
    
    if warehouse_id:
        stmt = stmt.where(SerialNumber.warehouse_id == warehouse_id)
    if serial_status:
        stmt = stmt.where(SerialNumber.status == serial_status.value)
        
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/{serial_id}/status", response_model=SerialNumberResponse)
async def update_serial_status(
    serial_id: uuid.UUID,
    req: UpdateSerialStatusRequest,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update the status of a specific serial number."""
    await _check_module_active(db, user.tenant_id)
    
    result = await db.execute(
        select(SerialNumber).where(
            SerialNumber.id == serial_id,
            SerialNumber.tenant_id == user.tenant_id
        )
    )
    serial = result.scalar_one_or_none()
    if not serial:
        raise HTTPException(status_code=404, detail="Serial number not found.")
        
    serial.status = req.status.value
    await db.commit()
    await db.refresh(serial)
    return serial
