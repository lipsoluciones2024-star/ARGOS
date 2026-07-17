from __future__ import annotations

from typing import Any, Dict, List

from argos.plugins.hooks.base import BaseHook
from argos.plugins.hooks.lifecycle import (
    OnAlertHook,
    PostDetectionHook,
    PreDetectionHook,
)


class BasePlugin:
    """Clase base para plugins de ARGOS.

    Un plugin declara componentes (skills/commands/agents/mcp_servers) y hooks.
    Los hooks se construyen bajo demanda con metodos build_<nombre_hook>.
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    category: str = "detection"
    permissions: List[str] = ["read"]

    def get_tools(self) -> List[Any]:
        return []

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": []}

    def build_pre_detection(self) -> BaseHook:
        return PreDetectionHook()

    def build_post_detection(self) -> BaseHook:
        return PostDetectionHook()

    def build_pre_response(self) -> BaseHook:
        from argos.plugins.hooks.lifecycle import PreResponseHook

        return PreResponseHook()

    def build_post_response(self) -> BaseHook:
        from argos.plugins.hooks.lifecycle import PostResponseHook

        return PostResponseHook()

    def build_on_alert(self) -> BaseHook:
        return OnAlertHook()


# --- Plugins de compatibilidad: exponen tools del nucleo como plugins ----------
# Esto permite que el sistema de plugins reconozca las herramientas ya existentes
# en argos.ai.tools.plugins sin duplicar su logica.


class EventsQueryPlugin(BasePlugin):
    name = "events-query"
    version = "1.0.0"
    description = "Consulta avanzada de eventos de seguridad"
    category = "detection"
    permissions = ["read"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": ["events"], "agents": [], "mcp_servers": [], "hooks": ["pre_detection"]}

    def build_pre_detection(self) -> BaseHook:
        return PreDetectionHook(priority=20)


class ProcessTreePlugin(BasePlugin):
    name = "process-tree"
    version = "1.0.0"
    description = "Analisis del arbol de procesos"
    category = "detection"
    permissions = ["read"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["pre_detection"]}


class NetworkConnectionsPlugin(BasePlugin):
    name = "network-connections"
    version = "1.0.0"
    description = "Conexiones de red activas"
    category = "detection"
    permissions = ["read"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["pre_detection"]}


class AlertsManagerPlugin(BasePlugin):
    name = "alerts-manager"
    version = "1.0.0"
    description = "Gestion de alertas de seguridad"
    category = "response"
    permissions = ["read"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["on_alert"]}

    def build_on_alert(self) -> BaseHook:
        return OnAlertHook(priority=20)


class ThreatIntelPlugin(BasePlugin):
    name = "threat-intel"
    version = "1.0.0"
    description = "Inteligencia de amenazas / lookup de IOCs"
    category = "analytics"
    permissions = ["analyze"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["post_detection"]}

    def build_post_detection(self) -> BaseHook:
        return PostDetectionHook(priority=15)


class DetectionCoveragePlugin(BasePlugin):
    name = "detection-coverage"
    version = "1.0.0"
    description = "Cobertura MITRE ATT&CK del motor"
    category = "analytics"
    permissions = ["read"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": []}


class YaraScannerPlugin(BasePlugin):
    name = "yara-scanner"
    version = "1.0.0"
    description = "Escaneo con reglas YARA"
    category = "detection"
    permissions = ["analyze"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["pre_detection"]}


class NetworkReconPlugin(BasePlugin):
    name = "network-recon"
    version = "1.0.0"
    description = "Reconocimiento de red (port/ping/traceroute/dns)"
    category = "detection"
    permissions = ["analyze"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": []}


class EventCorrelationPlugin(BasePlugin):
    name = "event-correlation"
    version = "1.0.0"
    description = "Correlacion de eventos en cadenas de ataque"
    category = "analytics"
    permissions = ["analyze"]

    def get_components(self) -> Dict[str, List[str]]:
        return {"skills": [], "commands": [], "agents": [], "mcp_servers": [], "hooks": ["post_detection"]}

    def build_post_detection(self) -> BaseHook:
        return PostDetectionHook(priority=18)
