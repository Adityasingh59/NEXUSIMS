"""NEXUS IMS — Purchase Order endpoints (Block 5)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_BOMS_MANAGE, PERM_TRANSACTIONS_RECEIVE,
)
from app.schemas.common import ApiResponse, Meta
from app.schemas.purchase_order import (
    POCreate, POReceiveRequest, POLineResponse, POResponse,
)
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter()


def _po_to_response(po) -> POResponse:
    return POResponse(
        id=po.id,
        supplier_name=po.supplier_name,
        status=po.status,
        warehouse_id=po.warehouse_id,
        notes=po.notes,
        lines=[
            POLineResponse(
                id=line.id,
                sku_id=line.sku_id,
                quantity_ordered=line.quantity_ordered,
                quantity_received=line.quantity_received,
                unit_cost=line.unit_cost,
            )
            for line in po.lines
        ],
        created_at=po.created_at.isoformat() if po.created_at else "",
    )


@router.get("", response_model=ApiResponse[list])
async def list_purchase_orders(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List Purchase Orders for the current tenant."""
    pos, total = await PurchaseOrderService.list_pos(
        db, user.tenant_id, status=status_filter, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[_po_to_response(po) for po in pos],
        meta=Meta(page=page, page_size=page_size, total_count=total),
    )


@router.post("", response_model=ApiResponse[POResponse], status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: POCreate,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new Purchase Order in DRAFT status."""
    lines = [line.model_dump() for line in body.lines]
    try:
        po = await PurchaseOrderService.create_po(
            db,
            tenant_id=user.tenant_id,
            supplier_name=body.supplier_name,
            warehouse_id=body.warehouse_id,
            lines=lines,
            notes=body.notes,
            created_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await db.commit()
    await db.refresh(po)
    return ApiResponse(data=_po_to_response(po))


@router.get("/{po_id}", response_model=ApiResponse[POResponse])
async def get_purchase_order(
    po_id: UUID,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a single Purchase Order with all lines."""
    po = await PurchaseOrderService.get_po(db, user.tenant_id, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found")
    return ApiResponse(data=_po_to_response(po))


@router.post("/{po_id}/receive", response_model=ApiResponse[POResponse])
async def receive_purchase_order(
    po_id: UUID,
    body: POReceiveRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_RECEIVE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive goods against a Purchase Order.
    Each line specifies how many units are being received.
    Automatically posts RECEIVE ledger events and updates PO status.
    """
    receive_lines = [item.model_dump() for item in body.lines]
    try:
        po = await PurchaseOrderService.receive_po(
            db, user.tenant_id, po_id, receive_lines, actor_id=user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await db.commit()
    await db.refresh(po)
    return ApiResponse(data=_po_to_response(po))


@router.post("/{po_id}/cancel", response_model=ApiResponse[POResponse])
async def cancel_purchase_order(
    po_id: UUID,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a Purchase Order (only allowed in DRAFT or ORDERED status)."""
    try:
        po = await PurchaseOrderService.cancel_po(db, user.tenant_id, po_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found")
    await db.commit()
    return ApiResponse(data=_po_to_response(po))
