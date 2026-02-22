import uuid
from typing import Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import ModuleAttributeType, ModuleInstall, ModuleWorkflowExtension
from app.sdk.manifest import ModuleManifest
from app.sdk.module import NexusContext, BaseModule


class ModuleService:
    """Manages the installation, lifecycle, and permissions of external/internal modules."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_installed_modules(self, tenant_id: uuid.UUID) -> Sequence[ModuleInstall]:
        """Fetch all installed modules for a given tenant."""
        stmt = select(ModuleInstall).where(ModuleInstall.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_module_install(self, tenant_id: uuid.UUID, module_slug: str) -> Optional[ModuleInstall]:
        """Get the module record if it's installed for the tenant."""
        stmt = select(ModuleInstall).where(
            ModuleInstall.tenant_id == tenant_id,
            ModuleInstall.module_slug == module_slug
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def install_module(
        self, 
        tenant_id: uuid.UUID, 
        manifest: ModuleManifest, 
        granted_permissions: list[str],
        module_class: type[BaseModule]
    ) -> ModuleInstall:
        """
        Installs a module into the tenant workspace.
        Creates permissions, registers schemas/triggers, and runs the module's on_install hook.
        """
        # Check if already installed
        existing = await self.get_module_install(tenant_id, manifest.slug)
        if existing:
            raise HTTPException(status_code=400, detail=f"Module {manifest.slug} is already installed.")
            
        # Validate that granted_permissions covers what the manifest actually asks for
        requested_perms = [f"{p.resource}:{p.action}" for p in manifest.permissions]
        for rp in requested_perms:
            if rp not in granted_permissions:
                raise HTTPException(status_code=403, detail=f"Missing required module permission: {rp}")

        # Create installation record
        install_record = ModuleInstall(
            tenant_id=tenant_id,
            module_slug=manifest.slug,
            version=manifest.version,
            is_active=True,
            permissions_granted=granted_permissions
        )
        self.db.add(install_record)
        
        # Register module-defined polymorphic attributes
        for attr in manifest.attributes:
            mattr = ModuleAttributeType(
                tenant_id=tenant_id,
                module_slug=manifest.slug,
                key=attr.key,
                schema_def={
                    "type": attr.type,
                    "name": attr.name,
                    "description": attr.description,
                    "required": attr.required,
                }
            )
            self.db.add(mattr)

        # Triggers / Events / Actions hookups will eventually register via ModuleWorkflowExtension
        # (This expands as Phase 3 API completes for the Event Bus)
        
        await self.db.flush()

        # Execute Module SDK Hook
        ctx = NexusContext(self.db, tenant_id, manifest.slug, granted_permissions)
        await module_class.on_install(ctx)
        
        await self.db.commit()
        await self.db.refresh(install_record)
        
        return install_record

    async def uninstall_module(
        self,
        tenant_id: uuid.UUID,
        module_slug: str,
        module_class: type[BaseModule]
    ) -> None:
        """
        Uninstalls a module from the tenant workspace.
        Executes on_uninstall hook and purges references. Core Ledger/SKU schema is unmodified.
        """
        install_record = await self.get_module_install(tenant_id, module_slug)
        if not install_record:
            raise HTTPException(status_code=404, detail="Module not found or not installed.")

        # Execute Module SDK Teardown Hook
        ctx = NexusContext(self.db, tenant_id, module_slug, install_record.permissions_granted)
        await module_class.on_uninstall(ctx)

        # De-register attributes and extensions
        attr_stmt = select(ModuleAttributeType).where(
            ModuleAttributeType.tenant_id == tenant_id,
            ModuleAttributeType.module_slug == module_slug
        )
        attrs = await self.db.execute(attr_stmt)
        for attr in attrs.scalars():
            await self.db.delete(attr)
            
        ext_stmt = select(ModuleWorkflowExtension).where(
            ModuleWorkflowExtension.tenant_id == tenant_id,
            ModuleWorkflowExtension.module_slug == module_slug
        )
        exts = await self.db.execute(ext_stmt)
        for ext in exts.scalars():
            await self.db.delete(ext)

        # Remove install record
        await self.db.delete(install_record)
        await self.db.commit()
