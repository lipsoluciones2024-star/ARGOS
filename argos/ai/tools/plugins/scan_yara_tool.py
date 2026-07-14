from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from argos import get_config
from argos.ai.tools.registry import BaseTool, register_tool
from argos.detection.yara_rules import scan_path


@register_tool
class ScanYaraTool(BaseTool):
    name = "scan_yara"
    description = (
        "Ejecuta las reglas YARA cargadas sobre un archivo o directorio (sandbox del servidor) "
        "para detectar malware/indicadores. Analisis, no modifica el sistema."
    )
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "ruta dentro del sandbox permitido"},
        },
        "required": ["path"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        path_str = str(a.get("path", "")).strip()
        if not path_str:
            return {"error": "path requerido"}
        cfg = get_config()
        allowed = [cfg.root, cfg.data_dir, Path(tempfile.gettempdir())]
        try:
            resolved = Path(path_str).resolve()
        except Exception:
            return {"error": "ruta no resolubible"}
        if not any(str(resolved).startswith(str(p.resolve())) for p in allowed):
            return {"error": "ruta fuera del sandbox permitido"}
        if not resolved.exists():
            return {"error": "ruta inexistente"}
        if resolved.is_file():
            hits = [{"file": str(resolved), **h} for h in self.ctx.engine.scan_file(resolved)]
        else:
            hits = scan_path(self.ctx.engine.yara, resolved)
        return {"scanned": str(resolved), "hits": hits}
