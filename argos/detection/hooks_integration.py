from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from argos.detection.alerts import Alert
from argos.detection.behavioral import AnomalyConfig, AnomalyDetector, BehavioralBaselineStore
from argos.detection.ti_correlation import ThreatIntelCorrelator, enrich_event
from argos.ocsf import OcsfEvent
from argos.plugins.base import HookEvent
from argos.plugins.hooks.base import BaseHook
from argos.plugins.registry import PluginRegistry

logger = logging.getLogger("argos.detection.integration")


class BehavioralThreatIntelHook(BaseHook):
    """Hook built-in que enriquece eventos y emite alertas conductuales.

    Se registra en POST_DETECTION. Enriquece el evento con threat intel y, si el
    detector conductual esta entrenado, anade una alerta de anomalia al contexto.
    """

    def __init__(self, intel, baseline_store: Optional[BehavioralBaselineStore] = None,
                 cfg: Optional[AnomalyConfig] = None) -> None:
        super().__init__(HookEvent.POST_DETECTION, priority=50)
        self.intel = intel
        self.baseline_store = baseline_store or BehavioralBaselineStore()
        self.detector = AnomalyDetector(self.baseline_store, cfg or AnomalyConfig())
        self.correlator = ThreatIntelCorrelator(intel)

    def train(self, events: list[OcsfEvent]) -> None:
        self.detector.train(events)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        event = context.get("event")
        if not isinstance(event, OcsfEvent):
            return context
        # Enriquecimiento de threat intel (si hay coincidencia, lo refleja en el dict).
        enriched = enrich_event(event, self.intel)
        context["event_enriched"] = enriched
        # Correlacion IOC.
        corr = self.correlator.correlate(event)
        if corr.hit:
            context.setdefault("ioc_matches", []).extend(
                {"indicator": m.indicator, "field": m.field} for m in corr.matches
            )
        # Deteccion de anomalia conductual.
        alert = self.detector.evaluate(event)
        if isinstance(alert, Alert):
            alerts = context.get("alerts") or []
            alerts.append(alert)
            context["alerts"] = alerts
        return context


def register_detection_hooks(registry: PluginRegistry, intel, events_for_training: Optional[list[OcsfEvent]] = None) -> BehavioralThreatIntelHook:
    """Registra el hook built-in de deteccion en el registry y lo entrena."""
    hook = BehavioralThreatIntelHook(intel)
    if events_for_training:
        hook.train(events_for_training)
    registry.hooks[HookEvent.POST_DETECTION].append(hook)
    registry._resort_all()
    logger.info("Hook built-in de deteccion (behavioral + threat intel) registrado")
    return hook
