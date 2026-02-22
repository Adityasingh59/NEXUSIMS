"""NEXUS IMS — Module Marketplace models (Block 3A)."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModuleExtensionType(str, Enum):
    TRIGGER = "TRIGGER"
    ACTION = "ACTION"


class ModuleInstall(Base):
    """Tracks which modules are installed in which tenant."""
    
    __tablename__ = "module_installs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    module_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    permissions_granted: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    
    # Ensure one active installation of a module slug per tenant
    __table_args__ = (
        {"schema": "public"}
    )


class ModuleAttributeType(Base):
    """Registers new polymorphic attribute types provided by a module."""
    
    __tablename__ = "module_attribute_types"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    module_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("item_types.id", ondelete="CASCADE"), nullable=True) # Nullable if global attribute
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_def: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class ModuleWorkflowExtension(Base):
    """Registers new triggers and actions for the workflow engine provided by a module."""
    
    __tablename__ = "module_workflow_extensions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    module_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    extension_type: Mapped[str] = mapped_column(String(50), nullable=False) # TRIGGER or ACTION
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_def: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
