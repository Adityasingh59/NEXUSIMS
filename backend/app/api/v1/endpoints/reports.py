"""NEXUS IMS — Reports endpoints (Block 6): Dashboard KPIs, stock valuation, low-stock, movement, accuracy, export."""
import json
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission, PERM_REPORTS_READ
from app.core.redis import get_redis
from app.models.warehouse import StockEventType, StockLedger
from app.schemas.common import ApiResponse, Meta
from app.services.report_service import ReportService

router = APIRouter()

DASHBOARD_CACHE_KEY = "report:dashboard:{tid}"
DASHBOARD_CACHE_TTL = 60


@router.get("/dashboard")
async def get_dashboard(
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """KPI dashboard: total SKUs, stock value, low-stock count, pending transfers. Redis-cached 60s."""
    r = await get_redis()
    key = DASHBOARD_CACHE_KEY.format(tid=user.tenant_id)
    cached = await r.get(key)
    if cached:
        return {"data": json.loads(cached), "error": None, "meta": {}}

    data = await ReportService.get_dashboard_kpis(db, user.tenant_id)
    await r.setex(key, DASHBOARD_CACHE_TTL, json.dumps(data))
    return {"data": data, "error": None, "meta": {}}


@router.get("/stock-valuation")
async def get_stock_valuation(
    warehouse_id: UUID | None = Query(None),
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Stock levels × unit_cost per SKU per warehouse."""
    data = await ReportService.get_stock_valuation(db, user.tenant_id, warehouse_id)
    total_value = sum(r["total_value"] or 0 for r in data)
    return {"data": data, "error": None, "meta": {"total_value": total_value, "count": len(data)}}


@router.get("/low-stock")
async def get_low_stock(
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """SKUs at or below reorder_point."""
    data = await ReportService.get_low_stock_skus(db, user.tenant_id)
    return {"data": data, "error": None, "meta": {"count": len(data)}}


@router.get("/movement-history")
async def get_movement_history(
    warehouse_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated ledger events by event type."""
    data = await ReportService.get_movement_summary(
        db, user.tenant_id, warehouse_id, date_from, date_to,
    )
    return {"data": data, "error": None, "meta": {}}


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Last N ledger events for dashboard activity feed."""
    data = await ReportService.get_recent_activity(db, user.tenant_id, limit)
    return {"data": data, "error": None, "meta": {}}


@router.get("/accuracy")
async def get_accuracy(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Cycle count history — COUNT_CORRECT events with variance data."""
    q = (
        select(StockLedger)
        .where(
            StockLedger.tenant_id == user.tenant_id,
            StockLedger.event_type == StockEventType.COUNT_CORRECT.value,
        )
    )
    count_q = (
        select(func.count(StockLedger.id))
        .where(
            StockLedger.tenant_id == user.tenant_id,
            StockLedger.event_type == StockEventType.COUNT_CORRECT.value,
        )
    )
    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(StockLedger.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = list(result.scalars().all())

    data = [
        {
            "id": str(r.id),
            "sku_id": str(r.sku_id),
            "warehouse_id": str(r.warehouse_id),
            "variance": float(r.quantity_delta),
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"data": data, "error": None, "meta": {"page": page, "page_size": page_size, "total_count": total}}


@router.post("/export")
async def request_export(
    report_type: str = Query(..., description="stock-valuation | movement-history | low-stock"),
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue CSV export job. Returns job_id for polling."""
    from app.tasks.report_tasks import generate_csv_export

    job_id = str(uuid.uuid4())
    generate_csv_export.delay(job_id, str(user.tenant_id), report_type)
    return {"data": {"job_id": job_id, "status": "PENDING"}, "error": None, "meta": {}}


@router.get("/exports/{job_id}")
async def get_export_status(
    job_id: str,
    user: CurrentUser = Depends(require_permission(PERM_REPORTS_READ)),
):
    """Poll export job status."""
    r = await get_redis()
    result = await r.get(f"export:{job_id}")
    if not result:
        return {"data": {"job_id": job_id, "status": "PENDING"}, "error": None, "meta": {}}
    info = json.loads(result)
    return {"data": info, "error": None, "meta": {}}
