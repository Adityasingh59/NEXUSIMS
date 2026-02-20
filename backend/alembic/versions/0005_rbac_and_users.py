"""RBAC, invitation_tokens, api_keys, audit_log — Block 4

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add warehouse_scope to users ────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "warehouse_scope",
            JSONB,
            nullable=True,
            comment="NULL = all warehouses (Admin). List of warehouse UUID strings for scoped roles.",
        ),
    )

    # ── 2. invitation_tokens table ─────────────────────────────────────────
    op.create_table(
        "invitation_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("warehouse_scope", JSONB, nullable=True),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_invitation_tokens_tenant_id", "invitation_tokens", ["tenant_id"])
    op.create_index("ix_invitation_tokens_email", "invitation_tokens", ["email"])

    # RLS
    op.execute("ALTER TABLE invitation_tokens ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY invitation_tokens_tenant_policy ON invitation_tokens "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # ── 3. api_keys table ──────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False, comment="First 8 chars of raw key for identification"),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True, comment="bcrypt hash of raw key"),
        sa.Column("scopes", JSONB, nullable=False, server_default="[]"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    # RLS
    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_keys_tenant_policy ON api_keys "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )

    # ── 4. audit_log table ─────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # RLS
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_log_tenant_policy ON audit_log "
        "USING (tenant_id = nullif(trim(current_setting('app.tenant_id', true)), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_log_tenant_policy ON audit_log")
    op.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.execute("DROP POLICY IF EXISTS api_keys_tenant_policy ON api_keys")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.execute("DROP POLICY IF EXISTS invitation_tokens_tenant_policy ON invitation_tokens")
    op.execute("ALTER TABLE invitation_tokens DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_invitation_tokens_email", table_name="invitation_tokens")
    op.drop_index("ix_invitation_tokens_tenant_id", table_name="invitation_tokens")
    op.drop_table("invitation_tokens")

    op.drop_column("users", "warehouse_scope")
