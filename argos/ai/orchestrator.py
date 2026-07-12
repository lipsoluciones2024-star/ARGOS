from __future__ import annotations

import json
from typing import Any, Callable, Iterator, Optional

from argos.ai.client import ChatMessage
from argos.ai.privacy import guard_privacy
from argos.ai.prompts import system_prompt
from argos.ai.router import HybridRouter
from argos.ai.tools import ToolExecutor, tool_schemas
from argos.config import Config
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.storage.settings import SettingsStore
from argos.storage.store import AlertStore, EventStore


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
    ) -> None:
        self.cfg = cfg
        self.store = store
        self.engine = engine
        self.intel = intel
        self.alert_store = alert_store
        self.router = HybridRouter(cfg)
        self.tools = ToolExecutor(store, engine, intel)
        self.on_push = on_push
        self.settings = settings
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
                    "temperature": 0.2, "max_tokens": 1024}
        return {
            "mode": self.settings.get_str("ai.mode", self.cfg.llm_mode.value),
            "model": self.settings.get_str("ai.model") or None,
            "temperature": self.settings.get_float("ai.temperature", 0.2),
            "max_tokens": self.settings.get_int("ai.max_tokens", 1024),
        }

    def _build_messages(self, user_message: str, history: Optional[list[dict[str, Any]]]) -> list[ChatMessage]:
        messages: list[ChatMessage] = [ChatMessage("system", self._system())]
        for h in history or []:
            messages.append(ChatMessage(h.get("role", "user"), h.get("content")))
        messages.append(ChatMessage("user", guard_privacy(user_message)))
        return messages

    def _finalize_tool_turn(self, messages: list[ChatMessage], tool_calls, buffer: str) -> None:
        messages.append(ChatMessage("assistant", buffer, [tc.to_dict() for tc in tool_calls]))
        for tc in tool_calls:
            if self.tools.validate(tc.name):
                result = self.tools.execute(tc.name, tc.arguments)
                messages.append(ChatMessage("tool", json.dumps(result.output, default=str),
                                            name=tc.name, tool_call_id=tc.id))
            else:
                messages.append(ChatMessage("tool", json.dumps({"error": "tool not allowed"}),
                                            name=tc.name, tool_call_id=tc.id))

    def chat(self, user_message: str, history: Optional[list[dict[str, Any]]] = None) -> str:
        messages = self._build_messages(user_message, history)
        runtime = self._runtime()
        last = ""
        for _ in range(self.max_iter):
            resp = self.router.chat(messages, tools=tool_schemas(), runtime=runtime)
            last = resp.content or ""
            if not resp.tool_calls:
                return last
            messages.append(ChatMessage("assistant", last, [tc.to_dict() for tc in resp.tool_calls]))
            for tc in resp.tool_calls:
                if self.tools.validate(tc.name):
                    result = self.tools.execute(tc.name, tc.arguments)
                    messages.append(ChatMessage("tool", json.dumps(result.output, default=str),
                                                name=tc.name, tool_call_id=tc.id))
                else:
                    messages.append(ChatMessage("tool", json.dumps({"error": "tool not allowed"}),
                                                name=tc.name, tool_call_id=tc.id))
        return last

    def chat_stream(self, user_message: str, history: Optional[list[dict[str, Any]]] = None) -> Iterator[dict[str, Any]]:
        messages = self._build_messages(user_message, history)
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
                    yield {"type": "token", "content": chunk.content}
            if tool_calls:
                self._finalize_tool_turn(messages, tool_calls, buffer)
                for tc in tool_calls:
                    yield {"type": "tool", "name": tc.name,
                           "arguments": tc.arguments.get("arguments", tc.arguments)
                           if isinstance(tc.arguments, dict) else tc.arguments}
                continue
            full = buffer
            break
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
