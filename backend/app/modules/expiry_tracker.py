"""NEXUS IMS — Expiry Tracker Module (Phase 3B)."""
import logging

from app.sdk.module import BaseModule, NexusContext
from app.sdk.manifest import (
    ModuleManifest,
    ManifestAttribute,
    ManifestPermission,
)

logger = logging.getLogger(__name__)

class ExpiryTrackerModule(BaseModule):
    """
    Module that allows automated expiry tracking of SKUs.
    Injects an `expiry_date` attribute into item_types.
    """
    
    @classmethod
    def get_manifest(cls) -> ModuleManifest:
        return ModuleManifest(
            name="Expiry Date Tracker",
            slug="expiry-tracker",
            version="1.0.0",
            description="Track expiration dates globally for perishable items.",
            author="Nexus Core Team",
            required_phase=3,
            permissions=[
                ManifestPermission(
                    resource="sku",
                    action="read",
                    reason="Needs to read SKU properties to find expired items."
                )
            ],
            attributes=[
                ManifestAttribute(
                    key="expiry_date",
                    name="Expiration Date",
                    type="date",
                    required=False,
                    description="If set, tracks the expiration date of this SKU.",
                )
            ],
            events=[]
        )

    @classmethod
    async def on_install(cls, ctx: NexusContext) -> None:
        """Called when module is installed for a tenant."""
        logger.info(f"ExpiryTrackerModule installed for tenant {ctx.tenant_id}")
        pass

    @classmethod
    async def on_uninstall(cls, ctx: NexusContext) -> None:
        """Called when module is uninstalled."""
        logger.info(f"ExpiryTrackerModule uninstalled for tenant {ctx.tenant_id}")
        pass
