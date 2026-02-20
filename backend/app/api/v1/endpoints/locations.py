"""NEXUS IMS — Location endpoints (Block 3)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_db, require_auth
from app.schemas.common import ApiResponse
from app.schemas.location import LocationCreate, LocationResponse
from app.services.location_service import LocationService
from app.services.warehouse_service import WarehouseService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[LocationResponse]])
async def list_locations(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    parent_id: UUID | None = Query(None, description="Filter by parent; omit for root"),
    include_inactive: bool = False,
    user: CurrentUser = Depends(require_auth),
):
    """List locations for warehouse (optionally by parent for hierarchy)."""
    items = await LocationService.list_by_warehouse(
        db, user.tenant_id, warehouse_id,
        parent_id=parent_id,
        include_inactive=include_inactive,
    )
    return ApiResponse(data=[LocationResponse.model_validate(i) for i in items])


@router.post("", response_model=ApiResponse[LocationResponse], status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Create location (zone/aisle/bin)."""
    wh = await WarehouseService.get_by_id(db, body.warehouse_id, user.tenant_id)
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    # Check code uniqueness per warehouse
    from sqlalchemy import select
    from app.models.location import Location as Loc
    result = await db.execute(
        select(Loc).where(Loc.warehouse_id == body.warehouse_id, Loc.code == body.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Location code already exists")
    loc = await LocationService.create(
        db, user.tenant_id, body.warehouse_id,
        body.name, body.code, body.location_type,
        parent_id=body.parent_id,
    )
    return ApiResponse(data=LocationResponse.model_validate(loc))


@router.get("/{id}/path", response_model=ApiResponse[list[str]])
async def get_location_path(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get full path (Zone > Aisle > Bin) for location."""
    path = await LocationService.get_location_path(db, id, user.tenant_id)
    return ApiResponse(data=path)
