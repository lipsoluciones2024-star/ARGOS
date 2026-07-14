from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class LookupIocTool(BaseTool):
    name = "lookup_ioc"
    description = "Busca un indicador de compromiso (IP, dominio, hash) en threat intel."
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {"indicator": {"type": "string"}},
        "required": ["indicator"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        return self.ctx.intel.lookup(str(a.get("indicator", "")))
