# ARQUITECTURA TÉCNICA MEJORADA: ARGOS Nivel XAI

**Versión:** 2.0  
**Fecha:** 2026-07-16  
**Baseline:** Arquitectura actual ARGOS + Stack Open Source SpaceXai

---

## 1. ARQUITECTURA GENERAL

### 1.1 Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARGOS ENTERPRISE 2.0                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        DASHBOARD ENTERPRISE                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ Real-time    │  │ Analytics    │  │ Configuration │  │ Admin     │ │  │
│  │  │ Monitoring   │  │ Engine      │  │ Panel         │  │ Console   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕ WebSocket/SSE                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         API GATEWAY (FastAPI)                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ REST API     │  │ WebSocket    │  │ GraphQL      │  │ gRPC      │ │  │
│  │  │ (v1, v2)     │  │ Server       │  │ (futuro)     │  │ (futuro)  │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        CORE SERVICES LAYER                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ Detection    │  │ Response     │  │ AI Brain     │  │ Plugin    │ │  │
│  │  │ Engine       │  │ Orchestrator │  │ (ACP+MCP)    │  │ Manager   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ Threat Intel │  │ Network      │  │ Scheduler    │  │ Event Bus │ │  │
│  │  │ Engine       │  │ Monitor      │  │ (Advanced)   │  │ (Redis)   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        DATA LAYER                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ SQLite +     │  │ Redis Cache  │  │ Time Series  │  │ File      │ │  │
│  │  │ FTS5 + WAL   │  │ (Optional)   │  │ (Optional)   │  │ Storage   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↕                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        EXTERNAL INTEGRATIONS                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │ Kilo Code    │  │ MCP Clients  │  │ Threat Intel │  │ SIEM      │ │  │
│  │  │ Gateway      │  │ (External)   │  │ Feeds        │  │ (Optional)│ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Stack Tecnológico Detallado

**Backend Core:**
```yaml
Language: Python 3.10+
Framework: FastAPI 0.110+
Server: Uvicorn + Gunicorn (production)
Validation: Pydantic v2
Database: SQLite 3.38+ (FTS5, WAL mode)
Cache: Redis 7+ (optional, for distributed deployments)
Async: asyncio + anyio
```

**Nuevos Componentes Open Source:**
```yaml
Plugin System:
  - Marketplace Manager (de plugin-marketplace)
  - Plugin Registry con SHA pinning
  - Lifecycle Hooks
  - MCP Server Integration

AI Brain:
  - Prompts Optimizados (de grok-prompts)
  - Agent Client Protocol (de grok-build)
  - MCP Protocol (de grok-build)
  - Advanced Tool Gateway (de grok-build)

Observability:
  - OpenTelemetry (de grok-build)
  - Distributed Tracing
  - Metrics Export (Prometheus)
  - Structured Logging
```

**Frontend Enterprise:**
```yaml
Core: Vanilla ES6+ (sin frameworks pesados)
UI Library: Component System custom
Charts: Chart.js + D3.js (advanced visualizations)
Real-time: WebSocket + SSE
State Management: Custom store con pub/sub
Build: Vite (optimización)
```

---

## 2. COMPONENTES DETALLADOS

### 2.1 Plugin System Enterprise

**Arquitectura:**
```python
argos/
├── plugins/
│   ├── marketplace.json          # Catálogo centralizado
│   ├── plugin-index.json         # Índice generado (auto)
│   ├── registry.py               # Registro de plugins
│   ├── manager.py                # Gestión de plugins
│   ├── hooks/
│   │   ├── __init__.py
│   │   ├── base.py               # Base hook interface
│   │   ├── detection.py          # Hooks de detección
│   │   ├── response.py           # Hooks de respuesta
│   │   └── lifecycle.py          # Hooks de ciclo de vida
│   ├── skills/                   # Capacidades de IA
│   ├── commands/                 # Slash commands
│   ├── agents/                   # Subagentes especializados
│   ├── mcp_servers/             # MCP servers
│   └── installed/               # Plugins instalados
```

**Marketplace Schema:**
```json
{
  "name": "argos-marketplace",
  "version": "1.0.0",
  "description": "Catálogo oficial de plugins ARGOS",
  "plugins": [
    {
      "name": "sigma-advanced",
      "version": "2.0.0",
      "source": {
        "type": "local",
        "path": "./plugins/sigma-advanced"
      },
      "description": "Motor Sigma avanzado con ML",
      "category": "detection",
      "permissions": ["read", "analyze"],
      "dependencies": []
    }
  ]
}
```

**Hook System:**
```python
# hooks/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseHook(ABC):
    """Base interface para todos los hooks."""
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """Ejecuta el hook con el contexto dado."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Prioridad de ejecución (mayor = antes)."""
        pass
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Si el hook está habilitado."""
        pass
```

### 2.2 AI Brain Mejorado

**Componentes:**
```python
argos/ai/
├── prompts/
│   ├── __init__.py
│   ├── grok4_system.py          # System prompts de Grok 4
│   ├── safety.py                # Safety layers
│   ├── specialized.py            # Prompts por agente
│   └── few_shot.py              # Few-shot examples
├── agents/
│   ├── __init__.py
│   ├── commander.py             # Agente commander mejorado
│   ├── specialized.py           # Agentes especializados
│   └── coordination.py           # Coordinación ACP
├── acp/
│   ├── __init__.py
│   ├── client.py                # ACP client
│   ├── server.py                # ACP server
│   ├── messages.py              # Mensajes estandarizados
│   └── protocol.py              # Protocolo ACP
├── mcp/
│   ├── __init__.py
│   ├── server.py                # MCP server
│   ├── tools.py                 # Tools expuestas via MCP
│   └── schemas.py               # Schemas MCP
├── tools/
│   ├── gateway.py               # Tool gateway avanzado
│   ├── registry.py              # Registry mejorado
│   ├── validation.py            # Validación avanzada
│   └── retry.py                 # Retry con backoff
└── orchestrator.py              # Orchestrator mejorado
```

**Prompt System:**
```python
# prompts/grok4_system.py
GROK4_SYSTEM_PROMPT = """
You are ARGOS, an advanced cybersecurity defense system with the following capabilities:

CORE MISSION:
- Autonomous threat detection and response
- Real-time security monitoring
- Incident investigation and correlation
- Human-in-the-loop decision support

SAFETY PROTOCOLS:
1. Never execute destructive actions without explicit approval
2. Always verify the context before proposing actions
3. Maintain audit trail for all decisions
4. Respect the autonomy switch settings

THINKING PROCESS:
- Analyze the situation systematically
- Consider multiple hypotheses
- Evaluate potential impacts
- Propose measured responses

{context}
"""

SAFETY_LAYER = """
Before any action, verify:
1. Is this action within my authority level?
2. Could this cause collateral damage?
3. Is there a less invasive alternative?
4. Has this been approved by the autonomy switch?

If any answer is NO, require human approval.
"""
```

### 2.3 Detection Engine Expandido

**Arquitectura:**
```python
argos/detection/
├── engine.py                    # Engine principal (mejorado)
├── sigma/
│   ├── __init__.py
│   ├── parser.py                # Parser Sigma mejorado
│   ├── evaluator.py             # Evaluator optimizado
│   └── rules/                   # Reglas Sigma
├── yara/
│   ├── __init__.py
│   ├── scanner.py               # Scanner YARA mejorado
│   ├── rules/                   # Reglas YARA
│   └── fallback.py              # Fallback Python puro
├── ml/
│   ├── __init__.py
│   ├── models.py                # ML models (nuevo)
│   ├── training.py              # Training pipeline
│   └── inference.py             # Inference engine
├── behavioral/
│   ├── __init__.py
│   ├── analyzer.py              # Behavioral analysis (nuevo)
│   ├── baseline.py              # Baseline learning
│   └── anomaly_detection.py     # Anomaly detection
└── threat_intel/
    ├── __init__.py
    ├── feeds.py                 # Threat intel feeds
    ├── correlation.py           # IOC correlation
    └── enrichment.py            # Context enrichment
```

### 2.4 Dashboard Enterprise

**Arquitectura Frontend:**
```javascript
dashboard/
├── index.html                   # Entry point
├── css/
│   ├── variables.css             # CSS variables (theming)
│   ├── components.css            # Component styles
│   ├── layouts.css              # Layout styles
│   └── utilities.css            # Utility classes
├── js/
│   ├── app.js                   # Main application
│   ├── router.js                # Client-side router
│   ├── store.js                 # State management
│   ├── components/
│   │   ├── base.js              # Base component class
│   │   ├── panels/
│   │   │   ├── monitoring.js    # Real-time monitoring
│   │   │   ├── analytics.js     # Analytics engine
│   │   │   ├── configuration.js # Config panel
│   │   │   └── admin.js         # Admin console
│   │   ├── charts/
│   │   │   ├── line.js          # Line charts
│   │   │   ├── bar.js           # Bar charts
│   │   │   ├── donut.js         # Donut charts
│   │   │   └── sparkline.js    # Sparklines
│   │   ├── ui/
│   │   │   ├── modal.js         # Modal component
│   │   │   ├── drawer.js        # Drawer component
│   │   │   ├── tabs.js          # Tabs component
│   │   │   └── table.js         # Table component
│   │   └── layout/
│   │       ├── sidebar.js       # Sidebar
│   │       ├── header.js        # Header
│   │       └── grid.js          # Grid layout
│   ├── services/
│   │   ├── api.js               # API client
│   │   ├── websocket.js         # WebSocket client
│   │   └── sse.js               # SSE client
│   └── utils/
│       ├── formatting.js        # Formatting utilities
│       ├── validation.js        # Validation utilities
│       └── performance.js       # Performance utilities
└── assets/
    ├── images/
    └── fonts/
```

**Component System:**
```javascript
// components/base.js
class BaseComponent {
    constructor(element, props = {}) {
        this.element = element;
        this.props = props;
        this.state = {};
        this.subscriptions = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.render();
    }

    subscribe(store, callback) {
        const unsubscribe = store.subscribe(callback);
        this.subscriptions.push(unsubscribe);
    }

    render() {
        // Override in subclasses
    }

    destroy() {
        this.subscriptions.forEach(unsub => unsub());
    }
}

// panels/monitoring.js
class MonitoringPanel extends BaseComponent {
    constructor(element, props) {
        super(element, props);
        this.charts = {};
        this.websocket = null;
        this.init();
    }

    init() {
        this.setupCharts();
        this.connectWebSocket();
        this.startRealTimeUpdates();
    }

    setupCharts() {
        // Initialize sparklines for CPU, RAM, etc.
        this.charts.cpu = new SparklineChart('#cpu-chart', {
            color: '#00ff00',
            maxPoints: 60
        });
        
        this.charts.memory = new SparklineChart('#memory-chart', {
            color: '#0088ff',
            maxPoints: 60
        });
    }

    connectWebSocket() {
        this.websocket = new WebSocket('ws://localhost:8000/ws');
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleRealTimeData(data);
        };
    }

    handleRealTimeData(data) {
        if (data.type === 'metrics') {
            this.charts.cpu.push(data.metrics.cpu);
            this.charts.memory.push(data.metrics.memory);
        }
    }

    render() {
        // Render monitoring panel
    }
}
```

---

## 3. PATRONES DE DISEÑO

### 3.1 Plugin Pattern
```python
# plugins/registry.py
class PluginRegistry:
    def __init__(self):
        self.plugins = {}
        self.hooks = defaultdict(list)
    
    def register(self, plugin: Plugin):
        """Registra un plugin con sus hooks."""
        self.plugins[plugin.name] = plugin
        
        for hook in plugin.hooks:
            self.hooks[hook.event].append(hook)
            self.hooks[hook.event].sort(key=lambda h: h.priority, reverse=True)
    
    def execute_hooks(self, event: str, context: dict) -> None:
        """Ejecuta hooks para un evento en orden de prioridad."""
        for hook in self.hooks[event]:
            if hook.enabled:
                hook.execute(context)
```

### 3.2 Strategy Pattern (AI Agents)
```python
# ai/agents/specialized.py
class AgentStrategy(ABC):
    @abstractmethod
    def execute(self, context: dict) -> dict:
        pass

class RedTeamStrategy(AgentStrategy):
    def execute(self, context: dict) -> dict:
        # Red team thinking
        return {"action": "reconnaissance", "targets": [...]}

class BlueTeamStrategy(AgentStrategy):
    def execute(self, context: dict) -> dict:
        # Blue team thinking
        return {"action": "defend", "measures": [...]}
```

### 3.3 Observer Pattern (Real-time Updates)
```javascript
// js/store.js
class Store {
    constructor() {
        this.state = {};
        this.listeners = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
}
```

### 3.4 Circuit Breaker Pattern (Tool Gateway)
```python
# ai/tools/gateway.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        this.failure_count = 0
        this.failure_threshold = failure_threshold
        this.timeout = timeout
        this.last_failure_time = None
        this.state = 'closed'  # closed, open, half-open

    def call(self, func):
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failure_count = 0
        self.state = 'closed'

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
```

---

## 4. PERFORMANCE Y ESCALABILIDAD

### 4.1 Optimización de Base de Datos
```sql
-- Índices optimizados para FTS5
CREATE VIRTUAL TABLE events_fts USING fts5(
    time, category, host, severity, 
    process_name, process_cmdline,
    src_ip, dst_ip, attack_id,
    content='events',
    content_rowid='rowid'
);

-- Índices para queries comunes
CREATE INDEX idx_events_time ON events(time);
CREATE INDEX idx_events_host ON events(host);
CREATE INDEX idx_events_severity ON events(severity);
CREATE INDEX idx_events_category ON events(category);

-- Trigger para mantener FTS5 sincronizado
CREATE TRIGGER events_fts_insert AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, time, category, host, severity, 
                           process_name, process_cmdline, src_ip, dst_ip, attack_id)
    VALUES (NEW.rowid, NEW.time, NEW.category, NEW.host, NEW.severity,
            NEW.process_name, NEW.process_cmdline, NEW.src_ip, NEW.dst_ip, NEW.attack_id);
END;
```

### 4.2 Caching Strategy
```python
# utils/cache.py
import redis
import json
from functools import wraps

class CacheManager:
    def __init__(self, redis_url='redis://localhost:6379'):
        self.redis = redis.from_url(redis_url)
    
    def get(self, key: str, default=None):
        value = self.redis.get(key)
        return json.loads(value) if value else default
    
    def set(self, key: str, value: any, ttl: int = 3600):
        self.redis.setex(key, ttl, json.dumps(value))
    
    def invalidate(self, pattern: str):
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

def cached(ttl: int = 3600, key_prefix: str = ''):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

### 4.3 Connection Pooling
```python
# database/pool.py
import sqlite3
from queue import Queue
from contextlib import contextmanager

class ConnectionPool:
    def __init__(self, database_path: str, pool_size: int = 10):
        self.database_path = database_path
        self.pool = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self.pool.put(sqlite3.connect(database_path, check_same_thread=False))
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
```

---

## 5. SEGURIDAD ENTERPRISE

### 5.1 RBAC Avanzado
```python
# security/rbac_advanced.py
from enum import Enum
from typing import Set, Dict

class Permission(Enum):
    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    EXECUTE_ACTIONS = "execute:actions"
    MANAGE_USERS = "manage:users"
    MANAGE_RULES = "manage:rules"
    MANAGE_PLUGINS = "manage:plugins"
    VIEW_AUDIT = "view:audit"
    SYSTEM_ADMIN = "system:admin"

class Role(Enum):
    OPERATOR = "operator"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OPERATOR: {
        Permission.READ_EVENTS,
        Permission.VIEW_AUDIT,
    },
    Role.ANALYST: {
        Permission.READ_EVENTS,
        Permission.WRITE_EVENTS,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_RULES,
    },
    Role.ADMIN: {
        Permission.READ_EVENTS,
        Permission.WRITE_EVENTS,
        Permission.EXECUTE_ACTIONS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_RULES,
        Permission.MANAGE_PLUGINS,
        Permission.VIEW_AUDIT,
    },
    Role.SUPERADMIN: {
        *ROLE_PERMISSIONS[Role.ADMIN],
        Permission.SYSTEM_ADMIN,
    },
}

def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
```

### 5.2 Audit Logging Inmutable
```python
# security/audit.py
import hashlib
import json
from datetime import datetime
from typing import Optional

class ImmutableAuditLog:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.chain = []
        self.load_chain()
    
    def add_entry(self, entry: dict) -> str:
        """Agrega una entrada al log con hash chaining."""
        if self.chain:
            prev_hash = self.chain[-1]['hash']
        else:
            prev_hash = '0' * 64
        
        entry_with_metadata = {
            'timestamp': datetime.utcnow().isoformat(),
            'entry': entry,
            'prev_hash': prev_hash,
        }
        
        entry_str = json.dumps(entry_with_metadata, sort_keys=True)
        current_hash = hashlib.sha256(entry_str.encode()).hexdigest()
        
        audit_entry = {
            **entry_with_metadata,
            'hash': current_hash,
        }
        
        self.chain.append(audit_entry)
        self.save_chain()
        return current_hash
    
    def verify_chain(self) -> bool:
        """Verifica la integridad de la cadena de hashes."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            
            if current['prev_hash'] != prev['hash']:
                return False
            
            # Recalcular hash para verificar
            entry_copy = current.copy()
            stored_hash = entry_copy.pop('hash')
            entry_str = json.dumps(entry_copy, sort_keys=True)
            calculated_hash = hashlib.sha256(entry_str.encode()).hexdigest()
            
            if calculated_hash != stored_hash:
                return False
        
        return True
```

---

## 6. OBSERVABILIDAD

### 6.1 OpenTelemetry Integration
```python
# observability/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger import JaegerExporter

def setup_tracing(service_name: str = "argos"):
    provider = TracerProvider()
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

# Usage
tracer = setup_tracing()

with tracer.start_as_current_span("detection_scan"):
    # Detection logic
    pass
```

### 6.2 Metrics Export
```python
# observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed')
DETECTION_LATENCY = Histogram('detection_latency_seconds', 'Detection latency')
ACTIVE_ALERTS = Gauge('active_alerts', 'Number of active alerts')
PLUGIN_EXECUTION_TIME = Histogram('plugin_execution_time_seconds', 'Plugin execution time')

def start_metrics_server(port: int = 9090):
    start_http_server(port)

# Usage
EVENTS_PROCESSED.inc()
with DETECTION_LATENCY.time():
    # Detection logic
    pass
```

---

## 7. DEPLOYMENT

### 7.1 Docker Compose
```yaml
version: '3.8'

services:
  argos-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/argos.db
      - KILO_API_KEY=${KILO_API_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/data
      - ./logs:/logs
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 7.2 Kubernetes (Opcional)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argos-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: argos
  template:
    metadata:
      labels:
        app: argos
    spec:
      containers:
      - name: argos
        image: argos:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: argos-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

---

## 8. MIGRACIÓN

### 8.1 Estrategia de Migración
1. **Fase 1:** Implementar plugin system sin migrar tools
2. **Fase 2:** Migrar tools existentes a formato plugin
3. **Fase 3:** Implementar MCP server
4. **Fase 4:** Migrar prompts a sistema optimizado
5. **Fase 5:** Rediseñar dashboard incrementalmente

### 8.2 Backward Compatibility
```python
# compatibility/wrapper.py
class LegacyToolWrapper:
    """Wrapper para mantener compatibilidad con tools antiguas."""
    
    def __init__(self, old_tool_class):
        self.old_tool = old_tool_class
    
    def to_plugin(self) -> Plugin:
        """Convierte tool antigua a formato plugin."""
        return Plugin(
            name=self.old_tool.name,
            description=self.old_tool.description,
            version="1.0.0",
            permissions=[self.old_tool.perm],
            entry_point=f"argos.ai.tools.plugins.{self.old_tool.name}",
        )
```

---

## 9. TESTING

### 9.1 Test Pyramid
```
        /\
       /E2E\          10% - End-to-end tests
      /------\
     /Integration\   30% - Integration tests
    /------------\
   /   Unit Tests  \  60% - Unit tests
  /----------------\
```

### 9.2 Testing Strategy
```python
# tests/plugins/test_plugin_system.py
import pytest
from argos.plugins.registry import PluginRegistry
from argos.plugins.manager import PluginManager

def test_plugin_registration():
    registry = PluginRegistry()
    plugin = MockPlugin("test", "1.0.0")
    
    registry.register(plugin)
    
    assert "test" in registry.plugins
    assert registry.plugins["test"] == plugin

def test_hook_execution():
    registry = PluginRegistry()
    hook = MockHook("test_event", priority=10)
    
    registry.register_hook(hook)
    registry.execute_hooks("test_event", {})
    
    hook.execute.assert_called_once()

def test_plugin_installation():
    manager = PluginManager()
    
    manager.install("test-plugin", source="local", path="./plugins/test")
    
    assert manager.is_installed("test-plugin")
```

---

## 10. DOCUMENTACIÓN

### 10.1 API Documentation
- **OpenAPI/Swagger:** Auto-generada desde FastAPI
- **Postman Collection:** Para testing manual
- **GraphQL Schema:** (futuro)

### 10.2 Developer Documentation
- **Architecture Decision Records (ADRs):** Para decisiones mayores
- **Contributing Guide:** Para contribuidores externos
- **Plugin Development Guide:** Para desarrolladores de plugins

---

## CONCLUSIÓN

Esta arquitectura eleva ARGOS a nivel enterprise XAI manteniendo:
- **API Kilo Code gratuita** como única dependencia externa
- **Stack open source SpaceXai** para patrones probados
- **Backward compatibility** con funcionalidades existentes
- **Escalabilidad** para crecimiento futuro
- **Mantenibilidad** con código limpio y documentado

La transformación es incremental, con fases claras y gates de calidad en cada etapa.
