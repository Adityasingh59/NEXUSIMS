"""NEXUS IMS — Users endpoints (Block 4)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_db,
    require_auth,
    require_permission,
    PERM_USERS_MANAGE,
)
from app.services.audit_service import (
    ACTION_USER_DEACTIVATED,
    ACTION_USER_INVITED,
    ACTION_USER_ROLE_UPDATED,
    log_audit,
)
from app.services.user_service import UserService

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: EmailStr
    role: str  # ADMIN | MANAGER | FLOOR_ASSOCIATE
    warehouse_scope: list[str] | None = None  # list of warehouse UUID strings


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str
    full_name: str | None = None


class UpdateRoleRequest(BaseModel):
    role: str
    warehouse_scope: list[str] | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    warehouse_scope: list[str] | None
    is_active: bool

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_USERS_MANAGE)),
) -> dict:
    """Invite a new user to this tenant. Token logged to console (email stub)."""
    valid_roles = {"ADMIN", "MANAGER", "FLOOR_ASSOCIATE"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {valid_roles}")

    raw_token = await UserService.invite_user(
        db,
        tenant_id=actor.tenant_id,
        email=body.email,
        role=body.role,
        invited_by=actor.id,
        warehouse_scope=body.warehouse_scope,
    )
    await log_audit(
        db, actor.tenant_id, actor.id,
        ACTION_USER_INVITED,
        target_type="user",
        payload={"email": body.email, "role": body.role},
    )
    await db.commit()
    return {
        "data": {
            "message": f"Invitation sent to {body.email}",
            "dev_token": raw_token,  # DEVELOPMENT ONLY — remove when email is wired
        },
        "error": None,
        "meta": {},
    }


@router.post("/accept-invitation", status_code=status.HTTP_201_CREATED)
async def accept_invitation(body: AcceptInvitationRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Accept an invitation and set password. Creates the user account."""
    try:
        user = await UserService.accept_invitation(
            db, raw_token=body.token, password=body.password, full_name=body.full_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "data": UserResponse.model_validate(user).model_dump(),
        "error": None,
        "meta": {},
    }


@router.get("", response_model=dict)
async def list_users(
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = False,
    actor: CurrentUser = Depends(require_permission(PERM_USERS_MANAGE)),
) -> dict:
    """List all users in the tenant. Admin only."""
    users = await UserService.list_users(db, actor.tenant_id, include_inactive=include_inactive)
    return {
        "data": [UserResponse.model_validate(u).model_dump() for u in users],
        "error": None,
        "meta": {"total_count": len(users)},
    }


@router.put("/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: UUID,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_USERS_MANAGE)),
) -> dict:
    """Update a user's role and warehouse scope. Admin only."""
    valid_roles = {"ADMIN", "MANAGER", "FLOOR_ASSOCIATE"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {valid_roles}")

    user = await UserService.update_user_role(
        db, user_id, actor.tenant_id, role=body.role, warehouse_scope=body.warehouse_scope
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await log_audit(
        db, actor.tenant_id, actor.id,
        ACTION_USER_ROLE_UPDATED,
        target_type="user",
        target_id=user_id,
        payload={"new_role": body.role},
    )
    await db.commit()
    return {"data": UserResponse.model_validate(user).model_dump(), "error": None, "meta": {}}


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: CurrentUser = Depends(require_permission(PERM_USERS_MANAGE)),
) -> dict:
    """Soft-deactivate a user. Admin only."""
    if actor.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user = await UserService.deactivate_user(db, user_id, actor.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await log_audit(
        db, actor.tenant_id, actor.id,
        ACTION_USER_DEACTIVATED,
        target_type="user",
        target_id=user_id,
    )
    await db.commit()
    return {"data": {"id": str(user_id), "is_active": False}, "error": None, "meta": {}}
