"""block 8 fulfillment

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-20 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sales_orders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('customer_name', sa.String(length=255), nullable=False),
    sa.Column('order_reference', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('shipping_address', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sales_order_lines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('sales_order_id', sa.UUID(), nullable=False),
    sa.Column('sku_id', sa.UUID(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('fulfilled_qty', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('sales_order_lines')
    op.drop_table('sales_orders')
