"""NEXUS IMS — APIKeyService — Block 4."""
import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import APIKey

logger = logging.getLogger(__name__)

_KEY_PREFIX_LEN = 8  # first N chars stored for identification


def _generate_raw_key() -> str:
    """Generate a cryptographically secure API key."""
    return "nxs_" + secrets.token_urlsafe(40)


def _hash_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=10)).decode()


def _verify_key(raw_key: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_key.encode(), key_hash.encode())
    except Exception:
        return False


class APIKeyService:
    """API key creation, listing, revocation, and authentication."""

    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        tenant_id: UUID,
        name: str,
        scopes: list[str],
        created_by: UUID,
    ) -> tuple[APIKey, str]:
        """Create an API key. Returns (APIKey record, raw_key). Raw key shown ONCE."""
        raw_key = _generate_raw_key()
        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:_KEY_PREFIX_LEN + 4]  # "nxs_" + first 8 chars

        api_key = APIKey(
            tenant_id=tenant_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
            is_active=True,
            created_by=created_by,
        )
        db.add(api_key)
        await db.flush()
        await db.refresh(api_key)
        return api_key, raw_key

    @staticmethod
    async def list_api_keys(db: AsyncSession, tenant_id: UUID) -> list[APIKey]:
        result = await db.execute(
            select(APIKey)
            .where(APIKey.tenant_id == tenant_id, APIKey.is_active.is_(True))
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_api_key(db: AsyncSession, key_id: UUID, tenant_id: UUID) -> APIKey | None:
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.tenant_id == tenant_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        api_key.is_active = False
        await db.flush()
        await db.refresh(api_key)
        return api_key

    @staticmethod
    async def authenticate_by_api_key(
        db: AsyncSession,
        raw_key: str,
    ) -> APIKey | None:
        """Find active key matching raw_key. Updates last_used_at on hit."""
        if not raw_key or len(raw_key) < 12:
            return None

        prefix = raw_key[:_KEY_PREFIX_LEN + 4]
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_prefix == prefix,
                APIKey.is_active.is_(True),
            )
        )
        candidates = list(result.scalars().all())

        for api_key in candidates:
            if _verify_key(raw_key, api_key.key_hash):
                api_key.last_used_at = datetime.now(timezone.utc)
                await db.flush()
                return api_key

        return None
