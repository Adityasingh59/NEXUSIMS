"""create warehouses and stock_ledger (Block 2.1)

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, NUMERIC

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # event_type enum for stock_ledger (idempotent)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE stock_event_type AS ENUM (
                'RECEIVE', 'PICK', 'ADJUST', 'RETURN',
                'TRANSFER_OUT', 'TRANSFER_IN', 'COUNT_CORRECT', 'WRITE_OFF'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # warehouses table (minimal for Block 2; Block 3 adds locations, etc.)
    op.create_table(
        "warehouses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"], unique=False)
    op.create_unique_constraint("uq_warehouses_tenant_code", "warehouses", ["tenant_id", "code"])

    # stock_ledger table (append-only, no updated_at)
    op.create_table(
        "stock_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), nullable=True),  # FK added in Block 3
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("quantity_delta", NUMERIC(18, 4), nullable=False),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_stock_ledger_tenant_sku_warehouse", "stock_ledger", ["tenant_id", "sku_id", "warehouse_id"], unique=False)
    op.create_index("ix_stock_ledger_reference_id", "stock_ledger", ["reference_id"], unique=False)
    op.create_index("ix_stock_ledger_created_at", "stock_ledger", ["created_at"], unique=False)
    op.create_index("ix_stock_ledger_warehouse_id", "stock_ledger", ["warehouse_id"], unique=False)

    # Trigger: prevent negative stock (raises before INSERT if balance would go below 0)
    op.execute("""
        CREATE OR REPLACE FUNCTION check_negative_stock()
        RETURNS TRIGGER AS $$
        DECLARE
            new_balance NUMERIC;
        BEGIN
            SELECT COALESCE(SUM(quantity_delta), 0) + NEW.quantity_delta
            INTO new_balance
            FROM stock_ledger
            WHERE sku_id = NEW.sku_id AND warehouse_id = NEW.warehouse_id;
            IF new_balance < 0 THEN
                RAISE EXCEPTION 'Negative stock not allowed: sku_id=%, warehouse_id=%, balance would be %',
                    NEW.sku_id, NEW.warehouse_id, new_balance;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_check_negative_stock
        BEFORE INSERT ON stock_ledger
        FOR EACH ROW EXECUTE FUNCTION check_negative_stock();
    """)

    # REVOKE UPDATE, DELETE on stock_ledger from nexus_app (INSERT-only)
    op.execute("REVOKE UPDATE ON stock_ledger FROM nexus_app")
    op.execute("REVOKE DELETE ON stock_ledger FROM nexus_app")
    op.execute("GRANT INSERT, SELECT ON stock_ledger TO nexus_app")

    # RLS on warehouses and stock_ledger
    op.execute("ALTER TABLE warehouses ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY warehouses_tenant_policy ON warehouses "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    op.execute("ALTER TABLE stock_ledger ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY stock_ledger_tenant_policy ON stock_ledger "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS stock_ledger_tenant_policy ON stock_ledger")
    op.execute("ALTER TABLE stock_ledger DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS warehouses_tenant_policy ON warehouses")
    op.execute("ALTER TABLE warehouses DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS trg_check_negative_stock ON stock_ledger")
    op.execute("DROP FUNCTION IF EXISTS check_negative_stock()")

    op.drop_index("ix_stock_ledger_warehouse_id", table_name="stock_ledger")
    op.drop_index("ix_stock_ledger_created_at", table_name="stock_ledger")
    op.drop_index("ix_stock_ledger_reference_id", table_name="stock_ledger")
    op.drop_index("ix_stock_ledger_tenant_sku_warehouse", table_name="stock_ledger")
    op.drop_table("stock_ledger")

    op.drop_constraint("uq_warehouses_tenant_code", "warehouses", type_="unique")
    op.drop_index("ix_warehouses_tenant_id", table_name="warehouses")
    op.drop_table("warehouses")

    op.execute("DROP TYPE IF EXISTS stock_event_type")
