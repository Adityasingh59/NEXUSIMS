from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
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

@router.post("/import", response_model=ApiResponse[dict])
async def import_skus_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Bulk import SKUs from CSV. Requires sku_code, name, item_type_id columns."""
    import csv
    from io import StringIO
    
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
        
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty or invalid CSV")
        
    created_count = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            sku_code = row.get("sku_code")
            name = row.get("name")
            item_type_id_str = row.get("item_type_id")
            
            if not all([sku_code, name, item_type_id_str]):
                errors.append(f"Row {row_num}: Missing required fields (sku_code, name, item_type_id)")
                continue

            try:
                item_type_id = UUID(item_type_id_str)
            except ValueError:
                errors.append(f"Row {row_num}: Invalid item_type_id UUID")
                continue

            # Parse optional fields
            reorder_point = Decimal(row["reorder_point"]) if row.get("reorder_point") else None
            unit_cost = Decimal(row["unit_cost"]) if row.get("unit_cost") else None
            
            # The rest of the columns are considered dynamic attributes!
            known_cols = {"sku_code", "name", "item_type_id", "reorder_point", "unit_cost"}
            attributes = {k: v for k, v in row.items() if k not in known_cols and v}

            existing = await SKUService.get_by_code(db, user.tenant_id, sku_code)
            if existing:
                await SKUService.update_sku(
                    db, existing.id, user.tenant_id, name=name, 
                    attributes=attributes, reorder_point=reorder_point, 
                    unit_cost=unit_cost
                )
            else:
                await SKUService.create_sku(
                    db, user.tenant_id, sku_code, name, item_type_id,
                    attributes, reorder_point, unit_cost
                )
            created_count += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            
    await db.commit()
    return ApiResponse(data={"processed": created_count, "errors": errors})
