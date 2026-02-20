"""NEXUS IMS — Item type endpoints (Block 1.3). GET /item-types, POST, PUT."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_db, require_auth, require_permission, PERM_SKUS_WRITE
from app.schemas.common import ApiResponse, Meta
from app.schemas.item_type import ItemTypeCreate, ItemTypeResponse, ItemTypeUpdate
from app.services.item_type_service import ItemTypeService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[ItemTypeResponse]])
async def list_item_types(
    db: AsyncSession = Depends(get_db),
    include_archived: bool = False,
    user: CurrentUser = Depends(require_auth),
):
    """List item types. Requires ADMIN role (Block 4)."""
    items = await ItemTypeService.get_item_types(db, user.tenant_id, include_archived)
    return ApiResponse(data=[ItemTypeResponse.model_validate(i) for i in items])


@router.post("", response_model=ApiResponse[ItemTypeResponse], status_code=status.HTTP_201_CREATED)
async def create_item_type(
    body: ItemTypeCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission(PERM_SKUS_WRITE)),
):
    """Create item type. Requires ADMIN."""
    existing = await ItemTypeService.get_by_code(db, user.tenant_id, body.code)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item type code already exists")
    item = await ItemTypeService.create_item_type(
        db, user.tenant_id, body.name, body.code, body.attribute_schema
    )
    return ApiResponse(data=ItemTypeResponse.model_validate(item))


@router.get("/{id}", response_model=ApiResponse[ItemTypeResponse])
async def get_item_type(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get item type by ID."""
    item = await ItemTypeService.get_by_id(db, id, user.tenant_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data=ItemTypeResponse.model_validate(item))


@router.put("/{id}", response_model=ApiResponse[ItemTypeResponse])
async def update_item_type(
    id: UUID,
    body: ItemTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission(PERM_SKUS_WRITE)),
):
    """Update item type. If attribute_schema provided, creates new version."""
    item = await ItemTypeService.get_by_id(db, id, user.tenant_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if body.name is not None:
        item.name = body.name
    if body.attribute_schema is not None:
        item = await ItemTypeService.update_schema(db, id, user.tenant_id, body.attribute_schema)
    else:
        await db.flush()
        await db.refresh(item)
    return ApiResponse(data=ItemTypeResponse.model_validate(item))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_item_type(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission(PERM_SKUS_WRITE)),
):
    """Soft-archive item type."""
    ok = await ItemTypeService.archive_item_type(db, id, user.tenant_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
