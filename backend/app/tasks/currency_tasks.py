"""NEXUS IMS — Currency synchronization daily tasks."""
import json
import logging
import httpx
from datetime import timedelta

from app.core.redis import get_redis
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def fetch_exchange_rates(self):
    """
    Fetches daily exchange rates from open.er-api.com and caches them in Redis.
    Base currency is usually USD.
    """
    import asyncio
    asyncio.run(_fetch_exchange_rates_async())


async def _fetch_exchange_rates_async():
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        
        rates = data.get("rates")
        if not rates:
            logger.error("No rates found in response from open.er-api.com")
            return
            
        r = await get_redis()
        # Store in Redis for 48 hours to be safe
        await r.setex("global_exchange_rates", 172800, json.dumps(rates))
        logger.info(f"Successfully updated exchange rates in Redis. USD to {len(rates)} currencies.")
        
    except Exception as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
