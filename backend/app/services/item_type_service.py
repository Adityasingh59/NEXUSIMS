"""NEXUS IMS — ItemTypeService (Block 1.2)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_type import ItemType


class ItemTypeService:
    """CRUD and schema management for item types."""

    @staticmethod
    async def get_item_types(
        db: AsyncSession,
        tenant_id: UUID,
        include_archived: bool = False,
    ) -> list[ItemType]:
        q = select(ItemType).where(ItemType.tenant_id == tenant_id)
        if not include_archived:
            q = q.where(ItemType.is_archived == False)
        q = q.order_by(ItemType.code)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, id: UUID, tenant_id: UUID) -> ItemType | None:
        result = await db.execute(
            select(ItemType).where(ItemType.id == id, ItemType.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, tenant_id: UUID, code: str) -> ItemType | None:
        result = await db.execute(
            select(ItemType).where(
                ItemType.tenant_id == tenant_id,
                ItemType.code == code,
                ItemType.is_archived == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_item_type(
        db: AsyncSession,
        tenant_id: UUID,
        name: str,
        code: str,
        attribute_schema: list[dict],
    ) -> ItemType:
        item_type = ItemType(
            tenant_id=tenant_id,
            name=name,
            code=code,
            attribute_schema=attribute_schema,
        )
        db.add(item_type)
        await db.flush()
        await db.refresh(item_type)
        return item_type

    @staticmethod
    async def update_schema(
        db: AsyncSession,
        id: UUID,
        tenant_id: UUID,
        attribute_schema: list[dict],
    ) -> ItemType | None:
        item_type = await ItemTypeService.get_by_id(db, id, tenant_id)
        if not item_type:
            return None
        item_type.attribute_schema = attribute_schema
        item_type.version += 1
        await db.flush()
        await db.refresh(item_type)
        return item_type

    @staticmethod
    async def archive_item_type(db: AsyncSession, id: UUID, tenant_id: UUID) -> bool:
        item_type = await ItemTypeService.get_by_id(db, id, tenant_id)
        if not item_type:
            return False
        item_type.is_archived = True
        await db.flush()
        return True
