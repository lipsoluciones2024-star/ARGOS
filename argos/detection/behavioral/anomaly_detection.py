from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from argos.detection.alerts import Alert
from argos.detection.behavioral.baseline import BehavioralBaselineStore
from argos.ocsf import OcsfEvent, Severity

logger = logging.getLogger("argos.detection.behavioral")


@dataclass
class AnomalyConfig:
    threshold: float = 0.5
    min_severity: Severity = Severity.MEDIUM
    enabled: bool = True


class AnomalyDetector:
    """Detector de anomalias conductuales sobre el baseline por host.

    Se invoca despues de la evaluacion de reglas (hook POST_DETECTION) y emite
    una alerta cuando el score supera el umbral. No reemplaza al motor, lo
    complementa.
    """

    def __init__(self, store: BehavioralBaselineStore, cfg: Optional[AnomalyConfig] = None) -> None:
        self.store = store
        self.cfg = cfg or AnomalyConfig()

    def train(self, events: List[OcsfEvent]) -> None:
        if not self.cfg.enabled:
            return
        self.store.train(events)
        logger.info("Baseline conductual entrenado para %d hosts", len(self.store.snapshot()))

    def evaluate(self, event: OcsfEvent) -> Optional[Alert]:
        if not self.cfg.enabled:
            return None
        score = self.store.score(event)
        if score >= self.cfg.threshold:
            return Alert(
                title=f"Behavioral anomaly on {event.host}",
                severity=self.cfg.min_severity,
                event_id=event.event_id,
                host=event.host,
                attack_id="T1070",
                attack_technique="Indicator Removal",
                summary=(
                    f"Anomaly score {score:.2f} for process '{event.process_name}' "
                    f"on {event.host} (not in baseline)"
                ),
                source="behavioral",
            )
        return None
