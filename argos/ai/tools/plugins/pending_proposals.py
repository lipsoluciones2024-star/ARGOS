from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class PendingProposalsTool(BaseTool):
    name = "pending_proposals"
    description = "Lista las propuestas de accion pendientes de aprobacion del orquestador de respuesta."
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, a: dict[str, Any]) -> Any:
        resp = self.ctx.response
        if resp is None:
            return {"error": "response not available"}
        proposals = resp.pending_proposals()
        return {
            "returned": len(proposals),
            "proposals": [
                {
                    "id": p.id,
                    "action": p.action,
                    "target": p.target,
                    "status": p.status,
                    "proposed_by": p.proposed_by,
                }
                for p in proposals
            ],
        }
