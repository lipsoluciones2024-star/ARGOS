from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from argos.ai.tools.registry import ToolExecutor
from argos.mcp.protocol import MCPError, MCPRequest, MCPResponse
from argos.mcp.tools import MCPToolRegistry
from argos.mcp.validation import validate_request, validate_tool_arguments

logger = logging.getLogger("argos.mcp.server")


class MCPServer:
    """Servidor MCP (JSON-RPC 2.0) integrado en ARGOS.

    Se expone como endpoints FastAPI (POST /api/v1/mcp y WS /api/v1/mcp/ws)
    para no introducir dependencias externas (aiohttp) y reutilizar el
    servidor unico de la aplicacion.
    """

    def __init__(self, executor: Optional[ToolExecutor] = None) -> None:
        self.registry = MCPToolRegistry(executor)

    def set_executor(self, executor: ToolExecutor) -> None:
        self.registry.set_executor(executor)

    def handle(self, payload: Dict[str, Any], role: str = "admin") -> Dict[str, Any]:
        try:
            req = MCPRequest.from_dict(payload)
        except Exception as exc:
            return MCPResponse(
                id=None, error=MCPError.make(MCPError.PARSE_ERROR, f"JSON invalido: {exc}")
            ).to_dict()

        validation_error = validate_request(req)
        if validation_error:
            return MCPResponse(
                id=req.id, error=MCPError.make(MCPError.INVALID_REQUEST, validation_error)
            ).to_dict()

        method = req.method
        params = req.params or {}

        try:
            if method == "ping":
                return MCPResponse(id=req.id, result={"status": "pong"}).to_dict()
            if method == "tools/list":
                return MCPResponse(id=req.id, result={"tools": self.registry.list_tools()}).to_dict()
            if method == "resources/list":
                return MCPResponse(id=req.id, result={"resources": self.registry.list_resources()}).to_dict()
            if method == "prompts/list":
                return MCPResponse(id=req.id, result={"prompts": self.registry.list_prompts()}).to_dict()
            if method == "resources/read":
                return self._resources_read(req, params)
            if method == "tools/call":
                return self._tools_call(req, params, role)
        except ValueError as exc:
            return MCPResponse(
                id=req.id, error=MCPError.make(MCPError.INVALID_PARAMS, str(exc))
            ).to_dict()
        except Exception as exc:
            logger.exception("Error MCP en %s", method)
            return MCPResponse(
                id=req.id, error=MCPError.make(MCPError.INTERNAL_ERROR, str(exc))
            ).to_dict()

        return MCPResponse(
            id=req.id, error=MCPError.make(MCPError.METHOD_NOT_FOUND, f"Metodo no soportado: {method}")
        ).to_dict()

    def _tools_call(self, req: MCPRequest, params: Dict[str, Any], role: str) -> Dict[str, Any]:
        name = params["name"]
        arguments = params.get("arguments", {})

        if name not in _registry_names():
            return MCPResponse(
                id=req.id, error=MCPError.make(MCPError.INVALID_PARAMS, f"Tool no encontrada: {name}")
            ).to_dict()

        adapter = self.registry._adapters[name]
        schema_errors = validate_tool_arguments(adapter.input_schema, arguments)
        if schema_errors:
            return MCPResponse(
                id=req.id,
                error=MCPError.make(MCPError.INVALID_PARAMS, "Argumentos invalidos",
                                    {"errors": schema_errors}),
            ).to_dict()

        result = self.registry.execute_tool(name, arguments, role=role)
        text = result if isinstance(result, str) else json.dumps(result, default=str, indent=2)
        return MCPResponse(
            id=req.id,
            result={"content": [{"type": "text", "text": text}]},
        ).to_dict()

    def _resources_read(self, req: MCPRequest, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri", "")
        # Las lecturas de recursos delegan en tools del nucleo segun el URI.
        mapping = {
            "argos://events/recent": ("query_events", {"limit": 20}),
            "argos://alerts/active": ("list_alerts", {"limit": 20}),
        }
        if uri not in mapping:
            return MCPResponse(
                id=req.id, error=MCPError.make(MCPError.INVALID_PARAMS, f"Recurso desconocido: {uri}")
            ).to_dict()
        name, args = mapping[uri]
        result = self.registry.execute_tool(name, args)
        text = result if isinstance(result, str) else json.dumps(result, default=str, indent=2)
        return MCPResponse(
            id=req.id,
            result={"contents": [{"uri": uri, "mimeType": "application/json", "text": text}]},
        ).to_dict()


def _registry_names() -> set:
    from argos.ai.tools.registry import _REGISTRY

    return set(_REGISTRY.keys())
