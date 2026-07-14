from __future__ import annotations

import time
from collections import deque
from typing import Optional


class ActionLimiter:
    """Límites de seguridad para el bucle autónomo.

    - Máximo de acciones por hora (global).
    - Cooldown por host para no machacar un mismo endpoint.
    Fail-safe: si se excede, devuelve False y no se ejecuta nada.
    """

    def __init__(self, max_per_hour: int = 10, cooldown_per_host_sec: int = 300) -> None:
        self.max_per_hour = max(1, max_per_hour)
        self.cooldown_per_host_sec = max(0, cooldown_per_host_sec)
        self._stamps: deque[float] = deque()
        self._host_last: dict[str, float] = {}

    def allow(self, host: str, now: Optional[float] = None) -> bool:
        now = now or time.time()
        cutoff = now - 3600.0
        while self._stamps and self._stamps[0] <= cutoff:
            self._stamps.popleft()
        if len(self._stamps) >= self.max_per_hour:
            return False
        last = self._host_last.get(host)
        if last and (now - last) < self.cooldown_per_host_sec:
            return False
        self._stamps.append(now)
        self._host_last[host] = now
        return True

    def reset(self) -> None:
        self._stamps.clear()
        self._host_last.clear()
