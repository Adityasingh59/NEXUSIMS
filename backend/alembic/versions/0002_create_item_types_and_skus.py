"""create item_types and skus (Block 1.1)

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # item_types table
    op.create_table(
        "item_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("attribute_schema", JSONB, nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_item_types_tenant_id", "item_types", ["tenant_id"], unique=False)
    op.create_unique_constraint("uq_item_types_tenant_code", "item_types", ["tenant_id", "code"])

    # skus table
    op.create_table(
        "skus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("item_type_id", UUID(as_uuid=True), sa.ForeignKey("item_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attributes", JSONB, nullable=False, server_default="{}"),
        sa.Column("reorder_point", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_skus_tenant_id", "skus", ["tenant_id"], unique=False)
    op.create_index("ix_skus_item_type_id", "skus", ["item_type_id"], unique=False)
    op.create_unique_constraint("uq_skus_tenant_code", "skus", ["tenant_id", "sku_code"])
    op.create_index("idx_skus_attributes", "skus", ["attributes"], unique=False, postgresql_using="gin")

    # RLS
    op.execute("ALTER TABLE item_types ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY item_types_tenant_policy ON item_types "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    op.execute("ALTER TABLE skus ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY skus_tenant_policy ON skus "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS skus_tenant_policy ON skus")
    op.execute("ALTER TABLE skus DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS item_types_tenant_policy ON item_types")
    op.execute("ALTER TABLE item_types DISABLE ROW LEVEL SECURITY")

    op.drop_index("idx_skus_attributes", table_name="skus")
    op.drop_constraint("uq_skus_tenant_code", "skus", type_="unique")
    op.drop_index("ix_skus_item_type_id", table_name="skus")
    op.drop_index("ix_skus_tenant_id", table_name="skus")
    op.drop_table("skus")
    op.drop_constraint("uq_item_types_tenant_code", "item_types", type_="unique")
    op.drop_index("ix_item_types_tenant_id", table_name="item_types")
    op.drop_table("item_types")
