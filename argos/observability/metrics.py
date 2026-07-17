from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional


class Metrics:
    """Registro de metricas en memoria (estilo Prometheus) sin dependencias externas.

    Expone contadores, histrogramas y gauges con un renderizador de texto plano
    compatible con Prometheus para facilitar scrapeo futuro.
    """

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._labels: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(name: str, labels: Optional[tuple]) -> str:
        if not labels:
            return name
        parts = ",".join(str(label) for label in labels)
        return f"{name}{{{parts}}}"

    def inc(self, name: str, amount: float = 1.0, labels: Optional[tuple] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + amount
            if labels is not None:
                self._labels[key] = labels

    def set_gauge(self, name: str, value: float, labels: Optional[tuple] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value
            if labels is not None:
                self._labels[key] = labels

    def observe(self, name: str, value: float, labels: Optional[tuple] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._histograms.setdefault(key, []).append(value)
            if labels is not None:
                self._labels[key] = labels

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: {"count": len(v), "sum": sum(v)} for k, v in self._histograms.items()},
            }

    def render_prometheus(self) -> str:
        lines: List[str] = []
        with self._lock:
            for key, value in self._counters.items():
                lines.append(f"# TYPE {self._base(key)} counter")
                lines.append(f"{key} {value}")
            for key, value in self._gauges.items():
                lines.append(f"# TYPE {self._base(key)} gauge")
                lines.append(f"{key} {value}")
            for key, values in self._histograms.items():
                total = sum(values)
                lines.append(f"# TYPE {self._base(key)} histogram")
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {total}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _base(key: str) -> str:
        return key.split("{", 1)[0]


class Tracer:
    """Tracer ligero para spans (open telemetry-compatible en forma basica)."""

    def __init__(self) -> None:
        self._spans: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        return Span(self, name, attributes or {})

    def record(self, span: "Span") -> None:
        with self._lock:
            self._spans.append(span.to_dict())
            if len(self._spans) > 1000:
                self._spans.pop(0)

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._spans[-limit:])


class Span:
    def __init__(self, tracer: Tracer, name: str, attributes: Dict[str, Any]) -> None:
        self.tracer = tracer
        self.name = name
        self.attributes = attributes
        self.start = time.time()
        self.end: Optional[float] = None

    def __enter__(self) -> "Span":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.end = time.time()
        if exc_type is not None:
            self.attributes["error"] = str(exc)
        self.tracer.record(self)

    def to_dict(self) -> Dict[str, Any]:
        duration = (self.end - self.start) if self.end else None
        return {
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "duration_ms": round(duration * 1000.0, 2) if duration else None,
            "attributes": self.attributes,
        }


# Instancias globales del sistema.
metrics = Metrics()
tracer = Tracer()

# Metricas semanticas del dominio.
EVENTS_PROCESSED = "argos_events_processed_total"
DETECTION_LATENCY = "argos_detection_latency_seconds"
ACTIVE_ALERTS = "argos_active_alerts"
TOOL_EXECUTION_TIME = "argos_tool_execution_seconds"
AI_RESPONSE_TIME = "argos_ai_response_seconds"
MCP_REQUESTS = "argos_mcp_requests_total"
PLUGIN_HOOK_EXECUTIONS = "argos_plugin_hook_executions_total"
