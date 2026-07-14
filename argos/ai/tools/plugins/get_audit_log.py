from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class GetAuditLogTool(BaseTool):
    name = "get_audit_log"
    description = "Devuelve el registro de auditoria inmutable (hash-chain) del orquestador de respuesta."
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, a: dict[str, Any]) -> Any:
        resp = self.ctx.response
        if resp is None or getattr(resp, "audit", None) is None:
            return {"error": "audit not available"}
        return {"returned": True, "entries": resp.audit.all()}
