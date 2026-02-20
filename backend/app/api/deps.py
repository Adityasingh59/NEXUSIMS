"""NEXUS IMS — FastAPI dependencies (auth, DB, permissions) — Block 4."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

# ── Permission keys ─────────────────────────────────────────────────────────
# Use these string constants everywhere — no raw strings in route files.
PERM_SKUS_WRITE = "skus:write"
PERM_SKUS_READ = "skus:read"
PERM_WAREHOUSES_MANAGE = "warehouses:manage"
PERM_USERS_MANAGE = "users:manage"
PERM_TRANSACTIONS_RECEIVE = "transactions:receive"
PERM_TRANSACTIONS_PICK = "transactions:pick"
PERM_TRANSACTIONS_ADJUST = "transactions:adjust"
PERM_REPORTS_READ = "reports:read"
PERM_WORKFLOWS_WRITE = "workflows:write"
PERM_BOMS_MANAGE = "boms:manage"
PERM_COGS_READ = "cogs:read"
PERM_API_KEYS_MANAGE = "api_keys:manage"

# ── Role → permissions matrix ────────────────────────────────────────────────
_ADMIN_PERMS = {
    PERM_SKUS_WRITE, PERM_SKUS_READ,
    PERM_WAREHOUSES_MANAGE,
    PERM_USERS_MANAGE,
    PERM_TRANSACTIONS_RECEIVE, PERM_TRANSACTIONS_PICK, PERM_TRANSACTIONS_ADJUST,
    PERM_REPORTS_READ,
    PERM_WORKFLOWS_WRITE,
    PERM_BOMS_MANAGE,
    PERM_COGS_READ,
    PERM_API_KEYS_MANAGE,
}

_MANAGER_PERMS = {
    PERM_SKUS_WRITE, PERM_SKUS_READ,
    PERM_TRANSACTIONS_RECEIVE, PERM_TRANSACTIONS_PICK, PERM_TRANSACTIONS_ADJUST,
    PERM_REPORTS_READ,
    PERM_BOMS_MANAGE,
    PERM_COGS_READ,
}

_FLOOR_ASSOCIATE_PERMS = {
    PERM_SKUS_READ,
    PERM_TRANSACTIONS_RECEIVE, PERM_TRANSACTIONS_PICK,
}

PERMISSION_MATRIX: dict[str, set[str]] = {
    "ADMIN": _ADMIN_PERMS,
    "MANAGER": _MANAGER_PERMS,
    "FLOOR_ASSOCIATE": _FLOOR_ASSOCIATE_PERMS,
}


class CurrentUser:
    """User identity from JWT or API key — set on request.state by middleware."""

    def __init__(
        self,
        id: UUID,
        email: str,
        tenant_id: UUID,
        role: str,
        warehouse_scope: list[str] | None = None,
    ):
        self.id = id
        self.email = email
        self.tenant_id = tenant_id
        self.role = role
        # None = all warehouses; list of UUID strings = restricted warehouses
        self.warehouse_scope: list[str] | None = warehouse_scope

    def has_permission(self, permission: str) -> bool:
        return permission in PERMISSION_MATRIX.get(self.role, set())


async def get_current_user(request: Request) -> CurrentUser | None:
    """Extract user from request.state (populated by auth middleware)."""
    return getattr(request.state, "user", None)


async def require_auth(request: Request) -> CurrentUser:
    """Require authenticated user. Raise 401 if not logged in."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def require_permission(permission: str):
    """Dependency factory: require specific RBAC permission."""

    async def _check(user: CurrentUser = Depends(require_auth)) -> CurrentUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required. Your role: {user.role}",
            )
        return user

    return _check
