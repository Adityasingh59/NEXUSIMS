"""NEXUS IMS — Assembly Orders endpoints (Block 7)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_BOMS_MANAGE,
)
from app.schemas.assembly_order import AssemblyOrderCreate, AssemblyOrderComplete, AssemblyOrderResponse
from app.schemas.common import ApiResponse, Meta
from app.services.assembly_service import AssemblyService
from app.models.assembly import AssemblyOrder

router = APIRouter()


def _order_to_response(order: AssemblyOrder) -> AssemblyOrderResponse:
    return AssemblyOrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        bom_id=order.bom_id,
        bom_version=order.bom_version,
        warehouse_id=order.warehouse_id,
        planned_qty=order.planned_qty,
        produced_qty=order.produced_qty,
        waste_qty=order.waste_qty,
        waste_reason=order.waste_reason,
        cogs_per_unit=order.cogs_per_unit,
        status=order.status,
        started_at=order.started_at.isoformat() if order.started_at else "",
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
    )


@router.get("", response_model=ApiResponse[list[AssemblyOrderResponse]])
async def list_assembly_orders(
    status: str | None = Query(None, description="Filter by status (e.g. IN_PROGRESS, COMPLETE)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List assembly orders for the current tenant."""
    query = select(AssemblyOrder).where(AssemblyOrder.tenant_id == user.tenant_id)
    if status:
        query = query.where(AssemblyOrder.status == status.upper())
        
    result = await db.scalars(query.order_by(AssemblyOrder.started_at.desc()))
    orders = result.all()
    
    total = len(orders)
    start = (page - 1) * page_size
    page_orders = orders[start:start + page_size]
    
    return ApiResponse(
        data=[_order_to_response(o) for o in page_orders],
        meta=Meta(page=page, page_size=page_size, total_count=total),
    )


@router.post("", response_model=ApiResponse[AssemblyOrderResponse], status_code=201)
async def create_assembly_order(
    body: AssemblyOrderCreate,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Start a new assembly order, reserving components."""
    order = await AssemblyService.start_assembly_order(
        db=db,
        tenant_id=user.tenant_id,
        bom_id=body.bom_id,
        warehouse_id=body.warehouse_id,
        planned_qty=body.planned_qty,
        created_by=user.id
    )
    await db.commit()
    await db.refresh(order)
    return ApiResponse(data=_order_to_response(order))


@router.post("/{order_id}/complete", response_model=ApiResponse[AssemblyOrderResponse])
async def complete_assembly_order(
    order_id: UUID,
    body: AssemblyOrderComplete,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Complete an assembly order, calculating COGS and recording finished goods."""
    order = await AssemblyService.complete_assembly_order(
        db=db,
        tenant_id=user.tenant_id,
        order_id=order_id,
        produced_qty=body.produced_qty,
        waste_qty=body.waste_qty,
        waste_reason=body.waste_reason,
        created_by=user.id
    )
    await db.commit()
    await db.refresh(order)
    return ApiResponse(data=_order_to_response(order))


@router.post("/{order_id}/cancel", response_model=ApiResponse[AssemblyOrderResponse])
async def cancel_assembly_order(
    order_id: UUID,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an assembly order. For MVP, we just update status without reversing ledger events."""
    order = await db.scalar(
        select(AssemblyOrder).where(AssemblyOrder.id == order_id, AssemblyOrder.tenant_id == user.tenant_id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status {order.status}")
        
    order.status = "CANCELLED"
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return ApiResponse(data=_order_to_response(order))
