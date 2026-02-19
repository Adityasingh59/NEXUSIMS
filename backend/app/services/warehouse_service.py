"""NEXUS IMS — WarehouseService (Block 2, 3 — CRUD + stock)."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import StockLedger, Warehouse


class WarehouseService:
    """CRUD and stock summary for warehouses."""

    @staticmethod
    async def get_by_id(db: AsyncSession, id: UUID, tenant_id: UUID) -> Warehouse | None:
        result = await db.execute(
            select(Warehouse).where(
                Warehouse.id == id,
                Warehouse.tenant_id == tenant_id,
                Warehouse.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active(db: AsyncSession, tenant_id: UUID) -> list[Warehouse]:
        result = await db.execute(
            select(Warehouse)
            .where(Warehouse.tenant_id == tenant_id, Warehouse.is_active == True)
            .order_by(Warehouse.code)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_warehouse_stock(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID,
    ) -> list[tuple[UUID, Decimal]]:
        """Returns list of (sku_id, quantity) for all SKUs with stock at warehouse."""
        result = await db.execute(
            select(StockLedger.sku_id, func.coalesce(func.sum(StockLedger.quantity_delta), 0))
            .where(
                StockLedger.tenant_id == tenant_id,
                StockLedger.warehouse_id == warehouse_id,
            )
            .group_by(StockLedger.sku_id)
            .having(func.sum(StockLedger.quantity_delta) > 0)
        )
        return [(row[0], Decimal(str(row[1]))) for row in result.all()]
