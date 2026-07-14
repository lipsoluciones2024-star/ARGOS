from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeRevertRegistryTool(ProposeActionTool):
    name = "propose_revert_registry"
    description = "Propone revertir una clave de registro a su valor conocido (gobernado por el switch)."
    action = "revert_registry"
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Clave de registro a revertir"},
            "value": {"type": "string", "description": "Valor a restaurar (opcional si hay backup)"},
        },
        "required": ["key"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        key = a.get("key")
        params: dict[str, Any] = {"key": key}
        if a.get("value") is not None:
            params["value"] = a["value"]
        return str(key), params
