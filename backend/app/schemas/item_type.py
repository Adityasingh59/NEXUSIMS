"""NEXUS IMS — Item type schemas (Block 1.3)."""
from uuid import UUID

from pydantic import BaseModel, Field


class AttributeFieldSchema(BaseModel):
    """Single field in attribute_schema."""

    name: str
    type: str = "text"  # text | number | date | boolean | enum
    required: bool = False
    options: list[str] | None = None


class ItemTypeCreate(BaseModel):
    name: str
    code: str
    attribute_schema: list[dict] = Field(default_factory=list)


class ItemTypeUpdate(BaseModel):
    name: str | None = None
    attribute_schema: list[dict] | None = None


class ItemTypeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    attribute_schema: list[dict]
    version: int
    is_archived: bool

    model_config = {"from_attributes": True}
