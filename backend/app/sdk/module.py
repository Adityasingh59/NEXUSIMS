import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class PermissionDeniedError(Exception):
    """Raised when a module attempts an action without the required permission."""
    pass


class NexusContext:
    """
    Sandboxed execution context passed to modules.
    Modules use this to interact with Nexus services safely.
    It enforces tenant isolation and module-specific permissions.
    """
    
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, module_slug: str, permissions: list[str]):
        self._db = db
        self.tenant_id = tenant_id
        self.module_slug = module_slug
        self.permissions = permissions
        
        # Initialize restricted service facades (to be built out as needed)
        self.ledger = _LedgerFacade(self)
        self.ledger = _LedgerFacade(self)
        self.skus = _SKUFacade(self)

    @property
    def db_session(self) -> AsyncSession:
        """Grants modules access to the underlying database session."""
        return self._db

    def require_permission(self, permission: str):
        """Checks if the module has the required permission string (e.g., 'ledger:write')."""
        if permission not in self.permissions:
            raise PermissionDeniedError(
                f"Module '{self.module_slug}' lacks the required permission: {permission}"
            )


class _LedgerFacade:
    """Restricted ledger methods for modules."""
    
    def __init__(self, ctx: NexusContext):
        self.ctx = ctx
        
    async def record_event(self, event_type: str, sku_id: uuid.UUID, quantity_delta: int, **kwargs) -> Any:
        self.ctx.require_permission("ledger:write")
        # Actual ledger service call goes here, with tenant_id isolation enforced
        # For now, this is a stub for the architecture.
        # In a real implementation this would import and call LedgerService
        pass


class _SKUFacade:
    """Restricted SKU methods for modules."""
    
    def __init__(self, ctx: NexusContext):
        self.ctx = ctx
        
    async def get_sku(self, sku_id: uuid.UUID) -> dict:
        self.ctx.require_permission("sku:read")
        # Fetch SKU and return as dict, enforcing tenant_id isolation
        pass


class BaseModule:
    """
    Base class that all Nexus internal and external modules must extend.
    Provides lifecycle hooks and event handlers.
    """
    
    @classmethod
    async def on_install(cls, ctx: NexusContext) -> None:
        """
        Called when the module is installed into a tenant.
        Use this to run migrations, set up default configurations, etc.
        """
        pass
        
    @classmethod
    async def on_uninstall(cls, ctx: NexusContext) -> None:
        """
        Called when the module is uninstalled.
        Use this to clean up module-specific data. Core schema data is preserved.
        """
        pass

