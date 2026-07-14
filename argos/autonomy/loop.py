from __future__ import annotations

import asyncio
from typing import Any, Optional

from argos.autonomy.investigator import Investigator
from argos.autonomy.limits import ActionLimiter
from argos.config import Config


class AutonomyLoop:
    """Bucle de razonamiento autónomo (cierra G2).

    Se suscribe a alertas high/critical; por cada una ejecuta el Investigador
    en background, respetando límites de seguridad y emitiendo eventos de
    visibilidad por WebSocket para que el operador vea al "organismo" pensar.
    """

    def __init__(self, ctx: Any, cfg: Config) -> None:
        self.ctx = ctx
        self.cfg = cfg
        self.investigator = Investigator(ctx.orchestrator)
        self.limiter = ActionLimiter(
            max_per_hour=cfg.autonomy_max_actions_per_hour,
            cooldown_per_host_sec=cfg.autonomy_host_cooldown_sec,
        )
        self.enabled = cfg.autonomy_enabled
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
        self.processed = 0
        self.rate_limited = 0

    def enabled_flag(self) -> bool:

        return self.enabled and self.ctx.settings.get_bool("autonomy.enabled", True)

    async def start(self) -> None:
        if not self.enabled_flag():
            return
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self._queue = None

    def enqueue(self, alert: dict[str, Any]) -> None:
        """Encola una alerta desde cualquier hilo (ingest/scheduler)."""
        if not self._queue or not self.enabled_flag():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._queue.put(alert), self.ctx.loop)
        except Exception:
            pass

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            alert = await self._queue.get()
            try:
                await self._process(alert)
            except Exception as exc:  # keep the organism alive
                self._broadcast({
                    "type": "autonomy_event", "status": "error",
                    "host": alert.get("host"), "detail": str(exc),
                })

    async def _process(self, alert: dict[str, Any]) -> None:
        host = alert.get("host", "unknown")
        self._broadcast({
            "type": "autonomy_event", "status": "investigating",
            "alert_id": alert.get("id"), "host": host,
            "title": alert.get("title"), "attack_id": alert.get("attack_id"),
        })
        if not self.limiter.allow(host):
            self.rate_limited += 1
            self._broadcast({
                "type": "autonomy_event", "status": "rate_limited",
                "host": host, "detail": "límite de acciones/hora o cooldown por host alcanzado",
            })
            return
        result = await asyncio.to_thread(self.investigator.investigate, alert)
        self.processed += 1
        try:
            self.ctx.memory.add_investigation(
                host=host, alert_id=alert.get("id"), attack_id=alert.get("attack_id"),
                verdict=result.get("verdict", ""), summary=result.get("title", ""),
            )
        except Exception:
            pass
        self._broadcast({"type": "autonomy_event", "status": "done", **result})

    def _broadcast(self, payload: dict[str, Any]) -> None:
        try:
            self.ctx._push(payload)
        except Exception:
            pass
