"""
NEXUS IMS — Demo Seed Script
Populates a realistic electronics/tech company scenario:
  - 3 warehouses (HQ, East DC, West DC)
  - 5 item types
  - 45 named SKUs
  - Location hierarchy (Zone → Aisle → Bin)
  - Stock receives, picks, adjustments
  - 3 purchase orders (one partial, one complete)
  - 4 sales orders (mixed statuses)
  - 2 transfer orders
  - 3 BOMs + 2 assembly orders
  - 3 users (admin already exists, + 2 more)
  - 2 workflows (low stock alert, auto-reorder trigger)
  - 1 webhook endpoint

Run as nexus_admin to bypass RLS:
  docker compose exec -e DATABASE_URL="postgresql+asyncpg://nexus_admin:nexus_dev_password@postgres:5432/nexus_ims" fastapi python seed_demo.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.assembly import AssemblyOrder
from app.models.bom import BOM, BOMLine
from app.models.item_type import ItemType, SKU
from app.models.location import Location, TransferOrder, TransferOrderLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.tenant import Tenant, User
from app.models.warehouse import StockLedger, Warehouse
from app.models.workflow import Workflow, WorkflowAction
from app.models.webhook import Webhook
from app.core.security import get_password_hash

NOW = datetime.now(timezone.utc)


def ago(days=0, hours=0):
    return NOW - timedelta(days=days, hours=hours)


async def get_tenant(db: AsyncSession) -> Tenant:
    result = await db.execute(select(Tenant).limit(1))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise RuntimeError("No tenant found. Run create_superuser.py first.")
    return tenant


async def ledger(db, tenant_id, sku_id, wh_id, event_type, qty, *, notes=None, reason=None, ref_id=None, at=None):
    """Insert a raw stock ledger row without triggering workflow engine."""
    ev = StockLedger(
        tenant_id=tenant_id,
        sku_id=sku_id,
        warehouse_id=wh_id,
        event_type=event_type,
        quantity_delta=Decimal(str(qty)),
        notes=notes,
        reason_code=reason,
        reference_id=ref_id,
    )
    if at:
        ev.created_at = at
    db.add(ev)
    return ev


async def seed():
    print("🚀  NEXUS IMS — Demo Seed")
    print("=" * 50)

    async with async_session_maker() as db:
        tenant = await get_tenant(db)
        tid = tenant.id
        print(f"✓  Tenant: {tenant.name} ({tid})")

        # RLS bypass for nexus_admin
        await db.execute(text("SET SESSION row_security TO OFF"))

        # ─────────────────────────────────────────────
        # WAREHOUSES
        # ─────────────────────────────────────────────
        print("\n📦  Creating warehouses…")

        wh_data = [
            ("HQ Manufacturing & Fulfillment", "HQ-MFG", "14 Innovation Drive, Austin TX 78701", "America/Chicago"),
            ("East Coast Distribution Center", "EC-DC", "88 Logistics Blvd, Newark NJ 07102", "America/New_York"),
            ("West Coast Distribution Center", "WC-DC", "221 Harbor Way, Long Beach CA 90802", "America/Los_Angeles"),
        ]
        warehouses = []
        for name, code, addr, tz in wh_data:
            r = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tid, Warehouse.code == code))
            wh = r.scalar_one_or_none()
            if not wh:
                wh = Warehouse(tenant_id=tid, name=name, code=code, address=addr, timezone=tz)
                db.add(wh)
                await db.flush()
                print(f"  + {code}")
            else:
                print(f"  ~ {code} (exists)")
            warehouses.append(wh)

        wh_hq, wh_ec, wh_wc = warehouses

        # ─────────────────────────────────────────────
        # LOCATIONS — HQ only (zone → aisle → bin)
        # ─────────────────────────────────────────────
        print("\n📍  Creating locations…")

        async def make_loc(wh_id, name, code, loc_type, parent_id=None):
            r = await db.execute(select(Location).where(Location.warehouse_id == wh_id, Location.code == code))
            loc = r.scalar_one_or_none()
            if not loc:
                loc = Location(tenant_id=tid, warehouse_id=wh_id, name=name, code=code,
                               location_type=loc_type, parent_id=parent_id)
                db.add(loc)
                await db.flush()
            return loc

        # HQ zones
        zone_a = await make_loc(wh_hq.id, "Zone A — Components", "HQ-A", "ZONE")
        zone_b = await make_loc(wh_hq.id, "Zone B — Finished Goods", "HQ-B", "ZONE")
        zone_r = await make_loc(wh_hq.id, "Zone R — Returns & QC", "HQ-R", "ZONE")

        # Zone A aisles
        a1 = await make_loc(wh_hq.id, "Aisle 1", "HQ-A-1", "AISLE", zone_a.id)
        a2 = await make_loc(wh_hq.id, "Aisle 2", "HQ-A-2", "AISLE", zone_a.id)

        # Bins under A-1
        bins_a1 = []
        for i in range(1, 7):
            b = await make_loc(wh_hq.id, f"Bin A1-{i:02d}", f"HQ-A-1-{i:02d}", "BIN", a1.id)
            bins_a1.append(b)

        # Bins under A-2
        bins_a2 = []
        for i in range(1, 5):
            b = await make_loc(wh_hq.id, f"Bin A2-{i:02d}", f"HQ-A-2-{i:02d}", "BIN", a2.id)
            bins_a2.append(b)

        # Zone B aisle + bins
        b1 = await make_loc(wh_hq.id, "Aisle 1", "HQ-B-1", "AISLE", zone_b.id)
        bins_b1 = []
        for i in range(1, 5):
            b = await make_loc(wh_hq.id, f"Bin B1-{i:02d}", f"HQ-B-1-{i:02d}", "BIN", b1.id)
            bins_b1.append(b)

        print(f"  + HQ: 3 zones, 3 aisles, {len(bins_a1) + len(bins_a2) + len(bins_b1)} bins")

        # ─────────────────────────────────────────────
        # ITEM TYPES
        # ─────────────────────────────────────────────
        print("\n🏷  Creating item types…")

        it_data = [
            ("Electronic Components", "ELEC", [
                {"name": "voltage_rating", "type": "string"},
                {"name": "package_type", "type": "string"},
                {"name": "rohs_compliant", "type": "boolean"},
            ]),
            ("Mechanical Parts", "MECH", [
                {"name": "material", "type": "string"},
                {"name": "weight_g", "type": "number"},
                {"name": "tolerance_mm", "type": "number"},
            ]),
            ("Finished Goods", "FG", [
                {"name": "model_number", "type": "string"},
                {"name": "warranty_months", "type": "number"},
                {"name": "color", "type": "string"},
            ]),
            ("Packaging Materials", "PKG", [
                {"name": "dimensions_cm", "type": "string"},
                {"name": "material", "type": "string"},
                {"name": "recyclable", "type": "boolean"},
            ]),
            ("Raw Materials", "RAW", [
                {"name": "grade", "type": "string"},
                {"name": "purity_pct", "type": "number"},
                {"name": "unit_of_measure", "type": "string"},
            ]),
        ]

        item_types = {}
        for name, code, schema in it_data:
            r = await db.execute(select(ItemType).where(ItemType.tenant_id == tid, ItemType.code == code))
            it = r.scalar_one_or_none()
            if not it:
                it = ItemType(tenant_id=tid, name=name, code=code, attribute_schema=schema)
                db.add(it)
                await db.flush()
                print(f"  + {code} — {name}")
            else:
                print(f"  ~ {code} (exists)")
            item_types[code] = it

        # ─────────────────────────────────────────────
        # SKUs (45 realistic items)
        # ─────────────────────────────────────────────
        print("\n🔧  Creating SKUs…")

        sku_data = [
            # Electronic Components
            ("ELEC-MCU-001", "STM32F4 Microcontroller", "ELEC", {"voltage_rating": "3.3V", "package_type": "LQFP-64", "rohs_compliant": True}, 50, 8.75, 200),
            ("ELEC-MCU-002", "ESP32-S3 WiFi/BT SoC", "ELEC", {"voltage_rating": "3.3V", "package_type": "QFN-56", "rohs_compliant": True}, 100, 4.20, 350),
            ("ELEC-CAP-001", "100µF Electrolytic Capacitor", "ELEC", {"voltage_rating": "16V", "package_type": "THT", "rohs_compliant": True}, 500, 0.18, 8000),
            ("ELEC-CAP-002", "10µF MLCC Capacitor", "ELEC", {"voltage_rating": "25V", "package_type": "0805", "rohs_compliant": True}, 1000, 0.05, 15000),
            ("ELEC-RES-001", "10kΩ Precision Resistor 1%", "ELEC", {"voltage_rating": "N/A", "package_type": "0402", "rohs_compliant": True}, 2000, 0.02, 50000),
            ("ELEC-RES-002", "100Ω Power Resistor 5W", "ELEC", {"voltage_rating": "N/A", "package_type": "TO-220", "rohs_compliant": True}, 300, 0.45, 1200),
            ("ELEC-LED-001", "High-Brightness White LED", "ELEC", {"voltage_rating": "3.2V", "package_type": "5050", "rohs_compliant": True}, 200, 0.12, 5000),
            ("ELEC-REG-001", "LM7805 5V Voltage Regulator", "ELEC", {"voltage_rating": "5V", "package_type": "TO-220", "rohs_compliant": True}, 150, 0.65, 800),
            ("ELEC-CONN-001", "USB-C Port Connector", "ELEC", {"voltage_rating": "20V", "package_type": "SMD", "rohs_compliant": True}, 80, 1.10, 600),
            ("ELEC-CONN-002", "2-Pin JST Connector (pair)", "ELEC", {"voltage_rating": "3A max", "package_type": "THT", "rohs_compliant": True}, 200, 0.22, 3000),
            ("ELEC-BAT-001", "18650 Li-ion Cell 3000mAh", "ELEC", {"voltage_rating": "3.7V", "package_type": "Cylindrical", "rohs_compliant": True}, 30, 3.80, 200),
            ("ELEC-DISP-001", "2.4\" TFT LCD Display", "ELEC", {"voltage_rating": "3.3V", "package_type": "Module", "rohs_compliant": True}, 40, 6.50, 150),
            ("ELEC-MOSFET-001", "N-Channel MOSFET IRF540N", "ELEC", {"voltage_rating": "100V", "package_type": "TO-220", "rohs_compliant": True}, 100, 0.85, 500),
            ("ELEC-SENSOR-001", "BME280 Temp/Humidity Sensor", "ELEC", {"voltage_rating": "3.3V", "package_type": "LGA-8", "rohs_compliant": True}, 60, 2.30, 400),
            ("ELEC-SENSOR-002", "MPU-6050 IMU (Gyro+Accel)", "ELEC", {"voltage_rating": "3.3V", "package_type": "QFN-24", "rohs_compliant": True}, 50, 1.95, 300),
            # Mechanical Parts
            ("MECH-SCREW-001", "M3×8mm Stainless Screw", "MECH", {"material": "Stainless Steel 304", "weight_g": 0.8, "tolerance_mm": 0.05}, 1000, 0.04, 20000),
            ("MECH-SCREW-002", "M4×12mm Hex Bolt", "MECH", {"material": "Stainless Steel 316", "weight_g": 2.1, "tolerance_mm": 0.05}, 500, 0.07, 8000),
            ("MECH-NUT-001", "M3 Hex Nut", "MECH", {"material": "Stainless Steel 304", "weight_g": 0.3, "tolerance_mm": 0.05}, 1000, 0.02, 15000),
            ("MECH-SPCR-001", "5mm Brass Standoff M3", "MECH", {"material": "Brass", "weight_g": 0.9, "tolerance_mm": 0.1}, 500, 0.08, 3000),
            ("MECH-HEAT-001", "Aluminum Heatsink 40×40×10mm", "MECH", {"material": "Aluminum 6061", "weight_g": 18.5, "tolerance_mm": 0.2}, 50, 0.95, 300),
            ("MECH-ENC-001", "ABS Plastic Enclosure 100×60×25mm", "MECH", {"material": "ABS Plastic", "weight_g": 45.0, "tolerance_mm": 0.5}, 30, 2.80, 200),
            ("MECH-ENC-002", "Aluminum Enclosure 120×80×40mm", "MECH", {"material": "Aluminum 6063", "weight_g": 210.0, "tolerance_mm": 0.3}, 20, 8.50, 100),
            ("MECH-PCB-001", "4-Layer PCB (100×80mm)", "MECH", {"material": "FR4", "weight_g": 32.0, "tolerance_mm": 0.1}, 20, 4.20, 500),
            ("MECH-PCB-002", "2-Layer PCB (50×40mm)", "MECH", {"material": "FR4", "weight_g": 8.0, "tolerance_mm": 0.1}, 20, 1.80, 1000),
            # Finished Goods
            ("FG-CTRL-001", "NexusCore IoT Controller v2", "FG", {"model_number": "NXC-200", "warranty_months": 24, "color": "Matte Black"}, 10, 89.00, 45),
            ("FG-CTRL-002", "NexusCore Industrial Gateway", "FG", {"model_number": "NXG-500", "warranty_months": 36, "color": "RAL 7035 Grey"}, 15, 249.00, 20),
            ("FG-SENS-001", "NexusSense Environmental Monitor", "FG", {"model_number": "NXS-100", "warranty_months": 12, "color": "White"}, 5, 59.00, 80),
            ("FG-DEV-001", "NexusDev Evaluation Board", "FG", {"model_number": "NXD-EVB1", "warranty_months": 12, "color": "PCB Green"}, 10, 35.00, 60),
            ("FG-KIT-001", "NexusDev Starter Kit", "FG", {"model_number": "NXD-KIT1", "warranty_months": 12, "color": "Mixed"}, 10, 79.00, 30),
            # Packaging Materials
            ("PKG-BOX-001", "Small Product Box 200×150×80mm", "PKG", {"dimensions_cm": "20x15x8", "material": "Corrugated Cardboard", "recyclable": True}, 200, 0.35, 2000),
            ("PKG-BOX-002", "Medium Product Box 300×250×150mm", "PKG", {"dimensions_cm": "30x25x15", "material": "Corrugated Cardboard", "recyclable": True}, 100, 0.65, 500),
            ("PKG-FOAM-001", "Custom Cut Foam Insert (Small)", "PKG", {"dimensions_cm": "19x14x7", "material": "Polyurethane Foam", "recyclable": False}, 100, 0.90, 500),
            ("PKG-TAPE-001", "Kraft Paper Packing Tape 50m", "PKG", {"dimensions_cm": "5x50x0.01", "material": "Kraft Paper", "recyclable": True}, 50, 1.20, 200),
            ("PKG-WRAP-001", "Anti-static Bubble Wrap 50m Roll", "PKG", {"dimensions_cm": "60x50x0.3", "material": "Polyethylene", "recyclable": False}, 20, 8.50, 30),
            ("PKG-LABEL-001", "Thermal Label 100×50mm (roll 500)", "PKG", {"dimensions_cm": "10x5x0.01", "material": "Thermal Paper", "recyclable": True}, 100, 4.20, 80),
            # Raw Materials
            ("RAW-PCB-LAMIN-001", "FR4 Laminate Sheet 300×300mm", "RAW", {"grade": "FR4-TG150", "purity_pct": 99.5, "unit_of_measure": "sheet"}, 50, 3.20, 100),
            ("RAW-SOLDER-001", "SAC305 Solder Paste 500g", "RAW", {"grade": "SAC305", "purity_pct": 96.5, "unit_of_measure": "jar"}, 20, 18.50, 15),
            ("RAW-FLUX-001", "No-Clean Flux Pen 10ml", "RAW", {"grade": "RMA", "purity_pct": 99.0, "unit_of_measure": "pen"}, 50, 3.40, 40),
            ("RAW-WIRE-001", "22AWG Hookup Wire Red 100m", "RAW", {"grade": "Commercial", "purity_pct": 99.9, "unit_of_measure": "roll"}, 20, 6.80, 25),
            ("RAW-WIRE-002", "22AWG Hookup Wire Black 100m", "RAW", {"grade": "Commercial", "purity_pct": 99.9, "unit_of_measure": "roll"}, 20, 6.80, 22),
            ("RAW-TIN-001", "Tinning Solution 250ml", "RAW", {"grade": "Industrial", "purity_pct": 98.0, "unit_of_measure": "bottle"}, 20, 12.00, 10),
            ("RAW-THERM-001", "Thermal Compound 50g Syringe", "RAW", {"grade": "High-Performance", "purity_pct": 99.0, "unit_of_measure": "syringe"}, 20, 4.50, 30),
            ("RAW-ALUM-001", "Aluminum Sheet 200×200×2mm", "RAW", {"grade": "6061-T6", "purity_pct": 97.8, "unit_of_measure": "sheet"}, 30, 2.20, 80),
            ("RAW-NYLON-001", "Nylon Filament 1.75mm 1kg Black", "RAW", {"grade": "PA12", "purity_pct": 99.5, "unit_of_measure": "spool"}, 15, 22.00, 12),
        ]

        skus = {}
        created_count = 0
        for sku_code, name, it_code, attrs, reorder, cost, initial_stock in sku_data:
            r = await db.execute(select(SKU).where(SKU.tenant_id == tid, SKU.sku_code == sku_code))
            sku = r.scalar_one_or_none()
            if not sku:
                sku = SKU(
                    tenant_id=tid,
                    sku_code=sku_code,
                    name=name,
                    item_type_id=item_types[it_code].id,
                    attributes=attrs,
                    reorder_point=Decimal(str(reorder)),
                    unit_cost=Decimal(str(cost)),
                )
                db.add(sku)
                await db.flush()
                created_count += 1

                # Seed initial stock at HQ with realistic timestamps
                if initial_stock > 0:
                    await ledger(db, tid, sku.id, wh_hq.id, "RECEIVE", initial_stock,
                                 notes="Initial inventory — opening count", reason="INITIAL_STOCK",
                                 at=ago(days=90))

                # Seed some stock at EC for finished goods + packaging
                if it_code in ("FG", "PKG") and initial_stock > 20:
                    ec_qty = initial_stock // 3
                    await ledger(db, tid, sku.id, wh_ec.id, "RECEIVE", ec_qty,
                                 notes="Initial EC stock allocation", reason="INITIAL_STOCK",
                                 at=ago(days=85))

            skus[sku_code] = sku

        await db.flush()
        print(f"  + Created {created_count} SKUs ({len(skus)} total)")

        # ─────────────────────────────────────────────
        # REALISTIC TRANSACTION HISTORY (last 30 days)
        # ─────────────────────────────────────────────
        print("\n📊  Generating transaction history…")

        # Component receives (simulating weekly purchase order deliveries)
        receive_events = [
            ("ELEC-MCU-001", wh_hq.id, 100, ago(days=28), "PO-2024-001 delivery"),
            ("ELEC-MCU-002", wh_hq.id, 200, ago(days=28), "PO-2024-001 delivery"),
            ("ELEC-CAP-001", wh_hq.id, 5000, ago(days=28), "PO-2024-001 delivery"),
            ("ELEC-CAP-002", wh_hq.id, 8000, ago(days=21), "PO-2024-002 delivery"),
            ("ELEC-RES-001", wh_hq.id, 10000, ago(days=21), "PO-2024-002 delivery"),
            ("MECH-SCREW-001", wh_hq.id, 5000, ago(days=21), "PO-2024-002 delivery"),
            ("MECH-PCB-001", wh_hq.id, 200, ago(days=14), "PO-2024-003 delivery"),
            ("MECH-PCB-002", wh_hq.id, 500, ago(days=14), "PO-2024-003 delivery"),
            ("RAW-SOLDER-001", wh_hq.id, 10, ago(days=7), "Monthly consumables restock"),
            ("PKG-BOX-001", wh_hq.id, 500, ago(days=10), "Packaging restock"),
            ("PKG-BOX-002", wh_hq.id, 200, ago(days=10), "Packaging restock"),
            ("ELEC-SENSOR-001", wh_hq.id, 150, ago(days=5), "PO-2024-004 partial delivery"),
        ]
        for sku_code, wh_id, qty, at, notes in receive_events:
            if sku_code in skus:
                await ledger(db, tid, skus[sku_code].id, wh_id, "RECEIVE", qty, notes=notes, at=at)

        # Production picks (components consumed in manufacturing)
        pick_events = [
            ("ELEC-MCU-001", wh_hq.id, -50, ago(days=25), "Assembly run AR-2024-001"),
            ("ELEC-MCU-002", wh_hq.id, -80, ago(days=25), "Assembly run AR-2024-001"),
            ("ELEC-CAP-001", wh_hq.id, -2000, ago(days=25), "Assembly run AR-2024-001"),
            ("ELEC-RES-001", wh_hq.id, -5000, ago(days=25), "Assembly run AR-2024-001"),
            ("MECH-PCB-001", wh_hq.id, -50, ago(days=24), "Assembly run AR-2024-001"),
            ("MECH-ENC-001", wh_hq.id, -30, ago(days=24), "Assembly run AR-2024-001"),
            ("ELEC-MCU-001", wh_hq.id, -30, ago(days=12), "Assembly run AR-2024-002"),
            ("ELEC-SENSOR-001", wh_hq.id, -60, ago(days=12), "Assembly run AR-2024-002"),
            ("MECH-PCB-002", wh_hq.id, -100, ago(days=12), "Assembly run AR-2024-002"),
            ("PKG-BOX-001", wh_hq.id, -80, ago(days=11), "Shipping — SO-2024-003 batch"),
            ("PKG-BOX-001", wh_hq.id, -40, ago(days=4), "Shipping — SO-2024-004 batch"),
            ("PKG-BOX-002", wh_hq.id, -20, ago(days=4), "Shipping — SO-2024-004 batch"),
        ]
        for sku_code, wh_id, qty, at, notes in pick_events:
            if sku_code in skus:
                await ledger(db, tid, skus[sku_code].id, wh_id, "PICK", qty, notes=notes, at=at)

        # Cycle count correction
        adjustments = [
            ("ELEC-LED-001", wh_hq.id, -12, ago(days=15), "Cycle count correction — damaged units"),
            ("MECH-SCREW-001", wh_hq.id, 85, ago(days=15), "Cycle count correction — found uncounted box"),
            ("ELEC-CAP-002", wh_hq.id, -200, ago(days=8), "Damaged in forklift incident — write-off"),
            ("RAW-FLUX-001", wh_hq.id, -5, ago(days=3), "Used for rework — expensed"),
        ]
        for sku_code, wh_id, qty, at, notes in adjustments:
            if sku_code in skus:
                ev = "ADJUST" if qty > 0 else "WRITE_OFF"
                await ledger(db, tid, skus[sku_code].id, wh_id, ev, qty, notes=notes, at=at)

        await db.flush()
        print(f"  + {len(receive_events)} receives, {len(pick_events)} picks, {len(adjustments)} adjustments")

        # ─────────────────────────────────────────────
        # PURCHASE ORDERS
        # ─────────────────────────────────────────────
        print("\n🛒  Creating purchase orders…")

        # PO 1 — RECEIVED (complete)
        r = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tid, PurchaseOrder.supplier_name == "Mouser Electronics"))
        po1 = r.scalar_one_or_none()
        if not po1:
            po1 = PurchaseOrder(tenant_id=tid, supplier_name="Mouser Electronics",
                                warehouse_id=wh_hq.id, status="RECEIVED",
                                notes="Q1 component restock — bulk order")
            db.add(po1)
            await db.flush()
            for sku_code, qty, cost in [
                ("ELEC-MCU-001", 100, 8.75), ("ELEC-MCU-002", 200, 4.20),
                ("ELEC-CAP-001", 5000, 0.18), ("ELEC-RES-001", 10000, 0.02),
            ]:
                if sku_code in skus:
                    line = PurchaseOrderLine(po_id=po1.id,
                                            sku_id=skus[sku_code].id,
                                            quantity_ordered=Decimal(str(qty)),
                                            quantity_received=Decimal(str(qty)),
                                            unit_cost=Decimal(str(cost)))
                    db.add(line)
            print("  + PO-001: Mouser Electronics [RECEIVED]")

        # PO 2 — PARTIAL
        r = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tid, PurchaseOrder.supplier_name == "Digi-Key Corporation"))
        po2 = r.scalar_one_or_none()
        if not po2:
            po2 = PurchaseOrder(tenant_id=tid, supplier_name="Digi-Key Corporation",
                                warehouse_id=wh_hq.id, status="PARTIAL",
                                notes="Sensors + display module order")
            db.add(po2)
            await db.flush()
            for sku_code, ordered, received, cost in [
                ("ELEC-SENSOR-001", 150, 150, 2.30),
                ("ELEC-SENSOR-002", 100, 50, 1.95),   # only 50 received so far
                ("ELEC-DISP-001", 80, 0, 6.50),         # not yet received
            ]:
                if sku_code in skus:
                    line = PurchaseOrderLine(po_id=po2.id,
                                            sku_id=skus[sku_code].id,
                                            quantity_ordered=Decimal(str(ordered)),
                                            quantity_received=Decimal(str(received)),
                                            unit_cost=Decimal(str(cost)))
                    db.add(line)
            print("  + PO-002: Digi-Key Corporation [PARTIAL]")

        # PO 3 — DRAFT
        r = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tid, PurchaseOrder.supplier_name == "PCBWay Manufacturing"))
        po3 = r.scalar_one_or_none()
        if not po3:
            po3 = PurchaseOrder(tenant_id=tid, supplier_name="PCBWay Manufacturing",
                                warehouse_id=wh_hq.id, status="DRAFT",
                                notes="Q2 PCB fabrication batch — awaiting engineering sign-off")
            db.add(po3)
            await db.flush()
            for sku_code, qty, cost in [
                ("MECH-PCB-001", 500, 4.20), ("MECH-PCB-002", 1000, 1.80),
            ]:
                if sku_code in skus:
                    line = PurchaseOrderLine(po_id=po3.id,
                                            sku_id=skus[sku_code].id,
                                            quantity_ordered=Decimal(str(qty)),
                                            quantity_received=Decimal("0"),
                                            unit_cost=Decimal(str(cost)))
                    db.add(line)
            print("  + PO-003: PCBWay Manufacturing [DRAFT]")

        # PO 4 — ORDERED
        r = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tid, PurchaseOrder.supplier_name == "RS Components"))
        po4 = r.scalar_one_or_none()
        if not po4:
            po4 = PurchaseOrder(tenant_id=tid, supplier_name="RS Components",
                                warehouse_id=wh_hq.id, status="ORDERED",
                                notes="Passive components top-up — ETA 3 business days")
            db.add(po4)
            await db.flush()
            for sku_code, qty, cost in [
                ("ELEC-CAP-002", 20000, 0.05), ("ELEC-RES-002", 500, 0.45),
                ("ELEC-MOSFET-001", 300, 0.85), ("ELEC-REG-001", 200, 0.65),
            ]:
                if sku_code in skus:
                    line = PurchaseOrderLine(po_id=po4.id,
                                            sku_id=skus[sku_code].id,
                                            quantity_ordered=Decimal(str(qty)),
                                            quantity_received=Decimal("0"),
                                            unit_cost=Decimal(str(cost)))
                    db.add(line)
            print("  + PO-004: RS Components [ORDERED]")

        await db.flush()

        # ─────────────────────────────────────────────
        # SALES ORDERS
        # ─────────────────────────────────────────────
        print("\n💼  Creating sales orders…")

        # Ensure finished goods have stock at HQ
        fg_stock_map = {
            "FG-CTRL-001": 45, "FG-CTRL-002": 20, "FG-SENS-001": 80, "FG-DEV-001": 60, "FG-KIT-001": 30,
        }
        for sku_code, qty in fg_stock_map.items():
            if sku_code in skus:
                # Check if stock already seeded (skip if exists from above)
                pass  # already seeded in initial stock

        so_data = [
            ("TechStart Labs GmbH", "SHIPPED", ago(days=20), [
                ("FG-CTRL-001", 5, 89.00), ("FG-SENS-001", 10, 59.00),
            ]),
            ("Apex Automation Ltd", "SHIPPED", ago(days=14), [
                ("FG-CTRL-002", 3, 249.00), ("FG-DEV-001", 8, 35.00), ("FG-KIT-001", 5, 79.00),
            ]),
            ("Meridian IoT Solutions", "ALLOCATED", ago(days=7), [
                ("FG-CTRL-001", 8, 89.00), ("FG-SENS-001", 20, 59.00), ("FG-KIT-001", 6, 79.00),
            ]),
            ("BlueSky Systems Inc.", "PENDING", ago(days=2), [
                ("FG-CTRL-001", 12, 89.00), ("FG-CTRL-002", 4, 249.00),
            ]),
            ("NovaTech Engineering", "PENDING", ago(days=1), [
                ("FG-DEV-001", 15, 35.00), ("FG-KIT-001", 10, 79.00), ("FG-SENS-001", 25, 59.00),
            ]),
        ]

        for customer, status, created, lines in so_data:
            r = await db.execute(select(SalesOrder).where(SalesOrder.tenant_id == tid, SalesOrder.customer_name == customer))
            so = r.scalar_one_or_none()
            if not so:
                so = SalesOrder(tenant_id=tid, customer_name=customer, status=status,
                                order_reference=f"Order via portal — {customer}")
                db.add(so)
                await db.flush()
                for sku_code, qty, price in lines:
                    if sku_code in skus:
                        line = SalesOrderLine(sales_order_id=so.id,
                                              sku_id=skus[sku_code].id,
                                              quantity=Decimal(str(qty)),
                                              fulfilled_qty=Decimal(str(qty)) if status == "SHIPPED" else Decimal("0"),
                                              unit_price=Decimal(str(price)))
                        db.add(line)

                # Post ledger events for shipped orders
                if status == "SHIPPED":
                    for sku_code, qty, _ in lines:
                        if sku_code in skus:
                            await ledger(db, tid, skus[sku_code].id, wh_hq.id, "SHIP_OUT", -qty,
                                         notes=f"Shipped to {customer}", ref_id=so.id, at=created)

                # Reserve for allocated
                if status == "ALLOCATED":
                    for sku_code, qty, _ in lines:
                        if sku_code in skus:
                            await ledger(db, tid, skus[sku_code].id, wh_hq.id, "RESERVE_OUT", -qty,
                                         notes=f"Reserved for {customer}", ref_id=so.id, at=created)

                print(f"  + SO: {customer} [{status}]")

        await db.flush()

        # ─────────────────────────────────────────────
        # TRANSFER ORDERS
        # ─────────────────────────────────────────────
        print("\n🚚  Creating transfer orders…")

        r = await db.execute(select(TransferOrder).where(TransferOrder.tenant_id == tid).limit(1))
        existing_to = r.scalar_one_or_none()
        if not existing_to:
            # TO 1: HQ → EC (RECEIVED)
            to1 = TransferOrder(tenant_id=tid, from_warehouse_id=wh_hq.id, to_warehouse_id=wh_ec.id,
                                status="RECEIVED")
            db.add(to1)
            await db.flush()
            for sku_code, qty in [("FG-CTRL-001", 10), ("FG-SENS-001", 20), ("PKG-BOX-001", 100)]:
                if sku_code in skus:
                    tol = TransferOrderLine(transfer_order_id=to1.id,
                                           sku_id=skus[sku_code].id,
                                           quantity_requested=Decimal(str(qty)),
                                           quantity_received=Decimal(str(qty)))
                    db.add(tol)
                    await ledger(db, tid, skus[sku_code].id, wh_hq.id, "TRANSFER_OUT", -qty,
                                 notes="TO-001: HQ → EC", ref_id=to1.id, at=ago(days=30))
                    await ledger(db, tid, skus[sku_code].id, wh_ec.id, "TRANSFER_IN", qty,
                                 notes="TO-001: HQ → EC", ref_id=to1.id, at=ago(days=29))
            print("  + TO-001: HQ → EC [RECEIVED]")

            # TO 2: HQ → WC (PENDING)
            to2 = TransferOrder(tenant_id=tid, from_warehouse_id=wh_hq.id, to_warehouse_id=wh_wc.id,
                                status="PENDING")
            db.add(to2)
            await db.flush()
            for sku_code, qty in [("FG-CTRL-001", 8), ("FG-DEV-001", 15), ("FG-KIT-001", 10)]:
                if sku_code in skus:
                    tol = TransferOrderLine(transfer_order_id=to2.id,
                                           sku_id=skus[sku_code].id,
                                           quantity_requested=Decimal(str(qty)),
                                           quantity_received=Decimal("0"))
                    db.add(tol)
            print("  + TO-002: HQ → WC [PENDING]")

        await db.flush()

        # ─────────────────────────────────────────────
        # BOMs + ASSEMBLY ORDERS
        # ─────────────────────────────────────────────
        print("\n⚙️  Creating BOMs and assembly orders…")

        r = await db.execute(select(BOM).where(BOM.tenant_id == tid).limit(1))
        existing_bom = r.scalar_one_or_none()
        if not existing_bom:
            # BOM 1: NexusCore IoT Controller v2
            bom1 = BOM(tenant_id=tid, finished_sku_id=skus["FG-CTRL-001"].id,
                       version=3, landed_cost=Decimal("5.00"),
                       landed_cost_description="Main product BOM. Includes PCB, MCU, passives, connectors, enclosure.")
            db.add(bom1)
            await db.flush()
            bom1_lines = [
                ("MECH-PCB-001", "1"), ("ELEC-MCU-001", "1"),
                ("ELEC-CAP-001", "10"), ("ELEC-CAP-002", "8"),
                ("ELEC-RES-001", "22"), ("ELEC-REG-001", "1"),
                ("ELEC-CONN-001", "1"), ("MECH-ENC-001", "1"),
                ("MECH-SCREW-001", "4"), ("PKG-BOX-001", "1"),
                ("PKG-FOAM-001", "1"),
            ]
            for sku_code, qty in bom1_lines:
                if sku_code in skus:
                    bl = BOMLine(bom_id=bom1.id,
                                 component_sku_id=skus[sku_code].id,
                                 quantity=Decimal(qty))
                    db.add(bl)
            print("  + BOM-001: NexusCore IoT Controller v2")

            # BOM 2: NexusSense Environmental Monitor
            bom2 = BOM(tenant_id=tid, finished_sku_id=skus["FG-SENS-001"].id,
                       version=2, landed_cost=Decimal("2.50"))
            db.add(bom2)
            await db.flush()
            bom2_lines = [
                ("MECH-PCB-002", "1"), ("ELEC-MCU-002", "1"),
                ("ELEC-SENSOR-001", "1"), ("ELEC-SENSOR-002", "1"),
                ("ELEC-CAP-001", "6"), ("ELEC-RES-001", "8"),
                ("MECH-ENC-001", "1"), ("ELEC-BAT-001", "1"),
                ("PKG-BOX-001", "1"),
            ]
            for sku_code, qty in bom2_lines:
                if sku_code in skus:
                    bl = BOMLine(bom_id=bom2.id,
                                 component_sku_id=skus[sku_code].id,
                                 quantity=Decimal(qty))
                    db.add(bl)
            print("  + BOM-002: NexusSense Environmental Monitor")

            # BOM 3: NexusDev Starter Kit (kitting)
            bom3 = BOM(tenant_id=tid, finished_sku_id=skus["FG-KIT-001"].id,
                       version=1, landed_cost=Decimal("1.50"),
                       landed_cost_description="Kitting BOM: bundles Dev Board + Sensor + accessories")
            db.add(bom3)
            await db.flush()
            bom3_lines = [
                ("FG-DEV-001", "1"), ("FG-SENS-001", "1"),
                ("PKG-BOX-002", "1"), ("PKG-FOAM-001", "1"),
            ]
            for sku_code, qty in bom3_lines:
                if sku_code in skus:
                    bl = BOMLine(bom_id=bom3.id,
                                 component_sku_id=skus[sku_code].id,
                                 quantity=Decimal(qty))
                    db.add(bl)
            print("  + BOM-003: NexusDev Starter Kit")

            await db.flush()

            # Assembly Orders
            ao1 = AssemblyOrder(tenant_id=tid, bom_id=bom1.id, bom_version=3,
                                warehouse_id=wh_hq.id,
                                planned_qty=Decimal("50"), produced_qty=Decimal("50"),
                                waste_qty=Decimal("1"),
                                status="COMPLETED",
                                waste_reason="Assembly run AR-2024-001 — 50 units NexusCore")
            db.add(ao1)
            await db.flush()
            await ledger(db, tid, skus["FG-CTRL-001"].id, wh_hq.id, "ASSEMBLE_IN", 50,
                         notes="AR-2024-001 output", ref_id=ao1.id, at=ago(days=22))
            print("  + AO-001: 50× NexusCore IoT [COMPLETED]")

            ao2 = AssemblyOrder(tenant_id=tid, bom_id=bom2.id, bom_version=2,
                                warehouse_id=wh_hq.id,
                                planned_qty=Decimal("80"), produced_qty=Decimal("0"),
                                waste_qty=Decimal("0"),
                                status="IN_PROGRESS")
            db.add(ao2)
            await db.flush()
            print("  + AO-002: 80× NexusSense [IN_PROGRESS]")

        await db.flush()

        # ─────────────────────────────────────────────
        # ADDITIONAL USERS
        # ─────────────────────────────────────────────
        print("\n👤  Creating team users…")

        users_data = [
            ("warehouse@nexus.com", "Alex Ramos", "FLOOR_ASSOCIATE", "warehouse123"),
            ("manager@nexus.com", "Sarah Chen", "MANAGER", "manager123"),
            ("ops@nexus.com", "Jordan Miller", "FLOOR_ASSOCIATE", "ops123"),
        ]
        for email, name, role, pw in users_data:
            r = await db.execute(select(User).where(User.email == email))
            u = r.scalar_one_or_none()
            if not u:
                u = User(tenant_id=tid, email=email, full_name=name, role=role,
                         hashed_password=get_password_hash(pw), is_active=True)
                db.add(u)
                print(f"  + {email} [{role}]")
            else:
                print(f"  ~ {email} (exists)")

        await db.flush()

        # ─────────────────────────────────────────────
        # WORKFLOWS
        # ─────────────────────────────────────────────
        print("\n🔁  Creating workflows…")

        r = await db.execute(select(Workflow).where(Workflow.tenant_id == tid).limit(1))
        existing_wf = r.scalar_one_or_none()
        if not existing_wf:
            # Workflow 1: Low stock alert on PICK
            wf1 = Workflow(
                tenant_id=tid,
                name="Low Stock Alert — Critical Components",
                trigger_type="PICK",
                trigger_config={
                    "operator": "AND",
                    "conditions": [{"field": "quantity", "operator": "less_than", "value": 50}]
                },
                is_active=True,
            )
            db.add(wf1)
            await db.flush()
            wf1_action = WorkflowAction(
                workflow_id=wf1.id, sequence_order=0,
                action_type="send_webhook",
                action_config={"url": "https://hooks.example.com/nexus/low-stock", "include_sku": True}
            )
            db.add(wf1_action)
            print("  + WF-001: Low Stock Alert [PICK trigger, qty < 50]")

            # Workflow 2: Notify on WRITE_OFF
            wf2 = Workflow(
                tenant_id=tid,
                name="Write-Off Notification",
                trigger_type="WRITE_OFF",
                trigger_config={},   # no conditions = always trigger
                is_active=True,
            )
            db.add(wf2)
            await db.flush()
            wf2_action = WorkflowAction(
                workflow_id=wf2.id, sequence_order=0,
                action_type="log_event",
                action_config={"log_level": "WARNING", "message": "Inventory write-off event triggered"}
            )
            db.add(wf2_action)
            print("  + WF-002: Write-Off Notification [always fires]")

            # Workflow 3: High-volume receive notification
            wf3 = Workflow(
                tenant_id=tid,
                name="Large Receipt Alert",
                trigger_type="RECEIVE",
                trigger_config={
                    "operator": "AND",
                    "conditions": [{"field": "quantity_delta", "operator": "greater_than", "value": 1000}]
                },
                is_active=True,
            )
            db.add(wf3)
            await db.flush()
            wf3_action = WorkflowAction(
                workflow_id=wf3.id, sequence_order=0,
                action_type="send_webhook",
                action_config={"url": "https://hooks.example.com/nexus/large-receive"}
            )
            db.add(wf3_action)
            print("  + WF-003: Large Receipt Alert [RECEIVE > 1000 units]")

        await db.flush()

        # ─────────────────────────────────────────────
        # WEBHOOKS
        # ─────────────────────────────────────────────
        print("\n🔗  Creating webhooks…")

        r = await db.execute(select(Webhook).where(Webhook.tenant_id == tid).limit(1))
        existing_wh = r.scalar_one_or_none()
        if not existing_wh:
            wh1 = Webhook(
                tenant_id=tid,
                url="https://hooks.example.com/nexus/events",
                secret="nexus-demo-secret-key-change-in-prod",
                events=["RECEIVE", "PICK", "SHIP_OUT", "WRITE_OFF", "TRANSFER_IN"],
                is_active=True,
            )
            db.add(wh1)

            wh2 = Webhook(
                tenant_id=tid,
                url="https://zapier.example.com/hooks/catch/nexus-ims",
                secret="zapier-webhook-secret-key",
                events=["SHIP_OUT", "RESERVE_OUT"],
                is_active=True,
            )
            db.add(wh2)
            print("  + 2 webhooks registered")

        await db.commit()

        # ─────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────
        print("\n" + "=" * 50)
        print("✅  Demo seed complete!")
        print()
        print("  Login:     admin@nexus.com / admin")
        print("  Manager:   manager@nexus.com / manager123")
        print("  Warehouse: warehouse@nexus.com / warehouse123")
        print("  Ops staff: ops@nexus.com / ops123")
        print()
        print("  → http://localhost:5173")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
