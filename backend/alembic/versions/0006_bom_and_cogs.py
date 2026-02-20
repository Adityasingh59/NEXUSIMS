"""BOM, BOM lines, Purchase Orders, Purchase Order Lines — Block 5

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. purchase_order_status enum (idempotent) ──────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE purchase_order_status AS ENUM ('DRAFT', 'ORDERED', 'PARTIAL', 'RECEIVED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # ── 2. boms table ────────────────────────────────────────────────────────
    op.create_table(
        "boms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_boms_tenant_id", "boms", ["tenant_id"])
    op.create_index("ix_boms_sku_id", "boms", ["sku_id"])
    op.create_index("ix_boms_tenant_sku", "boms", ["tenant_id", "sku_id"])

    # RLS
    op.execute("ALTER TABLE boms ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY boms_tenant_policy ON boms "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # ── 3. bom_lines table ───────────────────────────────────────────────────
    op.create_table(
        "bom_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(12, 4), nullable=False, comment="Cost per unit at time of BOM definition"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_bom_lines_bom_id", "bom_lines", ["bom_id"])
    op.create_index("ix_bom_lines_component_sku_id", "bom_lines", ["component_sku_id"])

    # ── 4. purchase_orders table ─────────────────────────────────────────────
    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT", comment="purchase_order_status enum"),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index("ix_purchase_orders_warehouse_id", "purchase_orders", ["warehouse_id"])

    # RLS
    op.execute("ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY purchase_orders_tenant_policy ON purchase_orders "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # ── 5. purchase_order_lines table ────────────────────────────────────────
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("po_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_ordered", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity_received", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_purchase_order_lines_po_id", "purchase_order_lines", ["po_id"])
    op.create_index("ix_purchase_order_lines_sku_id", "purchase_order_lines", ["sku_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_order_lines_sku_id", table_name="purchase_order_lines")
    op.drop_index("ix_purchase_order_lines_po_id", table_name="purchase_order_lines")
    op.drop_table("purchase_order_lines")

    op.execute("DROP POLICY IF EXISTS purchase_orders_tenant_policy ON purchase_orders")
    op.execute("ALTER TABLE purchase_orders DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_purchase_orders_warehouse_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_tenant_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index("ix_bom_lines_component_sku_id", table_name="bom_lines")
    op.drop_index("ix_bom_lines_bom_id", table_name="bom_lines")
    op.drop_table("bom_lines")

    op.execute("DROP POLICY IF EXISTS boms_tenant_policy ON boms")
    op.execute("ALTER TABLE boms DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_boms_tenant_sku", table_name="boms")
    op.drop_index("ix_boms_sku_id", table_name="boms")
    op.drop_index("ix_boms_tenant_id", table_name="boms")
    op.drop_table("boms")

    op.execute("DROP TYPE IF EXISTS purchase_order_status")
