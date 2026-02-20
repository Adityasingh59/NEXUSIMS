"""NEXUS IMS — COGS endpoint (Block 5)."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission, PERM_COGS_READ
from app.schemas.common import ApiResponse
from app.services.cogs_service import COGSService

router = APIRouter()


@router.get("", response_model=ApiResponse[dict])
async def calculate_cogs(
    sku_id: UUID = Query(..., description="Finished good SKU to calculate COGS for"),
    quantity: Decimal = Query(..., gt=0, description="Number of units to cost"),
    user: CurrentUser = Depends(require_permission(PERM_COGS_READ)),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate Cost of Goods Sold for a given SKU and quantity.
    Uses the most recent active BOM for the SKU (weighted-average unit costs from BOM lines).
    Returns total COGS and a line-by-line breakdown.
    """
    result = await COGSService.calculate_cogs(db, user.tenant_id, sku_id, quantity)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active BOM found for SKU {sku_id}. Create a BOM first.",
        )
    return ApiResponse(data=result)
