"""NEXUS IMS — API Response Helpers (Block 10)."""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard unified response envelope."""
    data: T | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


def success_response(data: Any, meta: dict | None = None) -> dict:
    return {"data": data, "error": None, "meta": meta}


def error_response(code: str, message: str, field_errors: list[dict] | None = None, meta: dict | None = None) -> dict:
    return {
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors or []
        },
        "meta": meta
    }
