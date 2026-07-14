from __future__ import annotations

from typing import Any

# Equipo especializado del Cyber Brain.
# Cada agente es un PERFIL de herramientas (rol mínimo), no un proceso LLM aparte:
# el Commander (un solo cerebro) delega mentalmente y usa solo las tools del perfil.
CYBER_BRAIN_AGENTS: dict[str, dict[str, Any]] = {
    "commander": {
        "name": "Commander Agent",
        "mission": "Comandante del SOC autonomo. Decide que agente especializado actua y que "
                   "herramientas usa. Nunca ejecuta una accion peligrosa directamente.",
        "tools": None,  # usa todas las herramientas disponibles
    },
    "red": {
        "name": "Red Team Agent",
        "mission": "Piensa como atacante autorizado: reconocimiento, movimiento lateral, explotacion.",
        "tools": [
            "query_events", "get_hosts", "get_host_detail", "get_active_connections",
            "get_process_tree", "alerts_by_host", "ip_reputation", "lookup_ioc",
            "network_recon",
        ],
    },
    "blue": {
        "name": "Blue Team Agent",
        "mission": "Deteccion y respuesta: reglas Sigma, cobertura ATT&CK, alertas y auditoria.",
        "tools": [
            "get_coverage", "detection_rules", "list_alerts", "alerts_by_host",
            "get_audit_log", "pending_proposals", "query_events",
            "scan_yara", "network_recon", "correlate",
        ],
    },
    "purple": {
        "name": "Purple Team Agent",
        "mission": "Convierte cada ataque en nuevas reglas de deteccion y valida que funcionen.",
        "tools": [
            "detection_rules", "get_coverage", "run_playbook",
            "explain_attck_technique", "query_events",
            "scan_yara", "network_recon", "correlate",
        ],
    },
    "threat_intel": {
        "name": "Threat Intel Agent",
        "mission": "Reputacion de IPs, IOC y contexto de amenazas (MITRE ATT&CK).",
        "tools": ["ip_reputation", "lookup_ioc", "explain_attck_technique"],
    },
    "malware": {
        "name": "Malware Agent",
        "mission": "Analisis de indicadores y artefactos sospechosos (FIM, procesos, hosts).",
        "tools": [
            "lookup_ioc", "ip_reputation", "query_events",
            "query_fim_events", "get_host_detail",
        ],
    },
    "cloud": {
        "name": "Cloud Agent",
        "mission": "Postura de nube y contenedores (mapeo a eventos de configuracion y hosts).",
        "tools": ["query_events", "get_hosts", "get_coverage"],
    },
    "forensics": {
        "name": "Forensics Agent",
        "mission": "Cadena de custodia, snapshot de memoria y reconstruccion de incidentes.",
        "tools": [
            "get_host_detail", "get_process_tree", "query_fim_events",
            "propose_memory_snapshot", "query_events",
        ],
    },
    "risk": {
        "name": "Risk Agent",
        "mission": "Calcula impacto y prioriza segun NIST CSF / CIS Controls.",
        "tools": ["get_coverage", "list_alerts", "alerts_by_host", "get_hosts"],
    },
    "investigator": {
        "name": "Investigator Agent",
        "mission": "Investiga incidentes de principio a fin: correlaciona eventos, alertas e IOCs, "
                   "reconstruye la cadena de ataque (MITRE ATT&CK) y emite veredicto con proximos pasos.",
        "tools": [
            "correlate", "network_recon", "run_playbook", "get_host_detail",
            "get_process_tree", "query_events", "list_alerts", "alerts_by_host",
            "ip_reputation", "lookup_ioc", "get_coverage", "scan_yara",
        ],
    },
}


def agent_catalog() -> list[dict[str, Any]]:
    """Roster de agentes con sus herramientas (para /api/v1/agents)."""
    return [
        {
            "id": aid,
            "name": spec["name"],
            "mission": spec["mission"],
            "tools": spec["tools"],
        }
        for aid, spec in CYBER_BRAIN_AGENTS.items()
    ]


def tool_to_agents() -> dict[str, list[str]]:
    """Mapea cada herramienta a los agentes que la usan."""
    mapping: dict[str, list[str]] = {}
    for aid, spec in CYBER_BRAIN_AGENTS.items():
        tools = spec["tools"]
        if tools is None:
            continue
        for t in tools:
            mapping.setdefault(t, []).append(aid)
    return mapping
