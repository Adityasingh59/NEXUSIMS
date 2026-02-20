"""NEXUS IMS — JWT + API key auth middleware: extracts credentials, sets request.state.user."""
import logging
from typing import Callable
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import CurrentUser
from app.core.security import decode_token

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Extract JWT from Authorization header (or API key from X-API-Key) and populate request.state.user."""

    PUBLIC_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/users/accept-invitation",
        "/health",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.user = None
        request.state.tenant_id = None

        path = request.url.path
        if (
            path in self.PUBLIC_PATHS
            or path.startswith("/api/v1/docs")
            or path.startswith("/api/v1/redoc")
            or path.startswith("/openapi")
        ):
            return await call_next(request)

        # ── 1. Try JWT Bearer token ─────────────────────────────────────────
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                sub = payload.get("sub")
                tenant_id = payload.get("tenant_id")
                role = payload.get("role", "FLOOR_ASSOCIATE")
                email = payload.get("email") or "unknown"
                warehouse_scope = payload.get("warehouse_scope")  # optional claim
                if sub and tenant_id:
                    request.state.user = CurrentUser(
                        id=UUID(sub),
                        email=email,
                        tenant_id=UUID(tenant_id),
                        role=role,
                        warehouse_scope=warehouse_scope,
                    )
                    request.state.tenant_id = tenant_id
            return await call_next(request)

        # ── 2. Try X-API-Key header ─────────────────────────────────────────
        raw_key = request.headers.get("X-API-Key", "").strip()
        if raw_key:
            try:
                from app.db.session import async_session_maker
                from app.services.api_key_service import APIKeyService

                async with async_session_maker() as db:
                    api_key = await APIKeyService.authenticate_by_api_key(db, raw_key)
                    if api_key:
                        await db.commit()
                        # API keys always use ADMIN role for now — can add per-key role later
                        request.state.user = CurrentUser(
                            id=api_key.created_by or api_key.id,
                            email="api-key",
                            tenant_id=api_key.tenant_id,
                            role="ADMIN",
                            warehouse_scope=None,
                        )
                        request.state.tenant_id = str(api_key.tenant_id)
            except Exception as exc:
                logger.warning("API key auth error: %s", exc)

        return await call_next(request)
