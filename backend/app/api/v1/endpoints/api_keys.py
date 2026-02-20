"""NEXUS IMS — API Keys endpoints (Block 4)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_db,
    require_permission,
    PERM_API_KEYS_MANAGE,
)
from app.services.api_key_service import APIKeyService
from app.services.audit_service import (
    ACTION_API_KEY_CREATED,
    ACTION_API_KEY_REVOKED,
)

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: str | None
    created_at: str

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_API_KEYS_MANAGE)),
) -> dict:
    """Generate a new API key. Raw key is returned ONCE and cannot be retrieved again."""
    api_key, raw_key = await APIKeyService.create_api_key(
        db,
        tenant_id=actor.tenant_id,
        name=body.name,
        scopes=body.scopes,
        created_by=actor.id,
    )
    await log_audit(
        db, actor.tenant_id, actor.id,
        ACTION_API_KEY_CREATED,
        target_type="api_key",
        target_id=api_key.id,
        payload={"name": body.name},
    )
    await db.commit()
    return {
        "data": {
            "id": str(api_key.id),
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "raw_key": raw_key,  # Shown ONCE — store securely!
            "scopes": api_key.scopes,
        },
        "error": None,
        "meta": {"warning": "Store this key securely. It will not be shown again."},
    }


@router.get("", response_model=dict)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_API_KEYS_MANAGE)),
) -> dict:
    """List all active API keys for this tenant. Raw keys are never returned."""
    keys = await APIKeyService.list_api_keys(db, actor.tenant_id)
    return {
        "data": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ],
        "error": None,
        "meta": {"total_count": len(keys)},
    }


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_API_KEYS_MANAGE)),
) -> dict:
    """Revoke an API key. Immediate effect — key will no longer authenticate."""
    api_key = await APIKeyService.revoke_api_key(db, key_id, actor.tenant_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await log_audit(
        db, actor.tenant_id, actor.id,
        ACTION_API_KEY_REVOKED,
        target_type="api_key",
        target_id=key_id,
    )
    await db.commit()
    return {"data": {"id": str(key_id), "revoked": True}, "error": None, "meta": {}}
