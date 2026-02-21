"""NEXUS IMS — Rate Limiting (Block 10)."""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import get_redis

# Rate limits: 1000 per min for users, 500 per min for API keys
LIMITS = {
    "auth": 1000,
    "api_key": 500,
    "default": 100  # Fallback for unauthenticated
}
WINDOW = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        r = await get_redis()
        
        # Identify caller type
        caller_id = request.client.host if request.client else "unknown"
        limit_type = "default"
        
        # Simple extraction for demo (production would parse tokens properly before middleware or use Depends)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            caller_id = auth_header.split(" ")[1][:20] # truncate
            limit_type = "auth"
        elif "X-API-Key" in request.headers:
            caller_id = request.headers.get("X-API-Key")[:20]
            limit_type = "api_key"

        key = f"rl:{limit_type}:{caller_id}"
        
        # Redis Token Bucket / Fixed Window approach
        current = await r.get(key)
        if current is None:
            await r.setex(key, WINDOW, 1)
            count = 1
        else:
            count = int(current) + 1
            if count > LIMITS[limit_type]:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={
                        "data": None,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please slow down."
                        },
                        "meta": {
                            "limit": LIMITS[limit_type],
                            "remaining": 0
                        }
                    },
                    headers={"Retry-After": str(WINDOW)}
                )
            await r.incr(key)

        response = await call_next(request)
        
        # Add Rate Limit Headers
        response.headers["X-RateLimit-Limit"] = str(LIMITS[limit_type])
        response.headers["X-RateLimit-Remaining"] = str(max(0, LIMITS[limit_type] - count))
        
        # Approximate reset time
        ttl = await r.ttl(key)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + (ttl if ttl > 0 else WINDOW))
        
        return response
