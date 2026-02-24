import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

async def dispatch_webhook(db: AsyncSession, tenant_id: UUID, event_type: str, payload: dict) -> None:
    """Dispatches a webhook event to all subscribed webhooks for a given tenant."""
    try:
        # Find all active webhooks for the tenant
        stmt = select(Webhook).where(
            Webhook.tenant_id == tenant_id,
            Webhook.is_active == True
        )
        result = await db.execute(stmt)
        webhooks = result.scalars().all()

        deliveries = []
        for wh in webhooks:
            # Check if this webhook subscribes to the event
            # Use '*' to indicate subscribing to all events
            if '*' in wh.events or event_type in wh.events:
                delivery = WebhookDelivery(
                    webhook_id=wh.id,
                    event_type=event_type,
                    payload=payload,
                    status="PENDING"
                )
                db.add(delivery)
                deliveries.append(delivery)
        
        if not deliveries:
            return

        await db.flush()  # to get delivery IDs
        
        # enqueue celery tasks
        from app.tasks.webhook_tasks import deliver_webhook
        for delivery in deliveries:
            deliver_webhook.delay(str(delivery.id))
            
    except Exception as e:
        logger.error(f"Error dispatching webhook event {event_type} for tenant {tenant_id}: {e}")
