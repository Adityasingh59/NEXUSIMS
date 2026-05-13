"""NEXUS IMS — LedgerService (Block 2): post_event, get_stock_level (cache-aside), get_transaction_history."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis, stock_cache_key, STOCK_CACHE_TTL
from app.models.warehouse import StockLedger, StockEventType
from app.services.warehouse_service import WarehouseService


class LedgerService:
    """Immutable stock ledger with Redis cache-aside."""

    @staticmethod
    async def get_stock_level(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
    ) -> Decimal:
        """Get current stock. Redis cache-aside, 30s TTL."""
        r = await get_redis()
        key = stock_cache_key(str(tenant_id), str(sku_id), str(warehouse_id))
        cached = await r.get(key)
        if cached is not None:
            return Decimal(cached)

        result = await db.execute(
            select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                StockLedger.sku_id == sku_id,
                StockLedger.warehouse_id == warehouse_id,
            )
        )
        level = result.scalar_one()
        await r.setex(key, STOCK_CACHE_TTL, str(level))
        return Decimal(str(level))

    @staticmethod
    async def post_event(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        event_type: StockEventType | str,
        quantity_delta: Decimal,
        *,
        location_id: UUID | None = None,
        reference_id: UUID | None = None,
        actor_id: UUID | None = None,
        notes: str | None = None,
        reason_code: str | None = None,
    ) -> StockLedger:
        """Append ledger event. Validates warehouse, checks negative stock, invalidates cache."""
        warehouse = await WarehouseService.get_by_id(db, warehouse_id, tenant_id)
        if not warehouse:
            raise ValueError("Warehouse not found or inactive")

        current = await LedgerService.get_stock_level(db, tenant_id, sku_id, warehouse_id)
        new_balance = current + quantity_delta
        if new_balance < 0:
            raise ValueError(f"Negative stock not allowed: balance would be {new_balance}")

        ev = StockLedger(
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            event_type=event_type.value if isinstance(event_type, StockEventType) else event_type,
            quantity_delta=quantity_delta,
            reference_id=reference_id,
            actor_id=actor_id,
            notes=notes,
            reason_code=reason_code,
        )
        db.add(ev)
        await db.flush()
        await db.refresh(ev)

        # Invalidate Redis cache
        r = await get_redis()
        await r.delete(stock_cache_key(str(tenant_id), str(sku_id), str(warehouse_id)))

        # Block 9: Evaluate Workflows automatically
        from app.services.workflow_engine import WorkflowEngine
        payload = {
            "event_id": str(ev.id),
            "sku_id": str(ev.sku_id),
            "warehouse_id": str(ev.warehouse_id),
            "quantity_delta": float(ev.quantity_delta),
            "quantity": float(new_balance),
            "notes": ev.notes,
            "reason": ev.reason_code
        }
        await WorkflowEngine.evaluate(db, str(tenant_id), ev.event_type, payload)

        return ev

    @staticmethod
    async def get_transaction_history(
        db: AsyncSession,
        tenant_id: UUID,
        *,
        sku_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        event_type: str | None = None,
        actor_id: UUID | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[tuple[StockLedger, Decimal]], int]:
        """Paginated transaction history with running balance computed via window function (single query)."""
        # Build filter conditions shared by count + data queries
        filters = [StockLedger.tenant_id == tenant_id]
        if sku_id:
            filters.append(StockLedger.sku_id == sku_id)
        if warehouse_id:
            filters.append(StockLedger.warehouse_id == warehouse_id)
        if event_type:
            filters.append(StockLedger.event_type == event_type)
        if actor_id:
            filters.append(StockLedger.actor_id == actor_id)
        if date_from:
            filters.append(StockLedger.created_at >= date_from)
        if date_to:
            filters.append(StockLedger.created_at <= date_to)

        total = (await db.execute(
            select(func.count(StockLedger.id)).where(*filters)
        )).scalar_one()

        # Single query: window function computes cumulative balance per sku+warehouse
        running_balance = (
            func.sum(StockLedger.quantity_delta)
            .over(
                partition_by=[StockLedger.sku_id, StockLedger.warehouse_id],
                order_by=StockLedger.created_at.asc(),
                rows=(None, 0),  # UNBOUNDED PRECEDING to CURRENT ROW
            )
            .label("running_balance")
        )

        data_q = (
            select(StockLedger, running_balance)
            .where(*filters)
            .order_by(StockLedger.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(data_q)
        rows = result.all()

        out: list[tuple[StockLedger, Decimal]] = [
            (row.StockLedger, Decimal(str(row.running_balance or 0)))
            for row in rows
        ]

        return out, total
