from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from argos.ocsf import EventCategory, OcsfEvent, Severity


class Normalizer:
    def normalize(self, raw: dict[str, Any]) -> OcsfEvent:
        category = raw.get("category")
        try:
            cat = EventCategory(category) if category else EventCategory.OTHER
        except ValueError:
            cat = EventCategory.OTHER
        severity = raw.get("severity")
        try:
            sev = Severity(severity) if severity else Severity.INFO
        except ValueError:
            sev = Severity.INFO
        return OcsfEvent(
            time=raw.get("time") or datetime.now(timezone.utc).isoformat(),
            category=cat,
            host=raw.get("host", "unknown"),
            source=raw.get("source", "agent"),
            process_name=raw.get("process_name"),
            process_pid=raw.get("process_pid"),
            process_parent_pid=raw.get("process_parent_pid"),
            process_cmdline=raw.get("process_cmdline"),
            process_image=raw.get("process_image"),
            process_hash=raw.get("process_hash"),
            src_ip=raw.get("src_ip"),
            dst_ip=raw.get("dst_ip"),
            dst_port=raw.get("dst_port"),
            src_port=raw.get("src_port"),
            dns=raw.get("dns"),
            protocol=raw.get("protocol"),
            file_path=raw.get("file_path"),
            file_action=raw.get("file_action"),
            registry_key=raw.get("registry_key"),
            registry_action=raw.get("registry_action"),
            user=raw.get("user"),
            logon_result=raw.get("logon_result"),
            attack_id=raw.get("attack_id"),
            attack_technique=raw.get("attack_technique"),
            severity=sev,
            raw=raw,
        )
