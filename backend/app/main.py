"""
NEXUS IMS — FastAPI ASGI Entry Point
"""
from contextlib import asynccontextmanager
# Trigger reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth_middleware import JWTAuthMiddleware
from app.core.rate_limit import RateLimitMiddleware

settings = get_settings()
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — Redis pool, startup/shutdown."""
    # Startup: init Redis connection pool (used in lifespan or dependency)
    yield
    # Shutdown: close connections
    pass


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
    """Health check for load balancers and Docker."""
    return {"status": "ok", "service": "nexus-ims"}
