"""NEXUS IMS — RMAService."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rma import RMA, RMALine, RMAStatus
from app.models.warehouse import StockEventType
from app.services.ledger_service import LedgerService


class RMAService:

    @staticmethod
    async def create_rma(
        db: AsyncSession,
        tenant_id: UUID,
        warehouse_id: UUID,
        lines: list[dict],
        customer_name: str | None = None,
        order_reference: str | None = None,
        notes: str | None = None,
        created_by: UUID | None = None,
    ) -> RMA:
        """Create a new RMA ticket."""
        rma = RMA(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            customer_name=customer_name,
            order_reference=order_reference,
            status=RMAStatus.PENDING.value,
            notes=notes,
            created_by=created_by,
        )
        db.add(rma)
        await db.flush()

        for line_data in lines:
            line = RMALine(
                rma_id=rma.id,
                sku_id=line_data["sku_id"],
                quantity_expected=Decimal(str(line_data["quantity_expected"])),
                quantity_received=Decimal("0"),
                reason=line_data.get("reason"),
            )
            db.add(line)

        await db.flush()
        await db.refresh(rma)
        return rma

    @staticmethod
    async def list_rmas(
        db: AsyncSession,
        tenant_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RMA], int]:
        q = select(RMA).where(RMA.tenant_id == tenant_id)
        count_q = select(func.count(RMA.id)).where(RMA.tenant_id == tenant_id)
        
        if status:
            q = q.where(RMA.status == status)
            count_q = count_q.where(RMA.status == status)
            
        total = (await db.execute(count_q)).scalar_one()
        q = q.order_by(RMA.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(q)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_rma(
        db: AsyncSession,
        tenant_id: UUID,
        rma_id: UUID,
    ) -> RMA | None:
        result = await db.execute(
            select(RMA).where(
                RMA.id == rma_id,
                RMA.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        tenant_id: UUID,
        rma_id: UUID,
        status: str,
        actor_id: UUID | None = None,
    ) -> RMA:
        """Update RMA status. If RESTOCKED, inflate available stock."""
        rma = await RMAService.get_rma(db, tenant_id, rma_id)
        if not rma:
            raise ValueError("RMA not found")

        if rma.status == RMAStatus.RESTOCKED.value and status != RMAStatus.RESTOCKED.value:
            raise ValueError("Cannot change status from RESTOCKED")

        if status == RMAStatus.RESTOCKED.value and rma.status != RMAStatus.RESTOCKED.value:
            # Move items back into stock
            for line in rma.lines:
                if line.quantity_received > 0:
                    await LedgerService.post_event(
                        db,
                        tenant_id=tenant_id,
                        sku_id=line.sku_id,
                        warehouse_id=rma.warehouse_id,
                        event_type=StockEventType.RETURN_TO_STOCK,
                        quantity_delta=line.quantity_received,
                        reference_id=rma.id,
                        actor_id=actor_id,
                        notes=f"RMA Restocked: {rma.id}",
                    )

        rma.status = status
        await db.flush()
        await db.refresh(rma)
        return rma

    @staticmethod
    async def receive_lines(
        db: AsyncSession,
        tenant_id: UUID,
        rma_id: UUID,
        receive_data: list[dict],
        actor_id: UUID | None = None,
    ) -> RMA:
        """Receive returned goods into quarantine (does not inflate sales stock yet)."""
        rma = await RMAService.get_rma(db, tenant_id, rma_id)
        if not rma:
            raise ValueError("RMA not found")
            
        if rma.status in (RMAStatus.APPROVED.value, RMAStatus.REJECTED.value, RMAStatus.RESTOCKED.value):
             raise ValueError(f"Cannot receive items for RMA in status {rma.status}")

        lines_by_id = {str(line.id): line for line in rma.lines}
        
        for recv in receive_data:
            line_id = str(recv["rma_line_id"])
            qty = Decimal(str(recv["quantity"]))
            condition = recv.get("condition")
            
            if line_id not in lines_by_id:
                raise ValueError(f"RMA line {line_id} not found")
                
            line = lines_by_id[line_id]
            line.quantity_received += qty
            if condition:
                line.condition = condition

        rma.status = RMAStatus.INSPECTING.value
        await db.flush()
        await db.refresh(rma)
        return rma
