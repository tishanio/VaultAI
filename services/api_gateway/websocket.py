from __future__ import annotations

"""WebSocket manager for real-time updates — matches, escrow, notifications."""
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from vault.security import decode_token
from vault.events import Event, EventType, publisher

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._user_info: dict[str, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, username: str):
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        self._user_info[user_id] = {"username": username}
        logger.info("WebSocket connected: user={} total={}", username, len(self._connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self._connections:
            if websocket in self._connections[user_id]:
                self._connections[user_id].remove(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
                self._user_info.pop(user_id, None)
        logger.info("WebSocket disconnected: user_id={}", user_id)

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        if user_id in self._connections:
            disconnected = []
            for ws in self._connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self._connections[user_id].remove(ws)

    async def broadcast(self, message: dict[str, Any]):
        disconnected = []
        for user_id, connections in self._connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)
        for ws in disconnected:
            for user_id, connections in self._connections.items():
                if ws in connections:
                    connections.remove(ws)

    @property
    def active_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    @property
    def connected_users(self) -> list[str]:
        return list(self._user_info.keys())


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time updates.

    Connect with: ws://localhost:8000/ws?token=<jwt_access_token>
    """
    # Authenticate via token query parameter
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")
    username = payload.get("username", "unknown")

    await manager.connect(websocket, user_id, username)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": f"Welcome {username}! You are connected to Vault real-time updates.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_connections": manager.active_connections,
        })

        # Listen for incoming messages (heartbeats, subscriptions, etc.)
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                elif msg_type == "subscribe":
                    # Client can subscribe to specific channels
                    channel = message.get("channel", "general")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("WebSocket error for user {}: {}", user_id, e)
        manager.disconnect(websocket, user_id)


# ---------------------------------------------------------------------------
# Event Forwarder — pushes events to connected WebSocket clients
# ---------------------------------------------------------------------------

class WebSocketEventForwarder:
    """Listens for platform events and forwards them to WebSocket clients."""

    EVENT_MAP = {
        EventType.MATCH_PROPOSED: "match.proposed",
        EventType.MATCH_ACCEPTED: "match.accepted",
        EventType.MATCH_COMPLETED: "match.completed",
        EventType.ESCROW_FUNDED: "escrow.funded",
        EventType.ESCROW_RELEASED: "escrow.released",
        EventType.ESCROW_DISPUTED: "escrow.disputed",
        EventType.SUBSCRIPTION_CREATED: "subscription.created",
        EventType.USER_CREATED: "user.created",
        EventType.RISK_ALERT: "compliance.risk_alert",
        EventType.TOS_VIOLATION: "compliance.tos_violation",
        EventType.CIRCUIT_BREAKER: "compliance.circuit_breaker",
    }

    async def handle(self, event: Event):
        ws_type = self.EVENT_MAP.get(event.event_type, event.event_type)

        message = {
            "type": ws_type,
            "data": event.data,
            "source": event.source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Route to specific user if user_id is in event data
        target_user_id = event.data.get("user_id") or event.data.get("buyer_id") or event.data.get("seller_id")
        if target_user_id:
            await manager.send_to_user(str(target_user_id), message)
        else:
            # Broadcast to all connected clients
            await manager.broadcast(message)


# Singleton forwarder
ws_forwarder = WebSocketEventForwarder()


# ---------------------------------------------------------------------------
# Public API for sending targeted updates
# ---------------------------------------------------------------------------

async def notify_user(user_id: str, event_type: str, data: dict[str, Any]):
    """Send a real-time notification to a specific user via WebSocket."""
    await manager.send_to_user(user_id, {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def broadcast_event(event_type: str, data: dict[str, Any]):
    """Broadcast an event to all connected WebSocket clients."""
    await manager.broadcast({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
