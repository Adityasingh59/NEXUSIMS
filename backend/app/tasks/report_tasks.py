"""NEXUS IMS — Celery tasks for reporting (Block 6).

- refresh_dashboard_cache:  Celery Beat runs every 60s — recalculates dashboard KPIs.
- generate_csv_export:      Async CSV generation, stores in Redis for download.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.worker import celery_app

logger = logging.getLogger(__name__)


def _sync_engine():
    """Create a sync engine for Celery tasks (workers cannot use async)."""
    from sqlalchemy import create_engine
    from app.config import get_settings
    settings = get_settings()
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
    return create_engine(sync_url, pool_pre_ping=True, pool_size=2)


def _sync_redis():
    """Get a sync Redis client for Celery tasks."""
    import redis
    from app.config import get_settings
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(bind=True, max_retries=2)
def refresh_dashboard_cache(self):
    """Refresh dashboard KPI cache for all tenants. Run by Celery Beat every 60s."""
    from sqlalchemy.orm import Session
    from app.models.item_type import SKU
    from app.models.warehouse import StockLedger, Warehouse
    from app.models.location import TransferOrder, TransferStatus
    from app.models.tenant import Tenant

    engine = _sync_engine()
    r = _sync_redis()

    try:
        with Session(engine) as db:
            tenants = db.execute(select(Tenant.id)).scalars().all()
            for tenant_id in tenants:
                try:
                    # Total active SKUs
                    total_skus = db.execute(
                        select(func.count(SKU.id)).where(
                            SKU.tenant_id == tenant_id,
                            SKU.is_archived == False,  # noqa: E712
                        )
                    ).scalar_one()

                    # Inventory value
                    stock_sub = (
                        select(
                            StockLedger.sku_id,
                            func.sum(StockLedger.quantity_delta).label("qty"),
                        )
                        .where(StockLedger.tenant_id == tenant_id)
                        .group_by(StockLedger.sku_id)
                        .subquery()
                    )
                    valuation = db.execute(
                        select(
                            func.coalesce(func.sum(stock_sub.c.qty * SKU.unit_cost), 0)
                        )
                        .select_from(stock_sub)
                        .join(SKU, SKU.id == stock_sub.c.sku_id)
                    ).scalar_one()

                    # Low-stock count
                    low_stock_count = db.execute(
                        select(func.count())
                        .select_from(stock_sub)
                        .join(SKU, SKU.id == stock_sub.c.sku_id)
                        .where(
                            SKU.reorder_point.isnot(None),
                            stock_sub.c.qty <= SKU.reorder_point,
                        )
                    ).scalar_one()

                    # Pending transfers
                    pending_transfers = db.execute(
                        select(func.count(TransferOrder.id)).where(
                            TransferOrder.tenant_id == tenant_id,
                            TransferOrder.status.in_([
                                TransferStatus.PENDING.value,
                                TransferStatus.IN_TRANSIT.value,
                            ]),
                        )
                    ).scalar_one()

                    data = {
                        "total_skus": total_skus,
                        "inventory_value": float(valuation),
                        "low_stock_count": low_stock_count,
                        "pending_transfers": pending_transfers,
                        "recent_events": [],  # Beat doesn't refresh the event feed
                    }
                    cache_key = f"report:dashboard:{tenant_id}"
                    r.setex(cache_key, 60, json.dumps(data))
                except Exception as exc:
                    logger.warning("Dashboard refresh failed for tenant %s: %s", tenant_id, exc)
    finally:
        engine.dispose()


@celery_app.task(bind=True, max_retries=2)
def generate_csv_export(self, job_id: str, tenant_id_str: str, report_type: str):
    """Generate CSV export and store download content in Redis (24h TTL)."""
    from sqlalchemy.orm import Session
    from app.models.item_type import SKU
    from app.models.warehouse import StockLedger, Warehouse

    engine = _sync_engine()
    r = _sync_redis()
    tenant_id = UUID(tenant_id_str)

    try:
        with Session(engine) as db:
            buf = io.StringIO()
            writer = csv.writer(buf)

            if report_type == "stock-valuation":
                writer.writerow(["SKU Code", "SKU Name", "Warehouse", "Quantity", "Unit Cost", "Line Value"])
                stock_sub = (
                    select(
                        StockLedger.sku_id,
                        StockLedger.warehouse_id,
                        func.sum(StockLedger.quantity_delta).label("qty"),
                    )
                    .where(StockLedger.tenant_id == tenant_id)
                    .group_by(StockLedger.sku_id, StockLedger.warehouse_id)
                    .subquery()
                )
                rows = db.execute(
                    select(
                        SKU.sku_code,
                        SKU.name,
                        Warehouse.code,
                        stock_sub.c.qty,
                        SKU.unit_cost,
                        (stock_sub.c.qty * func.coalesce(SKU.unit_cost, 0)).label("line_value"),
                    )
                    .select_from(stock_sub)
                    .join(SKU, SKU.id == stock_sub.c.sku_id)
                    .join(Warehouse, Warehouse.id == stock_sub.c.warehouse_id)
                    .order_by(SKU.sku_code)
                ).all()
                for row in rows:
                    writer.writerow([row.sku_code, row.name, row.code, float(row.qty),
                                     float(row.unit_cost) if row.unit_cost else "", float(row.line_value)])

            elif report_type == "movement-history":
                writer.writerow(["ID", "SKU ID", "Warehouse ID", "Event Type", "Qty Delta", "Notes", "Created At"])
                rows = db.execute(
                    select(StockLedger)
                    .where(StockLedger.tenant_id == tenant_id)
                    .order_by(StockLedger.created_at.desc())
                    .limit(10000)
                ).scalars().all()
                for row in rows:
                    writer.writerow([
                        str(row.id), str(row.sku_id), str(row.warehouse_id),
                        row.event_type, float(row.quantity_delta),
                        row.notes or "", row.created_at.isoformat() if row.created_at else "",
                    ])

            elif report_type == "low-stock":
                writer.writerow(["SKU Code", "SKU Name", "Warehouse", "Current Stock", "Reorder Point", "Deficit"])
                stock_sub = (
                    select(
                        StockLedger.sku_id,
                        StockLedger.warehouse_id,
                        func.sum(StockLedger.quantity_delta).label("qty"),
                    )
                    .where(StockLedger.tenant_id == tenant_id)
                    .group_by(StockLedger.sku_id, StockLedger.warehouse_id)
                    .subquery()
                )
                rows = db.execute(
                    select(
                        SKU.sku_code, SKU.name, Warehouse.code,
                        stock_sub.c.qty, SKU.reorder_point,
                        (SKU.reorder_point - stock_sub.c.qty).label("deficit"),
                    )
                    .select_from(stock_sub)
                    .join(SKU, SKU.id == stock_sub.c.sku_id)
                    .join(Warehouse, Warehouse.id == stock_sub.c.warehouse_id)
                    .where(
                        SKU.reorder_point.isnot(None),
                        stock_sub.c.qty <= SKU.reorder_point,
                    )
                    .order_by((SKU.reorder_point - stock_sub.c.qty).desc())
                ).all()
                for row in rows:
                    writer.writerow([
                        row.sku_code, row.name, row.code,
                        float(row.qty), float(row.reorder_point), float(row.deficit),
                    ])
            else:
                r.setex(f"export:{job_id}", 86400, json.dumps({
                    "job_id": job_id, "status": "FAILED", "error": f"Unknown report type: {report_type}",
                }))
                return

            csv_content = buf.getvalue()
            r.setex(f"export:{job_id}", 86400, json.dumps({
                "job_id": job_id, "status": "COMPLETE",
                "report_type": report_type,
                "csv": csv_content,
                "row_count": csv_content.count("\n") - 1,
            }))
    except Exception as exc:
        logger.exception("CSV export failed for job %s", job_id)
        r.setex(f"export:{job_id}", 86400, json.dumps({
            "job_id": job_id, "status": "FAILED", "error": str(exc),
        }))
    finally:
        engine.dispose()
