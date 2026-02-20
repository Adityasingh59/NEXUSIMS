"""NEXUS IMS — Warehouse endpoints (Block 2 — minimal for ledger)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_db, require_auth, require_permission, PERM_WAREHOUSES_MANAGE
from app.models.warehouse import Warehouse
from app.schemas.common import ApiResponse
from app.schemas.warehouse import WarehouseCreate, WarehouseResponse, WarehouseUpdate
from app.services.warehouse_service import WarehouseService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[WarehouseResponse]])
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """List active warehouses."""
    items = await WarehouseService.list_active(db, user.tenant_id)
    return ApiResponse(data=[WarehouseResponse.model_validate(i) for i in items])


@router.post("", response_model=ApiResponse[WarehouseResponse], status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission(PERM_WAREHOUSES_MANAGE)),
):
    """Create warehouse."""
    # Check code uniqueness per tenant
    from sqlalchemy import select
    from app.models.warehouse import Warehouse as WH
    result = await db.execute(
        select(WH).where(WH.tenant_id == user.tenant_id, WH.code == body.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Warehouse code already exists")
    wh = Warehouse(
        tenant_id=user.tenant_id,
        name=body.name,
        code=body.code,
        address=body.address,
        timezone=body.timezone,
    )
    db.add(wh)
    await db.flush()
    await db.refresh(wh)
    return ApiResponse(data=WarehouseResponse.model_validate(wh))


@router.get("/{id}", response_model=ApiResponse[WarehouseResponse])
async def get_warehouse(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get warehouse by ID."""
    wh = await WarehouseService.get_by_id(db, id, user.tenant_id)
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data=WarehouseResponse.model_validate(wh))


@router.put("/{id}", response_model=ApiResponse[WarehouseResponse])
async def update_warehouse(
    id: UUID,
    body: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission(PERM_WAREHOUSES_MANAGE)),
):
    """Update warehouse."""
    wh = await WarehouseService.get_by_id(db, id, user.tenant_id)
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if body.name is not None:
        wh.name = body.name
    if body.address is not None:
        wh.address = body.address
    if body.timezone is not None:
        wh.timezone = body.timezone
    await db.flush()
    await db.refresh(wh)
    return ApiResponse(data=WarehouseResponse.model_validate(wh))


@router.get("/{id}/stock", response_model=ApiResponse[list])
async def get_warehouse_stock(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get stock summary for warehouse (sku_id, quantity)."""
    wh = await WarehouseService.get_by_id(db, id, user.tenant_id)
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    rows = await WarehouseService.get_warehouse_stock(db, user.tenant_id, id)
    data = [{"sku_id": str(sku_id), "quantity": float(qty)} for sku_id, qty in rows]
    return ApiResponse(data=data)
