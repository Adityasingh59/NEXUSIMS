"""NEXUS IMS — ReportService (Block 6): Dashboard KPIs, stock valuation, low-stock alerts."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_type import SKU, ItemType
from app.models.warehouse import StockLedger, Warehouse
from app.models.location import TransferOrder
from app.core.redis import get_redis


DASHBOARD_CACHE_KEY = "dashboard:{tenant_id}"
DASHBOARD_CACHE_TTL = 60


class ReportService:
    """Reporting and analytics queries."""

    @staticmethod
    async def get_dashboard_kpis(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> dict:
        """KPI payload: total SKUs, stock value, low-stock count, pending transfers, recent tx count."""
        # Total active SKUs
        total_skus = (await db.execute(
            select(func.count(SKU.id)).where(SKU.tenant_id == tenant_id, SKU.is_archived == False)
        )).scalar_one()

        # Total stock value: SUM(stock_level * unit_cost) grouped by SKU+warehouse
        stock_value_q = (
            select(
                func.coalesce(
                    func.sum(StockLedger.quantity_delta * SKU.unit_cost), 0
                )
            )
            .join(SKU, StockLedger.sku_id == SKU.id)
            .where(StockLedger.tenant_id == tenant_id, SKU.unit_cost.isnot(None))
        )
        total_stock_value = (await db.execute(stock_value_q)).scalar_one()

        # Low-stock SKUs (at or below reorder_point)
        # Subquery: current stock per SKU
        stock_sub = (
            select(
                StockLedger.sku_id,
                func.sum(StockLedger.quantity_delta).label("total_stock"),
            )
            .where(StockLedger.tenant_id == tenant_id)
            .group_by(StockLedger.sku_id)
            .subquery()
        )
        low_stock_count = (await db.execute(
            select(func.count(SKU.id))
            .outerjoin(stock_sub, SKU.id == stock_sub.c.sku_id)
            .where(
                SKU.tenant_id == tenant_id,
                SKU.is_archived == False,
                SKU.reorder_point.isnot(None),
                func.coalesce(stock_sub.c.total_stock, 0) <= SKU.reorder_point,
            )
        )).scalar_one()

        # Pending transfers
        pending_transfers = (await db.execute(
            select(func.count(TransferOrder.id)).where(
                TransferOrder.tenant_id == tenant_id,
                TransferOrder.status.in_(["PENDING", "IN_TRANSIT"]),
            )
        )).scalar_one()

        # Recent transactions (last 24h)
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_tx_count = (await db.execute(
            select(func.count(StockLedger.id)).where(
                StockLedger.tenant_id == tenant_id,
                StockLedger.created_at >= cutoff,
            )
        )).scalar_one()

        # Active warehouses
        active_warehouses = (await db.execute(
            select(func.count(Warehouse.id)).where(
                Warehouse.tenant_id == tenant_id,
                Warehouse.is_active == True,
            )
        )).scalar_one()

        return {
            "total_skus": total_skus,
            "total_stock_value": float(total_stock_value or 0),
            "low_stock_count": low_stock_count,
            "pending_transfers": pending_transfers,
            "recent_transactions_24h": recent_tx_count,
            "active_warehouses": active_warehouses,
        }

    @staticmethod
    async def get_stock_valuation(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
    ) -> list[dict]:
        """Stock levels × unit_cost per SKU per warehouse."""
        q = (
            select(
                SKU.id.label("sku_id"),
                SKU.sku_code,
                SKU.name.label("sku_name"),
                SKU.unit_cost,
                Warehouse.id.label("warehouse_id"),
                Warehouse.code.label("warehouse_code"),
                func.coalesce(func.sum(StockLedger.quantity_delta), 0).label("stock_level"),
            )
            .join(StockLedger, StockLedger.sku_id == SKU.id)
            .join(Warehouse, StockLedger.warehouse_id == Warehouse.id)
            .where(SKU.tenant_id == tenant_id, SKU.is_archived == False)
            .group_by(SKU.id, SKU.sku_code, SKU.name, SKU.unit_cost, Warehouse.id, Warehouse.code)
            .having(func.sum(StockLedger.quantity_delta) > 0)
            .order_by(SKU.sku_code, Warehouse.code)
        )
        if warehouse_id:
            q = q.where(Warehouse.id == warehouse_id)

        rows = (await db.execute(q)).all()
        return [
            {
                "sku_id": str(r.sku_id),
                "sku_code": r.sku_code,
                "sku_name": r.sku_name,
                "unit_cost": float(r.unit_cost) if r.unit_cost else None,
                "warehouse_id": str(r.warehouse_id),
                "warehouse_code": r.warehouse_code,
                "stock_level": float(r.stock_level),
                "total_value": float(r.stock_level * r.unit_cost) if r.unit_cost else None,
            }
            for r in rows
        ]

    @staticmethod
    async def get_low_stock_skus(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[dict]:
        """SKUs at or below reorder_point with current stock levels."""
        stock_sub = (
            select(
                StockLedger.sku_id,
                func.sum(StockLedger.quantity_delta).label("total_stock"),
            )
            .where(StockLedger.tenant_id == tenant_id)
            .group_by(StockLedger.sku_id)
            .subquery()
        )
        q = (
            select(
                SKU.id,
                SKU.sku_code,
                SKU.name,
                SKU.reorder_point,
                SKU.unit_cost,
                func.coalesce(stock_sub.c.total_stock, 0).label("current_stock"),
            )
            .outerjoin(stock_sub, SKU.id == stock_sub.c.sku_id)
            .where(
                SKU.tenant_id == tenant_id,
                SKU.is_archived == False,
                SKU.reorder_point.isnot(None),
                func.coalesce(stock_sub.c.total_stock, 0) <= SKU.reorder_point,
            )
            .order_by(func.coalesce(stock_sub.c.total_stock, 0).asc())
        )
        rows = (await db.execute(q)).all()
        return [
            {
                "sku_id": str(r.id),
                "sku_code": r.sku_code,
                "sku_name": r.name,
                "reorder_point": float(r.reorder_point),
                "current_stock": float(r.current_stock),
                "unit_cost": float(r.unit_cost) if r.unit_cost else None,
                "deficit": float(r.reorder_point - r.current_stock),
            }
            for r in rows
        ]

    @staticmethod
    async def get_movement_summary(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Aggregated ledger events by type."""
        q = (
            select(
                StockLedger.event_type,
                func.count(StockLedger.id).label("count"),
                func.sum(func.abs(StockLedger.quantity_delta)).label("total_qty"),
            )
            .where(StockLedger.tenant_id == tenant_id)
            .group_by(StockLedger.event_type)
            .order_by(StockLedger.event_type)
        )
        if warehouse_id:
            q = q.where(StockLedger.warehouse_id == warehouse_id)
        if date_from:
            q = q.where(StockLedger.created_at >= date_from)
        if date_to:
            q = q.where(StockLedger.created_at <= date_to)

        rows = (await db.execute(q)).all()
        return {
            "summary": [
                {
                    "event_type": r.event_type,
                    "count": r.count,
                    "total_quantity": float(r.total_qty or 0),
                }
                for r in rows
            ],
        }

    @staticmethod
    async def get_recent_activity(
        db: AsyncSession,
        tenant_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Last N ledger events for activity feed."""
        from app.models.tenant import User
        q = (
            select(
                StockLedger.id,
                StockLedger.event_type,
                StockLedger.quantity_delta,
                StockLedger.created_at,
                StockLedger.notes,
                SKU.sku_code,
                SKU.name.label("sku_name"),
                Warehouse.code.label("warehouse_code"),
            )
            .join(SKU, StockLedger.sku_id == SKU.id)
            .join(Warehouse, StockLedger.warehouse_id == Warehouse.id)
            .where(StockLedger.tenant_id == tenant_id)
            .order_by(StockLedger.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(q)).all()
        return [
            {
                "id": str(r.id),
                "event_type": r.event_type,
                "quantity_delta": float(r.quantity_delta),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "notes": r.notes,
                "sku_code": r.sku_code,
                "sku_name": r.sku_name,
                "warehouse_code": r.warehouse_code,
            }
            for r in rows
        ]
