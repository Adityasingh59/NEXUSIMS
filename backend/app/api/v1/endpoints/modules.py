import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_auth, require_permission, PERM_MODULES_MANAGE
from app.models.tenant import Tenant, UserRoleEnum
from app.sdk.manifest import ModuleManifest
from app.sdk.module import BaseModule, NexusContext
from app.services.module_service import ModuleService
from app.schemas.module import ModuleInstallResponse

router = APIRouter()


class InstallModuleRequest(BaseModel):
    manifest: ModuleManifest
    granted_permissions: list[str]
    # For testing/sandbox Phase 3A: we use a string to dynamically load a local module class
    # In production Phase 3B/C this will download a secure bundle.
    module_class_path: str 


@router.get("/", response_model=list[ModuleInstallResponse])
async def list_installed_modules(
    user: CurrentUser = Depends(require_permission(PERM_MODULES_MANAGE)),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List all modules installed in the current tenant."""
    service = ModuleService(db)
    installs = await service.list_installed_modules(user.tenant_id)
    return installs


@router.post("/install", response_model=ModuleInstallResponse)
async def install_module(
    req: InstallModuleRequest,
    user: CurrentUser = Depends(require_permission(PERM_MODULES_MANAGE)),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Installs a module, registers its manifest extensions, and executes the on_install hook. (Admin Only)"""
    service = ModuleService(db)
    
    # In Phase 3A we dynamically load the class specified for testing.
    # We constrain this lookup to app.modules to prevent arbitrary code execution
    if not req.module_class_path.startswith("app.modules."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="For safety, Phase 3A only allows installing local python modules under 'app.modules.'"
        )
        
    try:
        import importlib
        module_path, class_name = req.module_class_path.rsplit('.', 1)
        mod = importlib.import_module(module_path)
        module_class = getattr(mod, class_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load module class: {str(e)}")

    if not issubclass(module_class, BaseModule):
        raise HTTPException(status_code=400, detail="Module class must extend BaseModule.")

    installed = await service.install_module(
        tenant_id=user.tenant_id,
        manifest=req.manifest,
        granted_permissions=req.granted_permissions,
        module_class=module_class
    )
    return installed


@router.post("/{module_slug}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_module(
    module_slug: str,
    module_class_path: str, # passed in body/query to know which teardown hook to call
    user: CurrentUser = Depends(require_permission(PERM_MODULES_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Uninstalls a module and cleans up its custom schemas and triggers. (Admin Only)"""
    service = ModuleService(db)

    try:
        import importlib
        module_path, class_name = module_class_path.rsplit('.', 1)
        mod = importlib.import_module(module_path)
        module_class = getattr(mod, class_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load module class: {str(e)}")

    await service.uninstall_module(
        tenant_id=user.tenant_id,
        module_slug=module_slug,
        module_class=module_class
    )
