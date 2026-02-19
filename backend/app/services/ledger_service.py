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
        """Paginated transaction history with running balance."""
        q = select(StockLedger).where(StockLedger.tenant_id == tenant_id)
        count_q = select(func.count(StockLedger.id)).where(StockLedger.tenant_id == tenant_id)
        if sku_id:
            q = q.where(StockLedger.sku_id == sku_id)
            count_q = count_q.where(StockLedger.sku_id == sku_id)
        if warehouse_id:
            q = q.where(StockLedger.warehouse_id == warehouse_id)
            count_q = count_q.where(StockLedger.warehouse_id == warehouse_id)
        if event_type:
            q = q.where(StockLedger.event_type == event_type)
            count_q = count_q.where(StockLedger.event_type == event_type)
        if actor_id:
            q = q.where(StockLedger.actor_id == actor_id)
            count_q = count_q.where(StockLedger.actor_id == actor_id)
        if date_from:
            q = q.where(StockLedger.created_at >= date_from)
            count_q = count_q.where(StockLedger.created_at >= date_from)
        if date_to:
            q = q.where(StockLedger.created_at <= date_to)
            count_q = count_q.where(StockLedger.created_at <= date_to)

        total = (await db.execute(count_q)).scalar_one()
        q = q.order_by(StockLedger.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(q)
        rows = list(result.scalars().all())

        # Running balance per row (simplified: sum up to this row for same sku+warehouse)
        out: list[tuple[StockLedger, Decimal]] = []
        for r in rows:
            bal_result = await db.execute(
                select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                    StockLedger.sku_id == r.sku_id,
                    StockLedger.warehouse_id == r.warehouse_id,
                    StockLedger.created_at <= r.created_at,
                )
            )
            bal = bal_result.scalar_one()
            out.append((r, Decimal(str(bal))))

        return out, total
