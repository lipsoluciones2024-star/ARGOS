from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from argos.ocsf import Severity

ACTION_CATALOG = [
    "kill_process",
    "isolate_host",
    "block_ip",
    "quarantine_file",
    "revert_registry",
    "disable_account",
    "memory_snapshot",
]

ACTION_RISK = {
    "kill_process": "medium",
    "isolate_host": "high",
    "block_ip": "low",
    "quarantine_file": "low",
    "revert_registry": "medium",
    "disable_account": "high",
    "memory_snapshot": "none",
}

ACTION_REVERSIBLE = {
    "kill_process": "partial",
    "isolate_host": "yes",
    "block_ip": "yes",
    "quarantine_file": "yes",
    "revert_registry": "depends",
    "disable_account": "yes",
    "memory_snapshot": "na",
}


@dataclass
class Alert:
    id: str = field(default_factory=lambda: uuid4().hex)
    time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    title: str = ""
    severity: Severity = Severity.MEDIUM
    event_id: str | None = None
    host: str = "unknown"
    attack_id: str | None = None
    attack_technique: str | None = None
    summary: str = ""
    source: str = "detection"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "time": self.time, "title": self.title,
            "severity": self.severity.value, "event_id": self.event_id,
            "host": self.host, "attack_id": self.attack_id,
            "attack_technique": self.attack_technique, "summary": self.summary,
            "source": self.source,
        }
