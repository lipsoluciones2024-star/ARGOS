from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional


class RateLimiter:
    """Limitador de tasa en memoria por clave (IP o token).

    Ventana deslizante: como mucho `max_requests` en `window_sec` segundos.
    """

    def __init__(self, max_requests: int = 200, window_sec: int = 3600) -> None:
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, now: Optional[float] = None) -> bool:
        now = now or time.time()
        dq = self._hits[key]
        cutoff = now - self.window_sec
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


def cors_origins(server_host: str, server_port: int, extra: Optional[list[str]] = None) -> list[str]:
    base = [
        f"http://{server_host}:{server_port}",
        f"http://127.0.0.1:{server_port}",
        f"http://localhost:{server_port}",
    ]
    for e in extra or []:
        if e and e not in base:
            base.append(e)
    return base
