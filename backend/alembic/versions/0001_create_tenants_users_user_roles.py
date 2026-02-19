"""create tenants, users, user_roles (Block 0.2 core schema)

Revision ID: 0001
Revises:
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create user_role enum
    op.execute("CREATE TYPE user_role_enum AS ENUM ('ADMIN', 'MANAGER', 'FLOOR_ASSOCIATE')")

    # tenants table
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.Enum("ADMIN", "MANAGER", "FLOOR_ASSOCIATE", name="user_role_enum", create_type=False), nullable=False, server_default="FLOOR_ASSOCIATE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_index("ix_users_tenant_email", "users", ["tenant_id", "email"], unique=True)

    # user_roles table (for future role-permission expansion; basic RBAC via users.role for now)
    op.create_table(
        "user_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)

    # Enable RLS on tenants
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenants_tenant_policy ON tenants "
        "USING (id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # Enable RLS on users
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY users_tenant_policy ON users "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # Enable RLS on user_roles
    op.execute("ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY user_roles_tenant_policy ON user_roles "
        "USING ((SELECT tenant_id FROM users WHERE users.id = user_roles.user_id) = "
        "nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_roles_tenant_policy ON user_roles")
    op.execute("ALTER TABLE user_roles DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS users_tenant_policy ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenants_tenant_policy ON tenants")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_users_tenant_email", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS user_role_enum")
