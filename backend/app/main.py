"""
NEXUS IMS — FastAPI ASGI Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.auth_middleware import JWTAuthMiddleware

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

app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check for load balancers and Docker."""
    return {"status": "ok", "service": "nexus-ims"}
