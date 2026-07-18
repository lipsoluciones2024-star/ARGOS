from __future__ import annotations

import asyncio
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from argos import get_config
from argos.ai.agents import agent_catalog
from argos.ai.context import ContextRetriever
from argos.ai.local_runtime_server import LocalRuntimeServer
from argos.ai.orchestrator import AiOrchestrator
from argos.autonomy import AutonomyLoop
from argos.chat.ws import ConnectionManager
from argos.collector.dedupe import Deduper
from argos.config import Config, SwitchLevel
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.logging_setup import setup_logging
from argos.ocsf import OcsfEvent
from argos.response.orchestrator import ResponseOrchestrator
from argos.scan import network as net_scan
from argos.scan.monitor import run_monitor_scan
from argos.scheduler import Scheduler
from argos.security import cors_origins, derive_secret
from argos.security.auth import sign_token, derive_secret
from argos.security.middleware import (
    AuthMiddleware,
    authorize_ws,
    ws_token_from_request,
)
from argos.security.ratelimit import RateLimiter
from argos.security.rbac import require_role
from argos.storage.cases import CasesStore
from argos.storage.chatlog import ChatLog
from argos.storage.memory import MemoryStore
from argos.storage.network_baseline import NetworkBaselineStore
from argos.storage.rules import RulesStore
from argos.storage.settings import SettingsStore
from argos.storage.store import AlertStore, AuditLog, EventStore
from argos.storage.ui_prefs import UiPrefsStore
from argos.storage.users import UsersStore

UI_DIR = Path(__file__).resolve().parent.parent / "dashboard"


class AppContext:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.logger = setup_logging(cfg, "argos.server")
        self.auth_secret = derive_secret(cfg.auth_secret, str(cfg.data_dir))
        if cfg.require_auth and not cfg.api_token and not cfg.auth_secret:
            bootstrap = secrets.token_hex(24)
            cfg.api_token = bootstrap
            cfg.auth_secret = bootstrap
            self.auth_secret = derive_secret(cfg.auth_secret, str(cfg.data_dir))
            self.logger.warning(
                "AUTH BOOTSTRAP: no se definió ARGOS_API_TOKEN. Token admin temporal: %s "
                "(guárdalo; no se volverá a mostrar. Usa 'argos auth token --role admin' para generar estables.)",
                bootstrap,
            )
        self.limiter = RateLimiter(max_requests=cfg.rate_limit_per_hour, window_sec=3600)
        self.settings = SettingsStore(cfg)
        self.ui_prefs = UiPrefsStore(cfg)
        self.store = EventStore(cfg)
        self.alert_store = AlertStore(cfg)
        self.audit = AuditLog(cfg)
        self.intel = ThreatIntel(cfg)
        self.users = UsersStore(cfg)
        self.rules_store = RulesStore(cfg)
        self.cases = CasesStore(cfg)
        self.net_baseline = NetworkBaselineStore(cfg)
        self.engine = DetectionEngine(cfg, alert_store=self.alert_store)
        self.manager = ConnectionManager()
        self.chatlog = ChatLog(cfg)
        self.memory = MemoryStore(cfg)
        self.response = ResponseOrchestrator(cfg, self.audit, switch=None, memory=self.memory)
        if cfg.default_switch_env:
            self.response.set_level(cfg.default_switch)
            self.settings.set("switch.default", cfg.default_switch.value)
        else:
            self.response.set_level(
                SwitchLevel(self.settings.get_str("switch.default", cfg.default_switch.value))
            )
        self.orchestrator = AiOrchestrator(cfg, self.store, self.engine, self.intel,
                                            self.alert_store, on_push=self._push, settings=self.settings,
                                            response=self.response, on_proposal=self._push_proposal,
                                            chatlog=self.chatlog, memory=self.memory,
                                            context=ContextRetriever(self.memory, self.chatlog))
        # --- Capa enterprise XAI: Tool Gateway, MCP y Plugins -------------------
        from argos.ai.tools.gateway import ToolGateway, ToolGatewayConfig
        from argos.ai.tools.registry import ToolExecutor
        from argos.mcp.server import MCPServer
        from argos.observability.health import health as health_registry
        from argos.plugins import build_plugin_runtime

        self.tool_executor = ToolExecutor(self.store, self.engine, self.intel, response=self.response)
        self.gateway = ToolGateway(self.tool_executor, ToolGatewayConfig())
        self.mcp = MCPServer(self.tool_executor)
        self.plugin_registry, self.plugin_manager = build_plugin_runtime(
            Path(__file__).resolve().parent / "plugins" / "installed"
        )
        # Hook built-in de deteccion: comportamental + threat intel (Fase R2).
        from argos.detection.hooks_integration import register_detection_hooks

        self.detection_hook = register_detection_hooks(self.plugin_registry, self.intel)
        # Entrenar baseline con eventos recientes si hay suficientes.
        try:
            recent = self.store.query(filters={}, limit=2000)
            if len(recent) >= 50:
                self.detection_hook.train(recent)
        except Exception:
            pass
        health_registry.register("database", lambda: {
            "status": "ok" if (cfg.data_dir / "argos.db").exists() else "degraded",
            "path": str(cfg.data_dir / "argos.db"),
        })
        health_registry.register("engine", lambda: {
            "status": "ok",
            "sigma_rules": len(self.engine.rules),
            "yara_rules": len(self.engine.yara.rules),
        }, critical=False)
        health_registry.register("switch", lambda: {
            "status": "ok", "level": self.response.switch.level.value
        }, critical=False)
        self.health_registry = health_registry
        self.deduper = Deduper()
        self.autonomy = AutonomyLoop(self, cfg)
        self.local_runtime = LocalRuntimeServer(cfg)
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

    def _push_proposal(self, payload: dict) -> None:
        if self.loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.manager.broadcast({"type": "proposal", **payload}), self.loop
            )
        except Exception:
            pass

    def ingest(self, raw_events: list[dict]) -> int:
        events: list[OcsfEvent] = []
        for r in raw_events:
            try:
                events.append(OcsfEvent.model_validate(r))
            except Exception as exc:  # T6.9: payload malformado no crashea el server
                self.logger.warning("ingest: evento descartado por esquema invalido: %s", exc)
        events = self.deduper.filter(events)
        if not events:
            return 0
        n = self.store.ingest_many(events)
        self.logger.debug("ingest: %d eventos validados y almacenados", n)
        alerts = self.engine.evaluate_batch(events)
        # Hook built-in de deteccion (comportamental + threat intel) por evento.
        try:
            from argos.plugins.base import HookEvent

            for e in events:
                ctx = {"event": e, "alerts": []}
                self.plugin_registry.execute_hooks(HookEvent.POST_DETECTION, ctx)
                extra = ctx.get("alerts") or []
                if isinstance(extra, list):
                    alerts.extend(extra)
        except Exception as exc:
            self.logger.warning("Hook POST_DETECTION fallo: %s", exc)
        for a in alerts:
            self.alert_store.add(a)
            self.logger.info("ALERTA %s: %s en %s (%s)", a.severity.value.upper(), a.title, a.host, a.attack_id)
        high = [a for a in alerts if a.severity.value in ("high", "critical")]
        for a in high:
            self._push({"type": "proactive_alert", "alert": a.as_dict(),
                        "message": f"[ALERTA {a.severity.value.upper()}] {a.title} en {a.host}"})
            self.autonomy.enqueue(a.as_dict())
        return n


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or get_config()
    ctx = AppContext(cfg)

    async def lifespan(app: FastAPI) -> Any:
        ctx.loop = asyncio.get_running_loop()
        ctx.local_runtime.start()
        await ctx.scheduler.start()
        await ctx.autonomy.start()
        yield
        await ctx.autonomy.stop()
        ctx.local_runtime.stop()
        await ctx.scheduler.stop()

    app = FastAPI(title="ARGOS", version="0.1.0", lifespan=lifespan)
    app.state.ctx = ctx

    # CORS restrictivo (origen de la UI). Misma procedencia => localhost permitido.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(cfg.server_host, cfg.server_port, cfg.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # Autenticación + rate limiting (salvo rutas públicas).
    app.add_middleware(AuthMiddleware, cfg=cfg, secret=ctx.auth_secret, limiter=ctx.limiter)

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
        cov = ctx.engine.coverage()
        return {
            "total_events": ctx.store.count(),
            "series": ctx.store.time_series(hours=24),
            "switch": ctx.response.switch.level.value,
            "rules": len(ctx.engine.rules),
            "coverage_blind_spots": cov["total"] - cov["covered"],
            "coverage_detected": cov["covered"],
            "coverage_total": cov["total"],
            "coverage_pct": round(100.0 * cov["covered"] / cov["total"], 1) if cov["total"] else 0.0,
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
    async def set_switch(payload: dict, request: Request):
        role = getattr(request.state, "claims", {}).get("role", "admin")
        if role != "admin":
            return JSONResponse(status_code=403, content={"error": "admin role required"})
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

    @app.get("/api/v1/agents")
    async def agents():
        from argos.ai.tools.registry import ROLE_PERMISSIONS

        return {"agents": agent_catalog(), "roles": list(ROLE_PERMISSIONS.keys())}

    @app.get("/api/v1/ai/status")
    async def ai_status():
        return ctx.orchestrator.status()

    @app.post("/api/v1/chat/session")
    async def chat_session(payload: dict = Body(default={})):
        title = payload.get("title", "chat")
        return {"session": ctx.chatlog.new_session(title)}

    @app.get("/api/v1/chat/sessions")
    async def chat_sessions():
        return ctx.chatlog.sessions()

    @app.get("/api/v1/chat/history")
    async def chat_history(session: str, limit: int = 50):
        return ctx.chatlog.history(session, limit)

    @app.get("/api/v1/memory/investigations")
    async def memory_investigations(limit: int = 50):
        return ctx.memory.recent_investigations(limit)

    @app.post("/api/v1/feedback")
    async def feedback(payload: dict):
        ctx.memory.add_feedback(
            payload.get("target_type", "action"), payload.get("target_id", ""),
            payload.get("rating", "neutral"), payload.get("note", ""))
        return {"ok": True}

    @app.get("/api/v1/settings")
    async def get_settings():
        return ctx.settings.as_dict()

    @app.put("/api/v1/settings")
    async def put_settings(payload: dict):
        return ctx.settings.set_many(payload)

    @app.get("/api/v1/ui/preferences")
    async def get_ui_preferences(request: Request):
        _, err = _auth(request, "operator")
        if err:
            return err
        return ctx.ui_prefs.get_all()

    @app.put("/api/v1/ui/preferences")
    async def put_ui_preferences(request: Request, payload: dict = Body(...)):
        _, err = _auth(request, "operator")
        if err:
            return err
        return ctx.ui_prefs.update(payload)

    # ------------------------------------------------------------------
    # Helpers de autorización por rol (Fase E)
    # ------------------------------------------------------------------
    def _auth(request: Request, min_role: str = "operator"):
        ok, claims = require_role(request, min_role)
        if not ok:
            return None, JSONResponse(
                status_code=403,
                content={"error": f"se requiere rol mínimo '{min_role}'"},
            )
        return claims, None

    def _safe_scan_path(p: str, cfg):

        path = Path(p)
        if not path.exists():
            return None, "ruta inexistente"
        allowed = [cfg.root, cfg.data_dir, Path(tempfile.gettempdir())]
        try:
            resolved = path.resolve()
        except Exception:
            return None, "ruta no resolubible"
        if any(str(resolved).startswith(str(a.resolve())) for a in allowed):
            return resolved, None
        return None, "ruta fuera del sandbox permitido"

    def _sub(request: Request) -> str:
        ok, claims = require_role(request, "operator")
        return claims.get("sub", "system") if ok else "system"

    def _now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Fase B: endpoints de gestión
    # ------------------------------------------------------------------
    @app.get("/api/v1/version")
    async def version():
        import platform as _platform
        import sys

        return {
            "version": "0.1.0",
            "build": (ctx.cfg.root / "BUILD").read_text(encoding="utf-8").strip()
            if (ctx.cfg.root / "BUILD").exists() else "dev",
            "python": sys.version.split()[0],
            "platform": _platform.platform(),
        }

    @app.post("/api/v1/auth/token")
    async def auth_token(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        role = payload.get("role", "operator")
        if role not in ("operator", "admin"):
            return JSONResponse(status_code=400, content={"error": "rol inválido"})
        sub = payload.get("sub", "cli")
        ttl = int(payload.get("ttl", 0) or 0)
        token = sign_token(ctx.auth_secret, role, sub=sub, ttl=ttl)
        return {"token": token, "role": role}

    @app.post("/api/v1/auth/login")
    async def auth_login(payload: dict, request: Request):
        """Login por usuario/clave. Ruta pública (rate-limited por IP).
        Emite un token HMAC firmado con el rol del usuario."""
        client_ip = request.client.host if request.client else "anon"
        if not ctx.limiter.is_allowed(client_ip):
            return JSONResponse(status_code=429, content={"error": "rate limit exceeded"})
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if not username or not password:
            return JSONResponse(status_code=400, content={"error": "username y password requeridos"})
        user = ctx.users.authenticate(username, password)
        if user is None:
            ctx.audit.append("auth_login", username, "unknown", "denied", {"ip": client_ip})
            return JSONResponse(status_code=401, content={"error": "credenciales inválidas"})
        ttl = int(payload.get("ttl", 0) or 0)
        token = sign_token(ctx.auth_secret, user["role"], sub=user["id"], ttl=ttl)
        ctx.audit.append("auth_login", username, user["role"], "success", {"ip": client_ip})
        return {"token": token, "role": user["role"], "username": user["username"]}

    @app.get("/api/v1/users")
    async def users_list(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        return ctx.users.list()

    @app.post("/api/v1/users")
    async def users_create(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        try:
            return ctx.users.create(
                payload["username"], payload["password"],
                role=payload.get("role", "operator"),
                enabled=bool(payload.get("enabled", True)),
                created_by="ui",
            )
        except (KeyError, ValueError) as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})

    @app.put("/api/v1/users")
    async def users_update(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        uid = payload.get("id")
        if not uid:
            return JSONResponse(status_code=400, content={"error": "id requerido"})
        try:
            updated = ctx.users.update(
                uid, role=payload.get("role"), password=payload.get("password"),
                enabled=payload.get("enabled"),
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        if updated is None:
            return JSONResponse(status_code=404, content={"error": "usuario no encontrado"})
        return updated

    @app.delete("/api/v1/users")
    async def users_delete(id: str, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        try:
            if not ctx.users.delete(id):
                return JSONResponse(status_code=404, content={"error": "usuario no encontrado"})
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return {"deleted": id}

    @app.post("/api/v1/rules")
    async def rules_create(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        try:
            rule = ctx.rules_store.create(
                payload["name"], payload.get("type", "yara"), payload["content"],
                enabled=bool(payload.get("enabled", True)), origin=payload.get("origin", "api"),
            )
        except (KeyError, ValueError) as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        if rule["type"] == "yara":
            ctx.engine.add_yara_rule(rule["name"], rule["content"])
        elif rule["type"] == "sigma":
            ctx.engine.add_sigma_rule_text(rule["name"], rule["content"])
        return rule

    @app.get("/api/v1/rules/managed")
    async def rules_managed(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        return ctx.rules_store.list_rules()

    @app.put("/api/v1/rules")
    async def rules_update(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        rid = payload.get("id")
        if not rid:
            return JSONResponse(status_code=400, content={"error": "id requerido"})
        updated = ctx.rules_store.update(
            rid, content=payload.get("content"), enabled=payload.get("enabled"),
            name=payload.get("name"),
        )
        if updated is None:
            return JSONResponse(status_code=404, content={"error": "regla no encontrada"})
        return updated

    @app.delete("/api/v1/rules")
    async def rules_delete(id: str, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        if not ctx.rules_store.delete(id):
            return JSONResponse(status_code=404, content={"error": "regla no encontrada"})
        return {"deleted": id}

    @app.post("/api/v1/rules/reload")
    async def rules_reload(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        enabled = ctx.rules_store.get_enabled("yara") + ctx.rules_store.get_enabled("sigma")
        result = ctx.engine.reload(enabled)
        ctx.audit.append("rules_reload", "admin", "admin", "executed", result)
        return result

    @app.post("/api/v1/alerts/{alert_id}/ack")
    async def alert_ack(alert_id: str, request: Request):
        ok, claims = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        acked = ctx.alert_store.ack(alert_id, claims.get("sub", "operator"))
        if acked is None:
            return JSONResponse(status_code=404, content={"error": "alerta no encontrada"})
        return acked

    @app.post("/api/v1/scan/yara")
    async def scan_yara(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        path_str = payload.get("path", "")
        if not path_str:
            return JSONResponse(status_code=400, content={"error": "path requerido"})
        resolved, verr = _safe_scan_path(path_str, ctx.cfg)
        if resolved is None:
            return JSONResponse(status_code=400, content={"error": verr})
        from argos.detection.yara_rules import scan_path as yara_scan_path

        if resolved.is_file():
            hits = ctx.engine.scan_file(resolved)
            hits = [{"file": str(resolved), **h} for h in hits]
        else:
            hits = yara_scan_path(ctx.engine.yara, resolved)
        return {"scanned": str(resolved), "hits": hits}

    @app.get("/api/v1/scan/capabilities")
    async def scan_capabilities(request: Request):
        ok, _ = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        return net_scan.capabilities()

    @app.post("/api/v1/scan/network")
    async def scan_network(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        target = str(payload.get("target", "")).strip()
        if not target:
            return JSONResponse(status_code=400, content={"error": "target requerido"})
        kinds = payload.get("kinds") or ["portscan", "ping", "dns"]
        ports = payload.get("ports")
        try:
            timeout = float(payload.get("timeout", 1.0))
        except (TypeError, ValueError):
            timeout = 1.0
        if ports:
            try:
                ports = [int(p) for p in ports][:2000]
            except (TypeError, ValueError):
                return JSONResponse(status_code=400, content={"error": "ports invalido"})
        try:
            result = net_scan.network_scan(target, kinds=kinds, ports=ports, timeout=timeout)
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})
        ctx.audit.append("scan_network", _sub(request), "admin", "executed",
                         {"target": target, "kinds": kinds})
        return result

    # ------------------------------------------------------------------
    # Fase K: monitoreo de red continuo + línea de base
    # ------------------------------------------------------------------
    @app.get("/api/v1/network/baseline")
    async def network_baseline(request: Request):
        ok, _ = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        return {
            "baselines": ctx.net_baseline.list_baselines(),
            "targets": ctx.net_baseline.list_targets(),
            "changes": ctx.net_baseline.get_changes(),
            "recent_scans": ctx.net_baseline.list_scans(limit=50),
        }

    @app.post("/api/v1/network/baseline")
    async def network_baseline_set(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        target = str(payload.get("target", "")).strip()
        if not target:
            return JSONResponse(status_code=400, content={"error": "target requerido"})
        ports = payload.get("open_ports")
        services = payload.get("services")
        if ports is None:
            # Si no se proveen puertos, fijar la base con un escaneo real.
            res = net_scan.network_scan(target, kinds=["portscan", "dns"], timeout=1.0)
            ports = res.get("results", {}).get("open_ports", [])
            services = {
                p["port"]: p["service"] for p in res.get("results", {}).get("portscan", [])
            }
        try:
            ports = [int(p) for p in ports]
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"error": "open_ports invalido"})
        if services is None:
            services = {p: "unknown" for p in ports}
        baseline = ctx.net_baseline.set_baseline(target, ports, services)
        ctx.audit.append("network_baseline_set", _sub(request), "admin", "executed",
                         {"target": target, "open_ports": ports})
        return baseline

    @app.get("/api/v1/network/targets")
    async def network_targets_list(request: Request):
        ok, _ = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        return {"targets": ctx.net_baseline.list_targets()}

    @app.post("/api/v1/network/targets")
    async def network_targets_add(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        target = str(payload.get("target", "")).strip()
        if not target:
            return JSONResponse(status_code=400, content={"error": "target requerido"})
        ctx.net_baseline.add_target(target, by=_sub(request))
        return {"added": target, "targets": ctx.net_baseline.list_targets()}

    @app.delete("/api/v1/network/targets")
    async def network_targets_del(target: str, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        removed = ctx.net_baseline.remove_target(target)
        if not removed:
            return JSONResponse(status_code=404, content={"error": "host no monitoreado"})
        return {"removed": target}

    @app.post("/api/v1/network/scan/schedule")
    async def network_scan_schedule(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        target = str(payload.get("target", "")).strip()
        if not target:
            return JSONResponse(status_code=400, content={"error": "target requerido"})
        kinds = payload.get("kinds") or ["portscan", "ping", "dns", "connections"]
        ports = payload.get("ports")
        try:
            timeout = float(payload.get("timeout", 1.0))
        except (TypeError, ValueError):
            timeout = 1.0
        if ports:
            try:
                ports = [int(p) for p in ports][:2000]
            except (TypeError, ValueError):
                return JSONResponse(status_code=400, content={"error": "ports invalido"})
        try:
            outcome = run_monitor_scan(
                ctx, target, kinds=kinds, ports=ports, timeout=timeout, by=_sub(request)
            )
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})
        return outcome

    @app.get("/api/v1/ioc")
    async def ioc_list(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        return {"iocs": ctx.intel.list()}

    @app.post("/api/v1/ioc")
    async def ioc_add(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        indicator = str(payload.get("indicator", "")).strip()
        if not indicator:
            return JSONResponse(status_code=400, content={"error": "indicator requerido"})
        ctx.intel.add(indicator)
        ctx.audit.append("ioc_add", _sub(request), "admin", "executed", {"indicator": indicator})
        return {"added": indicator, "total": len(ctx.intel.list())}

    @app.delete("/api/v1/ioc")
    async def ioc_delete(indicator: str, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        removed = ctx.intel.remove(indicator)
        if not removed:
            return JSONResponse(status_code=404, content={"error": "indicador no encontrado"})
        return {"removed": indicator}

    @app.get("/api/v1/threat-intel/feeds")
    async def ti_feeds(request: Request):
        _, err = _auth(request, "operator")
        if err:
            return err
        from argos.detection.ti_feeds import load_feeds

        return {"feeds": [f.__dict__ for f in load_feeds()]}

    @app.post("/api/v1/cases")
    async def cases_create(payload: dict, request: Request):
        ok, claims = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        try:
            case = ctx.cases.create(
                payload["title"],
                severity=str(payload.get("severity", "medium")),
                status=str(payload.get("status", "open")),
                assigned_to=payload.get("assigned_to"),
                description=payload.get("description"),
                linked_alerts=payload.get("linked_alerts"),
                linked_hosts=payload.get("linked_hosts"),
            )
        except (KeyError, ValueError) as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        ctx.audit.append("case_create", claims.get("sub", "operator"), "operator", "executed",
                         {"id": case["id"]})
        return case

    @app.get("/api/v1/cases")
    async def cases_list(status: str | None = None, request: Request = None):  # type: ignore[assignment]
        ok, _ = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        return ctx.cases.list(status=status)

    @app.get("/api/v1/cases/{case_id}")
    async def cases_get(case_id: str, request: Request):
        ok, _ = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        case = ctx.cases.get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"error": "caso no encontrado"})
        return case

    @app.put("/api/v1/cases/{case_id}")
    async def cases_update(case_id: str, payload: dict, request: Request):
        ok, claims = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        updated = ctx.cases.update(case_id, **payload)
        if updated is None:
            return JSONResponse(status_code=404, content={"error": "caso no encontrado"})
        ctx.audit.append("case_update", claims.get("sub", "operator"), "operator", "executed",
                         {"id": case_id})
        return updated

    @app.post("/api/v1/cases/{case_id}/notes")
    async def cases_note(case_id: str, payload: dict, request: Request):
        ok, claims = require_role(request, "operator")
        if not ok:
            return JSONResponse(status_code=403, content={"error": "rol operator requerido"})
        text = str(payload.get("text", "")).strip()
        if not text:
            return JSONResponse(status_code=400, content={"error": "text requerido"})
        note = ctx.cases.add_note(case_id, claims.get("sub", "operator"), text)
        if note is None:
            return JSONResponse(status_code=404, content={"error": "caso no encontrado"})
        return note

    @app.post("/api/v1/backup")
    async def backup(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        import shutil as _shutil

        dest = payload.get("path") or str(ctx.cfg.data_dir / "backups")
        from pathlib import Path as _Path

        d = _Path(dest)
        d.mkdir(parents=True, exist_ok=True)
        stamp = _now().replace(":", "").replace("-", "").replace(".", "")
        target = d / f"argos_{stamp}.db"
        try:
            _shutil.copy2(ctx.store.db_path, target)
            for suffix in ("-wal", "-shm"):
                src = ctx.store.db_path.with_suffix(ctx.store.db_path.suffix + suffix)
                if src.exists():
                    _shutil.copy2(src, str(target) + suffix)
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})
        ctx.audit.append("backup", _sub(request), "admin", "executed", {"path": str(target)})
        return {"backup": str(target)}

    @app.get("/api/v1/processes")
    async def processes(host: str | None = None, limit: int = 200):
        return ctx.store.process_inventory(host=host, limit=limit)

    @app.post("/api/v1/actions/execute")
    async def actions_execute(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        action: str = payload.get("action") or ""
        target: str = payload.get("target") or ""
        by = payload.get("approved_by", "ui")
        try:
            proposal = ctx.response.force_execute(
                action, target, payload.get("params"), by)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return {"id": proposal.id, "status": proposal.status, "result": proposal.result,
                "action": proposal.action, "target": proposal.target}

    @app.post("/api/v1/actions/undo")
    async def actions_undo(payload: dict, request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        pid = payload.get("proposal_id")
        if not pid:
            return JSONResponse(status_code=400, content={"error": "proposal_id requerido"})
        by = payload.get("approved_by", "ui")
        try:
            proposal, result = ctx.response.undo(pid, by)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return {"id": proposal.id, "status": proposal.status, "result": result}

    @app.post("/api/v1/proposals/{proposal_id}/reject")
    async def proposal_reject(proposal_id: str, request: Request, payload: dict | None = None):
        by = (payload or {}).get("rejected_by", "ui") if payload else "ui"
        try:
            proposal = ctx.response.reject(proposal_id, by)
        except ValueError as exc:
            return JSONResponse(status_code=404, content={"error": str(exc)})
        return {"id": proposal.id, "status": proposal.status}

    @app.get("/api/v1/audit/verify")
    async def audit_verify():
        return {"chain_valid": ctx.audit.verify_chain()}

    @app.get("/api/v1/export")
    async def export_data(kind: str = "events", fmt: str = "json", limit: int = 1000):
        if kind == "alerts":
            rows = ctx.alert_store.recent(limit=limit)
        elif kind == "audit":
            rows = ctx.audit.all(limit=limit)
        else:
            rows = [e.as_dict() for e in ctx.store.query(limit=limit)]
        if fmt == "csv":
            import csv
            import io

            buf = io.StringIO()
            if rows:
                writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)
            return Response(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={kind}.csv"})
        return rows

    @app.get("/api/v1/logs")
    async def logs_filtered(level: str | None = None, host: str | None = None,
                            since: str | None = None, until: str | None = None,
                            contains: str | None = None, limit: int = 500):
        log_path = ctx.cfg.data_dir / "argos.log"
        if not log_path.exists():
            return []
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for ln in lines:
            if level and level.upper() not in ln.upper():
                continue
            if contains and contains.lower() not in ln.lower():
                continue
            if since and ln[:19] < since[:19]:
                continue
            if until and ln[:19] > until[:19]:
                continue
            out.append(ln)
            if len(out) >= limit:
                break
        return out

    @app.get("/api/v1/health/deep")
    async def health_deep():
        import shutil

        checks: dict[str, Any] = {}
        db = ctx.cfg.data_dir / "argos.db"
        adb = ctx.cfg.data_dir / "audit.db"
        checks["database"] = {
            "path": str(db), "exists": db.exists(),
            "writable": os.access(str(db.parent), os.W_OK),
        }
        checks["audit_db"] = {"path": str(adb), "exists": adb.exists(),
                              "writable": os.access(str(adb.parent), os.W_OK)}
        checks["engine"] = {
            "sigma_rules": len(ctx.engine.rules),
            "yara_rules": len(ctx.engine.yara.rules),
            "yara_native": ctx.engine.yara.use_native,
        }
        checks["agent"] = {
            "realtime_enabled": ctx.cfg.realtime_enabled,
            "mode": "simulated" if not ctx.cfg.realtime_enabled else "realtime",
        }
        checks["gateway"] = {"base_url": ctx.cfg.gateway_base_url, "reachable": "not_checked"}
        try:
            du = shutil.disk_usage(str(ctx.cfg.data_dir))
            checks["disk"] = {
                "free_mb": round(du.free / (1024 * 1024), 1),
                "total_mb": round(du.total / (1024 * 1024), 1),
            }
        except Exception:
            checks["disk"] = {"error": "no disponible"}
        ok = all(c.get("exists", True) for c in (checks["database"], checks["audit_db"]))
        checks["status"] = "ok" if ok else "degraded"
        return checks

    @app.get("/api/v1/switch/audit")
    async def switch_audit(limit: int = 100):
        rows = ctx.audit.all(limit=limit * 4)
        return [r for r in rows if "switch" in r.get("action", "").lower()][:limit]

    @app.post("/api/v1/settings/test")
    async def settings_test(request: Request, payload: dict | None = None):
        if request is not None:
            _, err = _auth(request, "admin")
            if err:
                return err
        from argos.config import ConfigError, validate_config

        test_cfg = Config()
        test_cfg.data_dir = ctx.cfg.data_dir
        if payload:
            for k, v in payload.items():
                if hasattr(test_cfg, k):
                    setattr(test_cfg, k, v)
        try:
            validate_config(test_cfg)
            return {"valid": True, "errors": []}
        except ConfigError as exc:
            return {"valid": False, "errors": [str(exc)]}

    @app.websocket("/ws")
    async def ws(ws: WebSocket):
        token = ws_token_from_request(ws)
        claims = authorize_ws(cfg, ctx.auth_secret, token)
        if claims is None:
            await ws.close(code=1008, reason="unauthorized")
            return
        await ws.accept()
        await ctx.manager.connect(ws)
        try:
            while True:
                data = await ws.receive_json()
                kind = data.get("type")
                if kind == "chat":
                    try:
                        answer = await asyncio.to_thread(
                            ctx.orchestrator.chat, data.get("message", ""),
                            data.get("history"), data.get("session"),
                            role=claims.get("role", "admin"))
                    except Exception as exc:  # T3.4: respuesta controlada, no excepcion cruda
                        answer = (f"[ARGOS] No pude contactar al cerebro (modo avion/no configurado). "
                                  f"Detalle: {exc}")
                    await ctx.manager.send(ws, {"type": "chat", "role": "assistant", "content": answer})
                elif kind == "chat_stream":
                    await _stream_chat(ctx, ws, data, role=claims.get("role", "admin"))
                elif kind == "switch":
                    if claims.get("role") != "admin":
                        await ctx.manager.send(ws, {"type": "error", "content": "admin role required"})
                        continue
                    try:
                        lvl = SwitchLevel(data.get("level"))
                        ctx.response.set_level(lvl)
                        ctx.settings.set("switch.default", lvl.value)
                        await ctx.manager.send(ws, {"type": "switch", **ctx.response.switch.as_dict()})
                    except ValueError:
                        await ctx.manager.send(ws, {"type": "error", "content": "invalid level"})
                elif kind == "confirm":
                    try:
                        proposal = ctx.response.confirm(
                            data["id"], data.get("approved_by", "user"))
                        payload = {"type": "proposal", "id": proposal.id,
                                   "status": proposal.status, "result": proposal.result}
                        await ctx.manager.send(ws, payload)
                        await ctx.manager.broadcast(payload)
                    except (KeyError, ValueError) as exc:
                        await ctx.manager.send(ws, {"type": "error", "content": str(exc)})
                else:
                    await ctx.manager.send(ws, {"type": "error", "content": "unknown message type"})
        except WebSocketDisconnect:
            ctx.manager.disconnect(ws)

    # --- MCP (Model Context Protocol) endpoints ----------------------------------
    @app.post("/api/v1/mcp")
    async def mcp_http(request: Request, payload: dict = Body(...)):
        role = "admin"
        if cfg.require_auth:
            claims, err = _auth(request, "operator")
            if err:
                return err
            role = claims.get("role", "operator")
        from argos.observability.metrics import MCP_REQUESTS, metrics
        out = await asyncio.to_thread(ctx.mcp.handle, payload, role)
        if "error" not in out:
            metrics.inc(MCP_REQUESTS, 1)
        return out

    @app.websocket("/api/v1/mcp/ws")
    async def mcp_ws(ws: WebSocket):
        token = ws_token_from_request(ws)
        claims = authorize_ws(cfg, ctx.auth_secret, token)
        if claims is None:
            await ws.close(code=1008, reason="unauthorized")
            return
        await ws.accept()
        role = claims.get("role", "operator")
        try:
            while True:
                data = await ws.receive_json()
                out = await asyncio.to_thread(ctx.mcp.handle, data, role)
                await ws.send_json(out)
        except WebSocketDisconnect:
            pass

    # --- Plugin System endpoints ------------------------------------------------
    @app.get("/api/v1/plugins")
    async def plugins_list(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        return {
            "installed": ctx.plugin_registry.list_installed(),
            "marketplace": ctx.plugin_registry.available_in_marketplace(),
        }

    @app.post("/api/v1/plugins/install")
    async def plugin_install(request: Request, payload: dict = Body(...)):
        _, err = _auth(request, "admin")
        if err:
            return err
        name = payload.get("name")
        if not name:
            return JSONResponse({"error": "name requerido"}, status_code=400)
        manifest = ctx.plugin_registry.available_in_marketplace()
        from argos.plugins.marketplace import MARKETPLACE

        m = MARKETPLACE.get(name) or next(
            (p for p in manifest if p["name"] == name), None
        )
        if m is None:
            return JSONResponse({"error": f"plugin '{name}' no esta en el marketplace"}, status_code=404)
        from argos.plugins.base import PluginManifest

        man = m if isinstance(m, PluginManifest) else PluginManifest.from_dict(m)
        ok = ctx.plugin_manager.install(man)
        return {"installed": ok, "name": name}

    @app.post("/api/v1/plugins/uninstall")
    async def plugin_uninstall(request: Request, payload: dict = Body(...)):
        _, err = _auth(request, "admin")
        if err:
            return err
        name = payload.get("name")
        if not name:
            return JSONResponse({"error": "name requerido"}, status_code=400)
        ok = ctx.plugin_manager.uninstall(name)
        return {"uninstalled": ok, "name": name}

    @app.post("/api/v1/plugins/{name}/enable")
    async def plugin_enable(request: Request, name: str):
        _, err = _auth(request, "admin")
        if err:
            return err
        return {"enabled": ctx.plugin_manager.enable(name), "name": name}

    @app.post("/api/v1/plugins/{name}/disable")
    async def plugin_disable(request: Request, name: str):
        _, err = _auth(request, "admin")
        if err:
            return err
        return {"disabled": ctx.plugin_manager.disable(name), "name": name}

    # --- Tool Gateway & Observability endpoints ---------------------------------
    @app.get("/api/v1/gateway/metrics")
    async def gateway_metrics(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        return ctx.gateway.metrics()

    @app.post("/api/v1/gateway/breaker/reset")
    async def gateway_reset_breaker(request: Request, payload: dict = Body(...)):
        _, err = _auth(request, "admin")
        if err:
            return err
        name = payload.get("name")
        if not name:
            return JSONResponse({"error": "name requerido"}, status_code=400)
        return {"reset": ctx.gateway.reset_breaker(name), "name": name}

    @app.get("/api/v1/observability/metrics")
    async def observability_metrics(request: Request):
        _, err = _auth(request, "admin")
        if err:
            return err
        from argos.observability.metrics import ACTIVE_ALERTS, metrics

        metrics.set_gauge(ACTIVE_ALERTS, len(ctx.alert_store.recent(limit=1000)))
        return {"metrics": metrics.snapshot(), "prometheus": metrics.render_prometheus()}

    @app.get("/api/v1/observability/health")
    async def observability_health(request: Request):
        _, err = _auth(request, "operator")
        if err:
            return err
        return ctx.health_registry.run()

    if UI_DIR.exists():
        app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

        @app.get("/")
        async def index():
            return FileResponse(UI_DIR / "index.html")

    return app


async def _stream_chat(ctx: AppContext, ws: Any, data: dict, role: str = "admin") -> None:
    history = data.get("history")
    session = data.get("session")
    try:
        for chunk in ctx.orchestrator.chat_stream(data.get("message", ""), history, session,
                                                  role=role):
            await ctx.manager.send(ws, {"type": "chat_stream", **chunk})
            if chunk.get("type") == "token":
                await asyncio.sleep(0)
    except Exception as exc:  # T3.4: respuesta controlada en modo avion
        await ctx.manager.send(ws, {"type": "chat_stream", "stream_type": "done",
                                    "content": f"[ARGOS] No pude contactar al cerebro: {exc}"})


def main() -> None:
    import uvicorn

    cfg = get_config()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.server_host, port=cfg.server_port, log_level="info")


if __name__ == "__main__":
    main()
