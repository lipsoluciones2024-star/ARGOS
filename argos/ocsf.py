from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime] = None) -> str:
    return (dt or utc_now()).isoformat()


class EventCategory(str, Enum):
    PROCESS = "process"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    PERSISTENCE = "persistence"
    IDENTITY = "identity"
    KERNEL = "kernel"
    MEMORY = "memory"
    LOTL = "lotl"
    USB = "usb"
    EXFILTRATION = "exfiltration"
    OTHER = "other"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OcsfEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    time: str = Field(default_factory=utc_iso)
    category: EventCategory = EventCategory.OTHER
    host: str = "unknown"
    source: str = "agent"
    ostick_id: Optional[str] = None

    process_name: Optional[str] = None
    process_pid: Optional[int] = None
    process_parent_pid: Optional[int] = None
    process_cmdline: Optional[str] = None
    process_image: Optional[str] = None
    process_hash: Optional[str] = None

    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    dst_port: Optional[int] = None
    src_port: Optional[int] = None
    dns: Optional[str] = None
    protocol: Optional[str] = None

    file_path: Optional[str] = None
    file_action: Optional[str] = None

    registry_key: Optional[str] = None
    registry_action: Optional[str] = None

    user: Optional[str] = None
    logon_result: Optional[str] = None

    attack_id: Optional[str] = None
    attack_technique: Optional[str] = None

    severity: Severity = Severity.INFO
    raw: Optional[dict[str, Any]] = None

    def to_fts_text(self) -> str:
        parts = [
            self.category,
            self.host,
            self.source,
            self.process_name or "",
            self.process_cmdline or "",
            self.process_image or "",
            self.src_ip or "",
            self.dst_ip or "",
            self.dns or "",
            self.file_path or "",
            self.registry_key or "",
            self.user or "",
            self.attack_id or "",
            self.process_cmdline or "",
        ]
        return " ".join(p for p in parts if p)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


ATTACK_TECHNIQUES: dict[str, str] = {
    "T1059": "Command and Scripting Interpreter",
    "T1059.001": "PowerShell",
    "T1055": "Process Injection",
    "T1003": "OS Credential Dumping",
    "T1003.001": "LSASS Memory",
    "T1053": "Scheduled Task/Job",
    "T1547": "Boot or Logon Autostart Execution",
    "T1547.001": "Registry Run Keys",
    "T1071": "Application Layer Protocol",
    "T1071.004": "DNS",
    "T1041": "Exfiltration Over C2 Channel",
    "T1027": "Obfuscated Files or Information",
    "T1218": "System Binary Proxy Execution",
    "T1218.011": "Rundll32",
    "T1497": "Virtualization/Sandbox Evasion",
    "T1070": "Indicator Removal",
    "T1133": "External Remote Services",
}
