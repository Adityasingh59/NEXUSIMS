"""
NEXUS IMS — Auth endpoints (Block 0.3)
POST /auth/login, /auth/refresh, /auth/logout, GET /auth/me
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_auth
from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.tenant import User

router = APIRouter()
settings = get_settings()


# =========================
# Schemas
# =========================

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


# =========================
# LOGIN
# =========================

@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:

    # Disable RLS temporarily for login lookup
    await db.execute(text("SELECT set_config('app.tenant_id', '', true)"))

    result = await db.execute(
        select(User).where(
            User.email == form_data.username,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

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


# =========================
# REFRESH
# =========================

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:

    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(User).where(
            User.id == UUID(user_id),
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

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


# =========================
# LOGOUT
# =========================

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


# =========================
# ME
# =========================

@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(require_auth)):

    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=None,
        role=user.role,
        tenant_id=user.tenant_id,
    )
