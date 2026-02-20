"""NEXUS IMS — COGSService (Block 5): weighted-average cost from BOM lines."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import BOM


class COGSService:
    """Calculate Cost of Goods Sold from active BOM unit costs."""

    @staticmethod
    async def calculate_cogs(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        quantity: Decimal,
    ) -> dict | None:
        """
        Returns COGS for producing `quantity` units of `sku_id`.
        Uses the active BOM for that SKU.
        Returns None if no active BOM exists.

        Result: {sku_id, quantity, total_cogs, bom_id, line_breakdown: [{component_sku_id, qty, unit_cost, line_total}]}
        """
        result = await db.execute(
            select(BOM).where(
                BOM.tenant_id == tenant_id,
                BOM.sku_id == sku_id,
                BOM.is_active.is_(True),
            ).order_by(BOM.created_at.desc()).limit(1)
        )
        bom = result.scalar_one_or_none()
        if not bom:
            return None

        breakdown = []
        total_cogs = Decimal("0")

        for line in bom.lines:
            line_total = line.quantity * line.unit_cost_snapshot * quantity
            total_cogs += line_total
            breakdown.append({
                "component_sku_id": str(line.component_sku_id),
                "quantity_per_unit": float(line.quantity),
                "unit_cost": float(line.unit_cost_snapshot),
                "total_quantity": float(line.quantity * quantity),
                "line_total": float(line_total),
            })

        return {
            "sku_id": str(sku_id),
            "quantity": float(quantity),
            "bom_id": str(bom.id),
            "bom_name": bom.name,
            "total_cogs": float(total_cogs),
            "currency": "USD",
            "line_breakdown": breakdown,
        }
