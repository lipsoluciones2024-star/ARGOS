from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from argos.ai.tools.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from argos.ai.tools.registry import ToolExecutor
from argos.ai.tools.retry import RetryPolicy, with_retry, with_timeout

logger = logging.getLogger("argos.ai.tools.gateway")


@dataclass
class ToolGatewayConfig:
    default_timeout: float = 30.0
    default_retry: RetryPolicy = field(default_factory=RetryPolicy)
    circuit: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    rate_limit_per_min: int = 60
    enforce_permissions: bool = True


class PerToolRateLimiter:
    """Rate limit por herramienta (ventana deslizante simple)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(1, per_minute)
        self._hits: Dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, name: str) -> bool:
        now = time.time()
        window = 60.0
        with self._lock:
            hits = self._hits.setdefault(name, [])
            hits[:] = [t for t in hits if now - t < window]
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            return True

    def status(self, name: str) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(name, []) if now - t < 60.0]
            return {"calls_last_minute": len(hits), "limit": self.per_minute}


class ToolGateway:
    """Tool Gateway avanzado (Cyber Brain).

    Envuelve el ToolExecutor del nucleo agregando: validacion de argumentos,
    timeout configurable, reintentos con backoff exponencial, circuit breaker
    por tool y rate limit por tool. Tambien expone metricas de ejecucion.
    """

    def __init__(self, executor: ToolExecutor, cfg: Optional[ToolGatewayConfig] = None) -> None:
        self.executor = executor
        self.cfg = cfg or ToolGatewayConfig()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._rate = PerToolRateLimiter(self.cfg.rate_limit_per_min)
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _breaker(self, name: str) -> CircuitBreaker:
        with self._lock:
            br = self._breakers.get(name)
            if br is None:
                br = CircuitBreaker(self.cfg.circuit)
                self._breakers[name] = br
            return br

    def _record(self, name: str, ok: bool, elapsed: float) -> None:
        with self._lock:
            m = self._metrics.setdefault(name, {"calls": 0, "errors": 0, "total_ms": 0.0, "last_ms": 0.0})
            m["calls"] += 1
            m["total_ms"] += elapsed * 1000.0
            m["last_ms"] = elapsed * 1000.0
            if not ok:
                m["errors"] += 1

    def can_run(self, name: str, role: str = "admin") -> bool:
        return self.executor.can_run(name, role=role)

    def execute(self, name: str, arguments: Dict[str, Any], role: str = "admin") -> Dict[str, Any]:
        if not self.executor.validate(name):
            return {"error": f"tool '{name}' no existe", "tool": name, "ok": False}
        if self.cfg.enforce_permissions and not self.executor.can_run(name, role=role):
            return {"error": f"permiso insuficiente para '{name}' (rol {role})", "tool": name, "ok": False}

        if not self._rate.allow(name):
            return {"error": f"rate limit alcanzado para '{name}'", "tool": name, "rate_limited": True, "ok": False}

        breaker = self._breaker(name)
        timeout = self.cfg.default_timeout

        def _call() -> Any:
            return with_retry(
                lambda: with_timeout(
                    lambda: self.executor.execute(name, arguments, role=role).output,
                    timeout,
                ),
                self.cfg.default_retry,
            )

        start = time.time()
        try:
            output = breaker.call(_call)
            self._record(name, True, time.time() - start)
            return {"tool": name, "output": output, "ok": True}
        except Exception as exc:
            self._record(name, False, time.time() - start)
            logger.warning("Tool %s fallo: %s", name, exc)
            return {"tool": name, "error": str(exc), "ok": False}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tools": dict(self._metrics),
                "circuit_breakers": {n: b.snapshot() for n, b in self._breakers.items()},
                "rate": {n: self._rate.status(n) for n in self._metrics},
            }

    def breaker_state(self, name: str) -> Dict[str, Any]:
        return self._breaker(name).snapshot()

    def reset_breaker(self, name: str) -> bool:
        if name in self._breakers:
            self._breakers[name].reset()
            return True
        return False
