"""NEXUS IMS — BOM endpoints (Block 7)."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import (
    CurrentUser, get_db, require_auth, require_permission,
    PERM_BOMS_MANAGE,
)
from app.schemas.bom import BOMCreate, BOMResponse, BOMLineResponse, BOMAvailabilityResponse
from app.schemas.common import ApiResponse, Meta
from app.services.assembly_service import AssemblyService
from app.models.bom import BOM

router = APIRouter()


def _bom_to_response(bom: BOM) -> BOMResponse:
    return BOMResponse(
        id=bom.id,
        finished_sku_id=bom.finished_sku_id,
        version=bom.version,
        is_active=bom.is_active,
        landed_cost=bom.landed_cost,
        landed_cost_description=bom.landed_cost_description,
        lines=[
            BOMLineResponse(
                id=line.id,
                component_sku_id=line.component_sku_id,
                quantity=line.quantity,
                unit=line.unit,
            )
            for line in bom.lines
        ] if bom.lines else [],
        created_at=bom.created_at.isoformat() if bom.created_at else "",
    )


@router.get("", response_model=ApiResponse[list[BOMResponse]])
async def list_boms(
    finished_sku_id: UUID | None = Query(None, description="Filter by Finished SKU"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List BOMs for the current tenant."""
    query = select(BOM).where(BOM.tenant_id == user.tenant_id)
    if finished_sku_id:
        query = query.where(BOM.finished_sku_id == finished_sku_id)
    if not include_inactive:
        query = query.where(BOM.is_active == True)
        
    result = await db.scalars(query.order_by(BOM.created_at.desc()))
    boms = result.all()
    
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
    bom = await AssemblyService.create_bom(
        db, 
        user.tenant_id, 
        finished_sku_id=body.finished_sku_id, 
        lines=lines,
        landed_cost=body.landed_cost,
        landed_cost_description=body.landed_cost_description,
        created_by=user.id
    )
    await db.commit()
    await db.refresh(bom)
    # The bom may need lines loaded explicitly if session dropped them
    bom = await AssemblyService.get_bom(db, user.tenant_id, bom.id)
    return ApiResponse(data=_bom_to_response(bom))


@router.get("/{bom_id}", response_model=ApiResponse[BOMResponse])
async def get_bom(
    bom_id: UUID,
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a single BOM with all lines."""
    bom = await AssemblyService.get_bom(db, user.tenant_id, bom_id)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found")
    return ApiResponse(data=_bom_to_response(bom))


@router.get("/{bom_id}/availability", response_model=ApiResponse[BOMAvailabilityResponse])
async def check_availability(
    bom_id: UUID,
    planned_qty: Decimal = Query(..., gt=0),
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Check component availability for a given BOM and planned production quantity."""
    shortages = await AssemblyService.check_availability(db, user.tenant_id, bom_id, planned_qty)
    return ApiResponse(
        data=BOMAvailabilityResponse(
            is_available=len(shortages) == 0,
            shortages=shortages
        )
    )
