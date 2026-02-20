"""NEXUS IMS — UserService: invitation, user management — Block 4."""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import InvitationToken
from app.models.tenant import User

logger = logging.getLogger(__name__)


class UserService:
    """User management: invitation flow, role changes, deactivation."""

    INVITATION_TTL_HOURS = 24

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """SHA-256 hash for invitation token storage (not bcrypt — tokens are long/random)."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @staticmethod
    async def invite_user(
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        role: str,
        invited_by: UUID,
        warehouse_scope: list[str] | None = None,
    ) -> str:
        """Create an invitation token and return the raw token.
        
        In production: email the token URL. For now, log it.
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = UserService._hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=UserService.INVITATION_TTL_HOURS)

        invite = InvitationToken(
            tenant_id=tenant_id,
            email=email,
            role=role,
            warehouse_scope=warehouse_scope,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=invited_by,
        )
        db.add(invite)
        await db.flush()

        # Log token for development — replace with SendGrid call in production
        logger.warning(
            "INVITATION TOKEN [DEVELOPMENT ONLY] — email=%s token=%s "
            "URL=http://localhost:5173/accept-invitation?token=%s",
            email, raw_token, raw_token,
        )
        return raw_token

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        raw_token: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Validate token, create user, mark token accepted."""
        from app.core.security import get_password_hash as hash_password

        token_hash = UserService._hash_token(raw_token)
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(InvitationToken).where(
                InvitationToken.token_hash == token_hash,
                InvitationToken.accepted_at.is_(None),
                InvitationToken.expires_at > now,
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise ValueError("Invitation token is invalid or expired")

        # Check if user with this email already exists in the tenant
        existing = await db.execute(
            select(User).where(User.tenant_id == invite.tenant_id, User.email == invite.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("A user with this email already exists")

        user = User(
            tenant_id=invite.tenant_id,
            email=invite.email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=invite.role,
            warehouse_scope=invite.warehouse_scope,
            is_active=True,
        )
        db.add(user)

        invite.accepted_at = now
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        tenant_id: UUID,
        include_inactive: bool = False,
    ) -> list[User]:
        q = select(User).where(User.tenant_id == tenant_id)
        if not include_inactive:
            q = q.where(User.is_active.is_(True))
        q = q.order_by(User.created_at.desc())
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_user(db: AsyncSession, user_id: UUID, tenant_id: UUID) -> User | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_role(
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
        warehouse_scope: list[str] | None = None,
    ) -> User | None:
        user = await UserService.get_user(db, user_id, tenant_id)
        if not user:
            return None
        user.role = role
        user.warehouse_scope = warehouse_scope
        user.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: UUID, tenant_id: UUID) -> User | None:
        user = await UserService.get_user(db, user_id, tenant_id)
        if not user:
            return None
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(user)
        return user
