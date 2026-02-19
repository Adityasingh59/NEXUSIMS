"""NEXUS IMS — SKUService (Block 1.2)."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_type import ItemType, SKU
from app.services.attribute_validator import AttributeValidationError, validate_attributes
from app.services.item_type_service import ItemTypeService


class SKUService:
    """CRUD and search for SKUs with attribute validation."""

    @staticmethod
    async def get_skus(
        db: AsyncSession,
        tenant_id: UUID,
        *,
        item_type_id: UUID | None = None,
        search: str | None = None,
        low_stock: bool | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SKU], int]:
        q = select(SKU).where(SKU.tenant_id == tenant_id)
        count_q = select(func.count(SKU.id)).where(SKU.tenant_id == tenant_id)

        if not include_archived:
            q = q.where(SKU.is_archived == False)
            count_q = count_q.where(SKU.is_archived == False)
        if item_type_id:
            q = q.where(SKU.item_type_id == item_type_id)
            count_q = count_q.where(SKU.item_type_id == item_type_id)
        if search:
            search_term = f"%{search}%"
            q = q.where(or_(SKU.sku_code.ilike(search_term), SKU.name.ilike(search_term)))
            count_q = count_q.where(or_(SKU.sku_code.ilike(search_term), SKU.name.ilike(search_term)))

        # low_stock: requires reorder_point and stock level; defer to Block 2
        # For now, low_stock=True filters SKUs with reorder_point set (can't compare to stock yet)
        if low_stock is True:
            q = q.where(SKU.reorder_point.isnot(None))
            count_q = count_q.where(SKU.reorder_point.isnot(None))

        # Count
        count_result = await db.execute(count_q)
        total = count_result.scalar_one()

        q = q.order_by(SKU.sku_code).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(q)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_by_id(db: AsyncSession, id: UUID, tenant_id: UUID) -> SKU | None:
        result = await db.execute(
            select(SKU).where(SKU.id == id, SKU.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, tenant_id: UUID, sku_code: str) -> SKU | None:
        result = await db.execute(
            select(SKU).where(
                SKU.tenant_id == tenant_id,
                SKU.sku_code == sku_code,
                SKU.is_archived == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_sku(
        db: AsyncSession,
        tenant_id: UUID,
        sku_code: str,
        name: str,
        item_type_id: UUID,
        attributes: dict,
        reorder_point: Decimal | None = None,
        unit_cost: Decimal | None = None,
    ) -> SKU:
        item_type = await ItemTypeService.get_by_id(db, item_type_id, tenant_id)
        if not item_type:
            raise ValueError("Item type not found")
        validated_attrs = validate_attributes(attributes, item_type.attribute_schema)

        sku = SKU(
            tenant_id=tenant_id,
            sku_code=sku_code,
            name=name,
            item_type_id=item_type_id,
            attributes=validated_attrs,
            reorder_point=reorder_point,
            unit_cost=unit_cost,
        )
        db.add(sku)
        await db.flush()
        await db.refresh(sku)
        return sku

    @staticmethod
    async def update_sku(
        db: AsyncSession,
        id: UUID,
        tenant_id: UUID,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        reorder_point: Decimal | None = None,
        unit_cost: Decimal | None = None,
    ) -> SKU | None:
        sku = await SKUService.get_by_id(db, id, tenant_id)
        if not sku:
            return None

        if name is not None:
            sku.name = name
        if reorder_point is not None:
            sku.reorder_point = reorder_point
        if unit_cost is not None:
            sku.unit_cost = unit_cost
        if attributes is not None:
            item_type = await ItemTypeService.get_by_id(db, sku.item_type_id, tenant_id)
            if not item_type:
                raise ValueError("Item type not found")
            sku.attributes = validate_attributes(attributes, item_type.attribute_schema)

        await db.flush()
        await db.refresh(sku)
        return sku

    @staticmethod
    async def archive_sku(db: AsyncSession, id: UUID, tenant_id: UUID, force: bool = False) -> bool:
        sku = await SKUService.get_by_id(db, id, tenant_id)
        if not sku:
            return False
        # Block archive if stock > 0 unless force (Block 2 will add stock check)
        sku.is_archived = True
        await db.flush()
        return True
