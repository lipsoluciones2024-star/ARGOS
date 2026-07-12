from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from argos import get_config
from argos.ai.orchestrator import AiOrchestrator
from argos.chat.ws import ConnectionManager
from argos.config import Config, SwitchLevel
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.logging_setup import setup_logging
from argos.ocsf import OcsfEvent
from argos.response.orchestrator import ResponseOrchestrator
from argos.scheduler import Scheduler
from argos.storage.settings import SettingsStore
from argos.storage.store import AlertStore, AuditLog, EventStore

UI_DIR = Path(__file__).resolve().parent.parent / "chat-ui"


class AppContext:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.logger = setup_logging(cfg, "argos.server")
        self.settings = SettingsStore(cfg)
        self.store = EventStore(cfg)
        self.alert_store = AlertStore(cfg)
        self.audit = AuditLog(cfg)
        self.intel = ThreatIntel(cfg)
        self.engine = DetectionEngine(cfg, alert_store=self.alert_store)
        self.manager = ConnectionManager()
        self.orchestrator = AiOrchestrator(cfg, self.store, self.engine, self.intel,
                                           self.alert_store, on_push=self._push, settings=self.settings)
        self.response = ResponseOrchestrator(cfg, self.audit, switch=None)
        self.response.set_level(SwitchLevel(self.settings.get_str("switch.default", cfg.default_switch.value)))
        self.intel.feed_sample()
        self.scheduler = Scheduler(self, self.settings)
        self.loop: asyncio.AbstractEventLoop | None = None

    def _push(self, payload: dict) -> None:
        if self.loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self.manager.broadcast(payload), self.loop)
        except Exception:
            pass

    def ingest(self, raw_events: list[dict]) -> int:
        events = [OcsfEvent.model_validate(r) for r in raw_events]
        n = self.store.ingest_many(events)
        self.logger.debug("ingest: %d eventos validados y almacenados", n)
        alerts = self.engine.evaluate_batch(events)
        for a in alerts:
            self.alert_store.add(a)
            self.logger.info("ALERTA %s: %s en %s (%s)", a.severity.value.upper(), a.title, a.host, a.attack_id)
        high = [a for a in alerts if a.severity.value in ("high", "critical")]
        for a in high:
            self._push({"type": "proactive_alert", "alert": a.as_dict(),
                        "message": f"[ALERTA {a.severity.value.upper()}] {a.title} en {a.host}"})
        return n


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or get_config()
    ctx = AppContext(cfg)

    async def lifespan(app: FastAPI) -> Any:
        ctx.loop = asyncio.get_running_loop()
        await ctx.scheduler.start()
        yield
        await ctx.scheduler.stop()

    app = FastAPI(title="ARGOS", version="0.1.0", lifespan=lifespan)
    app.state.ctx = ctx

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "events": ctx.store.count(),
                "switch": ctx.response.switch.level.value,
                "llm_channel": ctx.orchestrator.channel()}

    @app.post("/api/v1/ingest")
    async def ingest(payload: Any = Body(...)):
        events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(events, list):
            events = []
        n = await asyncio.to_thread(ctx.ingest, events)
        return {"ingested": n}

    @app.get("/api/v1/events")
    async def events(category: str | None = None, host: str | None = None,
                     severity: str | None = None, attack_id: str | None = None,
                     text: str | None = None, since: str | None = None, limit: int = 100):
        return [e.as_dict() for e in ctx.store.query(
            filters={"category": category, "host": host, "severity": severity,
                     "attack_id": attack_id, "text": text, "since": since}, limit=limit)]

    @app.get("/api/v1/alerts")
    async def alerts(severity: str | None = None, limit: int = 50):
        return ctx.alert_store.recent(limit=limit, severity=severity)

    @app.get("/api/v1/hosts")
    async def hosts(limit: int = 50):
        return ctx.store.hosts(limit=limit)

    @app.get("/api/v1/stats")
    async def stats():
        return {
            "total_events": ctx.store.count(),
            "series": ctx.store.time_series(hours=24),
            "switch": ctx.response.switch.level.value,
            "rules": len(ctx.engine.rules),
            "coverage_blind_spots": sum(1 for v in ctx.engine.coverage().values() if v["status"] == "blind-spot"),
        }

    @app.get("/api/v1/metrics")
    async def metrics():
        if not ctx.scheduler.metrics:
            ctx.scheduler.run_once()
        return ctx.scheduler.metrics

    @app.get("/api/v1/coverage")
    async def coverage():
        return ctx.engine.coverage()

    @app.get("/api/v1/rules")
    async def rules():
        return ctx.engine.list_rules()

    @app.get("/api/v1/actions")
    async def actions():
        return ctx.response.catalog()

    @app.get("/api/v1/switch")
    async def get_switch():
        return ctx.response.switch.as_dict()

    @app.post("/api/v1/switch")
    async def set_switch(payload: dict):
        level = payload.get("level")
        try:
            lvl = SwitchLevel(level)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "invalid level"})
        ctx.response.set_level(lvl)
        ctx.settings.set("switch.default", lvl.value)
        return ctx.response.switch.as_dict()

    @app.get("/api/v1/proposals")
    async def proposals():
        return [{"id": p.id, "action": p.action, "target": p.target,
                 "status": p.status, "proposed_by": p.proposed_by}
                for p in ctx.response.pending_proposals()]

    @app.post("/api/v1/propose")
    async def propose(payload: dict):
        proposal = ctx.response.propose(
            action=payload["action"], target=payload["target"],
            proposed_by=payload.get("proposed_by", "ai"), params=payload.get("params"))
        return {"id": proposal.id, "status": proposal.status, "action": proposal.action,
                "target": proposal.target}

    @app.post("/api/v1/confirm")
    async def confirm(payload: dict):
        proposal = ctx.response.confirm(payload["id"], payload.get("approved_by", "user"))
        return {"id": proposal.id, "status": proposal.status, "result": proposal.result}

    @app.get("/api/v1/audit")
    async def audit():
        return ctx.audit.all()

    @app.get("/api/v1/logs")
    async def logs(tail: int = 200):
        log_path = ctx.cfg.data_dir / "argos.log"
        if not log_path.exists():
            return []
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-tail:]

    @app.get("/api/v1/models")
    async def models():
        try:
            from argos.ai.client import GatewayClient

            c = GatewayClient(cfg.gateway_base_url)
            return {"models": c.list_models(anonymous=True)[:50]}
        except Exception as exc:
            return {"error": str(exc)}

    @app.get("/api/v1/ai/status")
    async def ai_status():
        return ctx.orchestrator.status()

    @app.get("/api/v1/settings")
    async def get_settings():
        return ctx.settings.as_dict()

    @app.put("/api/v1/settings")
    async def put_settings(payload: dict):
        return ctx.settings.set_many(payload)

    @app.websocket("/ws")
    async def ws(ws: WebSocket):
        await ws.accept()
        await ctx.manager.connect(ws)
        try:
            while True:
                data = await ws.receive_json()
                kind = data.get("type")
                if kind == "chat":
                    answer = await asyncio.to_thread(
                        ctx.orchestrator.chat, data.get("message", ""), data.get("history"))
                    await ctx.manager.send(ws, {"type": "chat", "role": "assistant", "content": answer})
                elif kind == "chat_stream":
                    await _stream_chat(ctx, ws, data)
                elif kind == "switch":
                    try:
                        lvl = SwitchLevel(data.get("level"))
                        ctx.response.set_level(lvl)
                        ctx.settings.set("switch.default", lvl.value)
                        await ctx.manager.send(ws, {"type": "switch", **ctx.response.switch.as_dict()})
                    except ValueError:
                        await ctx.manager.send(ws, {"type": "error", "content": "invalid level"})
                else:
                    await ctx.manager.send(ws, {"type": "error", "content": "unknown message type"})
        except WebSocketDisconnect:
            ctx.manager.disconnect(ws)

    if UI_DIR.exists():
        app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

        @app.get("/")
        async def index():
            return FileResponse(UI_DIR / "index.html")

    return app


async def _stream_chat(ctx: AppContext, ws: Any, data: dict) -> None:
    history = data.get("history")
    for chunk in ctx.orchestrator.chat_stream(data.get("message", ""), history):
        await ctx.manager.send(ws, {"type": "chat_stream", **chunk})
        if chunk.get("type") == "token":
            await asyncio.sleep(0)


def main() -> None:
    import uvicorn

    cfg = get_config()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.server_host, port=cfg.server_port, log_level="info")


if __name__ == "__main__":
    main()
