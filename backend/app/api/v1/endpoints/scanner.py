"""NEXUS IMS — WebSocket scanner endpoint (Block 5).

Provides real-time scan → confirm flow for warehouse floor staff.
WS message protocol:
  Client → Server: {"barcode": "...", "event_type": "RECEIVE|PICK", "quantity": 10, "warehouse_id": "uuid", "location_id": "uuid?"}
  Server → Client: {"status": "ok|error", "sku": {...}, "event": {...}, "stock": N}
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.session import async_session_maker
from app.models.item_type import SKU
from app.models.warehouse import StockEventType
from app.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _lookup_sku_by_code(db: AsyncSession, tenant_id: UUID, barcode: str) -> SKU | None:
    """Find SKU by sku_code (barcode)."""
    result = await db.execute(
        select(SKU).where(
            SKU.tenant_id == tenant_id,
            SKU.sku_code == barcode,
            SKU.is_archived == False,  # noqa: E712
        )
    )
    return result.scalars().first()


@router.websocket("/ws/scan")
async def ws_scan(websocket: WebSocket):
    """
    WebSocket endpoint for barcode scanning.
    Auth: pass JWT as query param ?token=... (WebSocket can't use Authorization header).
    """
    await websocket.accept()

    # ── Authenticate from query param ────────────────────────────────────
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"status": "error", "message": "Missing token query param"})
        await websocket.close(code=4001)
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.send_json({"status": "error", "message": "Invalid or expired token"})
        await websocket.close(code=4001)
        return

    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tenant_id"])
    user_role = payload.get("role", "FLOOR_ASSOCIATE")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"status": "error", "message": "Invalid JSON"})
                continue

            barcode = msg.get("barcode", "").strip()
            event_type_str = msg.get("event_type", "").upper()
            quantity = msg.get("quantity")
            warehouse_id_str = msg.get("warehouse_id")
            location_id_str = msg.get("location_id")
            reason_code = msg.get("reason_code")

            # Validate required fields
            if not barcode:
                await websocket.send_json({"status": "error", "message": "barcode is required"})
                continue
            if not warehouse_id_str:
                await websocket.send_json({"status": "error", "message": "warehouse_id is required"})
                continue

            warehouse_id = UUID(warehouse_id_str)
            location_id = UUID(location_id_str) if location_id_str else None

            # ── Lookup mode: just look up the SKU without posting an event ──
            if event_type_str == "LOOKUP":
                async with async_session_maker() as db:
                    from sqlalchemy import text
                    await db.execute(
                        text("SELECT set_config('app.tenant_id', :tid, true)"),
                        {"tid": str(tenant_id)},
                    )
                    sku = await _lookup_sku_by_code(db, tenant_id, barcode)
                    if not sku:
                        await websocket.send_json({"status": "error", "message": f"SKU '{barcode}' not found"})
                        continue
                    stock = await LedgerService.get_stock_level(db, tenant_id, sku.id, warehouse_id)
                    await websocket.send_json({
                        "status": "ok",
                        "action": "LOOKUP",
                        "sku": {
                            "id": str(sku.id),
                            "sku_code": sku.sku_code,
                            "name": sku.name,
                            "unit_cost": float(sku.unit_cost) if sku.unit_cost else None,
                        },
                        "stock": float(stock),
                    })
                    continue

            # ── Transaction mode: post ledger event ─────────────────────────
            if event_type_str not in ("RECEIVE", "PICK", "ADJUST", "RETURN"):
                await websocket.send_json({"status": "error", "message": f"Invalid event_type: {event_type_str}"})
                continue
            if quantity is None:
                await websocket.send_json({"status": "error", "message": "quantity is required"})
                continue

            # RBAC check for ADJUST
            if event_type_str == "ADJUST" and user_role == "FLOOR_ASSOCIATE":
                await websocket.send_json({"status": "error", "message": "Floor associates cannot adjust stock"})
                continue

            # Map to StockEventType
            event_map = {
                "RECEIVE": StockEventType.RECEIVE,
                "PICK": StockEventType.PICK,
                "ADJUST": StockEventType.ADJUST,
                "RETURN": StockEventType.RETURN,
            }
            event_type = event_map[event_type_str]

            # Determine quantity delta sign
            qty = Decimal(str(abs(quantity)))
            if event_type_str == "PICK":
                qty = -qty

            async with async_session_maker() as db:
                from sqlalchemy import text
                await db.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(tenant_id)},
                )
                sku = await _lookup_sku_by_code(db, tenant_id, barcode)
                if not sku:
                    await websocket.send_json({"status": "error", "message": f"SKU '{barcode}' not found"})
                    continue

                try:
                    ev = await LedgerService.post_event(
                        db, tenant_id, sku.id, warehouse_id,
                        event_type, qty,
                        location_id=location_id,
                        actor_id=user_id,
                        reason_code=reason_code,
                        notes=f"Scanner: {event_type_str}",
                    )
                    await db.commit()

                    stock = await LedgerService.get_stock_level(db, tenant_id, sku.id, warehouse_id)

                    await websocket.send_json({
                        "status": "ok",
                        "action": event_type_str,
                        "sku": {
                            "id": str(sku.id),
                            "sku_code": sku.sku_code,
                            "name": sku.name,
                        },
                        "event": {
                            "id": str(ev.id),
                            "quantity_delta": float(ev.quantity_delta),
                            "event_type": ev.event_type,
                        },
                        "stock": float(stock),
                    })
                except ValueError as e:
                    await websocket.send_json({"status": "error", "message": str(e)})
                except Exception as e:
                    logger.exception("Scanner event error")
                    await websocket.send_json({"status": "error", "message": "Internal error"})

    except WebSocketDisconnect:
        logger.info("Scanner client disconnected: user=%s", user_id)
