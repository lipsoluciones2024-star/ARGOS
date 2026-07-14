from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argos.config import Config
from argos.detection.alerts import Alert
from argos.detection.attack import AttackMapper
from argos.detection.sigma_rules import SigmaRule, _to_severity, load_rules
from argos.detection.threat_intel import ThreatIntel
from argos.detection.yara_rules import YaraScanner
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
    def __init__(self, cfg: Config, rules_dir: Path | None = None, alert_store=None,
                 yara_dir: Path | None = None) -> None:
        self.cfg = cfg
        self.rules_dir = rules_dir or (cfg.root / "detection-engine" / "rules" / "sigma")
        self.rules: list[SigmaRule] = load_rules(self.rules_dir)
        self.yara_dir = yara_dir or (cfg.root / "detection-engine" / "rules" / "yara")
        self.yara = YaraScanner()
        self.yara.load_rules_from_dir(self.yara_dir)
        self.baseline = Baseline()
        self.attack = AttackMapper()
        self.threat_intel = ThreatIntel(cfg)
        self.alert_store = alert_store
        self.detected_techniques: set[str] = set()
        self.detectable = (
            {r.attack_id for r in self.rules if r.attack_id}
            | self.attack.known_techniques()
        )

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

    def coverage(self) -> dict[str, Any]:
        total = sorted(self.detectable)
        covered = [t for t in total if t in self.detected_techniques]
        matrix = {
            t: {
                "name": self.attack.technique_name(t),
                "status": "covered" if t in self.detected_techniques else "blind-spot",
            }
            for t in total
        }
        return {
            "total": len(total),
            "covered": len(covered),
            "matrix": matrix,
        }

    def recent_alerts(self, limit: int = 50, severity: str | None = None) -> list[dict[str, Any]]:
        return self.alert_store.recent(limit=limit, severity=severity)

    def list_rules(self) -> list[dict[str, Any]]:
        out = [{"title": r.title, "level": r.level, "attack_id": r.attack_id,
                "logsource": r.logsource, "engine": "sigma"} for r in self.rules]
        for yr in self.yara.rules:
            out.append({
                "title": yr.name, "level": yr.meta.get("severity", "medium"),
                "attack_id": yr.meta.get("attack_id"), "logsource": None,
                "engine": "yara", "meta": yr.meta,
            })
        return out

    def add_yara_rule(self, name: str, content: str) -> int:
        return self.yara.load_rule_text(content, name)

    def add_sigma_rule_text(self, name: str, content: str) -> int:
        """Parsea y carga una regla Sigma desde texto (reglas gestionadas por API)."""
        try:
            import yaml

            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return 0
            det = data.get("detection", {})
            attack = None
            for t in data.get("tags", []):
                if isinstance(t, str) and t.upper().startswith("ATTACK."):
                    attack = ".".join(t.split(".")[1:]).upper()
            rule = SigmaRule(
                title=data.get("title", name),
                logsource=data.get("logsource", {}),
                detection=det,
                condition=str(det.get("condition", "selection")),
                level=str(data.get("level", "medium")),
                attack_id=attack,
            )
            self.rules.append(rule)
            return 1
        except Exception:
            return 0

    def scan_file(self, path) -> list[dict[str, Any]]:
        from pathlib import Path

        return self.yara.scan_file(Path(path))

    def scan_bytes(self, data: bytes) -> list[dict[str, Any]]:
        return self.yara.scan_bytes(data)

    def reload(self, managed_rules: list[dict[str, Any]] | None = None) -> dict[str, int]:
        self.rules = load_rules(self.rules_dir)
        self.yara = YaraScanner()
        self.yara.load_rules_from_dir(self.yara_dir)
        managed = 0
        if managed_rules:
            for r in managed_rules:
                if not r.get("enabled"):
                    continue
                if r["type"] == "yara":
                    managed += self.yara.load_rule_text(r["content"], r["name"])
                elif r["type"] == "sigma":
                    managed += self.add_sigma_rule_text(r["name"], r["content"])
        return {"sigma": len(self.rules), "yara": len(self.yara.rules), "managed": managed}
