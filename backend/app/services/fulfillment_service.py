"""NEXUS IMS — FulfillmentService for Sales Orders (Block 8)."""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.warehouse import StockEventType
from app.services.ledger_service import LedgerService


class FulfillmentService:
    """Manages creation, allocation, shipping, and cancellation of sales orders."""

    @staticmethod
    async def get_by_id(db: AsyncSession, order_id: uuid.UUID, tenant_id: uuid.UUID) -> SalesOrder | None:
        """Fetch order with its lines."""
        stmt = (
            select(SalesOrder)
            .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
            .options(selectinload(SalesOrder.lines))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_sales_order(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        customer_name: str,
        lines_data: list[dict],
        order_reference: str | None = None,
        shipping_address: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> SalesOrder:
        """Create a new sales order in PENDING state."""
        order = SalesOrder(
            tenant_id=tenant_id,
            customer_name=customer_name,
            order_reference=order_reference,
            shipping_address=shipping_address,
            status="PENDING",
            created_by=user_id,
        )
        db.add(order)
        await db.flush()

        for line in lines_data:
            ol = SalesOrderLine(
                sales_order_id=order.id,
                sku_id=line["sku_id"],
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line.get("unit_price", 0))),
                fulfilled_qty=0,
            )
            db.add(ol)

        await db.flush()
        await db.refresh(order)
        return await FulfillmentService.get_by_id(db, order.id, tenant_id)

    @staticmethod
    async def allocate_stock(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> SalesOrder | dict:
        """Reserve stock for an order."""
        order = await FulfillmentService.get_by_id(db, order_id, tenant_id)
        if not order:
            raise ValueError("Sales order not found")
        if order.status != "PENDING":
            raise ValueError(f"Sales order must be PENDING, but is {order.status}")

        # 1. Verification
        shortages = []
        for line in order.lines:
            avail = await LedgerService.get_stock_level(db, tenant_id, line.sku_id, warehouse_id)
            if avail < line.quantity:
                shortages.append(
                    {
                        "sku_id": str(line.sku_id),
                        "required": float(line.quantity),
                        "available": float(avail),
                        "shortage": float(line.quantity - avail),
                    }
                )

        if shortages:
            return {"shortages": shortages}

        # 2. Allocation
        for line in order.lines:
            await LedgerService.post_event(
                db=db,
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=warehouse_id,
                event_type=StockEventType.RESERVE_OUT,
                quantity_delta=-line.quantity,
                reference_id=order.id,
                actor_id=user_id,
                notes=f"Allocated for order {order_id}",
            )

        order.status = "PROCESSING"
        # Save warehouse_id logic if we want to tie an order to a warehouse,
        # but for now we just log the event. If needed, we can track it per line.
        await db.flush()
        return await FulfillmentService.get_by_id(db, order.id, tenant_id)

    @staticmethod
    async def ship_order(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> SalesOrder:
        """Ship the order: clear the reservation and permanently deduct stock."""
        order = await FulfillmentService.get_by_id(db, order_id, tenant_id)
        if not order:
            raise ValueError("Sales order not found")
        if order.status != "PROCESSING":
            raise ValueError(f"Sales order must be PROCESSING, but is {order.status}")

        for line in order.lines:
            # Revert the soft allocation securely inside the ledger context.
            await LedgerService.post_event(
                db=db,
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=warehouse_id,
                event_type=StockEventType.RESERVE_IN,
                quantity_delta=line.quantity,
                reference_id=order.id,
                actor_id=user_id,
                notes=f"Resolve allocation for shipped order {order_id}",
            )
            # Physical dispatch out.
            await LedgerService.post_event(
                db=db,
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=warehouse_id,
                event_type=StockEventType.SHIP_OUT,
                quantity_delta=-line.quantity,
                reference_id=order.id,
                actor_id=user_id,
                notes=f"Shipped order {order_id}",
            )
            line.fulfilled_qty = line.quantity

        order.status = "SHIPPED"
        await db.flush()
        return await FulfillmentService.get_by_id(db, order.id, tenant_id)

    @staticmethod
    async def cancel_order(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> SalesOrder:
        """Cancel an order and return reserved stock if allocated."""
        order = await FulfillmentService.get_by_id(db, order_id, tenant_id)
        if not order:
            raise ValueError("Sales order not found")
        if order.status in ["SHIPPED", "CANCELLED"]:
            raise ValueError(f"Cannot cancel a {order.status} order")

        if order.status == "PROCESSING":
            # Revert allocation
            for line in order.lines:
                await LedgerService.post_event(
                    db=db,
                    tenant_id=tenant_id,
                    sku_id=line.sku_id,
                    warehouse_id=warehouse_id,
                    event_type=StockEventType.RESERVE_IN,
                    quantity_delta=line.quantity,
                    reference_id=order.id,
                    actor_id=user_id,
                    notes=f"Cancelled order {order_id} - reverted allocation",
                )

        order.status = "CANCELLED"
        await db.flush()
        return await FulfillmentService.get_by_id(db, order.id, tenant_id)
