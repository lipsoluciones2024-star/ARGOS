# ESPECIFICACIÓN: Protocolo MCP para ARGOS

**Versión:** 1.0  
**Fecha:** 2026-07-16  
**Objetivo:** Implementar protocolo MCP (Model Context Protocol) en ARGOS para integración estándar con ecosistema de herramientas

---

## 1. VISIÓN GENERAL

### 1.1 Qué es MCP
MCP (Model Context Protocol) es un protocolo estándar para conectar modelos de IA con herramientas y datos externos. Inspirado en la implementación de grok-build, permite:
- Exposición de herramientas via protocolo estandarizado
- Interoperabilidad entre diferentes sistemas
- Schema validation robusto
- Comunicación bidireccional cliente-servidor

### 1.2 Por qué MCP en ARGOS
- **Estandarización:** Protocolo probado en producción por XAI
- **Interoperabilidad:** Compatible con ecosistema MCP creciente
- **Extensibilidad:** Fácil agregar nuevas herramientas
- **Validación:** Schemas robustos para tools
- **Future-proof:** Protocolo mantenido por comunidad

### 1.3 Alcance
- Implementar MCP server para ARGOS
- Exponer 10+ tools via MCP
- Soportar MCP clients externos
- Mantener backward compatibility con sistema actual

---

## 2. ARQUITECTURA MCP

### 2.1 Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MCP SERVER (ARGOS)                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Tool Registry │  │ Schema       │  │ Validation   │  │  │
│  │  │              │  │ Manager      │  │ Engine       │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Request      │  │ Response     │  │ Error        │  │  │
│  │  │ Handler      │  │ Formatter    │  │ Handler      │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↕ JSON-RPC 2.0                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MCP CLIENTS                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Internal     │  │ External     │  │ Future       │  │  │
│  │  │ (ARGOS AI)   │  │ (Third-party) │  │ (Integrations)│ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Estructura de Directorios

```
argos/mcp/
├── __init__.py
├── server.py                    # MCP server principal
├── client.py                    # MCP client para testing
├── protocol.py                  # Definición de protocolo
├── tools/
│   ├── __init__.py
│   ├── registry.py              # Registry de tools MCP
│   ├── schemas.py               # Schemas JSON para tools
│   └── adapters.py              # Adaptadores de tools ARGOS → MCP
├── handlers/
│   ├── __init__.py
│   ├── tools.py                 # Handler de tool calls
│   ├── resources.py             # Handler de resources
│   └── prompts.py               # Handler de prompts
├── validation/
│   ├── __init__.py
│   ├── schemas.py               # Validación de schemas
│   └── requests.py              # Validación de requests
└── docs/
    ├── protocol.md              # Esta especificación
    ├── api.md                   # API documentation
    └── examples.md              # Ejemplos de uso
```

---

## 3. PROTOCOLO MCP

### 3.1 Mensajes JSON-RPC 2.0

MCP usa JSON-RPC 2.0 como protocolo de transporte:

```json
// Request
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "query_events",
        "arguments": {
            "filters": {"severity": "high"},
            "limit": 10
        }
    }
}

// Response
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Found 5 high-severity events..."
            }
        ]
    }
}

// Error
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32602,
        "message": "Invalid params",
        "data": {
            "validation_errors": [...]
        }
    }
}
```

### 3.2 Métodos del Protocolo

#### tools/list
Lista todas las herramientas disponibles:

```json
// Request
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
}

// Response
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "tools": [
            {
                "name": "query_events",
                "description": "Query security events with filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filters": {"type": "object"},
                        "limit": {"type": "integer", "default": 100}
                    }
                }
            }
        ]
    }
}
```

#### tools/call
Ejecuta una herramienta:

```json
// Request
{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "query_events",
        "arguments": {
            "filters": {"severity": "high"},
            "limit": 10
        }
    }
}

// Response
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Found 5 high-severity events:\n1. Suspicious PowerShell execution\n2. Unusual network connection\n..."
            }
        ]
    }
}
```

#### resources/list
Lista recursos disponibles:

```json
// Request
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "resources/list"
}

// Response
{
    "jsonrpc": "2.0",
    "id": 3,
    "result": {
        "resources": [
            {
                "uri": "argos://events/recent",
                "name": "Recent Events",
                "description": "Most recent security events",
                "mimeType": "application/json"
            }
        ]
    }
}
```

#### resources/read
Lee un recurso:

```json
// Request
{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "resources/read",
    "params": {
        "uri": "argos://events/recent"
    }
}

// Response
{
    "jsonrpc": "2.0",
    "id": 4,
    "result": {
        "contents": [
            {
                "uri": "argos://events/recent",
                "mimeType": "application/json",
                "text": "{\"events\": [...]}"
            }
        ]
    }
}
```

---

## 4. IMPLEMENTACIÓN DEL SERVER

### 4.1 MCP Server Básico

```python
# argos/mcp/server.py
import asyncio
import json
from typing import Any, Dict, Optional
from aiohttp import web, WSMessage
from .protocol import MCPRequest, MCPResponse
from .tools.registry import ToolRegistry
from .validation.requests import validate_request

class MCPServer:
    """MCP Server para ARGOS."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 3000):
        self.host = host
        self.port = port
        self.tool_registry = ToolRegistry()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura las rutas del servidor."""
        self.app.router.add_post("/mcp", self.handle_mcp)
        self.app.router.add_get("/mcp/ws", self.handle_websocket)
        self.app.router.add_get("/health", self.health_check)
    
    async def handle_mcp(self, request: web.Request) -> web.Response:
        """Maneja requests MCP via HTTP POST."""
        try:
            body = await request.json()
            mcp_request = MCPRequest(**body)
            
            # Validar request
            validation_error = validate_request(mcp_request)
            if validation_error:
                return self._error_response(mcp_request.id, validation_error)
            
            # Procesar request
            response = await self._process_request(mcp_request)
            
            return web.json_response(response.to_dict())
        
        except json.JSONDecodeError:
            return self._error_response(None, "Invalid JSON")
        except Exception as e:
            return self._error_response(None, str(e))
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Maneja conexiones WebSocket para streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    body = json.loads(msg.data)
                    mcp_request = MCPRequest(**body)
                    
                    # Procesar y enviar respuesta
                    response = await self._process_request(mcp_request)
                    await ws.send_json(response.to_dict())
                
                except Exception as e:
                    error = self._error_response(mcp_request.id, str(e))
                    await ws.send_json(error.to_dict())
            
            elif msg.type == WSMsgType.ERROR:
                print(f"WebSocket error: {ws.exception()}")
        
        return ws
    
    async def _process_request(self, request: MCPRequest) -> MCPResponse:
        """Procesa un request MCP."""
        method = request.method
        
        if method == "tools/list":
            return await self._handle_tools_list(request)
        elif method == "tools/call":
            return await self._handle_tools_call(request)
        elif method == "resources/list":
            return await self._handle_resources_list(request)
        elif method == "resources/read":
            return await self._handle_resources_read(request)
        else:
            return self._error_response(request.id, f"Unknown method: {method}")
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Maneja tools/list."""
        tools = self.tool_registry.list_tools()
        
        return MCPResponse(
            id=request.id,
            result={
                "tools": [tool.to_dict() for tool in tools]
            }
        )
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Maneja tools/call."""
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        # Ejecutar tool
        result = await self.tool_registry.execute_tool(tool_name, arguments)
        
        return MCPResponse(
            id=request.id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        )
    
    async def _handle_resources_list(self, request: MCPRequest) -> MCPResponse:
        """Maneja resources/list."""
        # Implementar listado de recursos
        return MCPResponse(
            id=request.id,
            result={"resources": []}
        )
    
    async def _handle_resources_read(self, request: MCPRequest) -> MCPResponse:
        """Maneja resources/read."""
        uri = request.params.get("uri")
        # Implementar lectura de recursos
        return MCPResponse(
            id=request.id,
            result={"contents": []}
        )
    
    def _error_response(self, request_id: Optional[int], message: str) -> MCPResponse:
        """Genera respuesta de error."""
        return MCPResponse(
            id=request_id,
            error={
                "code": -32603,
                "message": message
            }
        )
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy"})
    
    async def start(self):
        """Inicia el servidor MCP."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"MCP Server running on http://{self.host}:{self.port}")
```

### 4.2 Protocol Definition

```python
# argos/mcp/protocol.py
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class MCPRequest:
    """Request MCP."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params
        }

@dataclass
class MCPResponse:
    """Response MCP."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.result:
            response["result"] = self.result
        if self.error:
            response["error"] = self.error
        
        return response
```

### 4.3 Tool Registry

```python
# argos/mcp/tools/registry.py
from typing import Dict, List, Any
from argos.ai.tools.registry import _REGISTRY
from .adapters import ToolAdapter

class ToolRegistry:
    """Registry de tools MCP."""
    
    def __init__(self):
        self.adapters: Dict[str, ToolAdapter] = {}
        self._register_argos_tools()
    
    def _register_argos_tools(self):
        """Registra tools de ARGOS como tools MCP."""
        from argos.ai.tools.registry import _REGISTRY
        
        for tool_name, tool_class in _REGISTRY.items():
            adapter = ToolAdapter(tool_class)
            self.adapters[tool_name] = adapter
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las tools disponibles."""
        return [
            {
                "name": name,
                "description": adapter.description,
                "inputSchema": adapter.input_schema
            }
            for name, adapter in self.adapters.items()
        ]
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Ejecuta una tool."""
        if name not in self.adapters:
            raise ValueError(f"Tool not found: {name}")
        
        adapter = self.adapters[name]
        return await adapter.execute(arguments)
```

### 4.4 Tool Adapter

```python
# argos/mcp/tools/adapters.py
from typing import Dict, Any
from argos.ai.tools.registry import BaseTool, ToolContext

class ToolAdapter:
    """Adapta tools de ARGOS al formato MCP."""
    
    def __init__(self, tool_class: type):
        self.tool_class = tool_class
        self.description = tool_class.description
        self.input_schema = self._convert_schema(tool_class.parameters)
    
    def _convert_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte schema de tool a schema MCP."""
        # MCP usa JSON Schema directamente
        return parameters
    
    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Ejecuta la tool adaptada."""
        # Crear instancia de tool (necesita contexto)
        # Esto requiere integración con el contexto de ARGOS
        from argos.storage.store import EventStore
        from argos.detection.engine import DetectionEngine
        from argos.detection.threat_intel import ThreatIntel
        
        # Esto debería inyectarse desde el exterior
        context = ToolContext(
            store=EventStore(),  # inyectar instancia real
            engine=DetectionEngine(),
            intel=ThreatIntel()
        )
        
        tool = self.tool_class(context)
        result = tool.run(arguments)
        
        return result
```

---

## 5. TOOLS MCP EXPUESTAS

### 5.1 Tools Principales

```python
# argos/mcp/tools/schemas.py
MCP_TOOLS = {
    "query_events": {
        "name": "query_events",
        "description": "Query security events with advanced filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "object",
                    "description": "Filters for the query (severity, category, host, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 100
                },
                "offset": {
                    "type": "integer",
                    "description": "Offset for pagination",
                    "default": 0
                }
            }
        }
    },
    "get_process_tree": {
        "name": "get_process_tree",
        "description": "Get the process tree for a specific process ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to analyze"
                },
                "depth": {
                    "type": "integer",
                    "description": "Maximum depth of tree",
                    "default": 5
                }
            },
            "required": ["pid"]
        }
    },
    "get_active_connections": {
        "name": "get_active_connections",
        "description": "Get active network connections",
        "inputSchema": {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Filter by host"
                },
                "state": {
                    "type": "string",
                    "description": "Filter by connection state (ESTABLISHED, LISTEN, etc.)"
                }
            }
        }
    },
    "list_alerts": {
        "name": "list_alerts",
        "description": "List security alerts with filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "Filter by severity (low, medium, high, critical)"
                },
                "acknowledged": {
                    "type": "boolean",
                    "description": "Filter by acknowledgment status"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of alerts",
                    "default": 50
                }
            }
        }
    },
    "lookup_ioc": {
        "name": "lookup_ioc",
        "description": "Look up indicators of compromise in threat intelligence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ioc": {
                    "type": "string",
                    "description": "IOC to lookup (IP, domain, hash, etc.)"
                },
                "type": {
                    "type": "string",
                    "description": "Type of IOC (ip, domain, hash, url)",
                    "enum": ["ip", "domain", "hash", "url"]
                }
            },
            "required": ["ioc"]
        }
    },
    "get_coverage": {
        "name": "get_coverage",
        "description": "Get detection coverage statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "technique_id": {
                    "type": "string",
                    "description": "MITRE ATT&CK technique ID (e.g., T1059)"
                }
            }
        }
    },
    "detection_rules": {
        "name": "detection_rules",
        "description": "List or manage detection rules",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform (list, enable, disable)",
                    "enum": ["list", "enable", "disable"],
                    "default": "list"
                },
                "rule_id": {
                    "type": "string",
                    "description": "Rule ID for enable/disable actions"
                }
            }
        }
    },
    "scan_yara": {
        "name": "scan_yara",
        "description": "Scan files or processes with YARA rules",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target to scan (file path or process ID)"
                },
                "target_type": {
                    "type": "string",
                    "description": "Type of target",
                    "enum": ["file", "process"]
                },
                "rules": {
                    "type": "array",
                    "description": "Specific YARA rules to use (empty for all)"
                }
            },
            "required": ["target", "target_type"]
        }
    },
    "network_recon": {
        "name": "network_recon",
        "description": "Perform network reconnaissance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target IP or hostname"
                },
                "scan_type": {
                    "type": "string",
                    "description": "Type of scan",
                    "enum": ["port", "ping", "traceroute", "dns"],
                    "default": "port"
                },
                "ports": {
                    "type": "array",
                    "description": "Specific ports to scan (for port scan)"
                }
            },
            "required": ["target"]
        }
    },
    "correlate": {
        "name": "correlate",
        "description": "Correlate events to identify attack chains",
        "inputSchema": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "description": "Events to correlate"
                },
                "time_window": {
                    "type": "integer",
                    "description": "Time window in seconds for correlation",
                    "default": 300
                }
            },
            "required": ["events"]
        }
    }
}
```

---

## 6. MCP CLIENT

### 6.1 Client Implementation

```python
# argos/mcp/client.py
import asyncio
import aiohttp
from typing import Any, Dict, Optional, List
from .protocol import MCPRequest, MCPResponse

class MCPClient:
    """Client para conectar con MCP server."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> MCPResponse:
        """Envía un request al servidor MCP."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        self.request_id += 1
        request = MCPRequest(
            id=self.request_id,
            method=method,
            params=params
        )
        
        async with self.session.post(
            f"{self.base_url}/mcp",
            json=request.to_dict()
        ) as response:
            data = await response.json()
            return MCPResponse(**data)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las tools disponibles."""
        response = await self._send_request("tools/list")
        
        if response.error:
            raise RuntimeError(response.error["message"])
        
        return response.result["tools"]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Ejecuta una tool."""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        if response.error:
            raise RuntimeError(response.error["message"])
        
        return response.result
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """Lista todos los recursos disponibles."""
        response = await self._send_request("resources/list")
        
        if response.error:
            raise RuntimeError(response.error["message"])
        
        return response.result["resources"]
    
    async def read_resource(self, uri: str) -> Any:
        """Lee un recurso."""
        response = await self._send_request("resources/read", {"uri": uri})
        
        if response.error:
            raise RuntimeError(response.error["message"])
        
        return response.result
```

### 6.2 Usage Example

```python
# examples/mcp_client_example.py
import asyncio
from argos.mcp.client import MCPClient

async def main():
    async with MCPClient() as client:
        # Listar tools
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
        
        # Ejecutar tool
        result = await client.call_tool("query_events", {
            "filters": {"severity": "high"},
            "limit": 5
        })
        
        print("\nQuery result:")
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. VALIDACIÓN

### 7.1 Schema Validation

```python
# argos/mcp/validation/schemas.py
from jsonschema import validate, ValidationError
from typing import Dict, Any

def validate_tool_schema(schema: Dict[str, Any]) -> bool:
    """Valida que un schema de tool sea válido."""
    try:
        # Validar estructura básica
        assert "type" in schema, "Missing 'type' field"
        assert schema["type"] == "object", "Type must be 'object'"
        assert "properties" in schema, "Missing 'properties' field"
        
        # Validar que properties sea un dict
        assert isinstance(schema["properties"], dict), "Properties must be a dict"
        
        return True
    except AssertionError as e:
        print(f"Schema validation failed: {e}")
        return False

def validate_tool_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> bool:
    """Valida arguments contra schema."""
    try:
        validate(instance=arguments, schema=schema)
        return True
    except ValidationError as e:
        print(f"Arguments validation failed: {e}")
        return False
```

### 7.2 Request Validation

```python
# argos/mcp/validation/requests.py
from typing import Optional, Dict, Any
from .schemas import validate_tool_schema

def validate_request(request) -> Optional[str]:
    """Valida un request MCP."""
    # Validar estructura básica
    if not hasattr(request, 'method'):
        return "Missing 'method' field"
    
    if not hasattr(request, 'id'):
        return "Missing 'id' field"
    
    # Validar método conocido
    known_methods = [
        "tools/list",
        "tools/call",
        "resources/list",
        "resources/read"
    ]
    
    if request.method not in known_methods:
        return f"Unknown method: {request.method}"
    
    # Validar params para methods específicos
    if request.method == "tools/call":
        return validate_tools_call_params(request.params)
    
    return None

def validate_tools_call_params(params: Optional[Dict[str, Any]]) -> Optional[str]:
    """Valida params para tools/call."""
    if params is None:
        return "Missing params for tools/call"
    
    if "name" not in params:
        return "Missing 'name' in params"
    
    if "arguments" not in params:
        return "Missing 'arguments' in params"
    
    return None
```

---

## 8. TESTING

### 8.1 Tests del MCP Server

```python
# tests/mcp/test_server.py
import pytest
from aiohttp import web
from argos.mcp.server import MCPServer

@pytest.fixture
async def mcp_server():
    """Fixture para MCP server de prueba."""
    server = MCPServer(host="127.0.0.1", port=3001)
    await server.start()
    yield server
    # Cleanup si es necesario

@pytest.mark.asyncio
async def test_tools_list(mcp_server):
    """Test endpoint tools/list."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:3001/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        ) as response:
            data = await response.json()
            
            assert data["jsonrpc"] == "2.0"
            assert "result" in data
            assert "tools" in data["result"]
            assert len(data["result"]["tools"]) > 0

@pytest.mark.asyncio
async def test_tools_call(mcp_server):
    """Test endpoint tools/call."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:3001/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "query_events",
                    "arguments": {
                        "filters": {"severity": "high"},
                        "limit": 5
                    }
                }
            }
        ) as response:
            data = await response.json()
            
            assert data["jsonrpc"] == "2.0"
            assert "result" in data
            assert "content" in data["result"]

@pytest.mark.asyncio
async def test_invalid_method(mcp_server):
    """Test método inválido."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:3001/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "invalid_method"
            }
        ) as response:
            data = await response.json()
            
            assert "error" in data
            assert data["error"]["code"] == -32603
```

### 8.2 Tests del MCP Client

```python
# tests/mcp/test_client.py
import pytest
from argos.mcp.client import MCPClient

@pytest.mark.asyncio
async def test_list_tools():
    """Test list_tools del client."""
    async with MCPClient() as client:
        tools = await client.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all("name" in tool for tool in tools)

@pytest.mark.asyncio
async def test_call_tool():
    """Test call_tool del client."""
    async with MCPClient() as client:
        result = await client.call_tool("query_events", {
            "filters": {},
            "limit": 1
        })
        
        assert "content" in result
```

---

## 9. INTEGRACIÓN CON ARGOS

### 9.1 Integración en Server Principal

```python
# argos/server.py (modificado)
from argos.mcp.server import MCPServer

class ArgosServer:
    def __init__(self, cfg: Config):
        # ... código existente ...
        self.mcp_server = MCPServer(
            host=cfg.mcp_host,
            port=cfg.mcp_port
        )
    
    async def start(self):
        """Inicia todos los servidores."""
        # Iniciar servidor FastAPI existente
        await self.start_fastapi()
        
        # Iniciar servidor MCP
        await self.mcp_server.start()
        
        print("ARGOS Server running with MCP endpoint")
```

### 9.2 Configuración

```python
# argos/config.py (modificado)
@dataclass
class Config:
    # ... configuración existente ...
    
    # MCP Configuration
    mcp_enabled: bool = True
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 3000
    mcp_auth_required: bool = False
```

---

## 10. DOCUMENTACIÓN API

### 10.1 OpenAPI/Swagger

```yaml
# mcp-openapi.yaml
openapi: 3.0.0
info:
  title: ARGOS MCP Server API
  version: 1.0.0
  description: MCP Server for ARGOS security platform

paths:
  /mcp:
    post:
      summary: MCP endpoint
      description: Main MCP endpoint for tool calls
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPRequest'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MCPResponse'
  
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: Server is healthy

components:
  schemas:
    MCPRequest:
      type: object
      required:
        - jsonrpc
        - method
      properties:
        jsonrpc:
          type: string
          default: "2.0"
        id:
          type: integer
        method:
          type: string
        params:
          type: object
    
    MCPResponse:
      type: object
      properties:
        jsonrpc:
          type: string
        id:
          type: integer
        result:
          type: object
        error:
          type: object
```

---

## 11. EJEMPLOS DE USO

### 11.1 Ejemplo Básico

```python
# examples/basic_mcp_usage.py
import asyncio
from argos.mcp.client import MCPClient

async def basic_example():
    async with MCPClient() as client:
        # Listar tools disponibles
        tools = await client.list_tools()
        print(f"Available tools: {len(tools)}")
        
        # Consultar eventos de alta severidad
        result = await client.call_tool("query_events", {
            "filters": {"severity": "high"},
            "limit": 10
        })
        
        print(f"Found {len(result['content'])} high-severity events")

if __name__ == "__main__":
    asyncio.run(basic_example())
```

### 11.2 Ejemplo de Correlación

```python
# examples/correlation_example.py
import asyncio
from argos.mcp.client import MCPClient

async def correlation_example():
    async with MCPClient() as client:
        # Obtener eventos recientes
        events_result = await client.call_tool("query_events", {
            "filters": {"time_range": "1h"},
            "limit": 20
        })
        
        events = events_result["content"]
        
        # Correlacionar eventos
        correlation_result = await client.call_tool("correlate", {
            "events": events,
            "time_window": 300
        })
        
        print("Correlation analysis:")
        print(correlation_result)

if __name__ == "__main__":
    asyncio.run(correlation_example())
```

### 11.3 Ejemplo de Threat Intel

```python
# examples/threat_intel_example.py
import asyncio
from argos.mcp.client import MCPClient

async def threat_intel_example():
    async with MCPClient() as client:
        # Lookup IP sospechosa
        result = await client.call_tool("lookup_ioc", {
            "ioc": "45.33.32.156",
            "type": "ip"
        })
        
        print("Threat intelligence result:")
        print(result)

if __name__ == "__main__":
    asyncio.run(threat_intel_example())
```

---

## 12. DEPLOYMENT

### 12.1 Docker Compose

```yaml
# docker-compose.mcp.yml
version: '3.8'

services:
  argos-mcp:
    build: .
    ports:
      - "3000:3000"
    environment:
      - MCP_ENABLED=true
      - MCP_HOST=0.0.0.0
      - MCP_PORT=3000
    depends_on:
      - argos-server
  
  argos-server:
    # ... configuración existente ...
```

### 12.2 Kubernetes

```yaml
# k8s/mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argos-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: argos-mcp
  template:
    metadata:
      labels:
        app: argos-mcp
    spec:
      containers:
      - name: mcp-server
        image: argos:latest
        ports:
        - containerPort: 3000
        env:
        - name: MCP_ENABLED
          value: "true"
        - name: MCP_HOST
          value: "0.0.0.0"
        - name: MCP_PORT
          value: "3000"
```

---

## 13. MONITOREO

### 13.1 Métricas

```python
# argos/mcp/monitoring.py
from prometheus_client import Counter, Histogram

# Métricas MCP
MCP_REQUESTS_TOTAL = Counter(
    'mcp_requests_total',
    'Total MCP requests',
    ['method', 'status']
)

MCP_REQUEST_DURATION = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['method']
)

MCP_TOOL_EXECUTIONS = Counter(
    'mcp_tool_executions_total',
    'Total tool executions via MCP',
    ['tool_name', 'status']
)
```

---

## 14. SEGURIDAD

### 14.1 Authentication

```python
# argos/mcp/auth.py
from typing import Optional
from aiohttp import web

async def check_auth(request: web.Request) -> bool:
    """Verifica authentication para requests MCP."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        return False
    
    # Validar token (implementar lógica específica)
    # return validate_token(auth_header)
    
    return True

@web.middleware
async def auth_middleware(request: web.Request, handler):
    """Middleware de authentication."""
    if request.path == "/health":
        return await handler(request)
    
    if not await check_auth(request):
        return web.json_response(
            {"error": "Unauthorized"},
            status=401
        )
    
    return await handler(request)
```

---

## 15. TROUBLESHOOTING

### 15.1 Problemas Comunes

**Server no inicia:**
- Verificar que el puerto no esté en uso
- Check logs de errores
- Validar configuración

**Tools no ejecutan:**
- Verificar que tool esté registrada
- Validar arguments contra schema
- Check logs del tool adapter

**Conexión rechazada:**
- Verificar authentication
- Check firewall rules
- Validar URL del servidor

---

## 16. PRÓXIMOS PASOS

1. **Inmediato:**
   - Implementar MCP server básico
   - Exponer 5 tools iniciales
   - Crear tests básicos

2. **Corto plazo (1 semana):**
   - Exponer 10 tools adicionales
   - Implementar validation robusto
   - Agregar authentication

3. **Mediano plazo (2 semanas):**
   - Implementar resources
   - Agregar streaming support
   - Crear documentación completa

4. **Largo plazo (1 mes):**
   - Optimizar performance
   - Agregar métricas avanzadas
   - Crear ecosistema de plugins MCP

---

## CONCLUSIÓN

Esta especificación proporciona un camino completo para implementar el protocolo MCP en ARGOS, permitiendo integración estándar con el ecosistema MCP mientras se mantiene compatibilidad con el sistema existente.
