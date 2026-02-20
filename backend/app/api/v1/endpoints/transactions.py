"""NEXUS IMS — Transaction endpoints (Block 2). POST receive/pick/adjust/return, GET transactions."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_TRANSACTIONS_RECEIVE, PERM_TRANSACTIONS_PICK, PERM_TRANSACTIONS_ADJUST,
)
from app.models.warehouse import StockEventType
from app.schemas.common import ApiResponse, Meta
from app.schemas.warehouse import AdjustRequest, PickRequest, ReceiveRequest, ReturnRequest
from app.services.ledger_service import LedgerService

router = APIRouter()


class LedgerEventResponse(BaseModel):
    id: UUID
    sku_id: UUID
    warehouse_id: UUID
    event_type: str
    quantity_delta: Decimal
    reference_id: UUID | None
    actor_id: UUID | None
    notes: str | None
    reason_code: str | None
    created_at: str
    running_balance: Decimal | None = None

    class Config:
        from_attributes = True


@router.post("/receive", response_model=ApiResponse[LedgerEventResponse])
async def receive(
    body: ReceiveRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_RECEIVE)),
    db: AsyncSession = Depends(get_db),
):
    """Post RECEIVE event (inbound). quantity is positive."""
    try:
        ev = await LedgerService.post_event(
            db, user.tenant_id, body.sku_id, body.warehouse_id,
            StockEventType.RECEIVE, Decimal(str(body.quantity)),
            location_id=body.location_id, reference_id=body.reference_id,
            actor_id=user.id, notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApiResponse(data=LedgerEventResponse(
        id=ev.id, sku_id=ev.sku_id, warehouse_id=ev.warehouse_id,
        event_type=ev.event_type, quantity_delta=ev.quantity_delta,
        reference_id=ev.reference_id, actor_id=ev.actor_id,
        notes=ev.notes, reason_code=ev.reason_code,
        created_at=ev.created_at.isoformat() if ev.created_at else "",
    ))


@router.post("/pick", response_model=ApiResponse[LedgerEventResponse])
async def pick(
    body: PickRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_PICK)),
    db: AsyncSession = Depends(get_db),
):
    """Post PICK event (outbound). quantity is negative."""
    qty = -abs(body.quantity)
    try:
        ev = await LedgerService.post_event(
            db, user.tenant_id, body.sku_id, body.warehouse_id,
            StockEventType.PICK, Decimal(str(qty)),
            location_id=body.location_id, reference_id=body.reference_id,
            actor_id=user.id, notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApiResponse(data=LedgerEventResponse(
        id=ev.id, sku_id=ev.sku_id, warehouse_id=ev.warehouse_id,
        event_type=ev.event_type, quantity_delta=ev.quantity_delta,
        reference_id=ev.reference_id, actor_id=ev.actor_id,
        notes=ev.notes, reason_code=ev.reason_code,
        created_at=ev.created_at.isoformat() if ev.created_at else "",
    ))


@router.post("/adjust", response_model=ApiResponse[LedgerEventResponse])
async def adjust(
    body: AdjustRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_ADJUST)),
    db: AsyncSession = Depends(get_db),
):
    """Post ADJUST event. quantity can be positive or negative. Requires reason_code."""
    try:
        ev = await LedgerService.post_event(
            db, user.tenant_id, body.sku_id, body.warehouse_id,
            StockEventType.ADJUST, Decimal(str(body.quantity)),
            actor_id=user.id, notes=body.notes,
            reason_code=body.reason_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApiResponse(data=LedgerEventResponse(
        id=ev.id, sku_id=ev.sku_id, warehouse_id=ev.warehouse_id,
        event_type=ev.event_type, quantity_delta=ev.quantity_delta,
        reference_id=ev.reference_id, actor_id=ev.actor_id,
        notes=ev.notes, reason_code=ev.reason_code,
        created_at=ev.created_at.isoformat() if ev.created_at else "",
    ))


@router.post("/return", response_model=ApiResponse[LedgerEventResponse])
async def return_event(
    body: ReturnRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_RECEIVE)),
    db: AsyncSession = Depends(get_db),
):
    """Post RETURN event (inbound). quantity positive."""
    try:
        ev = await LedgerService.post_event(
            db, user.tenant_id, body.sku_id, body.warehouse_id,
            StockEventType.RETURN, Decimal(str(abs(body.quantity))),
            actor_id=user.id, notes=f"{body.notes or ''} disposition={body.disposition}".strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApiResponse(data=LedgerEventResponse(
        id=ev.id, sku_id=ev.sku_id, warehouse_id=ev.warehouse_id,
        event_type=ev.event_type, quantity_delta=ev.quantity_delta,
        reference_id=ev.reference_id, actor_id=ev.actor_id,
        notes=ev.notes, reason_code=ev.reason_code,
        created_at=ev.created_at.isoformat() if ev.created_at else "",
    ))


@router.get("/stock", response_model=ApiResponse[dict])
async def get_stock(
    sku_id: UUID,
    warehouse_id: UUID,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get current stock level for SKU at warehouse (Redis cache-aside)."""
    level = await LedgerService.get_stock_level(db, user.tenant_id, sku_id, warehouse_id)
    return ApiResponse(data={"sku_id": str(sku_id), "warehouse_id": str(warehouse_id), "quantity": float(level)})


@router.get("", response_model=ApiResponse[list])
async def list_transactions(
    sku_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    event_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List transaction history with running balance."""
    rows, total = await LedgerService.get_transaction_history(
        db, user.tenant_id,
        sku_id=sku_id, warehouse_id=warehouse_id, event_type=event_type,
        page=page, page_size=page_size,
    )
    data = [
        {
            "id": str(r.id), "sku_id": str(r.sku_id), "warehouse_id": str(r.warehouse_id),
            "event_type": r.event_type, "quantity_delta": float(r.quantity_delta),
            "reference_id": str(r.reference_id) if r.reference_id else None,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "notes": r.notes, "reason_code": r.reason_code,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "running_balance": float(bal),
        }
        for r, bal in rows
    ]
    return ApiResponse(data=data, meta=Meta(page=page, page_size=page_size, total_count=total))
