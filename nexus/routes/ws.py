from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

_connections: set[WebSocket] = set()


@router.websocket("/ws/feed")
async def feed_ws(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.discard(websocket)


async def broadcast(event: str, data: dict) -> None:
    msg = json.dumps({"event": event, "data": data})
    dead: list[WebSocket] = []
    for ws in _connections:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.discard(ws)
