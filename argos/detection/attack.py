from __future__ import annotations

from argos.ocsf import ATTACK_TECHNIQUES, OcsfEvent


class AttackMapper:
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
