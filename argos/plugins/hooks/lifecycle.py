from __future__ import annotations

import time
from typing import Any, Dict

from argos.plugins.base import HookEvent
from argos.plugins.hooks.base import BaseHook


class PreDetectionHook(BaseHook):
    """Valida y enriquece el evento antes de la evaluación del motor."""

    def __init__(self, priority: int = 10) -> None:
        super().__init__(HookEvent.PRE_DETECTION, priority)

    def execute(self, context: Dict[str, Any]) -> Any:
        event = context.get("event")
        if event is None:
            return context
        context.setdefault("enriched", True)
        context.setdefault("ingest_ts", time.time())
        return context


class PostDetectionHook(BaseHook):
    """Registra y reacciona ante resultados de detección (alertas)."""

    def __init__(self, priority: int = 10) -> None:
        super().__init__(HookEvent.POST_DETECTION, priority)

    def execute(self, context: Dict[str, Any]) -> Any:
        result = context.get("result") or {}
        alert = result.get("alert")
        severity = result.get("severity") or (alert or {}).get("severity")
        if severity in ("critical", "high"):
            context.setdefault("requires_attention", True)
        return context


class PreResponseHook(BaseHook):
    """Último filtro antes de que una acción pase por el switch de autonomía."""

    def __init__(self, priority: int = 10) -> None:
        super().__init__(HookEvent.PRE_RESPONSE, priority)

    def execute(self, context: Dict[str, Any]) -> Any:
        context.setdefault("validated", True)
        return context


class PostResponseHook(BaseHook):
    """Audita y propaga el resultado de una respuesta ejecutada."""

    def __init__(self, priority: int = 10) -> None:
        super().__init__(HookEvent.POST_RESPONSE, priority)

    def execute(self, context: Dict[str, Any]) -> Any:
        result = context.get("result") or {}
        if result.get("status") in ("executed", "undone", "rejected"):
            context.setdefault("response_recorded", True)
        return context


class OnAlertHook(BaseHook):
    """Reacciona a la creación de una alerta (notificación / enriquecimiento)."""

    def __init__(self, priority: int = 10) -> None:
        super().__init__(HookEvent.ON_ALERT, priority)

    def execute(self, context: Dict[str, Any]) -> Any:
        alert = context.get("alert") or {}
        if alert.get("severity") == "critical":
            context.setdefault("notify", True)
        return context
