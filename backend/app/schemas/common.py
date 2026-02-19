"""NEXUS IMS — Common response envelope (Block 1.3)."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    """Pagination and metadata."""

    page: int = 1
    page_size: int = 50
    total_count: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard response envelope: {data, error, meta}."""

    data: T | None = None
    error: str | None = None
    meta: Meta | None = None
