"""NEXUS IMS — AuditService — Block 4."""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import AuditLog

logger = logging.getLogger(__name__)

# ── Audit action constants ────────────────────────────────────────────────────
ACTION_USER_INVITED = "user.invited"
ACTION_USER_ROLE_UPDATED = "user.role_updated"
ACTION_USER_DEACTIVATED = "user.deactivated"
ACTION_API_KEY_CREATED = "api_key.created"
ACTION_API_KEY_REVOKED = "api_key.revoked"
ACTION_SKU_ARCHIVED = "sku.archived"
ACTION_WAREHOUSE_CREATED = "warehouse.created"
ACTION_TRANSFER_CREATED = "transfer.created"
ACTION_TRANSFER_RECEIVED = "transfer.received"
ACTION_TRANSFER_CANCELLED = "transfer.cancelled"


async def log_audit(
    db: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    payload: dict | None = None,
) -> None:
    """Write an audit log entry. Call this from services/endpoints after the main action."""
    try:
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
        )
        db.add(entry)
        # We don't flush here — the surrounding transaction flush will pick it up.
        # The audit log row is committed atomically with the main action.
    except Exception as exc:
        # Never allow audit failure to break the main request
        logger.error("Audit log write failed: %s", exc, exc_info=True)
