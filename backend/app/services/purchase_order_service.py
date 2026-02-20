"""NEXUS IMS — PurchaseOrderService (Block 5): create, list, get, receive, cancel."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase_order import POStatus, PurchaseOrder, PurchaseOrderLine
from app.models.warehouse import StockEventType
from app.services.ledger_service import LedgerService


class PurchaseOrderService:
    """CRUD + business logic for Purchase Orders."""

    @staticmethod
    async def create_po(
        db: AsyncSession,
        tenant_id: UUID,
        supplier_name: str,
        warehouse_id: UUID,
        lines: list[dict],
        notes: str | None = None,
        created_by: UUID | None = None,
    ) -> PurchaseOrder:
        """Create a new PO with lines in DRAFT status."""
        po = PurchaseOrder(
            tenant_id=tenant_id,
            supplier_name=supplier_name,
            warehouse_id=warehouse_id,
            status=POStatus.DRAFT.value,
            notes=notes,
            created_by=created_by,
        )
        db.add(po)
        await db.flush()

        for line_data in lines:
            line = PurchaseOrderLine(
                po_id=po.id,
                sku_id=line_data["sku_id"],
                quantity_ordered=Decimal(str(line_data["quantity_ordered"])),
                quantity_received=Decimal("0"),
                unit_cost=Decimal(str(line_data["unit_cost"])),
            )
            db.add(line)

        await db.flush()
        await db.refresh(po)
        return po

    @staticmethod
    async def list_pos(
        db: AsyncSession,
        tenant_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PurchaseOrder], int]:
        """Paginated list of POs for tenant."""
        from sqlalchemy import func
        q = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
        count_q = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.tenant_id == tenant_id)
        if status:
            q = q.where(PurchaseOrder.status == status)
            count_q = count_q.where(PurchaseOrder.status == status)
        total = (await db.execute(count_q)).scalar_one()
        q = q.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(q)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_po(
        db: AsyncSession,
        tenant_id: UUID,
        po_id: UUID,
    ) -> PurchaseOrder | None:
        """Get single PO with lines (selectin loaded)."""
        result = await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def receive_po(
        db: AsyncSession,
        tenant_id: UUID,
        po_id: UUID,
        receive_lines: list[dict],
        actor_id: UUID | None = None,
    ) -> PurchaseOrder:
        """
        Partially or fully receive a PO.
        - Updates quantity_received on each line.
        - Posts a RECEIVE ledger event for each received line.
        - Updates PO status to PARTIAL or RECEIVED.
        """
        po = await PurchaseOrderService.get_po(db, tenant_id, po_id)
        if not po:
            raise ValueError("Purchase Order not found")
        if po.status in (POStatus.RECEIVED.value, POStatus.CANCELLED.value):
            raise ValueError(f"Cannot receive a PO in status: {po.status}")

        # Build lookup from po_line_id → line
        lines_by_id = {str(line.id): line for line in po.lines}

        for recv in receive_lines:
            line_id = str(recv["po_line_id"])
            qty = Decimal(str(recv["quantity_received"]))

            if line_id not in lines_by_id:
                raise ValueError(f"PO line {line_id} not found on this PO")

            line = lines_by_id[line_id]
            remaining = line.quantity_ordered - line.quantity_received
            if qty > remaining:
                raise ValueError(
                    f"Cannot receive {qty} for line {line_id}: only {remaining} remaining"
                )

            # Post RECEIVE ledger event
            await LedgerService.post_event(
                db,
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=po.warehouse_id,
                event_type=StockEventType.RECEIVE,
                quantity_delta=qty,
                reference_id=po.id,
                actor_id=actor_id,
                notes=f"PO receipt: {po.supplier_name}",
            )

            line.quantity_received += qty

        # Recalculate PO status
        all_received = all(
            line.quantity_received >= line.quantity_ordered
            for line in po.lines
        )
        any_received = any(line.quantity_received > 0 for line in po.lines)

        if all_received:
            po.status = POStatus.RECEIVED.value
        elif any_received:
            po.status = POStatus.PARTIAL.value
        else:
            po.status = POStatus.ORDERED.value

        await db.flush()
        await db.refresh(po)
        return po

    @staticmethod
    async def cancel_po(
        db: AsyncSession,
        tenant_id: UUID,
        po_id: UUID,
    ) -> PurchaseOrder | None:
        """Cancel a PO. Only allowed in DRAFT or ORDERED status."""
        po = await PurchaseOrderService.get_po(db, tenant_id, po_id)
        if not po:
            return None
        if po.status not in (POStatus.DRAFT.value, POStatus.ORDERED.value):
            raise ValueError(f"Cannot cancel a PO in status: {po.status}")
        po.status = POStatus.CANCELLED.value
        await db.flush()
        return po
