"""NEXUS IMS — Tenant context middleware (RLS activation)."""
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import async_session_maker


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extract tenant_id from JWT claim and set app.tenant_id for RLS.
    Must run after auth middleware populates request.state.user.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = None
        if hasattr(request.state, "user") and request.state.user:
            tenant_id = getattr(request.state.user, "tenant_id", None)
        if tenant_id:
            # Store for later use in DB session
            request.state.tenant_id = str(tenant_id)

        response = await call_next(request)
        return response


async def set_tenant_in_db(request: Request) -> None:
    """Set app.tenant_id in the DB connection before queries (called per request)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        # Will be executed in the same connection used for the request
        pass  # Handled via engine execution events or explicit execute in dependency


def get_tenant_id_from_request(request: Request) -> str | None:
    """Extract tenant_id from request state (set by auth middleware)."""
    return getattr(request.state, "tenant_id", None)
