from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argos.config import Config
from argos.detection.alerts import Alert
from argos.detection.attack import AttackMapper
from argos.detection.sigma_rules import SigmaRule, _to_severity, load_rules
from argos.detection.threat_intel import ThreatIntel
from argos.ocsf import OcsfEvent, Severity


@dataclass
class Baseline:
    known_processes: set[str] = field(default_factory=set)
    trained: bool = False

    def observe(self, event: OcsfEvent) -> None:
        if event.process_name:
            self.known_processes.add(event.process_name.lower())

    def flag_anomaly(self, event: OcsfEvent) -> bool:
        if not self.trained:
            return False
        if event.process_name and event.process_name.lower() not in self.known_processes:
            return True
        return False


class DetectionEngine:
    def __init__(self, cfg: Config, rules_dir: Path | None = None, alert_store=None) -> None:
        self.cfg = cfg
        self.rules_dir = rules_dir or (cfg.root / "detection-engine" / "rules" / "sigma")
        self.rules: list[SigmaRule] = load_rules(self.rules_dir)
        self.baseline = Baseline()
        self.attack = AttackMapper()
        self.threat_intel = ThreatIntel(cfg)
        self.alert_store = alert_store
        self.detected_techniques: set[str] = set()

    def train_baseline(self, events: list[OcsfEvent]) -> None:
        for e in events:
            self.baseline.observe(e)
        self.baseline.trained = True

    def evaluate(self, event: OcsfEvent) -> list[Alert]:
        alerts: list[Alert] = []
        self.baseline.observe(event)
        self.attack.enrich(event)
        if event.attack_id:
            self.detected_techniques.add(event.attack_id)
        for rule in self.rules:
            try:
                if rule.evaluate(event):
                    alerts.append(self._alert_from_rule(rule, event))
            except Exception:
                continue
        if self.baseline.flag_anomaly(event):
            alerts.append(Alert(
                title="Behavioral anomaly: new process name",
                severity=Severity.MEDIUM, event_id=event.event_id, host=event.host,
                summary=f"Process '{event.process_name}' not seen during baseline on {event.host}",
                source="baseline",
            ))
        return alerts

    def _alert_from_rule(self, rule: SigmaRule, event: OcsfEvent) -> Alert:
        if rule.attack_id:
            self.detected_techniques.add(rule.attack_id)
        return Alert(
            title=rule.title,
            severity=_to_severity(rule.level),
            event_id=event.event_id, host=event.host,
            attack_id=rule.attack_id,
            attack_technique=self.attack.technique_name(rule.attack_id),
            summary=f"Rule '{rule.title}' matched on {event.host} ({event.category})",
            source="sigma",
        )

    def evaluate_batch(self, events: list[OcsfEvent]) -> list[Alert]:
        alerts: list[Alert] = []
        for e in events:
            alerts.extend(self.evaluate(e))
        return alerts

    def coverage(self) -> dict[str, dict[str, str]]:
        return self.attack.coverage_matrix(self.detected_techniques)

    def recent_alerts(self, limit: int = 50, severity: str | None = None) -> list[dict[str, Any]]:
        return self.alert_store.recent(limit=limit, severity=severity)

    def list_rules(self) -> list[dict[str, Any]]:
        return [{"title": r.title, "level": r.level, "attack_id": r.attack_id,
                 "logsource": r.logsource} for r in self.rules]
