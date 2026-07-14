from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class ExplainAttckTechniqueTool(BaseTool):
    name = "explain_attck_technique"
    description = "Explica una tecnica MITRE ATT&CK por su ID (ej. T1059.001)."
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        from argos.detection.attack import AttackMapper

        tid = str(a.get("id", "")).upper()
        mapper = AttackMapper()
        name = mapper.technique_name(tid)
        return {"id": tid, "name": name or "unknown", "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"}
