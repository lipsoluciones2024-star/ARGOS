from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterator, Optional

from argos.ai.client import ChatMessage
from argos.ai.privacy import guard_privacy
from argos.ai.prompts import FEW_SHOT, system_prompt
from argos.ai.router import HybridRouter
from argos.ai.tools import ToolExecutor, ToolResult, tool_schemas
from argos.config import Config
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.response.orchestrator import ResponseOrchestrator
from argos.storage.chatlog import ChatLog
from argos.storage.memory import MemoryStore
from argos.storage.settings import SettingsStore
from argos.storage.store import AlertStore, EventStore

_THINK_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_TC_RE = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL | re.IGNORECASE)
_WARN_RE = re.compile(r"^\s*(?:⚠️\s*)?(?:warning|aviso|note)[\s:].*$", re.IGNORECASE | re.MULTILINE)


def _sanitize(text: str) -> str:
    """Limpia la salida del modelo: quita bloques de razonamiento, tool-calls crudos
    y lineas de warning/aviso del sistema que el modelo libre a veces escupe."""
    if not isinstance(text, str):
        return text
    text = _THINK_RE.sub("", text)
    text = _TC_RE.sub("", text)
    text = _WARN_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_streaming(text: str) -> str:
    text = _THINK_RE.sub("", text)
    text = _TC_RE.sub("", text)
    if re.search(r"<thinking>", text, re.IGNORECASE):
        text = re.split(r"<thinking>", text, flags=re.IGNORECASE)[0]
    return text


class AiOrchestrator:
    def __init__(
        self,
        cfg: Config,
        store: EventStore,
        engine: DetectionEngine,
        intel: ThreatIntel,
        alert_store: AlertStore,
        on_push: Optional[Callable[[dict[str, Any]], None]] = None,
        settings: Optional[SettingsStore] = None,
        response: Optional[ResponseOrchestrator] = None,
        on_proposal: Optional[Callable[[dict[str, Any]], None]] = None,
        chatlog: Optional[ChatLog] = None,
        memory: Optional[MemoryStore] = None,
        context: Optional[Any] = None,
    ) -> None:
        self.cfg = cfg
        self.store = store
        self.engine = engine
        self.intel = intel
        self.alert_store = alert_store
        self.router = HybridRouter(cfg)
        self.tools = ToolExecutor(store, engine, intel, response=response)
        self.response = response
        self.on_push = on_push
        self.on_proposal = on_proposal
        self.settings = settings
        self.chatlog = chatlog
        self.memory = memory
        self.context = context
        self.max_iter = 6

    def _system(self) -> str:
        if self.settings:
            custom = self.settings.get_str("ai.system_prompt")
            if custom:
                return custom
        return system_prompt()

    def _runtime(self) -> dict[str, Any]:
        if not self.settings:
            return {"mode": self.cfg.llm_mode.value, "model": None,
                    "temperature": 0.3, "max_tokens": 2048}
        return {
            "mode": self.settings.get_str("ai.mode", self.cfg.llm_mode.value),
            "model": self.settings.get_str("ai.model") or None,
            "temperature": self.settings.get_float("ai.temperature", 0.3),
            "max_tokens": self.settings.get_int("ai.max_tokens", 2048),
        }

    def _build_messages(self, user_message: str, history: Optional[list[dict[str, Any]]],
                         context: Optional[str] = None) -> list[ChatMessage]:
        messages: list[ChatMessage] = [ChatMessage("system", self._system())]
        if context:
            messages.append(ChatMessage("system", context))
        for ex in FEW_SHOT:
            messages.append(ChatMessage(
                ex["role"], ex.get("content"),
                tool_calls=ex.get("tool_calls", []),
                name=ex.get("name"), tool_call_id=ex.get("tool_call_id"),
            ))
        for h in history or []:
            messages.append(ChatMessage(h.get("role", "user"), h.get("content")))
        messages.append(ChatMessage("user", guard_privacy(user_message)))
        return messages

    def _emit_proposal(self, tc_name: str, result: "ToolResult") -> None:
        if self.on_proposal and isinstance(result.output, dict) and result.output.get("id"):
            self.on_proposal(result.output)

    def _finalize_tool_turn(self, messages: list[ChatMessage], tool_calls, buffer: str, role: str = "admin") -> None:
        messages.append(ChatMessage("assistant", buffer, [tc.to_dict() for tc in tool_calls]))
        for tc in tool_calls:
            if self.tools.validate(tc.name):
                result = self.tools.execute(tc.name, tc.arguments, role=role)
                self._emit_proposal(tc.name, result)
                messages.append(ChatMessage("tool", json.dumps(result.output, default=str),
                                            name=tc.name, tool_call_id=tc.id))
            else:
                messages.append(ChatMessage("tool", json.dumps({"error": "tool not allowed"}),
                                            name=tc.name, tool_call_id=tc.id))

    def chat(self, user_message: str, history: Optional[list[dict[str, Any]]] = None,
              session: Optional[str] = None, role: str = "admin") -> str:
        history = self._resolve_history(history, session)
        context = self.context.build(user_message, session) if self.context else None
        messages = self._build_messages(user_message, history, context)
        runtime = self._runtime()
        last = ""
        for _ in range(self.max_iter):
            resp = self.router.chat(messages, tools=tool_schemas(), runtime=runtime)
            last = resp.content or ""
            if not resp.tool_calls:
                self._persist(session, user_message, last)
                return _sanitize(last)
            messages.append(ChatMessage("assistant", last, [tc.to_dict() for tc in resp.tool_calls]))
            for tc in resp.tool_calls:
                if self.tools.validate(tc.name):
                    result = self.tools.execute(tc.name, tc.arguments, role=role)
                    self._emit_proposal(tc.name, result)
                    messages.append(ChatMessage("tool", json.dumps(result.output, default=str),
                                                name=tc.name, tool_call_id=tc.id))
                else:
                    messages.append(ChatMessage("tool", json.dumps({"error": "tool not allowed"}),
                                                name=tc.name, tool_call_id=tc.id))
        self._persist(session, user_message, last)
        return _sanitize(last)

    def _resolve_history(self, history: Optional[list[dict[str, Any]]],
                         session: Optional[str]) -> Optional[list[dict[str, Any]]]:
        if history:
            return history
        if self.chatlog and session:
            return self.chatlog.history(session)
        return None

    def _persist(self, session: Optional[str], user: str, assistant: str) -> None:
        if not self.chatlog or not session:
            return
        try:
            self.chatlog.add(session, "user", user)
            self.chatlog.add(session, "assistant", assistant)
        except Exception:
            pass

    def chat_stream(self, user_message: str, history: Optional[list[dict[str, Any]]] = None,
                     session: Optional[str] = None, role: str = "admin") -> Iterator[dict[str, Any]]:
        history = self._resolve_history(history, session)
        context = self.context.build(user_message, session) if self.context else None
        messages = self._build_messages(user_message, history, context)
        runtime = self._runtime()
        yield {"type": "begin", "channel": self.router.channel()}
        full = ""
        for _ in range(self.max_iter):
            buffer = ""
            tool_calls = []
            for chunk in self.router.stream(messages, tools=tool_schemas(), runtime=runtime):
                for tc in chunk.tool_calls:
                    tool_calls.append(tc)
                if chunk.content:
                    buffer += chunk.content
                    yield {"type": "token", "content": _strip_streaming(chunk.content)}
            if tool_calls:
                self._finalize_tool_turn(messages, tool_calls, buffer, role)
                for tc in tool_calls:
                    yield {"type": "tool", "name": tc.name,
                           "arguments": tc.arguments.get("arguments", tc.arguments)
                           if isinstance(tc.arguments, dict) else tc.arguments}
                continue
            full = _sanitize(buffer)
            break
        self._persist(session, user_message, full)
        yield {"type": "done", "content": full, "channel": self.router.channel()}

    def push_high_alerts(self) -> list[dict[str, Any]]:
        alerts = self.alert_store.high_or_critical(limit=20)
        pushed: list[dict[str, Any]] = []
        for a in alerts:
            if self.on_push:
                payload = {
                    "type": "proactive_alert",
                    "alert": a,
                    "message": f"[ALERTA {a['severity'].upper()}] {a['title']} en {a['host']}",
                }
                self.on_push(payload)
                pushed.append(payload)
        return pushed

    def channel(self) -> str:
        return self.router.channel()

    def status(self) -> dict[str, Any]:
        status = self.router.status()
        if self.settings:
            status["enabled"] = self.settings.get_bool("ai.enabled", True)
            status["mode_setting"] = self.settings.get_str("ai.mode", self.cfg.llm_mode.value)
            status["model_setting"] = self.settings.get_str("ai.model") or "auto"
        return status
