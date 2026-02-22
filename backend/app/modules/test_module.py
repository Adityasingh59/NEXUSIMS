"""Dummy module for testing the module service installation."""

from app.sdk.manifest import ModuleManifest, ManifestPermission, ManifestAttribute
from app.sdk.module import BaseModule, NexusContext

manifest = ModuleManifest(
    name="Test Expiry Tracker",
    slug="test-expiry",
    version="1.0.0",
    description="A test module defining an expiry date attribute.",
    author="Nexus Test",
    required_phase=3,
    permissions=[
        ManifestPermission(resource="ledger", action="write", reason="Needed to write expiry ledger events."),
        ManifestPermission(resource="sku", action="read", reason="Needed to read SKU data.")
    ],
    attributes=[
        ManifestAttribute(
            key="expiry_date",
            name="Expiry Date",
            type="date",
            required=False,
            description="The expiration date of the unit."
        )
    ]
)

class TestExpiryModule(BaseModule):
    
    @classmethod
    async def on_install(cls, ctx: NexusContext) -> None:
        # Verify context is loaded
        assert ctx.module_slug == "test-expiry"
        assert "ledger:write" in ctx.permissions
        
    @classmethod
    async def on_uninstall(cls, ctx: NexusContext) -> None:
        # Verify context is loaded
        assert ctx.module_slug == "test-expiry"

