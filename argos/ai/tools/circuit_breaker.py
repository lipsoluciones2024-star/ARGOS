from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class CircuitBreakerOpenError(RuntimeError):
    """Se lanza cuando el circuit breaker esta OPEN y rechaza la llamada."""


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout: float = 60.0
    success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker sencillo y thread-safe por herramienta.

    Cerrado: deja pasar llamadas. Tras `failure_threshold` fallos consecutivos
    pasa a OPEN y rechaza durante `timeout` segundos. Luego prueba HALF_OPEN;
    si acierta `success_threshold` veces vuelve a CLOSED.
    """

    def __init__(self, cfg: Optional[CircuitBreakerConfig] = None) -> None:
        self.cfg = cfg or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock_state: CircuitState = self.state

    def call(self, func: Callable[[], Any]) -> Any:
        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                raise CircuitBreakerOpenError()
            if time.time() - self.last_failure_time >= self.cfg.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError()

        try:
            result = func()
        except Exception:
            self.on_failure()
            raise

        self.on_success()
        return result

    def on_success(self) -> None:
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.cfg.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
        else:
            self.state = CircuitState.CLOSED

    def on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.cfg.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }
