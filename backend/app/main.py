"""
NEXUS IMS — FastAPI ASGI Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth_middleware import JWTAuthMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.config import get_settings

settings = get_settings()
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — verify Redis on startup."""
    from app.core.redis import get_redis
    try:
        r = await get_redis()
        await r.ping()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Redis not reachable at startup: %s", exc)
    yield


app = FastAPI(
    title="NEXUS IMS",
    description="Rigid Accuracy. Infinite Flexibility. Inventory Management System",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# WebSocket scanner (outside /api/v1 — WS doesn't use HTTP middleware)
from app.api.v1.endpoints.scanner import router as ws_scanner_router
app.include_router(ws_scanner_router)


@app.get("/health")
async def health():
    """Health check — verifies API, DB, and Redis connectivity."""
    from app.db.session import async_session_maker
    from sqlalchemy import text

    status = {"api": "ok", "db": "ok", "redis": "ok"}
    http_status = 200

    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
    except Exception as exc:
        status["db"] = f"error: {exc}"
        http_status = 503

    try:
        from app.core.redis import get_redis
        r = await get_redis()
        await r.ping()
    except Exception as exc:
        status["redis"] = f"error: {exc}"
        http_status = 503

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=http_status, content={"status": status, "service": "nexus-ims"})
