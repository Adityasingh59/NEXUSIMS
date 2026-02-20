"""NEXUS IMS — Scanner endpoints (Block 5): fast barcode lookup, scan-to-receive, scan-to-pick."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_TRANSACTIONS_RECEIVE, PERM_TRANSACTIONS_PICK, PERM_TRANSACTIONS_ADJUST,
)
from app.models.item_type import SKU
from app.models.warehouse import StockLedger, StockEventType
from app.services.ledger_service import LedgerService

router = APIRouter()


# ── Request / Response schemas ───────────────────────────────────────────────

class ScanLookupRequest(BaseModel):
    barcode: str  # Can be sku_code or UUID
    warehouse_id: UUID


class ScanLookupResponse(BaseModel):
    sku_id: str
    sku_code: str
    sku_name: str
    unit_cost: float | None
    current_stock: float
    reorder_point: float | None
    warehouse_id: str


class ScanReceiveRequest(BaseModel):
    barcode: str
    warehouse_id: UUID
    quantity: Decimal
    notes: str | None = None


class ScanPickRequest(BaseModel):
    barcode: str
    warehouse_id: UUID
    quantity: Decimal = Decimal("1")
    notes: str | None = None


class ScanAdjustRequest(BaseModel):
    barcode: str
    warehouse_id: UUID
    quantity_delta: Decimal
    reason_code: str
    notes: str | None = None


class ScanConfirmation(BaseModel):
    success: bool
    event_type: str
    sku_code: str
    sku_name: str
    quantity: float
    new_balance: float
    message: str


# ── Helper ───────────────────────────────────────────────────────────────────

async def _resolve_sku(db: AsyncSession, barcode: str, tenant_id: UUID) -> SKU:
    """Resolve barcode to SKU: try sku_code first, then UUID."""
    # Try sku_code (most common for scanners)
    result = await db.execute(
        select(SKU).where(
            SKU.tenant_id == tenant_id,
            SKU.sku_code == barcode,
            SKU.is_archived == False,
        )
    )
    sku = result.scalar_one_or_none()
    if sku:
        return sku

    # Try as UUID
    try:
        sku_uuid = UUID(barcode)
        result = await db.execute(
            select(SKU).where(
                SKU.tenant_id == tenant_id,
                SKU.id == sku_uuid,
                SKU.is_archived == False,
            )
        )
        sku = result.scalar_one_or_none()
        if sku:
            return sku
    except ValueError:
        pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"SKU not found for barcode: {barcode}",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/lookup", response_model=ScanLookupResponse)
async def scan_lookup(
    body: ScanLookupRequest,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Barcode → SKU info + current stock. Optimized for scanner speed."""
    sku = await _resolve_sku(db, body.barcode, user.tenant_id)
    stock = await LedgerService.get_stock_level(db, user.tenant_id, sku.id, body.warehouse_id)

    return ScanLookupResponse(
        sku_id=str(sku.id),
        sku_code=sku.sku_code,
        sku_name=sku.name,
        unit_cost=float(sku.unit_cost) if sku.unit_cost else None,
        current_stock=float(stock),
        reorder_point=float(sku.reorder_point) if sku.reorder_point else None,
        warehouse_id=str(body.warehouse_id),
    )


@router.post("/receive", response_model=ScanConfirmation)
async def scan_receive(
    body: ScanReceiveRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_RECEIVE)),
    db: AsyncSession = Depends(get_db),
):
    """Scan-to-receive: barcode + qty → RECEIVE ledger event."""
    sku = await _resolve_sku(db, body.barcode, user.tenant_id)

    try:
        event = await LedgerService.post_event(
            db, user.tenant_id, sku.id, body.warehouse_id,
            StockEventType.RECEIVE, body.quantity,
            actor_id=user.id, notes=body.notes,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_balance = await LedgerService.get_stock_level(db, user.tenant_id, sku.id, body.warehouse_id)

    return ScanConfirmation(
        success=True,
        event_type="RECEIVE",
        sku_code=sku.sku_code,
        sku_name=sku.name,
        quantity=float(body.quantity),
        new_balance=float(new_balance),
        message=f"Received {body.quantity} × {sku.sku_code}",
    )


@router.post("/pick", response_model=ScanConfirmation)
async def scan_pick(
    body: ScanPickRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_PICK)),
    db: AsyncSession = Depends(get_db),
):
    """Scan-to-pick: barcode → PICK ledger event."""
    sku = await _resolve_sku(db, body.barcode, user.tenant_id)

    try:
        event = await LedgerService.post_event(
            db, user.tenant_id, sku.id, body.warehouse_id,
            StockEventType.PICK, -abs(body.quantity),
            actor_id=user.id, notes=body.notes,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_balance = await LedgerService.get_stock_level(db, user.tenant_id, sku.id, body.warehouse_id)

    return ScanConfirmation(
        success=True,
        event_type="PICK",
        sku_code=sku.sku_code,
        sku_name=sku.name,
        quantity=float(body.quantity),
        new_balance=float(new_balance),
        message=f"Picked {body.quantity} × {sku.sku_code}",
    )


@router.post("/adjust", response_model=ScanConfirmation)
async def scan_adjust(
    body: ScanAdjustRequest,
    user: CurrentUser = Depends(require_permission(PERM_TRANSACTIONS_ADJUST)),
    db: AsyncSession = Depends(get_db),
):
    """Scan-to-adjust: barcode + delta + reason → ADJUST ledger event."""
    sku = await _resolve_sku(db, body.barcode, user.tenant_id)

    try:
        event = await LedgerService.post_event(
            db, user.tenant_id, sku.id, body.warehouse_id,
            StockEventType.ADJUST, body.quantity_delta,
            actor_id=user.id, notes=body.notes, reason_code=body.reason_code,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_balance = await LedgerService.get_stock_level(db, user.tenant_id, sku.id, body.warehouse_id)

    return ScanConfirmation(
        success=True,
        event_type="ADJUST",
        sku_code=sku.sku_code,
        sku_name=sku.name,
        quantity=float(body.quantity_delta),
        new_balance=float(new_balance),
        message=f"Adjusted {sku.sku_code} by {body.quantity_delta} ({body.reason_code})",
    )
