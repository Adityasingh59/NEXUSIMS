"""NEXUS IMS — Transfer order endpoints (Block 3)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, require_auth
from app.schemas.common import ApiResponse
from app.schemas.location import TransferCreate, TransferReceiveRequest, TransferResponse, TransferLineResponse
from app.services.transfer_service import TransferService

router = APIRouter()


@router.post("", response_model=ApiResponse[TransferResponse], status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: TransferCreate,
    user: CurrentUser = Depends(require_auth),
    db: DbSession,
):
    """Create transfer order. Posts TRANSFER_OUT on source immediately."""
    if not body.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one line required")
    try:
        order = await TransferService.create_transfer_order(
            db, user.tenant_id,
            body.from_warehouse_id, body.to_warehouse_id,
            [{"sku_id": l.sku_id, "quantity_requested": l.quantity_requested} for l in body.lines],
            created_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    lines = [TransferLineResponse(id=l.id, sku_id=l.sku_id, quantity_requested=l.quantity_requested, quantity_received=l.quantity_received) for l in order.lines]
    return ApiResponse(data=TransferResponse(
        id=order.id, tenant_id=order.tenant_id,
        from_warehouse_id=order.from_warehouse_id, to_warehouse_id=order.to_warehouse_id,
        status=order.status,
        created_at=order.created_at.isoformat() if order.created_at else None,
        received_at=order.received_at.isoformat() if order.received_at else None,
        lines=lines,
    ))


@router.get("", response_model=ApiResponse[list])
async def list_transfers(
    status: str | None = Query(None, description="PENDING|IN_TRANSIT|RECEIVED|CANCELLED"),
    warehouse_id: UUID | None = None,
    user: CurrentUser = Depends(require_auth),
    db: DbSession,
):
    """List transfer orders."""
    orders = await TransferService.list_transfers(db, user.tenant_id, status=status, warehouse_id=warehouse_id)
    data = []
    for o in orders:
        lines = [{"id": str(l.id), "sku_id": str(l.sku_id), "quantity_requested": float(l.quantity_requested), "quantity_received": float(l.quantity_received) if l.quantity_received else None} for l in o.lines]
        data.append({
            "id": str(o.id),
            "from_warehouse_id": str(o.from_warehouse_id),
            "to_warehouse_id": str(o.to_warehouse_id),
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "received_at": o.received_at.isoformat() if o.received_at else None,
            "lines": lines,
        })
    return ApiResponse(data=data)


@router.post("/{id}/receive", response_model=ApiResponse[dict])
async def receive_transfer(
    id: UUID,
    body: TransferReceiveRequest,
    user: CurrentUser = Depends(require_auth),
    db: DbSession,
):
    """Confirm receipt. Posts TRANSFER_IN on destination. Can be partial."""
    line_qty: dict | None = None
    if body.line_quantities:
        from decimal import Decimal
        line_qty = {UUID(k): Decimal(str(v)) for k, v in body.line_quantities.items()}
    order = await TransferService.confirm_receipt(db, id, user.tenant_id, line_quantities=line_qty)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data={"id": str(order.id), "status": order.status})


@router.post("/{id}/cancel", response_model=ApiResponse[dict])
async def cancel_transfer(
    id: UUID,
    user: CurrentUser = Depends(require_auth),
    db: DbSession,
):
    """Cancel transfer. Reverses TRANSFER_OUT by posting TRANSFER_IN on source."""
    order = await TransferService.cancel_transfer_order(db, id, user.tenant_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data={"id": str(order.id), "status": order.status})
