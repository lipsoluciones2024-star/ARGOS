from __future__ import annotations

"""Capa AI/MCP de ARGOS.

El servidor MCP completo (JSON-RPC 2.0 con HTTP y WebSocket) vive en
``argos.mcp.server.MCPServer`` y esta cableado en ``argos/server.py``
(``POST /api/v1/mcp`` y ``WS /api/v1/mcp/ws``). Este paquete expone una
interfaz de conveniencia sobre ese servidor para que el AI Brain (ACP) pueda
invocar tools MCP sin depender del transporte.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from argos.ai.tools.registry import ToolExecutor
from argos.mcp.protocol import MCPRequest
from argos.mcp.server import MCPServer as _RealMCPServer


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )


class MCPServer:
    """Adaptador ligero sobre el MCPServer real de ARGOS.

    Permite al AI Brain enumerar e invocar tools MCP localmente (sin red),
    manteniendo una unica fuente de verdad en ``argos.mcp``.
    """

    def __init__(self, executor: ToolExecutor, server_name: str = "argos-mcp") -> None:
        self._real = _RealMCPServer(executor)
        self.server_name = server_name

    def list_tools(self) -> List[MCPTool]:
        raw = self._real.registry.list_tools()
        return [
            MCPTool(name=t["name"], description=t.get("description", ""), input_schema=t.get("inputSchema", {}))
            for t in raw
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any], role: str = "admin") -> Dict[str, Any]:
        resp = self._real.handle(
            MCPRequest(id=0, method="tools/call", params={"name": name, "arguments": arguments}).to_dict(),
            role=role,
        )
        return resp

    def capabilities(self) -> Dict[str, Any]:
        return self._real.handle(MCPRequest(id=0, method="tools/list").to_dict())
