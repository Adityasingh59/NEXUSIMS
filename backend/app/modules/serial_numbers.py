"""NEXUS IMS — Serial Numbers Module (Phase 3B)."""
import uuid
import logging

from app.sdk.module import BaseModule, NexusContext
from app.sdk.manifest import (
    ModuleManifest,
    ManifestAttribute,
    ManifestPermission,
)
from app.models.tenant import UserRoleEnum

logger = logging.getLogger(__name__)

class SerialNumbersModule(BaseModule):
    """
    Module that allows serialized tracking of SKUs.
    Injects an `is_serialized` attribute into item_types.
    Provides API endpoints to register unique serials per SKU.
    """
    
    @classmethod
    def get_manifest(cls) -> ModuleManifest:
        return ModuleManifest(
            name="Unit Serialization Tracking",
            slug="serial-numbers",
            version="1.0.0",
            description="Track individual units with unique serial numbers across your warehouse.",
            author="Nexus Core Team",
            required_phase=3,
            permissions=[
                ManifestPermission(
                    resource="sku",
                    action="read",
                    reason="Needs to read SKU properties to verify serialization flag."
                ),
                ManifestPermission(
                    resource="ledger",
                    action="read",
                    reason="Needs to verify stock levels when serials are shipped."
                ),
            ],
            attributes=[
                ManifestAttribute(
                    key="is_serialized",
                    name="Is Serialized",
                    type="boolean",
                    required=False,
                    description="If true, each unit in stock must have a unique serial tracked.",
                )
            ],
            events=[]
        )

    @classmethod
    async def on_install(cls, ctx: NexusContext) -> None:
        """Called when module is installed for a tenant."""
        logger.info(f"SerialNumbersModule installed for tenant {ctx.tenant_id}")
        pass

    @classmethod
    async def on_uninstall(cls, ctx: NexusContext) -> None:
        """Called when module is uninstalled."""
        logger.info(f"SerialNumbersModule uninstalled for tenant {ctx.tenant_id}")
        # Could delete all serial_numbers for this tenant here, but we will preserve data.
        pass
