"""
NEXUS IMS — Auth endpoints (Block 0.3)
POST /auth/login, /auth/refresh, /auth/logout, GET /auth/me
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_auth, CurrentUser
from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.tenant import User

router = APIRouter()
settings = get_settings()


# --- Schemas ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID | None = None  # Optional: for multi-tenant login


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    tenant_id: UUID


# --- Endpoints ---
@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: DbSession,
) -> TokenResponse:
    """Authenticate with email/password. Returns access token. Sets refresh token in httpOnly cookie."""
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    tenant_id = str(user.tenant_id)
    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=tenant_id,
        email=user.email,
        extra_claims={"role": user.role},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_TTL_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
) -> TokenResponse:
    """Exchange refresh token (from cookie) for new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == UUID(user_id), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    tenant_id = str(user.tenant_id)
    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=tenant_id,
        email=user.email,
        extra_claims={"role": user.role},
    )
    new_refresh = create_refresh_token(subject=str(user.id))

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_TTL_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear refresh token cookie."""
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(require_auth)) -> MeResponse:
    """Return current user info from JWT."""
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=None,  # Populated from DB if needed
        role=user.role,
        tenant_id=user.tenant_id,
    )
