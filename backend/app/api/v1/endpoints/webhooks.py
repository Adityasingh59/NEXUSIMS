"""NEXUS IMS — Webhooks API (Block 10)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.tenant import User
from app.models.webhook import Webhook, WebhookDelivery

router = APIRouter()


@router.get("/")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List webhooks for the tenant."""
    stmt = select(Webhook).where(Webhook.tenant_id == current_user.tenant_id).order_by(Webhook.created_at.desc())
    result = await db.execute(stmt)
    webhooks = result.scalars().all()

    return {
        "data": webhooks,
        "error": None,
        "meta": {"count": len(webhooks)}
    }


@router.post("/")
async def create_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new webhook."""
    url = payload.get("url")
    secret = payload.get("secret")
    events = payload.get("events", [])

    if not url or not secret:
        raise HTTPException(status_code=422, detail="url and secret are required")

    webhook = Webhook(
        tenant_id=current_user.tenant_id,
        url=url,
        secret=secret,
        events=events,
        is_active=payload.get("is_active", True),
        created_by=current_user.id
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return {"data": webhook, "error": None, "meta": None}


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a webhook."""
    webhook = await db.get(Webhook, webhook_id)
    if not webhook or webhook.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    await db.commit()

    return {"data": {"success": True}, "error": None, "meta": None}


@router.get("/{webhook_id}/deliveries")
async def list_webhook_deliveries(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List delivery logs for a webhook."""
    webhook = await db.get(Webhook, webhook_id)
    if not webhook or webhook.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    stmt = select(WebhookDelivery).where(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.last_attempt_at.desc().nulls_last()).limit(100)
    
    result = await db.execute(stmt)
    deliveries = result.scalars().all()

    return {
        "data": deliveries,
        "error": None,
        "meta": {"count": len(deliveries)}
    }


@router.post("/{webhook_id}/deliveries/{delivery_id}/retry")
async def retry_delivery(
    webhook_id: UUID,
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Manually retry a failed webhook delivery."""
    webhook = await db.get(Webhook, webhook_id)
    if not webhook or webhook.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery or delivery.webhook_id != webhook_id:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Enqueue a new celery task instance
    from app.tasks.webhook_tasks import deliver_webhook
    deliver_webhook.delay(str(delivery.id))

    return {
        "data": {"status": "Retry enqueued"},
        "error": None,
        "meta": None
    }
