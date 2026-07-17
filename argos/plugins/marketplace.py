from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from argos.plugins.base import PluginManifest

logger = logging.getLogger("argos.plugins.marketplace")

_MARKETPLACE_FILE = Path(__file__).resolve().parent / "marketplace.json"


def _default_marketplace() -> Dict[str, Any]:
    """Catálogo oficial de plugins ARGOS.

    Incluye wrappers de las herramientas del núcleo (migración transparente)
    y hooks de ciclo de vida listos para usar.
    """
    return {
        "name": "argos-marketplace",
        "version": "1.0.0",
        "description": "Catálogo oficial de plugins ARGOS",
        "plugins": [
            {
                "name": "events-query",
                "version": "1.0.0",
                "description": "Consulta avanzada de eventos de seguridad",
                "category": "detection",
                "permissions": ["read"],
                "entry_point": "argos.plugins.compat:EventsQueryPlugin",
                "components": {"hooks": ["pre_detection"], "commands": ["events"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/events-query"},
            },
            {
                "name": "process-tree",
                "version": "1.0.0",
                "description": "Analisis del arbol de procesos",
                "category": "detection",
                "permissions": ["read"],
                "entry_point": "argos.plugins.compat:ProcessTreePlugin",
                "components": {"hooks": ["pre_detection"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/process-tree"},
            },
            {
                "name": "network-connections",
                "version": "1.0.0",
                "description": "Conexiones de red activas",
                "category": "detection",
                "permissions": ["read"],
                "entry_point": "argos.plugins.compat:NetworkConnectionsPlugin",
                "components": {"hooks": ["pre_detection"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/network-connections"},
            },
            {
                "name": "alerts-manager",
                "version": "1.0.0",
                "description": "Gestion de alertas de seguridad",
                "category": "response",
                "permissions": ["read"],
                "entry_point": "argos.plugins.compat:AlertsManagerPlugin",
                "components": {"hooks": ["on_alert"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/alerts-manager"},
            },
            {
                "name": "threat-intel",
                "version": "1.0.0",
                "description": "Inteligencia de amenazas / lookup de IOCs",
                "category": "analytics",
                "permissions": ["analyze"],
                "entry_point": "argos.plugins.compat:ThreatIntelPlugin",
                "components": {"hooks": ["post_detection"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/threat-intel"},
            },
            {
                "name": "detection-coverage",
                "version": "1.0.0",
                "description": "Cobertura MITRE ATT&CK del motor",
                "category": "analytics",
                "permissions": ["read"],
                "entry_point": "argos.plugins.compat:DetectionCoveragePlugin",
                "components": {"hooks": []},
                "source": {"type": "local", "path": "./argos/plugins/installed/detection-coverage"},
            },
            {
                "name": "yara-scanner",
                "version": "1.0.0",
                "description": "Escaneo con reglas YARA",
                "category": "detection",
                "permissions": ["analyze"],
                "entry_point": "argos.plugins.compat:YaraScannerPlugin",
                "components": {"hooks": ["pre_detection"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/yara-scanner"},
            },
            {
                "name": "network-recon",
                "version": "1.0.0",
                "description": "Reconocimiento de red (port/ping/traceroute/dns)",
                "category": "detection",
                "permissions": ["analyze"],
                "entry_point": "argos.plugins.compat:NetworkReconPlugin",
                "components": {"hooks": []},
                "source": {"type": "local", "path": "./argos/plugins/installed/network-recon"},
            },
            {
                "name": "event-correlation",
                "version": "1.0.0",
                "description": "Correlacion de eventos en cadenas de ataque",
                "category": "analytics",
                "permissions": ["analyze"],
                "entry_point": "argos.plugins.compat:EventCorrelationPlugin",
                "components": {"hooks": ["post_detection"]},
                "source": {"type": "local", "path": "./argos/plugins/installed/event-correlation"},
            },
        ],
    }


class Marketplace:
    """Catálogo centralizado de plugins disponibles."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.name = str(data.get("name", "argos-marketplace"))
        self.version = str(data.get("version", "1.0.0"))
        self.description = str(data.get("description", ""))
        raw_plugins = data.get("plugins", []) or []
        self.plugins: List[PluginManifest] = []
        for raw in raw_plugins:
            if isinstance(raw, dict):
                self.plugins.append(PluginManifest.from_dict(raw))

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "plugins": [p.to_dict() for p in self.plugins],
        }

    def get(self, name: str) -> PluginManifest | None:
        for p in self.plugins:
            if p.name == name:
                return p
        return None


@lru_cache(maxsize=1)
def _load_marketplace() -> Marketplace:
    if _MARKETPLACE_FILE.exists():
        try:
            data = json.loads(_MARKETPLACE_FILE.read_text(encoding="utf-8"))
            return Marketplace(data)
        except Exception as exc:
            logger.warning("marketplace.json ilegible (%s), usando default", exc)
    return Marketplace(_default_marketplace())


MARKETPLACE: Marketplace = _load_marketplace()
