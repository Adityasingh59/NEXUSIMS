"""NEXUS IMS — Webhook Delivery Celery Tasks (Block 10)."""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from app.db.session import async_session_factory
from app.models.webhook import Webhook, WebhookDelivery
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def deliver_webhook(self, delivery_id: str) -> None:
    """
    Delivers a webhook payload to the configured URL with exponential backoff.
    Retries automatically 3 times if response is not 200-299.
    """
    import asyncio
    try:
        asyncio.run(_deliver_webhook_async(self, delivery_id))
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        # Exponential backoff: 2^retry_count * 5 seconds (5s, 10s, 20s)
        delay = (2 ** self.request.retries) * 5
        logger.warning(f"Webhook {delivery_id} failed, retrying in {delay}s: {exc}")
        raise self.retry(exc=exc, countdown=delay)


async def _deliver_webhook_async(task, delivery_id: str) -> None:
    async with async_session_factory() as db:
        # Fetch delivery and webhook config
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = select(WebhookDelivery).options(selectinload(WebhookDelivery.webhook)).where(WebhookDelivery.id == delivery_id)
        result = await db.execute(stmt)
        delivery = result.scalar_one_or_none()
        
        if not delivery or not delivery.webhook or not delivery.webhook.is_active:
            logger.info(f"Skipping delivery {delivery_id}: Invalid webhook or inactive.")
            return

        webhook = delivery.webhook
        
        # Prepare payload and signature
        payload_str = json.dumps(delivery.payload, separators=(',', ':'))
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Nexus-Signature": signature,
            "X-Nexus-Event": delivery.event_type,
            "X-Nexus-Delivery": str(delivery.id),
        }

        # Update attempt info
        delivery.attempts += 1
        delivery.last_attempt_at = datetime.now(tz=timezone.utc)
        delivery.status = "PENDING"
        await db.commit()

        # Send HTTP POST
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook.url, content=payload_str, headers=headers)
            
            # Record response
            delivery.response_code = response.status_code
            delivery.response_body = response.text[:2000] # clamp to avoid massive logs

            if 200 <= response.status_code < 300:
                delivery.status = "SUCCESS"
                delivery.delivered_at = datetime.now(tz=timezone.utc)
                await db.commit()
                return # Task complete
            else:
                delivery.status = "FAILED"
                await db.commit()
                # httpx raise_for_status to trigger Celery retry
                response.raise_for_status()
