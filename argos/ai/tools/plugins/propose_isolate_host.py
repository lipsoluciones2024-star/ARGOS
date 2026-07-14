from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeIsolateHostTool(ProposeActionTool):
    name = "propose_isolate_host"
    description = "Propone aislar un host bloqueando su trafico de red (gobernado por el switch)."
    action = "isolate_host"
    parameters = {
        "type": "object",
        "properties": {"host": {"type": "string", "description": "Host a aislar"}},
        "required": ["host"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return str(a.get("host", "")), {}
