from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool


class ProposeActionTool(BaseTool):
    """Base para tools de acción: enruta al ResponseOrchestrator.propose,
    que aplica el switch de autonomía (DENY / REQUIRES_APPROVAL / EXECUTE)."""

    action: str = ""
    # Toda acción propuesta requiere permiso de ejecución (gobernado por el switch).
    perm: str = "execute"

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        target = str(a.get("target", ""))
        params = {k: v for k, v in a.items() if k != "target"}
        return target, params

    def run(self, a: dict[str, Any]) -> Any:
        resp = self.ctx.response
        if resp is None:
            return {"error": "response orchestrator no disponible"}
        target, params = self._extract(a)
        if not target:
            return {"error": f"'target' requerido para {self.action}"}
        proposal = resp.propose(
            action=self.action, target=target, proposed_by="ai", params=params or None
        )
        return {
            "id": proposal.id,
            "status": proposal.status,
            "action": proposal.action,
            "target": proposal.target,
        }
