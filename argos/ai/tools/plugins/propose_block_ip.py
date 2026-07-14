from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeBlockIpTool(ProposeActionTool):
    name = "propose_block_ip"
    description = "Propone bloquear trafico hacia una IP (gobernado por el switch de autonomia)."
    action = "block_ip"
    parameters = {
        "type": "object",
        "properties": {"ip": {"type": "string", "description": "IP a bloquear"}},
        "required": ["ip"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return str(a.get("ip", "")), {}
