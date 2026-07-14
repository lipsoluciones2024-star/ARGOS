from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class DetectionRulesTool(BaseTool):
    name = "detection_rules"
    description = "Lista las reglas de deteccion Sigma cargadas en el motor."
    perm = "analyze"
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, a: dict[str, Any]) -> Any:
        rules = self.ctx.engine.list_rules()
        return {"returned": len(rules), "rules": rules}
