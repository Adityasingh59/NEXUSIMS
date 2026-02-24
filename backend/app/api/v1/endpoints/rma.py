"""NEXUS IMS — RMA API Endpoints."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.tenant import User
from app.services.rma_service import RMAService

router = APIRouter()


@router.post("/")
async def create_rma(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        rma = await RMAService.create_rma(
            db,
            tenant_id=current_user.tenant_id,
            warehouse_id=UUID(payload["warehouse_id"]),
            lines=payload["lines"],
            customer_name=payload.get("customer_name"),
            order_reference=payload.get("order_reference"),
            notes=payload.get("notes"),
            created_by=current_user.id,
        )
        await db.commit()
        return {"data": rma, "error": None, "meta": None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_rmas(
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    rmas, total = await RMAService.list_rmas(
        db,
        tenant_id=current_user.tenant_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "data": rmas,
        "error": None,
        "meta": {"total": total, "page": page, "page_size": page_size}
    }


@router.get("/{rma_id}")
async def get_rma(
    rma_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    rma = await RMAService.get_rma(db, current_user.tenant_id, rma_id)
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return {"data": rma, "error": None, "meta": None}


@router.post("/{rma_id}/receive")
async def receive_rma(
    rma_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        rma = await RMAService.receive_lines(
            db,
            tenant_id=current_user.tenant_id,
            rma_id=rma_id,
            receive_data=payload["lines"],
            actor_id=current_user.id,
        )
        await db.commit()
        return {"data": rma, "error": None, "meta": None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{rma_id}/status")
async def update_rma_status(
    rma_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        rma = await RMAService.update_status(
            db,
            tenant_id=current_user.tenant_id,
            rma_id=rma_id,
            status=payload["status"],
            actor_id=current_user.id,
        )
        await db.commit()
        return {"data": rma, "error": None, "meta": None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
