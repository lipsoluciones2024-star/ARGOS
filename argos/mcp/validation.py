from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("argos.mcp.validation")


def validate_tool_schema(schema: Dict[str, Any]) -> bool:
    """Valida la estructura minima de un JSON Schema de tool MCP."""
    try:
        assert isinstance(schema, dict), "schema debe ser dict"
        assert schema.get("type") == "object", "type debe ser 'object'"
        assert isinstance(schema.get("properties"), dict), "properties debe ser dict"
        return True
    except AssertionError as exc:
        logger.warning("Schema invalido: %s", exc)
        return False


def validate_tool_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> Optional[List[str]]:
    """Valida `arguments` contra `schema`. Devuelve lista de errores o None."""
    errors: List[str] = []
    props = schema.get("properties", {})
    required = schema.get("required", [])
    arguments = arguments or {}

    for field in required:
        if field not in arguments:
            errors.append(f"Falta el parametro requerido: {field}")

    for key, value in arguments.items():
        if key not in props:
            errors.append(f"Parametro desconocido: {key}")
            continue
        expected = props[key].get("type")
        if expected == "integer" and not isinstance(value, int):
            errors.append(f"{key} debe ser entero")
        elif expected == "number" and not isinstance(value, (int, float)):
            errors.append(f"{key} debe ser numero")
        elif expected == "string" and not isinstance(value, str):
            errors.append(f"{key} debe ser texto")
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append(f"{key} debe ser booleano")
        elif expected == "array" and not isinstance(value, list):
            errors.append(f"{key} debe ser lista")
        elif expected == "object" and not isinstance(value, dict):
            errors.append(f"{key} debe ser objeto")
    return errors or None


def validate_request(req: Any) -> Optional[str]:
    """Valida la estructura basica de un MCPRequest. Devuelve mensaje o None.

    Solo valida la forma del request (JSON-RPC 2.0). El enrutamiento de métodos
    desconocidos se resuelve en el servidor con METHOD_NOT_FOUND.
    """
    if not isinstance(req, (dict,)) and not hasattr(req, "method"):
        return "Request invalido"
    method = getattr(req, "method", None)
    if not method:
        return "Falta el campo 'method'"
    if method == "tools/call":
        params = getattr(req, "params", None)
        if not isinstance(params, dict):
            return "tools/call requiere 'params'"
        if "name" not in params:
            return "tools/call requiere 'params.name'"
        if "arguments" not in params:
            return "tools/call requiere 'params.arguments'"
    return None
