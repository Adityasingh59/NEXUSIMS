"""NEXUS IMS — LocationService (Block 3.2)."""
from uuid import UUID

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location


class LocationService:
    """CRUD for locations with parent hierarchy."""

    @staticmethod
    async def get_by_id(db: AsyncSession, id: UUID, tenant_id: UUID) -> Location | None:
        result = await db.execute(
            select(Location).where(
                Location.id == id,
                Location.tenant_id == tenant_id,
                Location.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_warehouse(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID,
        parent_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[Location]:
        q = select(Location).where(
            Location.tenant_id == tenant_id,
            Location.warehouse_id == warehouse_id,
        )
        if parent_id is None:
            q = q.where(Location.parent_id.is_(None))
        else:
            q = q.where(Location.parent_id == parent_id)
        if not include_inactive:
            q = q.where(Location.is_active == True)
        q = q.order_by(Location.code)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_location_path(db: AsyncSession, id: UUID, tenant_id: UUID) -> list[str]:
        """Return full path as list of names: Zone > Aisle > Bin."""
        loc = await LocationService.get_by_id(db, id, tenant_id)
        if not loc:
            return []
        path = [loc.name]
        current = loc
        while current.parent_id:
            result = await db.execute(
                select(Location).where(Location.id == current.parent_id)
            )
            parent = result.scalar_one_or_none()
            if not parent:
                break
            path.insert(0, parent.name)
            current = parent
        return path

    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID,
        name: str,
        code: str,
        location_type: str,
        parent_id: UUID | None = None,
    ) -> Location:
        loc = Location(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            parent_id=parent_id,
            name=name,
            code=code,
            location_type=location_type,
        )
        db.add(loc)
        await db.flush()
        await db.refresh(loc)
        return loc

    @staticmethod
    async def update(db: AsyncSession, id: UUID, tenant_id: UUID, **kwargs) -> Location | None:
        loc = await LocationService.get_by_id(db, id, tenant_id)
        if not loc:
            return None
        for k, v in kwargs.items():
            if hasattr(loc, k):
                setattr(loc, k, v)
        await db.flush()
        await db.refresh(loc)
        return loc
