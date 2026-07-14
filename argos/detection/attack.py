from __future__ import annotations

from argos.ocsf import ATTACK_TECHNIQUES, OcsfEvent

# Técnicas que ARGOS puede detectar por diseño (detección base del motor),
# independientemente de si ya hubo tráfico. Se combina con las reglas Sigma cargadas.
BASE_TECHNIQUES: set[str] = {
    "T1059", "T1053", "T1055", "T1070", "T1071", "T1078", "T1098", "T1110",
    "T1136", "T1190", "T1204", "T1486", "T1490", "T1496", "T1505", "T1543",
    "T1547", "T1566", "T1567", "T1027", "T1003", "T1016", "T1046", "T1056",
    "T1218", "T1220", "T1497", "T1518", "T1574", "T1571",
}


class AttackMapper:
    def known_techniques(self) -> set[str]:
        return set(BASE_TECHNIQUES)

    def technique_name(self, attack_id: str | None) -> str | None:
        if not attack_id:
            return None
        return ATTACK_TECHNIQUES.get(attack_id)

    def coverage_matrix(self, detected: set[str]) -> dict[str, dict[str, str]]:
        matrix: dict[str, dict[str, str]] = {}
        for tid, name in ATTACK_TECHNIQUES.items():
            covered = tid in detected
            matrix[tid] = {
                "name": name,
                "status": "covered" if covered else "blind-spot",
            }
        return matrix

    def enrich(self, event: OcsfEvent) -> OcsfEvent:
        if event.attack_id and not event.attack_technique:
            event.attack_technique = self.technique_name(event.attack_id)
        return event
