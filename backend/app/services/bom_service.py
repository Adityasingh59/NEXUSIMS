"""NEXUS IMS — BOMService (Block 5): create, read, update, archive, explode."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import BOM, BOMLine


class BOMService:
    """CRUD for Bill of Materials."""

    @staticmethod
    async def create_bom(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        name: str,
        lines: list[dict],
        created_by: UUID | None = None,
    ) -> BOM:
        """Create BOM with lines atomically."""
        bom = BOM(
            tenant_id=tenant_id,
            sku_id=sku_id,
            name=name,
            created_by=created_by,
        )
        db.add(bom)
        await db.flush()  # Get bom.id

        for line_data in lines:
            line = BOMLine(
                bom_id=bom.id,
                component_sku_id=line_data["component_sku_id"],
                quantity=Decimal(str(line_data["quantity"])),
                unit_cost_snapshot=Decimal(str(line_data["unit_cost_snapshot"])),
            )
            db.add(line)

        await db.flush()
        await db.refresh(bom)
        return bom

    @staticmethod
    async def get_boms(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[BOM]:
        """List BOMs for tenant, optionally filtered by SKU."""
        q = select(BOM).where(BOM.tenant_id == tenant_id)
        if not include_inactive:
            q = q.where(BOM.is_active.is_(True))
        if sku_id:
            q = q.where(BOM.sku_id == sku_id)
        q = q.order_by(BOM.created_at.desc())
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_bom(
        db: AsyncSession,
        tenant_id: UUID,
        bom_id: UUID,
    ) -> BOM | None:
        """Get single BOM with lines (selectin loaded)."""
        result = await db.execute(
            select(BOM).where(BOM.id == bom_id, BOM.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_bom(
        db: AsyncSession,
        tenant_id: UUID,
        bom_id: UUID,
        name: str | None = None,
        lines: list[dict] | None = None,
    ) -> BOM | None:
        """Update BOM name and/or replace all lines."""
        bom = await BOMService.get_bom(db, tenant_id, bom_id)
        if not bom:
            return None

        if name is not None:
            bom.name = name

        if lines is not None:
            # Delete existing lines and replace
            for existing_line in list(bom.lines):
                await db.delete(existing_line)
            await db.flush()

            for line_data in lines:
                line = BOMLine(
                    bom_id=bom.id,
                    component_sku_id=line_data["component_sku_id"],
                    quantity=Decimal(str(line_data["quantity"])),
                    unit_cost_snapshot=Decimal(str(line_data["unit_cost_snapshot"])),
                )
                db.add(line)

        await db.flush()
        await db.refresh(bom)
        return bom

    @staticmethod
    async def archive_bom(
        db: AsyncSession,
        tenant_id: UUID,
        bom_id: UUID,
    ) -> BOM | None:
        """Soft-delete a BOM by setting is_active=False."""
        bom = await BOMService.get_bom(db, tenant_id, bom_id)
        if not bom:
            return None
        bom.is_active = False
        await db.flush()
        return bom

    @staticmethod
    async def explode_bom(
        db: AsyncSession,
        tenant_id: UUID,
        bom_id: UUID,
        quantity: Decimal,
    ) -> dict[str, Decimal]:
        """
        Expand BOM for a given production quantity.
        Returns {component_sku_id_str: total_required_quantity}.
        """
        bom = await BOMService.get_bom(db, tenant_id, bom_id)
        if not bom:
            return {}

        result: dict[str, Decimal] = {}
        for line in bom.lines:
            key = str(line.component_sku_id)
            result[key] = result.get(key, Decimal("0")) + (line.quantity * quantity)
        return result
