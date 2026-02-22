"""NEXUS IMS — Expiry Tracker API Endpoints (Phase 3B)."""
import uuid
from typing import Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_auth
from app.models.item_type import SKU
from app.models.module import ModuleInstall

router = APIRouter()

class ExpiredSKUResponse(BaseModel):
    id: uuid.UUID
    sku_code: str
    name: str
    expiry_date: date

    class Config:
        from_attributes = True

async def _check_module_active(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Helper to verify the tracking module is actually installed and active."""
    result = await db.execute(
        select(ModuleInstall).where(
            ModuleInstall.tenant_id == tenant_id,
            ModuleInstall.module_slug == "expiry-tracker",
            ModuleInstall.is_active == True
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The 'expiry-tracker' module is not installed or active."
        )

@router.get("/expired", response_model=list[ExpiredSKUResponse])
async def list_expired_skus(
    user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List all SKUs that have passed their expiration date."""
    await _check_module_active(db, user.tenant_id)
    
    # We query JSONB payload for expiry_date.
    # Note: In a real heavy-duty db we might want a func index on this cast.
    # We look for all SKUs where attributes->>'expiry_date' <= current_date (string comparison works for ISO dates).
    today_str = date.today().isoformat()
    
    stmt = select(SKU).where(
        SKU.tenant_id == user.tenant_id,
        SKU.attributes.op('->>')('expiry_date') <= today_str
    ).order_by(SKU.attributes.op('->>')('expiry_date').asc())

    result = await db.execute(stmt)
    skus = result.scalars().all()
    
    out = []
    for s in skus:
        exp_str = s.attributes.get('expiry_date')
        if exp_str:
            out.append({
                "id": s.id,
                "sku_code": s.sku_code,
                "name": s.name,
                "expiry_date": date.fromisoformat(exp_str)
            })
            
    return out
