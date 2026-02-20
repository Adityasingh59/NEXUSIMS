"""NEXUS IMS — BOM endpoints (Block 5)."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_BOMS_MANAGE,
)
from app.schemas.bom import BOMCreate, BOMResponse, BOMUpdate, BOMLineResponse, ExplodeResponse
from app.schemas.common import ApiResponse, Meta
from app.services.bom_service import BOMService

router = APIRouter()


def _bom_to_response(bom) -> BOMResponse:
    return BOMResponse(
        id=bom.id,
        sku_id=bom.sku_id,
        name=bom.name,
        is_active=bom.is_active,
        lines=[
            BOMLineResponse(
                id=line.id,
                component_sku_id=line.component_sku_id,
                quantity=line.quantity,
                unit_cost_snapshot=line.unit_cost_snapshot,
            )
            for line in bom.lines
        ],
        created_at=bom.created_at.isoformat() if bom.created_at else "",
    )


@router.get("", response_model=ApiResponse[list])
async def list_boms(
    sku_id: UUID | None = Query(None, description="Filter by SKU"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List BOMs for the current tenant."""
    boms = await BOMService.get_boms(db, user.tenant_id, sku_id=sku_id, include_inactive=include_inactive)
    # Manual pagination (BOMs are typically not huge)
    total = len(boms)
    start = (page - 1) * page_size
    page_boms = boms[start:start + page_size]
    return ApiResponse(
        data=[_bom_to_response(b) for b in page_boms],
        meta=Meta(page=page, page_size=page_size, total_count=total),
    )


@router.post("", response_model=ApiResponse[BOMResponse], status_code=status.HTTP_201_CREATED)
async def create_bom(
    body: BOMCreate,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new Bill of Materials."""
    lines = [line.model_dump() for line in body.lines]
    bom = await BOMService.create_bom(
        db, user.tenant_id, body.sku_id, body.name, lines, created_by=user.id
    )
    await db.commit()
    await db.refresh(bom)
    return ApiResponse(data=_bom_to_response(bom))


@router.get("/{bom_id}", response_model=ApiResponse[BOMResponse])
async def get_bom(
    bom_id: UUID,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a single BOM with all lines."""
    bom = await BOMService.get_bom(db, user.tenant_id, bom_id)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found")
    return ApiResponse(data=_bom_to_response(bom))


@router.put("/{bom_id}", response_model=ApiResponse[BOMResponse])
async def update_bom(
    bom_id: UUID,
    body: BOMUpdate,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update a BOM's name and/or replace all its lines."""
    lines = [line.model_dump() for line in body.lines] if body.lines is not None else None
    bom = await BOMService.update_bom(db, user.tenant_id, bom_id, name=body.name, lines=lines)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found")
    await db.commit()
    await db.refresh(bom)
    return ApiResponse(data=_bom_to_response(bom))


@router.delete("/{bom_id}", response_model=ApiResponse[BOMResponse])
async def archive_bom(
    bom_id: UUID,
    user: CurrentUser = Depends(require_permission(PERM_BOMS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Archive (soft-delete) a BOM."""
    bom = await BOMService.archive_bom(db, user.tenant_id, bom_id)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found")
    await db.commit()
    return ApiResponse(data=_bom_to_response(bom))


@router.post("/{bom_id}/explode", response_model=ApiResponse[ExplodeResponse])
async def explode_bom(
    bom_id: UUID,
    quantity: Decimal = Query(..., gt=0, description="Production quantity to explode for"),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Expand BOM for a given production quantity — returns total component quantities needed."""
    components = await BOMService.explode_bom(db, user.tenant_id, bom_id, quantity)
    if not components and not await BOMService.get_bom(db, user.tenant_id, bom_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found")
    return ApiResponse(data=ExplodeResponse(
        bom_id=bom_id,
        quantity=quantity,
        components={k: Decimal(str(v)) for k, v in components.items()},
    ))
