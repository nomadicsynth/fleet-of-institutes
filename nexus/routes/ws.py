from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import WS_ENABLED, WS_MAX_CONNECTIONS, WS_MAX_PER_IP

router = APIRouter(tags=["websocket"])

_connections: dict[WebSocket, str] = {}
_ip_counts: dict[str, int] = {}


def _ws_client_ip(websocket: WebSocket) -> str:
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return websocket.client.host if websocket.client else "unknown"


def _remove_connection(ws: WebSocket, ip: str) -> None:
    _connections.pop(ws, None)
    count = _ip_counts.get(ip, 1) - 1
    if count <= 0:
        _ip_counts.pop(ip, None)
    else:
        _ip_counts[ip] = count


@router.websocket("/ws/feed")
async def feed_ws(websocket: WebSocket):
    if not WS_ENABLED:
        await websocket.close(code=1013)
        return

    if len(_connections) >= WS_MAX_CONNECTIONS:
        await websocket.close(code=1013)
        return

    ip = _ws_client_ip(websocket)
    if _ip_counts.get(ip, 0) >= WS_MAX_PER_IP:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    _connections[websocket] = ip
    _ip_counts[ip] = _ip_counts.get(ip, 0) + 1
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _remove_connection(websocket, ip)


async def broadcast(event: str, data: dict) -> None:
    msg = json.dumps({"event": event, "data": data})
    dead: list[WebSocket] = []
    for ws in _connections:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ip = _connections.get(ws, "unknown")
        _remove_connection(ws, ip)
