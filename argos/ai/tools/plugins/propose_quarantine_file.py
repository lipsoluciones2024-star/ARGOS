from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeQuarantineFileTool(ProposeActionTool):
    name = "propose_quarantine_file"
    description = "Propone mover un archivo a cuarentena (gobernado por el switch de autonomia)."
    action = "quarantine_file"
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta del archivo a aislar"}},
        "required": ["path"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return str(a.get("path", "")), {}
