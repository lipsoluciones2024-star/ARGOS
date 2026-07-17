from __future__ import annotations

from typing import Optional

from argos.mcp.protocol import MCPError, MCPRequest, MCPResponse
from argos.mcp.server import MCPServer
from argos.mcp.tools import MCPToolRegistry


class MCPClient:
    """Cliente MCP ligero para testing y para clientes externos.

    No requiere aiohttp: usa httpx (ya dependencia del proyecto) de forma
    sincrona, con una variante async minima sobre la misma API.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", token: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._id = 0

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post(self, method: str, params: Optional[dict] = None) -> MCPResponse:
        import httpx

        self._id += 1
        req = MCPRequest(id=self._id, method=method, params=params)
        resp = httpx.post(f"{self.base_url}/api/v1/mcp", json=req.to_dict(), headers=self._headers(), timeout=30)
        return MCPResponse.from_dict(resp.json())

    def list_tools(self) -> list:
        return (self._post("tools/list").result or {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._post("tools/call", {"name": name, "arguments": arguments}).result or {}

    def list_resources(self) -> list:
        return (self._post("resources/list").result or {}).get("resources", [])


__all__ = ["MCPClient", "MCPServer", "MCPToolRegistry", "MCPRequest", "MCPResponse", "MCPError"]
