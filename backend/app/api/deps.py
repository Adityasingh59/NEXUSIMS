"""NEXUS IMS — FastAPI dependencies (auth, DB, permissions)."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import User

DbSession = Annotated[AsyncSession, Depends(get_db)]


class CurrentUser:
    """Minimal user info from JWT — populated by auth middleware."""

    def __init__(self, id: UUID, email: str, tenant_id: UUID, role: str):
        self.id = id
        self.email = email
        self.tenant_id = tenant_id
        self.role = role


async def get_current_user(request: Request) -> CurrentUser | None:
    """Extract user from request.state (populated by auth middleware)."""
    return getattr(request.state, "user", None)


async def require_auth(request: Request) -> CurrentUser:
    """Require authenticated user. Raise 401 if not logged in."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_permission(permission: str):
    """Dependency factory: require specific permission (Block 4). Placeholder for now."""

    async def _check(request: Request, user: CurrentUser = Depends(require_auth)) -> CurrentUser:
        # Block 4: check user.role against permission matrix
        return user

    return _check
