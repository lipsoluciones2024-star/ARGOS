from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List

from argos.ocsf import OcsfEvent


@dataclass
class BehavioralBaseline:
    """Baseline de comportamiento por host (procesos, destinos de red, volumen)."""

    host: str
    processes: set[str] = field(default_factory=set)
    dst_ips: set[str] = field(default_factory=set)
    cmdline_tokens: set[str] = field(default_factory=set)
    hourly_volume: Counter = field(default_factory=Counter)
    trained: bool = False
    window: int = 0

    def observe(self, event: OcsfEvent) -> None:
        if event.process_name:
            self.processes.add(event.process_name.lower())
        if event.dst_ip:
            self.dst_ips.add(event.dst_ip)
        if event.process_cmdline:
            for tok in event.process_cmdline.lower().split():
                if len(tok) > 3:
                    self.cmdline_tokens.add(tok)
        if event.time:
            hour = str(event.time)[:13]
            self.hourly_volume[hour] += 1
            self.window += 1

    def finalize(self) -> None:
        self.trained = True

    def anomaly_score(self, event: OcsfEvent) -> float:
        """0.0 (normal) .. 1.0 (muy anomalo). Solo tras entrenar."""
        if not self.trained:
            return 0.0
        score = 0.0
        if event.process_name and event.process_name.lower() not in self.processes:
            score += 0.4
        if event.dst_ip and event.dst_ip not in self.dst_ips:
            score += 0.3
        if event.process_cmdline:
            toks = {t for t in event.process_cmdline.lower().split() if len(t) > 3}
            if toks and not (toks & self.cmdline_tokens):
                score += 0.2
        return min(1.0, score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "trained": self.trained,
            "process_count": len(self.processes),
            "dst_ip_count": len(self.dst_ips),
            "volume": dict(self.hourly_volume),
        }


class BehavioralBaselineStore:
    """Almacen en memoria de baselines por host."""

    def __init__(self) -> None:
        self._baselines: Dict[str, BehavioralBaseline] = {}
        self._lock = threading.Lock()

    def get_or_create(self, host: str) -> BehavioralBaseline:
        with self._lock:
            bl = self._baselines.get(host)
            if bl is None:
                bl = BehavioralBaseline(host=host)
                self._baselines[host] = bl
            return bl

    def train(self, events: List[OcsfEvent]) -> None:
        by_host: Dict[str, List[OcsfEvent]] = {}
        for e in events:
            by_host.setdefault(e.host or "unknown", []).append(e)
        for host, evs in by_host.items():
            bl = self.get_or_create(host)
            for e in evs:
                bl.observe(e)
            bl.finalize()

    def score(self, event: OcsfEvent) -> float:
        bl = self._baselines.get(event.host or "unknown")
        if bl is None:
            return 0.0
        return bl.anomaly_score(event)

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [bl.to_dict() for bl in self._baselines.values()]
