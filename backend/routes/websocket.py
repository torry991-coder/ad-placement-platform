"""
WebSocket real-time data streaming.

Endpoint: ws://localhost:8003/ws/dashboard
Messages:
  → kpi_update: Dashboard KPI changes (every 10s)
  → alert_triggered: New alert fired
  → auction_result: Latest bidding result
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Connection manager ──────────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._counter = 0

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        self._counter += 1
        conn_id = f"ws_{self._counter}"
        self._connections[conn_id] = ws
        logger.info("WebSocket connected: %s (total: %d)", conn_id, len(self._connections))
        return conn_id

    def disconnect(self, conn_id: str):
        self._connections.pop(conn_id, None)
        logger.info("WebSocket disconnected: %s (total: %d)", conn_id, len(self._connections))

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, event: str, data: dict[str, Any]):
        """Send an event to all connected clients."""
        if not self._connections:
            return
        message = json.dumps({"event": event, "data": data, "ts": datetime.now(timezone.utc).isoformat()}, default=str)
        dead: list[str] = []
        for conn_id, ws in self._connections.items():
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(conn_id)
        for d in dead:
            self._connections.pop(d, None)

    async def broadcast_json(self, data: dict[str, Any]):
        """Send raw JSON data to all clients."""
        message = json.dumps(data, default=str)
        dead: list[str] = []
        for conn_id, ws in self._connections.items():
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(conn_id)
        for d in dead:
            self._connections.pop(d, None)


manager = ConnectionManager()


# ── WebSocket endpoint ──────────────────────────────────────────────────

@router.websocket("/ws/dashboard")
async def dashboard_websocket(ws: WebSocket):
    """Real-time dashboard data stream.

    Sends KPI updates every 10 seconds. Clients receive:
      {"event": "kpi_update", "data": {...}, "ts": "..."}
    """
    conn_id = await manager.connect(ws)

    # Send initial connection message
    await ws.send_text(json.dumps({
        "event": "connected",
        "data": {"client_id": conn_id, "active_connections": manager.active_count},
        "ts": datetime.now(timezone.utc).isoformat(),
    }))

    try:
        # Keep connection alive, send heartbeat + KPI updates
        tick = 0
        while True:
            await asyncio.sleep(10)

            # Fetch latest KPIs
            try:
                from backend.database import async_session_factory
                from backend.services.campaign_service import get_dashboard_kpis
                async with async_session_factory() as db:
                    kpis = await get_dashboard_kpis(db)
            except Exception:
                kpis = {"error": "Failed to fetch KPIs"}

            await ws.send_text(json.dumps({
                "event": "kpi_update",
                "data": kpis,
                "ts": datetime.now(timezone.utc).isoformat(),
            }, default=str))

            tick += 1
            if tick % 6 == 0:  # Every 60s
                await ws.send_text(json.dumps({
                    "event": "heartbeat",
                    "data": {"connections": manager.active_count},
                    "ts": datetime.now(timezone.utc).isoformat(),
                }))

    except WebSocketDisconnect:
        manager.disconnect(conn_id)
    except Exception:
        manager.disconnect(conn_id)


@router.websocket("/ws/auction")
async def auction_websocket(ws: WebSocket):
    """Real-time auction results stream.

    Clients receive simulated auction results every 2 seconds.
    """
    conn_id = await manager.connect(ws)
    await ws.send_text(json.dumps({"event": "connected", "data": {"type": "auction_stream"}}))

    try:
        while True:
            import random
            bid = round(random.uniform(0.5, 8.0), 4)
            won = random.random() > 0.55
            await ws.send_text(json.dumps({
                "event": "auction_result",
                "data": {
                    "campaign_id": random.randint(1, 12),
                    "bid_amount": bid,
                    "predicted_ctr": round(random.uniform(1.5, 6.0), 3),
                    "won": won,
                    "win_price": round(bid * random.uniform(0.7, 1.0), 4) if won else 0,
                    "model_used": "statistical",
                },
                "ts": datetime.now(timezone.utc).isoformat(),
            }))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(conn_id)


# ── HTTP helper for broadcasting alerts ─────────────────────────────────

async def broadcast_alert(alert_data: dict[str, Any]):
    """Broadcast an alert to all WebSocket clients."""
    await manager.broadcast("alert_triggered", alert_data)


def get_ws_stats() -> dict:
    return {"active_connections": manager.active_count}
