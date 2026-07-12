from __future__ import annotations

from typing import Any


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[Any] = set()

    async def connect(self, ws: Any) -> None:
        self.active.add(ws)

    def disconnect(self, ws: Any) -> None:
        self.active.discard(ws)

    async def send(self, ws: Any, payload: dict[str, Any]) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        for ws in list(self.active):
            await self.send(ws, payload)
