"""NEXUS IMS — JWT auth middleware: extract Bearer token, set request.state.user."""
from typing import Callable
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import CurrentUser
from app.core.security import decode_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Extract JWT from Authorization header and populate request.state.user."""

    # Paths that don't require auth
    PUBLIC_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh", "/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.user = None
        request.state.tenant_id = None

        # Skip auth for public paths
        path = request.url.path
        if path in self.PUBLIC_PATHS or path.startswith("/api/v1/docs") or path.startswith("/api/v1/redoc") or path.startswith("/openapi"):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:].strip()
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                sub = payload.get("sub")
                tenant_id = payload.get("tenant_id")
                role = payload.get("role", "FLOOR_ASSOCIATE")
                email = payload.get("email") or "unknown"  # JWT may not have email; load from DB in /me
                if sub and tenant_id:
                    request.state.user = CurrentUser(
                        id=UUID(sub),
                        email=email,
                        tenant_id=UUID(tenant_id),
                        role=role,
                    )
                    request.state.tenant_id = tenant_id

        return await call_next(request)
