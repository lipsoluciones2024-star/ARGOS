from __future__ import annotations

from typing import Any

from argos.ai.orchestrator import AiOrchestrator


class Investigator:
    """Agente investigador: ante una alerta usa las herramientas de lectura
    y el cerebro para dictaminar y, si procede, proponer una acción
    (gobernada por el switch de autonomía)."""

    def __init__(self, orchestrator: AiOrchestrator) -> None:
        self.orch = orchestrator

    def build_prompt(self, alert: dict[str, Any]) -> str:
        host = alert.get("host", "desconocido")
        title = alert.get("title", "alerta")
        attack = alert.get("attack_id") or alert.get("attack_technique") or "desconocido"
        summary = alert.get("summary", "")
        return (
            "Eres ARGOS, un SOC agentico. Se ha disparado una alerta de seguridad. "
            "Investígala usando tus herramientas de lectura (query_events, get_process_tree, "
            "get_active_connections, lookup_ioc, list_alerts, explain_attck_technique) y, "
            "SÓLO si hay evidencia clara de compromiso activo, propón UNA acción de respuesta "
            "con la herramienta propose_* correspondiente. No propongas acciones si no hay "
            "evidencia. Responde en español con un dictamen breve.\n\n"
            f"ALERTA: {title}\nHost: {host}\nTécnica ATT&CK: {attack}\nResumen: {summary}"
        )

    def investigate(self, alert: dict[str, Any]) -> dict[str, Any]:
        if self.orch.response is None:
            return {"alert_id": alert.get("id"), "host": alert.get("host"),
                    "verdict": "sin response orchestrator", "proposals": []}
        resp = self.orch.response
        prompt = self.build_prompt(alert)
        ids_before = {p.id for p in resp.all_proposals()}
        verdict = self.orch.chat(prompt, history=[])
        created = [p for p in resp.all_proposals() if p.id not in ids_before]
        return {
            "alert_id": alert.get("id"),
            "host": alert.get("host"),
            "attack_id": alert.get("attack_id"),
            "verdict": verdict,
            "proposals": [p.__dict__ for p in created],
        }
