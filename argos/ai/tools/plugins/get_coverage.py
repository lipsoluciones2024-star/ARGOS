from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class GetCoverageTool(BaseTool):
    name = "get_coverage"
    description = "Devuelve la matriz de cobertura ATT&CK (detectables vs detectadas)."
    perm = "analyze"
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, a: dict[str, Any]) -> Any:
        return self.ctx.engine.coverage()
