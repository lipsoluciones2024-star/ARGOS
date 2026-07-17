# GUÍA DE MIGRACIÓN: Sistema de Plugins Enterprise

**Versión:** 1.0  
**Fecha:** 2026-07-16  
**Objetivo:** Migrar el sistema de tools actual a arquitectura de plugins enterprise inspirada en plugin-marketplace de SpaceXai

---

## 1. VISIÓN GENERAL

### 1.1 Estado Actual
ARGOS tiene un sistema de herramientas básico en `argos.ai.tools.plugins` con:
- Tools registradas en `_REGISTRY` dict
- Ejecución vía `ToolExecutor`
- Validación básica de permisos
- Sin capacidad de instalación/desinstalación en runtime
- Sin sistema de hooks
- Sin catálogo centralizado

### 1.2 Estado Objetivo
Sistema de plugins enterprise con:
- Marketplace centralizado (`marketplace.json`)
- Plugin registry con SHA pinning
- Instalación/desinstalación en runtime
- Sistema de hooks lifecycle
- Soporte para plugins locales y remotos
- Catálogo de componentes (skills, commands, agents, MCP servers)

### 1.3 Beneficios
- **Extensibilidad:** Plugins instalables sin modificar core
- **Seguridad:** SHA pinning para plugins remotos
- **Mantenibilidad:** Separación de concerns clara
- **Escalabilidad:** Ecosistema de plugins creíble
- **Comunidad:** Plugins compartibles entre usuarios

---

## 2. ARQUITECTURA DE PLUGINS

### 2.1 Estructura de Directorios

```
argos/plugins/
├── __init__.py
├── marketplace.json              # Catálogo centralizado
├── plugin-index.json             # Índice generado (auto)
├── registry.py                   # Registro de plugins
├── manager.py                    # Gestión de plugins
├── hooks/
│   ├── __init__.py
│   ├── base.py                   # Base hook interface
│   ├── detection.py              # Hooks de detección
│   ├── response.py               # Hooks de respuesta
│   ├── lifecycle.py              # Hooks de ciclo de vida
│   └── security.py               # Hooks de seguridad
├── skills/                       # Capacidades de IA (opcional)
├── commands/                     # Slash commands (opcional)
├── agents/                       # Subagentes (opcional)
├── mcp_servers/                 # MCP servers (opcional)
└── installed/                    # Plugins instalados
    ├── plugin-a/
    ├── plugin-b/
    └── plugin-c/
```

### 2.2 Esquema de Plugin

```python
# Estructura de un plugin
{
    "name": "plugin-name",
    "version": "1.0.0",
    "description": "Descripción del plugin",
    "author": "Autor",
    "license": "Apache-2.0",
    "category": "detection|response|analytics|ui",
    "permissions": ["read", "analyze", "execute", "modify"],
    "dependencies": [],
    "entry_point": "argos.plugins.installed.plugin_name:Plugin",
    "components": {
        "skills": ["skill1", "skill2"],
        "commands": ["cmd1", "cmd2"],
        "agents": ["agent1"],
        "mcp_servers": ["mcp1"],
        "hooks": ["pre_detection", "post_response"]
    },
    "source": {
        "type": "local|remote",
        "path": "./plugins/plugin-name",  # para local
        "url": "https://github.com/user/repo",  # para remote
        "sha": "abc123..."  # SHA para remote
    }
}
```

---

## 3. MIGRACIÓN DE TOOLS ACTUALES

### 3.1 Tools a Migrar

**Tools actuales en `argos.ai.tools.plugins`:**
1. `query_events` → Plugin: `events-query`
2. `get_process_tree` → Plugin: `process-tree`
3. `get_active_connections` → Plugin: `network-connections`
4. `list_alerts` → Plugin: `alerts-manager`
5. `lookup_ioc` → Plugin: `threat-intel`
6. `get_coverage` → Plugin: `detection-coverage`
7. `detection_rules` → Plugin: `rules-manager`
8. `scan_yara` → Plugin: `yara-scanner`
9. `network_recon` → Plugin: `network-recon`
10. `correlate` → Plugin: `event-correlation`

### 3.2 Proceso de Migración

#### Paso 1: Crear Wrapper de Compatibilidad

```python
# argos/plugins/compatibility.py
from argos.ai.tools.registry import _REGISTRY, BaseTool
from typing import Any, Dict

class LegacyToolWrapper:
    """Wrapper para migrar tools antiguas a formato plugin."""
    
    @staticmethod
    def to_plugin(tool_class: type) -> Dict[str, Any]:
        """Convierte una tool antigua a schema de plugin."""
        return {
            "name": tool_class.name,
            "version": "1.0.0",
            "description": tool_class.description,
            "category": "detection",
            "permissions": [tool_class.perm],
            "entry_point": f"argos.ai.tools.plugins:{tool_class.__name__}",
            "components": {
                "hooks": [],
                "skills": [],
                "commands": [],
                "agents": [],
                "mcp_servers": []
            },
            "source": {
                "type": "local",
                "path": f"./argos/ai/tools/plugins"
            }
        }

def migrate_legacy_tools():
    """Migra todas las tools antiguas a formato plugin."""
    plugins = []
    for name, tool_class in _REGISTRY.items():
        plugin = LegacyToolWrapper.to_plugin(tool_class)
        plugins.append(plugin)
    return plugins
```

#### Paso 2: Migrar Tool Individual (Ejemplo: query_events)

```python
# argos/plugins/installed/events-query/__init__.py
from argos.plugins.base import BasePlugin
from argos.ai.tools.registry import BaseTool, ToolContext

class EventsQueryTool(BaseTool):
    name = "query_events"
    description = "Consulta eventos de seguridad con filtros avanzados"
    perm = "read"
    
    parameters = {
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "description": "Filtros para la consulta"
            },
            "limit": {
                "type": "integer",
                "description": "Límite de resultados",
                "default": 100
            }
        },
        "required": []
    }

    def run(self, arguments: dict) -> Any:
        filters = arguments.get("filters", {})
        limit = arguments.get("limit", 100)
        
        # Lógica original de query_events
        events = self.ctx.store.query(filters=filters, limit=limit)
        
        return {
            "count": len(events),
            "events": [self._slim_event(e) for e in events]
        }
    
    def _slim_event(self, event) -> dict:
        d = event.as_dict()
        return {
            "time": d.get("time"),
            "category": d.get("category"),
            "host": d.get("host"),
            "severity": d.get("severity"),
            "process_name": d.get("process_name"),
            "src_ip": d.get("src_ip"),
            "dst_ip": d.get("dst_ip"),
        }

class EventsQueryPlugin(BasePlugin):
    """Plugin para consulta de eventos."""
    
    name = "events-query"
    version = "1.0.0"
    description = "Plugin para consulta avanzada de eventos de seguridad"
    category = "detection"
    permissions = ["read"]
    
    def __init__(self):
        super().__init__()
        self.tool = EventsQueryTool
    
    def get_tools(self):
        return [EventsQueryTool]
    
    def get_hooks(self):
        return []
```

#### Paso 3: Crear Plugin Manifest

```json
// argos/plugins/installed/events-query/plugin.json
{
    "name": "events-query",
    "version": "1.0.0",
    "description": "Plugin para consulta avanzada de eventos de seguridad",
    "author": "ARGOS Team",
    "license": "Apache-2.0",
    "category": "detection",
    "permissions": ["read"],
    "dependencies": [],
    "entry_point": "argos.plugins.installed.events_query:EventsQueryPlugin",
    "components": {
        "skills": [],
        "commands": ["events"],
        "agents": [],
        "mcp_servers": [],
        "hooks": []
    },
    "source": {
        "type": "local",
        "path": "./argos/plugins/installed/events-query"
    }
}
```

#### Paso 4: Actualizar Marketplace

```json
// argos/plugins/marketplace.json
{
    "name": "argos-marketplace",
    "version": "1.0.0",
    "description": "Catálogo oficial de plugins ARGOS",
    "plugins": [
        {
            "name": "events-query",
            "version": "1.0.0",
            "source": {
                "type": "local",
                "path": "./plugins/installed/events-query"
            },
            "description": "Plugin para consulta avanzada de eventos",
            "category": "detection",
            "permissions": ["read"]
        },
        {
            "name": "process-tree",
            "version": "1.0.0",
            "source": {
                "type": "local",
                "path": "./plugins/installed/process-tree"
            },
            "description": "Plugin para análisis de árbol de procesos",
            "category": "detection",
            "permissions": ["read"]
        }
        // ... más plugins
    ]
}
```

### 3.3 Script de Migración Automatizada

```python
# scripts/migrate_tools_to_plugins.py
import os
import json
from pathlib import Path
from argos.plugins.compatibility import migrate_legacy_tools

def create_plugin_structure(tool_name: str, tool_class: type):
    """Crea la estructura de directorios para un plugin."""
    plugin_dir = Path(f"argos/plugins/installed/{tool_name}")
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text(generate_plugin_init(tool_name, tool_class))
    
    # Crear plugin.json
    manifest_file = plugin_dir / "plugin.json"
    manifest_file.write_text(generate_plugin_manifest(tool_name, tool_class))

def generate_plugin_init(tool_name: str, tool_class: type) -> str:
    """Genera el código __init__.py para el plugin."""
    return f'''
from argos.plugins.base import BasePlugin
from argos.ai.tools.registry import BaseTool, ToolContext

class {tool_class.__name__}Tool(BaseTool):
    name = "{tool_class.name}"
    description = "{tool_class.description}"
    perm = "{tool_class.perm}"
    parameters = {json.dumps(tool_class.parameters)}
    
    def run(self, arguments: dict):
        # Lógica original de la tool
        # Copiar desde argos.ai.tools.plugins
        pass

class {tool_name.title()}Plugin(BasePlugin):
    name = "{tool_name}"
    version = "1.0.0"
    description = "{tool_class.description}"
    category = "detection"
    permissions = ["{tool_class.perm}"]
    
    def get_tools(self):
        return [{tool_class.__name__}Tool]
    
    def get_hooks(self):
        return []
'''

def generate_plugin_manifest(tool_name: str, tool_class: type) -> str:
    """Genera el manifest del plugin."""
    return json.dumps({
        "name": tool_name,
        "version": "1.0.0",
        "description": tool_class.description,
        "author": "ARGOS Team",
        "license": "Apache-2.0",
        "category": "detection",
        "permissions": [tool_class.perm],
        "dependencies": [],
        "entry_point": f"argos.plugins.installed.{tool_name}:{tool_name.title()}Plugin",
        "components": {
            "skills": [],
            "commands": [],
            "agents": [],
            "mcp_servers": [],
            "hooks": []
        },
        "source": {
            "type": "local",
            "path": f"./plugins/installed/{tool_name}"
        }
    }, indent=2)

def main():
    """Ejecuta la migración de todas las tools."""
    from argos.ai.tools.registry import _REGISTRY
    
    for tool_name, tool_class in _REGISTRY.items():
        plugin_name = tool_name.replace("_", "-")
        create_plugin_structure(plugin_name, tool_class)
        print(f"✓ Migrated {tool_name} -> {plugin_name}")
    
    print("Migration complete!")

if __name__ == "__main__":
    main()
```

---

## 4. SISTEMA DE HOOKS

### 4.1 Base Hook Interface

```python
# argos/plugins/hooks/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum

class HookEvent(Enum):
    """Eventos disponibles para hooks."""
    PRE_DETECTION = "pre_detection"
    POST_DETECTION = "post_detection"
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"
    ON_ALERT = "on_alert"
    ON_PLUGIN_INSTALL = "on_plugin_install"
    ON_PLUGIN_UNINSTALL = "on_plugin_uninstall"
    ON_CONFIG_CHANGE = "on_config_change"

class BaseHook(ABC):
    """Base interface para todos los hooks."""
    
    def __init__(self, event: HookEvent, priority: int = 10):
        self.event = event
        self.priority = priority
        self.enabled = True
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """Ejecuta el hook con el contexto dado."""
        pass
    
    def enable(self):
        """Habilita el hook."""
        self.enabled = True
    
    def disable(self):
        """Deshabilita el hook."""
        self.enabled = False
```

### 4.2 Implementación de Hooks Específicos

```python
# argos/plugins/hooks/detection.py
from .base import BaseHook, HookEvent
from typing import Dict, Any

class PreDetectionHook(BaseHook):
    """Hook ejecutado antes de la detección."""
    
    def __init__(self, priority: int = 10):
        super().__init__(HookEvent.PRE_DETECTION, priority)
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """Valida y enriquece el contexto antes de detección."""
        event = context.get("event")
        
        # Validación básica
        if not event:
            raise ValueError("Event is required")
        
        # Enriquecimiento
        context["enriched"] = True
        context["timestamp"] = context.get("timestamp", time.time())
        
        return context

class PostDetectionHook(BaseHook):
    """Hook ejecutado después de la detección."""
    
    def __init__(self, priority: int = 10):
        super().__init__(HookEvent.POST_DETECTION, priority)
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """Procesa el resultado de detección."""
        result = context.get("result")
        
        # Logging
        if result.get("alert"):
            log_detection_alert(result)
        
        # Notificación
        if result.get("severity") == "critical":
            send_critical_notification(result)
        
        return result
```

### 4.3 Registro y Ejecución de Hooks

```python
# argos/plugins/registry.py
from collections import defaultdict
from typing import Dict, List, Callable, Any
from .hooks.base import BaseHook, HookEvent

class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[HookEvent, List[BaseHook]] = defaultdict(list)
    
    def register_plugin(self, plugin: Plugin):
        """Registra un plugin."""
        self.plugins[plugin.name] = plugin
        
        # Registrar hooks del plugin
        for hook in plugin.get_hooks():
            self.hooks[hook.event].append(hook)
            # Ordenar por prioridad (mayor = antes)
            self.hooks[hook.event].sort(key=lambda h: h.priority, reverse=True)
    
    def execute_hooks(self, event: HookEvent, context: Dict[str, Any]) -> None:
        """Ejecuta hooks para un evento en orden de prioridad."""
        for hook in self.hooks[event]:
            if hook.enabled:
                try:
                    context = hook.execute(context)
                except Exception as e:
                    log_hook_error(hook, e)
```

---

## 5. PLUGIN MANAGER

### 5.1 Implementación del Manager

```python
# argos/plugins/manager.py
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from .registry import PluginRegistry
from .base import BasePlugin

class PluginManager:
    def __init__(self, registry: PluginRegistry, marketplace_path: str = "plugins/marketplace.json"):
        self.registry = registry
        self.marketplace_path = Path(marketplace_path)
        self.installed_dir = Path("plugins/installed")
        self.installed_dir.mkdir(exist_ok=True)
    
    def install(self, plugin_name: str, source: Dict[str, Any]) -> bool:
        """Instala un plugin desde source."""
        try:
            if source["type"] == "local":
                return self._install_local(plugin_name, source["path"])
            elif source["type"] == "remote":
                return self._install_remote(plugin_name, source["url"], source["sha"])
            else:
                raise ValueError(f"Unknown source type: {source['type']}")
        except Exception as e:
            log_install_error(plugin_name, e)
            return False
    
    def _install_local(self, plugin_name: str, path: str) -> bool:
        """Instala un plugin local."""
        source_path = Path(path)
        target_path = self.installed_dir / plugin_name
        
        if target_path.exists():
            raise ValueError(f"Plugin {plugin_name} already installed")
        
        shutil.copytree(source_path, target_path)
        
        # Cargar y registrar plugin
        plugin = self._load_plugin(target_path)
        self.registry.register_plugin(plugin)
        
        return True
    
    def _install_remote(self, plugin_name: str, url: str, sha: str) -> bool:
        """Instala un plugin remoto con verificación SHA."""
        import subprocess
        
        target_path = self.installed_dir / plugin_name
        
        if target_path.exists():
            raise ValueError(f"Plugin {plugin_name} already installed")
        
        # Clone repository
        subprocess.run(["git", "clone", url, str(target_path)], check=True)
        
        # Verificar SHA
        actual_sha = self._get_git_sha(target_path)
        if actual_sha != sha.lower():
            shutil.rmtree(target_path)
            raise ValueError(f"SHA mismatch: expected {sha}, got {actual_sha}")
        
        # Cargar y registrar plugin
        plugin = self._load_plugin(target_path)
        self.registry.register_plugin(plugin)
        
        return True
    
    def _get_git_sha(self, path: Path) -> str:
        """Obtiene el SHA actual del repo git."""
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    
    def uninstall(self, plugin_name: str) -> bool:
        """Desinstala un plugin."""
        if plugin_name not in self.registry.plugins:
            raise ValueError(f"Plugin {plugin_name} not installed")
        
        # Remover del registry
        del self.registry.plugins[plugin_name]
        
        # Remover directorio
        plugin_path = self.installed_dir / plugin_name
        if plugin_path.exists():
            shutil.rmtree(plugin_path)
        
        return True
    
    def _load_plugin(self, plugin_path: Path) -> BasePlugin:
        """Carga un plugin desde su directorio."""
        manifest_path = plugin_path / "plugin.json"
        
        if not manifest_path.exists():
            raise ValueError(f"plugin.json not found in {plugin_path}")
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Importar dinámicamente
        module_path, class_name = manifest["entry_point"].rsplit(":", 1)
        module = __import__(module_path, fromlist=[class_name])
        plugin_class = getattr(module, class_name)
        
        return plugin_class()
    
    def list_installed(self) -> List[Dict[str, Any]]:
        """Lista todos los plugins instalados."""
        return [
            {
                "name": name,
                "version": plugin.version,
                "description": plugin.description,
                "enabled": True
            }
            for name, plugin in self.registry.plugins.items()
        ]
    
    def update_marketplace(self) -> None:
        """Actualiza el marketplace.json desde el catálogo."""
        # Implementar lógica de actualización
        pass
```

---

## 6. TESTING

### 6.1 Tests de Migración

```python
# tests/plugins/test_migration.py
import pytest
from argos.plugins.compatibility import LegacyToolWrapper, migrate_legacy_tools
from argos.ai.tools.registry import _REGISTRY

def test_legacy_tool_wrapper():
    """Test el wrapper de tools antiguas."""
    tool_class = _REGISTRY.get("query_events")
    wrapper = LegacyToolWrapper()
    
    plugin = wrapper.to_plugin(tool_class)
    
    assert plugin["name"] == "query_events"
    assert plugin["version"] == "1.0.0"
    assert plugin["permissions"] == ["read"]

def test_migrate_legacy_tools():
    """Test la migración de todas las tools."""
    plugins = migrate_legacy_tools()
    
    assert len(plugins) > 0
    assert all("name" in p for p in plugins)
    assert all("version" in p for p in plugins)

def test_plugin_structure():
    """Test la estructura de plugins creados."""
    from scripts.migrate_tools_to_plugins import create_plugin_structure
    
    tool_class = _REGISTRY.get("query_events")
    create_plugin_structure("events-query", tool_class)
    
    plugin_dir = Path("argos/plugins/installed/events-query")
    assert plugin_dir.exists()
    assert (plugin_dir / "__init__.py").exists()
    assert (plugin_dir / "plugin.json").exists()
```

### 6.2 Tests de Hooks

```python
# tests/plugins/test_hooks.py
import pytest
from argos.plugins.hooks.base import BaseHook, HookEvent
from argos.plugins.hooks.detection import PreDetectionHook, PostDetectionHook

def test_pre_detection_hook():
    """Test hook de pre-detección."""
    hook = PreDetectionHook(priority=10)
    
    context = {"event": {"type": "test"}}
    result = hook.execute(context)
    
    assert result["enriched"] == True
    assert "timestamp" in result

def test_post_detection_hook():
    """Test hook de post-detección."""
    hook = PostDetectionHook(priority=10)
    
    context = {"result": {"alert": True, "severity": "critical"}}
    result = hook.execute(context)
    
    assert result == context  # Hook modifica contexto

def test_hook_priority():
    """Test ordenamiento de hooks por prioridad."""
    from argos.plugins.registry import PluginRegistry
    
    registry = PluginRegistry()
    hook1 = PreDetectionHook(priority=5)
    hook2 = PreDetectionHook(priority=10)
    
    registry.register_hook(hook1)
    registry.register_hook(hook2)
    
    hooks = registry.hooks[HookEvent.PRE_DETECTION]
    assert hooks[0].priority == 10  # Mayor prioridad primero
    assert hooks[1].priority == 5
```

### 6.3 Tests de Plugin Manager

```python
# tests/plugins/test_manager.py
import pytest
from pathlib import Path
from argos.plugins.manager import PluginManager
from argos.plugins.registry import PluginRegistry

def test_install_local_plugin():
    """Test instalación de plugin local."""
    registry = PluginRegistry()
    manager = PluginManager(registry)
    
    # Crear plugin de prueba
    test_plugin_dir = Path("test_plugin")
    test_plugin_dir.mkdir()
    (test_plugin_dir / "plugin.json").write_text('{"name": "test", "version": "1.0.0"}')
    
    result = manager.install("test", {"type": "local", "path": str(test_plugin_dir)})
    
    assert result == True
    assert "test" in registry.plugins
    
    # Cleanup
    import shutil
    shutil.rmtree(test_plugin_dir)
    shutil.rmtree("plugins/installed/test")

def test_uninstall_plugin():
    """Test desinstalación de plugin."""
    registry = PluginRegistry()
    manager = PluginManager(registry)
    
    # Instalar primero
    manager.install("test", {"type": "local", "path": "test_plugin"})
    
    # Desinstalar
    result = manager.uninstall("test")
    
    assert result == True
    assert "test" not in registry.plugins
```

---

## 7. VALIDACIÓN

### 7.1 Checklist de Validación

**Antes de considerar la migración completa:**

- [ ] Todas las tools originales migradas a plugins
- [ ] Marketplace.json actualizado con todos los plugins
- [ ] Plugin-index.json generado correctamente
- [ ] Hooks básicos implementados y testeados
- [ ] Plugin manager funcional (install/uninstall/list)
- [ ] Tests unitarios para cada componente
- [ ] Integration tests para el flujo completo
- [ ] Documentación actualizada
- [ ] Backward compatibility mantenida
- [ ] Performance no degradada

### 7.2 Tests de Regresión

```python
# tests/test_regression.py
import pytest
from argos.ai.tools.registry import ToolExecutor
from argos.plugins.manager import PluginManager

def test_backward_compatibility():
    """Test que las tools originales aún funcionan."""
    # Las tools originales deben seguir funcionando
    # a través del nuevo sistema de plugins
    executor = ToolExecutor(store, engine, intel)
    
    result = executor.execute("query_events", {"filters": {}, "limit": 10})
    
    assert result.output["count"] >= 0
    assert "events" in result.output

def test_plugin_performance():
    """Test que el sistema de plugins no degrada performance."""
    import time
    
    executor = ToolExecutor(store, engine, intel)
    
    start = time.time()
    for _ in range(100):
        executor.execute("query_events", {"filters": {}, "limit": 10})
    elapsed = time.time() - start
    
    # No debe ser más del 20% más lento
    assert elapsed < 2.0  # 100 calls en <2s
```

---

## 8. DEPLOYMENT

### 8.1 Estrategia de Rollout

**Fase 1: Shadow Mode**
- Ejecutar ambos sistemas en paralelo
- Comparar resultados
- Validar que no haya diferencias

**Fase 2: Canary Release**
- Habilitar plugin system para 10% de usuarios
- Monitorear errores y performance
- Aumentar gradualmente

**Fase 3: Full Rollout**
- Habilitar para todos los usuarios
- Mantener sistema antiguo como fallback
- Monitorear por 1 semana

**Fase 4: Cleanup**
- Remover código antiguo
- Actualizar documentación
- Entrenar equipo

### 8.2 Rollback Plan

Si algo falla:
1. Deshabilitar plugin system vía config
2. Revertir a sistema de tools original
3. Investigar causa del fallo
4. Corregir y retry

---

## 9. DOCUMENTACIÓN

### 9.1 Para Desarrolladores de Plugins

```markdown
# Guía de Desarrollo de Plugins

## Estructura Mínima

```
my-plugin/
├── __init__.py
├── plugin.json
└── (archivos adicionales)
```

## plugin.json Ejemplo

```json
{
    "name": "my-plugin",
    "version": "1.0.0",
    "description": "Mi plugin personalizado",
    "category": "detection",
    "permissions": ["read"],
    "entry_point": "my_plugin:MyPlugin"
}
```

## Implementación Básica

```python
class MyPlugin(BasePlugin):
    name = "my-plugin"
    version = "1.0.0"
    
    def get_tools(self):
        return [MyTool]
    
    def get_hooks(self):
        return [MyHook]
```
```

### 9.2 Para Usuarios

```markdown
# Guía de Uso de Plugins

## Instalar un Plugin

```bash
argos-cli plugin install events-query
```

## Listar Plugins Instalados

```bash
argos-cli plugin list
```

## Desinstalar un Plugin

```bash
argos-cli plugin uninstall events-query
```

## Habilitar/Deshabilitar Plugin

```bash
argos-cli plugin enable events-query
argos-cli plugin disable events-query
```
```

---

## 10. PRÓXIMOS PASOS

1. **Inmediato:**
   - Ejecutar script de migración
   - Validar estructura creada
   - Ejecutar tests de regresión

2. **Corto plazo (1 semana):**
   - Implementar hooks adicionales
   - Completar testing
   - Documentación para desarrolladores

3. **Mediano plazo (2 semanas):**
   - Shadow mode deployment
   - Canary release
   - Full rollout

4. **Largo plazo (1 mes):**
   - Ecosistema de plugins comunitario
   - Marketplace de plugins externos
   - Plugins avanzados (ML, UEBA, etc.)

---

## CONCLUSIÓN

Esta guía proporciona un camino completo para migrar el sistema de tools actual a una arquitectura de plugins enterprise, manteniendo backward compatibility y mejorando significativamente la extensibilidad y mantenibilidad del sistema.
