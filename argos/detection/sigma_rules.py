from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from argos.ocsf import EventCategory, OcsfEvent, Severity


class SigmaLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


FIELD_MAP = {
    "image": "process_image",
    "commandline": "process_cmdline",
    "parentimage": "process_image",
    "processname": "process_name",
    "parentprocessname": "process_name",
    "originalfilename": "process_name",
    "dstip": "dst_ip",
    "sourceip": "src_ip",
    "destinationip": "dst_ip",
    "destinationport": "dst_port",
    "destinationhostname": "dst_ip",
    "queryname": "dns",
    "targetfilename": "file_path",
    "targetfilename|endswith": "file_path",
    "eventid": "_eventid",
    "parentcommandline": "process_cmdline",
}


def _map_field(name: str) -> str:
    key = name.lower().replace(" ", "")
    return FIELD_MAP.get(key, name.lower())


def _to_severity(level: str) -> Severity:
    try:
        return Severity(level.lower())
    except ValueError:
        return Severity.MEDIUM


def _get_value(event: OcsfEvent, field: str) -> Any:
    if field == "_eventid":
        raw = event.raw or {}
        return str(raw.get("EventID", ""))
    return getattr(event, field, None)


def _match_op(value: Any, op: str, expected: Any) -> bool:
    if value is None:
        return False
    sval = str(value)
    if op == "equals" or op == "":
        return sval == str(expected)
    if op == "contains":
        return str(expected).lower() in sval.lower()
    if op == "endswith":
        return sval.lower().endswith(str(expected).lower())
    if op == "startswith":
        return sval.lower().startswith(str(expected).lower())
    if op == "regex":
        try:
            return re.search(str(expected), sval, re.IGNORECASE) is not None
        except re.error:
            return False
    return False


def _match_selection(event: OcsfEvent, selection: dict[str, Any]) -> bool:
    for raw_field, expected in selection.items():
        if "|" in raw_field:
            field_name, op = raw_field.rsplit("|", 1)
        else:
            field_name, op = raw_field, "equals"
        ocsf_field = _map_field(field_name)
        value = _get_value(event, ocsf_field)
        if isinstance(expected, list):
            if not any(_match_op(value, op, e) for e in expected):
                return False
        else:
            if not _match_op(value, op, expected):
                return False
    return True


def category_matches(event: OcsfEvent, logsource: dict[str, Any]) -> bool:
    cat = (logsource or {}).get("category")
    if not cat:
        return True
    mapping = {
        "process_creation": EventCategory.PROCESS,
        "network_connection": EventCategory.NETWORK,
        "dns_query": EventCategory.NETWORK,
        "file_event": EventCategory.FILESYSTEM,
        "registry_event": EventCategory.PERSISTENCE,
        "registry_add": EventCategory.PERSISTENCE,
    }
    return mapping.get(cat, None) in (None, event.category)


@dataclass
class SigmaRule:
    title: str
    logsource: dict[str, Any]
    detection: dict[str, Any]
    condition: str = "selection"
    level: str = "medium"
    attack_id: str | None = None

    def evaluate(self, event: OcsfEvent) -> bool:
        if not category_matches(event, self.logsource):
            return False
        selections = {k: v for k, v in self.detection.items() if k != "condition"}
        if self.condition == "selection" or self.condition == "all of them" or self.condition == "1 of them":
            target = self.condition.replace(" of them", "") if " of them" in self.condition else "selection"
            sel = selections.get(target, selections.get("selection"))
            if sel is None:
                return False
            return _match_selection(event, sel)
        return False


def load_rules(directory: Path) -> list[SigmaRule]:
    rules: list[SigmaRule] = []
    if not directory.exists():
        return rules
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        det = data.get("detection", {})
        attack = None
        tags = data.get("tags", [])
        for t in tags:
            if isinstance(t, str) and t.upper().startswith("ATTACK."):
                attack = ".".join(t.split(".")[1:]).upper()
        rules.append(
            SigmaRule(
                title=data.get("title", path.name),
                logsource=data.get("logsource", {}),
                detection=det,
                condition=str(det.get("condition", "selection")),
                level=str(data.get("level", "medium")),
                attack_id=attack,
            )
        )
    return rules
