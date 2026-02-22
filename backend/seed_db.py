import asyncio
import uuid
import random
from decimal import Decimal

from sqlalchemy import select, text
from app.db.session import async_session_maker
from app.models.tenant import Tenant, User, UserRoleEnum
from app.models.item_type import ItemType, SKU
from app.models.warehouse import Warehouse, StockLedger, StockEventType
from app.core.security import get_password_hash

async def seed_database():
    print("Connecting to database for seeding...")
    async with async_session_maker() as db:
        
        # 1. Get or create Tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("Creating new default tenant...")
            tenant = Tenant(
                name="Nexus Manufacturing Inc.",
                slug="nexus-mfg",
                is_active=True
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            
            # Create an admin user for this tenant to allow login
            user = User(
                tenant_id=tenant.id,
                email="admin@nexus.com",
                hashed_password=get_password_hash("password123"), # default easy password
                full_name="Nexus Admin",
                role=UserRoleEnum.ADMIN.value,
                is_active=True
            )
            db.add(user)
            await db.commit()
            print("Created default tenant and admin user: admin@nexus.com / password123")
        else:
            print(f"Using existing tenant: {tenant.name} ({tenant.id})")
            
        # Bypass RLS manually for the sync connection 
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant.id)})

        # 2. Get or create a Warehouse
        result = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant.id).limit(1))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            warehouse = Warehouse(
                tenant_id=tenant.id,
                name="Primary Fulfillment Center",
                code="PFC-01",
                address="123 Industrial Way, Sector B",
                timezone="UTC"
            )
            db.add(warehouse)
            await db.commit()
            await db.refresh(warehouse)
        
        # 3. Create Item Types
        item_types = [
            ("Electronics Parts", "ELEC", [{"name": "voltage", "type": "number"}, {"name": "compliance", "type": "string"}]),
            ("Mechanical Components", "MECH", [{"name": "material", "type": "string"}, {"name": "weight_kg", "type": "number"}]),
            ("Packaging", "PKG", [{"name": "dimensions", "type": "string"}, {"name": "recyclable", "type": "boolean"}])
        ]
        
        db_types = []
        for name, code, schema in item_types:
            result = await db.execute(select(ItemType).where(ItemType.tenant_id == tenant.id, ItemType.code == code))
            it = result.scalar_one_or_none()
            if not it:
                it = ItemType(tenant_id=tenant.id, name=name, code=code, attribute_schema=schema)
                db.add(it)
                await db.commit()
                await db.refresh(it)
            db_types.append(it)

        # 4. Generate ~100 SKUs 
        print("Generating SKUs and initial stock ledgers...")
        adjectives = ["Advanced", "Durable", "Precision", "Compact", "Heavy-Duty", "Flexible", "Standard", "Premium"]
        nouns = ["Resistor", "Capacitor", "Microcontroller", "Bearing", "Gear", "Bracket", "Sensor", "Actuator", "Box", "Pallet", "Wrap"]
        
        skus_to_create = 500
        if skus_to_create > 0:
            for i in range(skus_to_create):
                it = random.choice(db_types)
                name = f"{random.choice(adjectives)} {random.choice(nouns)} {random.randint(100, 999)}"
                code = f"{it.code}-{random.randint(10000, 99999)}"
                
                # Mock attributes
                attrs = {}
                for f in it.attribute_schema:
                    if f["type"] == "number":
                        attrs[f["name"]] = round(random.uniform(0.1, 100.0), 2)
                    elif f["type"] == "boolean":
                        attrs[f["name"]] = random.choice([True, False])
                    else:
                        attrs[f["name"]] = random.choice(["RoHS", "Standard", "Aluminum", "Steel", "Plastic", "10x10"])
                
                sku = SKU(
                    tenant_id=tenant.id,
                    sku_code=code,
                    name=name,
                    item_type_id=it.id,
                    attributes=attrs,
                    reorder_point=Decimal(random.randint(10, 50)),
                    unit_cost=Decimal(round(random.uniform(1.0, 500.0), 2))
                )
                db.add(sku)
                await db.flush() # get id
                
                # Assign initial stock
                initial_stock = random.randint(0, 500)
                if initial_stock > 0:
                    ledger = StockLedger(
                        tenant_id=tenant.id,
                        sku_id=sku.id,
                        warehouse_id=warehouse.id,
                        event_type=StockEventType.RECEIVE.value,
                        quantity_delta=Decimal(initial_stock),
                        reason_code="INITIAL_SEED",
                        notes="Generated by seeding script"
                    )
                    db.add(ledger)
            
            await db.commit()
            print(f"Seeded {skus_to_create} additional SKUs and initial stock.")

if __name__ == "__main__":
    asyncio.run(seed_database())
