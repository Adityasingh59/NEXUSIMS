"""create locations and transfer_orders (Block 3.1)

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, NUMERIC

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # location_type enum and transfer_status enum (idempotent)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE location_type_enum AS ENUM ('ZONE', 'AISLE', 'BIN');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE transfer_status_enum AS ENUM ('PENDING', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # locations table (zone > aisle > bin hierarchy)
    op.create_table(
        "locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),  # self-FK added after table creation
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("location_type", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_foreign_key("fk_locations_parent", "locations", "locations", ["parent_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_locations_warehouse_id", "locations", ["warehouse_id"], unique=False)
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"], unique=False)
    op.create_unique_constraint("uq_locations_warehouse_code", "locations", ["warehouse_id", "code"])

    # Add FK from stock_ledger.location_id to locations
    op.create_foreign_key("fk_stock_ledger_location", "stock_ledger", "locations", ["location_id"], ["id"], ondelete="SET NULL")

    # transfer_orders table
    op.create_table(
        "transfer_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_transfer_orders_from_warehouse", "transfer_orders", ["from_warehouse_id"], unique=False)
    op.create_index("ix_transfer_orders_to_warehouse", "transfer_orders", ["to_warehouse_id"], unique=False)
    op.create_index("ix_transfer_orders_status", "transfer_orders", ["status"], unique=False)

    # transfer_order_lines table
    op.create_table(
        "transfer_order_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transfer_order_id", UUID(as_uuid=True), sa.ForeignKey("transfer_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_requested", NUMERIC(18, 4), nullable=False),
        sa.Column("quantity_received", NUMERIC(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_transfer_order_lines_transfer_order_id", "transfer_order_lines", ["transfer_order_id"], unique=False)

    # RLS on locations, transfer_orders, transfer_order_lines
    op.execute("ALTER TABLE locations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY locations_tenant_policy ON locations "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    op.execute("ALTER TABLE transfer_orders ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY transfer_orders_tenant_policy ON transfer_orders "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    op.execute("ALTER TABLE transfer_order_lines ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY transfer_order_lines_tenant_policy ON transfer_order_lines "
        "USING ((SELECT tenant_id FROM transfer_orders WHERE transfer_orders.id = transfer_order_lines.transfer_order_id) = "
        "nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS transfer_order_lines_tenant_policy ON transfer_order_lines")
    op.execute("ALTER TABLE transfer_order_lines DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS transfer_orders_tenant_policy ON transfer_orders")
    op.execute("ALTER TABLE transfer_orders DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS locations_tenant_policy ON locations")
    op.execute("ALTER TABLE locations DISABLE ROW LEVEL SECURITY")

    op.drop_foreign_key("fk_stock_ledger_location", "stock_ledger", "locations")

    op.drop_index("ix_transfer_order_lines_transfer_order_id", table_name="transfer_order_lines")
    op.drop_table("transfer_order_lines")
    op.drop_index("ix_transfer_orders_status", table_name="transfer_orders")
    op.drop_index("ix_transfer_orders_to_warehouse", table_name="transfer_orders")
    op.drop_index("ix_transfer_orders_from_warehouse", table_name="transfer_orders")
    op.drop_table("transfer_orders")

    op.drop_constraint("uq_locations_warehouse_code", "locations", type_="unique")
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_index("ix_locations_warehouse_id", table_name="locations")
    op.drop_table("locations")

    op.execute("DROP TYPE IF EXISTS transfer_status_enum")
    op.execute("DROP TYPE IF EXISTS location_type_enum")
