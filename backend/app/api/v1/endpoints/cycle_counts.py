"""NEXUS IMS — Cycle count endpoints (Block 2.3). Simplified flow."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_db, require_auth
from app.models.warehouse import StockEventType
from app.schemas.common import ApiResponse
from app.services.ledger_service import LedgerService

router = APIRouter()


class CycleCountSubmit(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    location_id: UUID | None = None
    physical_count: float


class CycleCountCommit(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    location_id: UUID | None = None
    physical_count: float
    variance: float  # physical - system; positive = add stock


@router.post("/submit", response_model=ApiResponse[dict])
async def submit_cycle_count(
    body: CycleCountSubmit,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Record physical count, return variance (physical - system). No ledger write yet."""
    system = await LedgerService.get_stock_level(db, user.tenant_id, body.sku_id, body.warehouse_id)
    physical = Decimal(str(body.physical_count))
    variance = physical - system
    return ApiResponse(data={
        "sku_id": str(body.sku_id),
        "warehouse_id": str(body.warehouse_id),
        "physical_count": float(physical),
        "system_count": float(system),
        "variance": float(variance),
    })


@router.post("/commit", response_model=ApiResponse[dict])
async def commit_cycle_count(
    body: CycleCountCommit,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Write COUNT_CORRECT (ADJUST) event after review. quantity_delta = variance."""
    if body.variance == 0:
        return ApiResponse(data={"message": "No variance, no event written"})
    try:
        ev = await LedgerService.post_event(
            db, user.tenant_id, body.sku_id, body.warehouse_id,
            StockEventType.COUNT_CORRECT, Decimal(str(body.variance)),
            location_id=body.location_id, actor_id=user.id,
            reason_code="CYCLE_COUNT",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApiResponse(data={
        "id": str(ev.id),
        "event_type": ev.event_type,
        "quantity_delta": float(ev.quantity_delta),
    })
