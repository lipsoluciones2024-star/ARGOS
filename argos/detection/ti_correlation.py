from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argos.detection.threat_intel import ThreatIntel
from argos.ocsf import OcsfEvent


@dataclass
class IocMatch:
    indicator: str
    field: str
    intel: Dict[str, Any]


@dataclass
class CorrelationResult:
    event_id: str
    matches: List[IocMatch] = field(default_factory=list)

    @property
    def hit(self) -> bool:
        return bool(self.matches)


class ThreatIntelCorrelator:
    """Correlaciona eventos contra los IOCs locales (capa Threat Intel)."""

    def __init__(self, intel: ThreatIntel) -> None:
        self.intel = intel

    def correlate(self, event: OcsfEvent) -> CorrelationResult:
        candidates: List[tuple[Optional[str], str]] = [
            (event.src_ip, "src_ip"),
            (event.dst_ip, "dst_ip"),
            (event.process_name, "process_name"),
        ]
        result = CorrelationResult(event_id=event.event_id)
        for value, field_name in candidates:
            if not value:
                continue
            lookup = self.intel.lookup(value)
            if lookup.get("malicious"):
                result.matches.append(IocMatch(indicator=value, field=field_name, intel=lookup))
        return result


def enrich_event(event: OcsfEvent, intel: ThreatIntel) -> Dict[str, Any]:
    """Devuelve un dict del evento enriquecido con metadatos de threat intel."""
    corr = ThreatIntelCorrelator(intel).correlate(event)
    enriched = event.as_dict()
    if corr.hit:
        enriched["threat_intel"] = [
            {"indicator": m.indicator, "field": m.field, "source": m.intel.get("source")}
            for m in corr.matches
        ]
    return enriched
