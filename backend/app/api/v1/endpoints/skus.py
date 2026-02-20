"""NEXUS IMS — SKU endpoints (Block 1.3). GET /skus, POST, GET/{id}, PUT, DELETE."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_db, require_auth
from app.schemas.common import ApiResponse, Meta
from app.schemas.sku import SKUCreate, SKUResponse, SKUUpdate
from app.services.attribute_validator import AttributeValidationError
from app.services.sku_service import SKUService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[SKUResponse]])
async def list_skus(
    db: AsyncSession = Depends(get_db),
    item_type_id: UUID | None = None,
    search: str | None = None,
    low_stock: bool | None = None,
    include_archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
):
    """List SKUs with filters."""
    items, total = await SKUService.get_skus(
        db,
        user.tenant_id,
        item_type_id=item_type_id,
        search=search,
        low_stock=low_stock,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=[SKUResponse.model_validate(i) for i in items],
        meta=Meta(page=page, page_size=page_size, total_count=total),
    )


@router.post("", response_model=ApiResponse[SKUResponse], status_code=status.HTTP_201_CREATED)
async def create_sku(
    body: SKUCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Create SKU. Validates attributes against item_type.attribute_schema."""
    existing = await SKUService.get_by_code(db, user.tenant_id, body.sku_code)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU code already exists")
    try:
        sku = await SKUService.create_sku(
            db,
            user.tenant_id,
            body.sku_code,
            body.name,
            body.item_type_id,
            body.attributes,
            body.reorder_point,
            body.unit_cost,
        )
    except AttributeValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.field_errors or e.message)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ApiResponse(data=SKUResponse.model_validate(sku))


@router.get("/{id}", response_model=ApiResponse[SKUResponse])
async def get_sku(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get SKU by ID."""
    sku = await SKUService.get_by_id(db, id, user.tenant_id)
    if not sku:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data=SKUResponse.model_validate(sku))


@router.put("/{id}", response_model=ApiResponse[SKUResponse])
async def update_sku(
    id: UUID,
    body: SKUUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Update SKU."""
    try:
        sku = await SKUService.update_sku(
            db,
            id,
            user.tenant_id,
            name=body.name,
            attributes=body.attributes,
            reorder_point=body.reorder_point,
            unit_cost=body.unit_cost,
        )
    except AttributeValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.field_errors or e.message)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if not sku:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ApiResponse(data=SKUResponse.model_validate(sku))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_sku(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    force: bool = False,
    user: CurrentUser = Depends(require_auth),
):
    """Soft-archive SKU. Blocked if stock > 0 unless force (Block 2)."""
    ok = await SKUService.archive_sku(db, id, user.tenant_id, force=force)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
