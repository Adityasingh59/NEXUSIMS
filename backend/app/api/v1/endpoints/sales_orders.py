"""NEXUS IMS — Sales Orders API endpoints (Block 8)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_db, require_auth
from app.schemas.common import ApiResponse
from app.models.tenant import User
from app.schemas.sales_order import (
    SalesOrderAllocateRequest,
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderShipRequest,
    SalesOrderCancelRequest,
)
from app.services.fulfillment_service import FulfillmentService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sales_order import SalesOrder

router = APIRouter()


@router.get("", response_model=ApiResponse[list[SalesOrderResponse]])
async def list_sales_orders(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """List all sales orders for the current tenant."""
    # Simplified list
    stmt = select(SalesOrder).where(SalesOrder.tenant_id == current_user.tenant_id).order_by(SalesOrder.created_at.desc())
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    # We don't eager load lines here for list view performance, 
    # but the frontend might just want a top-level list.
    return ApiResponse(data=list(orders))


@router.get("/{order_id}", response_model=ApiResponse[SalesOrderResponse])
async def get_sales_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """Get sales order details including lines."""
    order = await FulfillmentService.get_by_id(db, order_id, current_user.tenant_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sales Order not found")
    return ApiResponse(data=order)


@router.post("", response_model=ApiResponse[SalesOrderResponse])
async def create_sales_order(
    request: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """Create a new sales order in PENDING state."""
    order = await FulfillmentService.create_sales_order(
        db=db,
        tenant_id=current_user.tenant_id,
        customer_name=request.customer_name,
        lines_data=[line.model_dump() for line in request.lines],
        order_reference=request.order_reference,
        shipping_address=request.shipping_address,
        user_id=current_user.id,
    )
    return ApiResponse(data=order, meta={"message": "Sales order created"})


@router.post("/{order_id}/allocate", response_model=ApiResponse[Any])
async def allocate_sales_order(
    order_id: UUID,
    request: SalesOrderAllocateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """Allocate (reserve) stock for an order from a specific warehouse."""
    try:
        result = await FulfillmentService.allocate_stock(
            db=db,
            tenant_id=current_user.tenant_id,
            order_id=order_id,
            warehouse_id=request.warehouse_id,
            user_id=current_user.id,
        )
        if isinstance(result, dict) and "shortages" in result:
            return ApiResponse(data=result, meta={"message": "Insufficient stock to allocate order"}, error="STOCK_SHORTAGE")
        
        return ApiResponse(data=result, meta={"message": "Order allocated and is now PROCESSING"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/ship", response_model=ApiResponse[SalesOrderResponse])
async def ship_sales_order(
    order_id: UUID,
    request: SalesOrderShipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """Ship an order, removing physical stock and clearing reservations."""
    try:
        order = await FulfillmentService.ship_order(
            db=db,
            tenant_id=current_user.tenant_id,
            order_id=order_id,
            warehouse_id=request.warehouse_id,
            user_id=current_user.id,
        )
        return ApiResponse(data=order, meta={"message": "Order SHIPPED successfully"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=ApiResponse[SalesOrderResponse])
async def cancel_sales_order(
    order_id: UUID,
    request: SalesOrderCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> Any:
    """Cancel an order and return any allocated stock back to available."""
    try:
        order = await FulfillmentService.cancel_order(
            db=db,
            tenant_id=current_user.tenant_id,
            order_id=order_id,
            warehouse_id=request.warehouse_id,
            user_id=current_user.id,
        )
        return ApiResponse(data=order, meta={"message": "Order CANCELLED"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
