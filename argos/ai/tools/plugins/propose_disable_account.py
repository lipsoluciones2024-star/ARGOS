from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeDisableAccountTool(ProposeActionTool):
    name = "propose_disable_account"
    description = "Propone deshabilitar una cuenta de usuario (gobernado por el switch de autonomia)."
    action = "disable_account"
    parameters = {
        "type": "object",
        "properties": {"user": {"type": "string", "description": "Nombre de la cuenta"}},
        "required": ["user"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return str(a.get("user", "")), {}
