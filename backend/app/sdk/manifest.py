from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManifestPermission(BaseModel):
    """A permission required by the module."""
    resource: str = Field(..., description="The resource namespace, e.g., 'ledger', 'sku'")
    action: str = Field(..., description="The action required, e.g., 'read', 'write'")
    reason: str = Field(..., description="Human-readable reason for needing this permission.")


class ManifestAttribute(BaseModel):
    """A polymorphic attribute schema definition to be injected into the system."""
    key: str = Field(..., description="The dictionary key for this attribute, e.g. 'expiry_date'")
    name: str = Field(..., description="Human-readable name.")
    type: str = Field(..., description="Type of the field: string, integer, date, boolean, etc.")
    required: bool = Field(default=False)
    description: str | None = None
    target_item_type_codes: list[str] = Field(default_factory=list, description="Optional. Apply globally if empty.")


class ManifestEvent(BaseModel):
    """An event subtype the module can publish to the ledger."""
    event_type: str = Field(..., description="The ledger event_type string (e.g. EXPIRY_QUARANTINE). Must be module-prefixed.")
    description: str = Field(..., description="What this event represents.")


class ModuleManifest(BaseModel):
    """Represents a nexus-module.json file."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., description="Human-readable name of the module, e.g. 'Expiry Date Tracker'")
    slug: str = Field(..., description="Unique slug for the module", pattern=r"^[a-z0-9-]+$")
    version: str = Field(..., description="SemVer version string")
    description: str = Field(..., description="Short description of the module")
    author: str = Field(..., description="Author name or organization")
    
    required_phase: int = Field(default=1, description="Minimum Nexus phase required (1, 2, or 3)")
    
    permissions: list[ManifestPermission] = Field(default_factory=list)
    attributes: list[ManifestAttribute] = Field(default_factory=list)
    events: list[ManifestEvent] = Field(default_factory=list)

    @classmethod
    def from_file(cls, filepath: str) -> "ModuleManifest":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())
