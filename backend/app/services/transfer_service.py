"""NEXUS IMS — TransferService (Block 3.2)."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import TransferOrder, TransferOrderLine, TransferStatus
from app.models.warehouse import StockEventType
from app.services.ledger_service import LedgerService
from app.services.warehouse_service import WarehouseService


class TransferService:
    """Transfer orders with TRANSFER_OUT on create, TRANSFER_IN on receipt."""

    @staticmethod
    async def create_transfer_order(
        db: AsyncSession,
        tenant_id: UUID,
        from_warehouse_id: UUID,
        to_warehouse_id: UUID,
        lines: list[dict],  # [{"sku_id": uuid, "quantity_requested": decimal}]
        created_by: UUID | None = None,
    ) -> TransferOrder:
        """Create transfer order. Posts TRANSFER_OUT events immediately (atomic)."""
        if from_warehouse_id == to_warehouse_id:
            raise ValueError("Source and destination warehouse must differ")

        fwh = await WarehouseService.get_by_id(db, from_warehouse_id, tenant_id)
        twh = await WarehouseService.get_by_id(db, to_warehouse_id, tenant_id)
        if not fwh or not twh:
            raise ValueError("Warehouse not found or inactive")

        order = TransferOrder(
            tenant_id=tenant_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            status=TransferStatus.IN_TRANSIT.value,
            created_by=created_by,
        )
        db.add(order)
        await db.flush()

        for line in lines:
            sku_id = line["sku_id"]
            qty = Decimal(str(line["quantity_requested"]))
            await LedgerService.post_event(
                db, tenant_id, sku_id, from_warehouse_id,
                StockEventType.TRANSFER_OUT, -qty,
                reference_id=order.id, actor_id=created_by,
                notes=f"Transfer to {twh.code}",
            )
            db.add(TransferOrderLine(
                transfer_order_id=order.id,
                sku_id=sku_id,
                quantity_requested=qty,
            ))

        await db.flush()
        await db.refresh(order)
        return order

    @staticmethod
    async def confirm_receipt(
        db: AsyncSession,
        transfer_order_id: UUID,
        tenant_id: UUID,
        line_quantities: dict[UUID, Decimal] | None = None,  # line_id -> qty_received
    ) -> TransferOrder | None:
        """Post TRANSFER_IN events on destination. Can be partial receipt."""
        result = await db.execute(
            select(TransferOrder)
            .where(
                TransferOrder.id == transfer_order_id,
                TransferOrder.tenant_id == tenant_id,
                TransferOrder.status == TransferStatus.IN_TRANSIT.value,
            )
            .options(selectinload(TransferOrder.lines))
        )
        order = result.scalar_one_or_none()
        if not order:
            return None

        for line in order.lines:
            qty_received = line_quantities.get(line.id, line.quantity_requested) if line_quantities else line.quantity_requested
            await LedgerService.post_event(
                db, tenant_id, line.sku_id, order.to_warehouse_id,
                StockEventType.TRANSFER_IN, qty_received,
                reference_id=order.id,
                notes=f"Transfer from warehouse",
            )
            line.quantity_received = qty_received

        from datetime import datetime, timezone
        order.status = TransferStatus.RECEIVED.value
        order.received_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(order)
        return order

    @staticmethod
    async def cancel_transfer_order(
        db: AsyncSession,
        transfer_order_id: UUID,
        tenant_id: UUID,
    ) -> TransferOrder | None:
        """Reverse TRANSFER_OUT by posting TRANSFER_IN on source (return)."""
        result = await db.execute(
            select(TransferOrder)
            .where(
                TransferOrder.id == transfer_order_id,
                TransferOrder.tenant_id == tenant_id,
                TransferOrder.status == TransferStatus.IN_TRANSIT.value,
            )
            .options(selectinload(TransferOrder.lines))
        )
        order = result.scalar_one_or_none()
        if not order:
            return None

        for line in order.lines:
            qty = line.quantity_requested
            await LedgerService.post_event(
                db, tenant_id, line.sku_id, order.from_warehouse_id,
                StockEventType.TRANSFER_IN, qty,  # Return to source
                reference_id=order.id,
                notes="Transfer cancelled - returned to source",
            )

        order.status = TransferStatus.CANCELLED.value
        await db.flush()
        await db.refresh(order)
        return order

    @staticmethod
    async def list_transfers(
        db: AsyncSession,
        tenant_id: UUID,
        *,
        status: str | None = None,
        warehouse_id: UUID | None = None,
    ) -> list[TransferOrder]:
        q = select(TransferOrder).where(TransferOrder.tenant_id == tenant_id)
        if status:
            q = q.where(TransferOrder.status == status)
        if warehouse_id:
            q = q.where(
                (TransferOrder.from_warehouse_id == warehouse_id) |
                (TransferOrder.to_warehouse_id == warehouse_id)
            )
        q = q.order_by(TransferOrder.created_at.desc())
        result = await db.execute(q.options(selectinload(TransferOrder.lines)))
        return list(result.scalars().all())
