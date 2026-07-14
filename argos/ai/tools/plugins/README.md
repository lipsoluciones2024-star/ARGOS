# Tentáculos del Pulpo (plugins de herramientas)

Cada herramienta que el LLM puede invocar vive aquí como un **plugin** que se
auto-registra. No hace falta tocar el core (`argos/ai/tools/registry.py` ni
`orchestrator.py`) para añadir una nueva: basta con crear un módulo `.py` en
esta carpeta y decorar una clase con `@register_tool`.

## Anatomía de un tentáculo

```python
# argos/ai/tools/plugins/mi_tool.py
from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class MiTool(BaseTool):
    # Nombre expuesto al LLM (debe ser único y sin espacios)
    name = "mi_tool"

    # Descripción que el modelo usará para decidir cuándo llamarlo
    description = "Hace algo útil con los datos de ARGOS."

    # Esquema JSON Schema de los parámetros (formato OpenAI function-calling)
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "qué es param1"},
        },
        "required": ["param1"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        # Acceso a las dependencias inyectadas vía self.ctx
        ctx = self.ctx  # ToolContext(store, engine, intel)
        resultado = hacer_algo(ctx.store, a["param1"])
        return {"ok": True, "data": resultado}
```

## Reglas

- El módulo se importa automáticamente al arrancar (`discover_tools()`), así que
  **cualquier `@register_tool` en esta carpeta queda disponible al instante**.
- La clase debe definir `name`, `description` y `parameters`. Si falta `name`,
  el registro lanza `ValueError`.
- Dentro de `run` usa `self.ctx.store`, `self.ctx.engine` y `self.ctx.intel`.
- Devuelve un `dict`/`list`/`str` serializable. Los `str` pasan por
  `guard_privacy` automáticamente. Captura de errores la hace el `ToolExecutor`.
- Nunca ejecutes acciones de respuesta aquí: las tools son **solo lectura**
  (el LLM propone, el switch de autonomía decide). Para acciones usa
  `argos/response/`.

## Descubrimiento

`argos/ai/tools/registry.py::discover_tools()` recorre este paquete con
`pkgutil.iter_modules` e importa cada módulo, disparando los `@register_tool`.
La API pública (`ALLOWED_TOOLS`, `tool_schemas`, `ToolExecutor`) se recalcula
desde el registro, por lo que `ALLOWED_TOOLS == set(registry)`.
