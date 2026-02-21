"""NEXUS IMS — Assembly Service (Block 7)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.assembly import AssemblyOrder
from app.models.bom import BOM, BOMLine
from app.models.item_type import SKU
from app.models.warehouse import StockLedger
from app.services.ledger_service import LedgerService


class AssemblyService:

    @staticmethod
    async def create_bom(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        finished_sku_id: uuid.UUID,
        lines: list[dict],
        landed_cost: Decimal = Decimal("0"),
        landed_cost_description: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> BOM:
        """Create a new BOM version, deactivating the old one."""
        # 1. Validate finished SKU exists
        finished_sku = await db.scalar(
            select(SKU).where(SKU.id == finished_sku_id, SKU.tenant_id == tenant_id)
        )
        if not finished_sku:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finished SKU not found")

        # 2. Check circular reference (component == finished)
        for line in lines:
            if uuid.UUID(str(line["component_sku_id"])) == finished_sku_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Circular reference: finished SKU cannot be a component of itself")

        # 3. Find current active version
        current_active = await db.scalar(
            select(BOM)
            .where(BOM.tenant_id == tenant_id, BOM.finished_sku_id == finished_sku_id, BOM.is_active == True)
            .order_by(BOM.version.desc())
        )
        new_version = 1
        if current_active:
            new_version = current_active.version + 1
            current_active.is_active = False
            db.add(current_active)

        # 4. Create new BOM
        bom = BOM(
            tenant_id=tenant_id,
            finished_sku_id=finished_sku_id,
            version=new_version,
            is_active=True,
            landed_cost=landed_cost,
            landed_cost_description=landed_cost_description,
            created_by=created_by,
        )
        db.add(bom)
        await db.flush()

        # 5. Create lines
        bom_lines = []
        for line in lines:
            bom_line = BOMLine(
                bom_id=bom.id,
                component_sku_id=uuid.UUID(str(line["component_sku_id"])),
                quantity=Decimal(str(line["quantity"])),
                unit=line.get("unit"),
            )
            db.add(bom_line)
            bom_lines.append(bom_line)
        
        await db.flush()
        return bom
        
    @staticmethod
    async def get_bom(db: AsyncSession, tenant_id: uuid.UUID, bom_id: uuid.UUID) -> BOM | None:
        return await db.scalar(
            select(BOM).where(BOM.id == bom_id, BOM.tenant_id == tenant_id)
        )
        
    @staticmethod
    async def check_availability(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        bom_id: uuid.UUID,
        planned_qty: Decimal
    ) -> dict[uuid.UUID, dict]:
        """
        Check if sufficient component stock exists for the planned quantity.
        Returns a dictionary of shortages. Empty dict means all good.
        """
        bom = await AssemblyService.get_bom(db, tenant_id, bom_id)
        if not bom:
            raise HTTPException(status_code=404, detail="BOM not found")
            
        shortages = {}
        for line in bom.lines:
            required_qty = line.quantity * planned_qty
            # Get total stock across all locations in tenant (or we could scope to warehouse)
            # For simplicity, scope to tenant total availability first
            current_stock = await LedgerService.get_stock_level(
                db, tenant_id, line.component_sku_id, warehouse_id=None
            )
            if current_stock < required_qty:
                shortages[line.component_sku_id] = {
                    "required": required_qty,
                    "available": current_stock,
                    "shortage": required_qty - current_stock
                }
        return shortages

    @staticmethod
    async def start_assembly_order(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        bom_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        planned_qty: Decimal,
        created_by: uuid.UUID | None = None,
    ) -> AssemblyOrder:
        bom = await AssemblyService.get_bom(db, tenant_id, bom_id)
        if not bom or not bom.is_active:
            raise HTTPException(status_code=400, detail="Active BOM not found")
            
        # 1. Check availability
        shortages = await AssemblyService.check_availability(db, tenant_id, bom_id, planned_qty)
        if shortages:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Insufficient component stock", "shortages": {str(k): float(v["shortage"]) for k, v in shortages.items()}}
            )
            
        # 2. Insert ASSEMBLE_OUT events for all components
        for line in bom.lines:
            await LedgerService.post_event(
                db=db,
                tenant_id=tenant_id,
                sku_id=line.component_sku_id,
                warehouse_id=warehouse_id,
                event_type="ASSEMBLE_OUT",
                quantity_delta=-(line.quantity * planned_qty),
                actor_id=created_by,
                reference_id=None, # Will update with real order ID later if needed
                notes=f"Reserved for assembly of BOM {bom_id}"
            )
            
        # 3. Create the order
        order = AssemblyOrder(
            tenant_id=tenant_id,
            bom_id=bom_id,
            bom_version=bom.version,
            warehouse_id=warehouse_id,
            planned_qty=planned_qty,
            status="IN_PROGRESS",
            created_by=created_by
        )
        db.add(order)
        await db.flush()
        
        # We could go back and update reference_id on those ledger events to order.id
        # For strictness, let's do an update
        await db.execute(
            update(StockLedger)
            .where(StockLedger.tenant_id == tenant_id, StockLedger.notes == f"Reserved for assembly of BOM {bom_id}", StockLedger.reference_id.is_(None))
            .values(reference_id=order.id, notes="Reserved for assembly order")
        )
        
        return order

    @staticmethod
    async def complete_assembly_order(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        produced_qty: Decimal,
        waste_qty: Decimal = Decimal("0"),
        waste_reason: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> AssemblyOrder:
        # 1. Fetch order
        order = await db.scalar(
            select(AssemblyOrder).where(AssemblyOrder.id == order_id, AssemblyOrder.tenant_id == tenant_id)
        )
        if not order:
            raise HTTPException(status_code=404, detail="Assembly order not found")
        if order.status != "IN_PROGRESS":
            raise HTTPException(status_code=400, detail=f"Cannot complete order in status {order.status}")

        # 2. Fetch BOM
        bom = await AssemblyService.get_bom(db, tenant_id, order.bom_id)
        if not bom:
            raise HTTPException(status_code=404, detail="Associated BOM not found")

        # 3. Calculate COGS (snapshot)
        # cogs_per_unit = landed_cost + sum(line_qty * component_unit_cost)
        total_component_cost = Decimal("0")
        for line in bom.lines:
            sku = await db.scalar(select(SKU).where(SKU.id == line.component_sku_id, SKU.tenant_id == tenant_id))
            if sku and sku.unit_cost:
                total_component_cost += Decimal(str(line.quantity * sku.unit_cost))
        
        cogs_per_unit = Decimal(str(bom.landed_cost)) + total_component_cost

        # 4. Insert ASSEMBLE_IN for finished goods
        # We manually create the event to include the unit_cost_snapshot
        event = StockLedger(
            tenant_id=tenant_id,
            sku_id=bom.finished_sku_id,
            warehouse_id=order.warehouse_id,
            event_type="ASSEMBLE_IN",
            quantity_delta=produced_qty,
            reference_id=order.id,
            actor_id=created_by,
            notes=f"Completed assembly order {order_id}"
        )
        # Assuming unit_cost_snapshot is an attribute on StockLedger now
        # We need to set it via kwargs since it might not be in the Base init if not typed
        # wait, we typed it in the DB schema but maybe not in python model yet. We can set it dynamically.
        # Actually, let's just make sure it's valid. The schema has unit_cost_snapshot NUMERIC.
        setattr(event, 'unit_cost_snapshot', cogs_per_unit)
        db.add(event)

        # 5. Handle waste
        # The components were fully reserved/deducted during start_assembly_order based on planned_qty.
        # If waste_qty > 0, we could log a WRITE_OFF for the components that were wasted 
        # (excess components consumed). But for MVP simplicity, the components are already gone
        # into the "Assembly Order" black hole. The finished goods are ASSEMBLE_IN. 
        # The waste is recorded on the order itself for auditing without needing complex ledger juggling.

        # 6. Update order stats
        order.produced_qty = produced_qty
        order.waste_qty = waste_qty
        order.waste_reason = waste_reason
        order.cogs_per_unit = cogs_per_unit
        order.status = "COMPLETE"
        order.completed_at = datetime.now(timezone.utc)
        
        await db.flush()
        return order
