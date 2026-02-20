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
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email/password. Returns access token. Sets refresh token in httpOnly cookie."""
    try:
        # Use SECURITY DEFINER function to bypass RLS for login
        # RLS prevents nexus_app from seeing users until tenant_id is set, 
        # but we need to find the user first to get the tenant_id.
        result = await db.execute(
            text("SELECT * FROM get_user_for_login(:email)").bindparams(email=form_data.username)
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            
        # Manually map row to User object or just use fields directly
        # Row has fields: id, tenant_id, email, hashed_password, role, etc.
        # We need: id, tenant_id, email, hashed_password, role.
        
        # Verify password
        if not verify_password(form_data.password, row.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        tenant_id = str(row.tenant_id)
        access_token = create_access_token(
            subject=str(row.id),
            tenant_id=tenant_id,
            email=row.email,
            extra_claims={"role": row.role},
        )
        refresh_token = create_refresh_token(subject=str(row.id))

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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
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
