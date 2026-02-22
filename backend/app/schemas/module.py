from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict


class ModuleInstallResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    module_slug: str
    version: str
    is_active: bool
    permissions_granted: list[str]
    installed_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
