"""block_7_assembly

Revision ID: b271ac5d13fe
Revises: 0006
Create Date: 2026-02-20 18:06:59.291840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. (Omitted) event_type is a String(50), not a Postgres ENUM ─────────
    pass

    # ── 2. Add column to stock_ledger ────────────────────────────────────────
    op.execute("ALTER TABLE stock_ledger ADD COLUMN IF NOT EXISTS unit_cost_snapshot NUMERIC(12, 4)")

    # ── 3. Drop existing BOM tables (no data) ────────────────────────────────
    op.drop_index("ix_bom_lines_component_sku_id", table_name="bom_lines", if_exists=True)
    op.drop_index("ix_bom_lines_bom_id", table_name="bom_lines", if_exists=True)
    op.drop_table("bom_lines", if_exists=True)

    op.execute("DROP POLICY IF EXISTS boms_tenant_policy ON boms")
    op.drop_index("ix_boms_tenant_sku", table_name="boms", if_exists=True)
    op.drop_index("ix_boms_sku_id", table_name="boms", if_exists=True)
    op.drop_index("ix_boms_tenant_id", table_name="boms", if_exists=True)
    op.drop_table("boms", if_exists=True)

    # ── 4. Create new boms table ─────────────────────────────────────────────
    op.create_table(
        "boms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finished_sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("landed_cost", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("landed_cost_description", sa.String(255), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_boms_tenant_id", "boms", ["tenant_id"])
    op.create_index("ix_boms_finished_sku_id", "boms", ["finished_sku_id"])

    # RLS
    op.execute("ALTER TABLE boms ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY boms_tenant_policy ON boms "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # ── 5. Create new bom_lines table ────────────────────────────────────────
    op.create_table(
        "bom_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
    )
    op.create_index("ix_bom_lines_bom_id", "bom_lines", ["bom_id"])
    op.create_index("ix_bom_lines_component_sku_id", "bom_lines", ["component_sku_id"])

    # ── 6. Create assembly_orders table ──────────────────────────────────────
    op.create_table(
        "assembly_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bom_version", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("planned_qty", sa.Numeric(12, 4), nullable=False),
        sa.Column("produced_qty", sa.Numeric(12, 4), nullable=True),
        sa.Column("waste_qty", sa.Numeric(12, 4), nullable=True),
        sa.Column("waste_reason", sa.Text(), nullable=True),
        sa.Column("cogs_per_unit", sa.Numeric(12, 4), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_assembly_orders_tenant_id", "assembly_orders", ["tenant_id"])
    op.create_index("ix_assembly_orders_warehouse_id", "assembly_orders", ["warehouse_id"])
    op.create_index("ix_assembly_orders_status", "assembly_orders", ["status"])

    # RLS
    op.execute("ALTER TABLE assembly_orders ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY assembly_orders_tenant_policy ON assembly_orders "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS assembly_orders_tenant_policy ON assembly_orders")
    op.execute("ALTER TABLE assembly_orders DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_assembly_orders_status", table_name="assembly_orders")
    op.drop_index("ix_assembly_orders_warehouse_id", table_name="assembly_orders")
    op.drop_index("ix_assembly_orders_tenant_id", table_name="assembly_orders")
    op.drop_table("assembly_orders")

    op.drop_index("ix_bom_lines_component_sku_id", table_name="bom_lines")
    op.drop_index("ix_bom_lines_bom_id", table_name="bom_lines")
    op.drop_table("bom_lines")

    op.execute("DROP POLICY IF EXISTS boms_tenant_policy ON boms")
    op.execute("ALTER TABLE boms DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_boms_finished_sku_id", table_name="boms")
    op.drop_index("ix_boms_tenant_id", table_name="boms")
    op.drop_table("boms")

    op.execute("ALTER TABLE stock_ledger drop column IF EXISTS unit_cost_snapshot")
    # ENUM removal is complex in PG without cascading drops, usually left alone.
