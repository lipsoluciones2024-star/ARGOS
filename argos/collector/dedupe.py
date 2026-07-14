from __future__ import annotations

from datetime import datetime, timezone

from argos.ocsf import OcsfEvent


class Deduper:
    """Colapsa eventos idénticos por (host, category, key) dentro de una ventana."""

    def __init__(self, window_sec: int = 60) -> None:
        self.window_sec = window_sec
        self._seen: dict[str, float] = {}

    def should_store(self, event: OcsfEvent) -> bool:
        key = event.dedup_key()
        now = datetime.now(timezone.utc).timestamp()
        last = self._seen.get(key)
        if last is not None and (now - last) < self.window_sec:
            return False
        self._seen[key] = now
        self._compact(now)
        return True

    def _compact(self, now: float) -> None:
        if len(self._seen) < 4096:
            return
        stale = [k for k, t in self._seen.items() if (now - t) >= self.window_sec]
        for k in stale:
            self._seen.pop(k, None)

    def filter(self, events: list[OcsfEvent]) -> list[OcsfEvent]:
        out: list[OcsfEvent] = []
        for e in events:
            if self.should_store(e):
                out.append(e)
        return out
