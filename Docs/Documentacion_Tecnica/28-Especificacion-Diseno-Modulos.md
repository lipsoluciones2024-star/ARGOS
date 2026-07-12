---
título: 28 - Especificación de Diseño por Módulo (qué debe ir en el código)
objetivo: Para cada módulo, especificar a nivel granular qué componentes, responsabilidades, funciones/tools, estructuras de datos y comportamientos debe contener el código. Sin código fuente.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 3,5,6,7,12; 05-Arquitectura-Carpetas.md; 06-Arquitectura-Codigo.md.
dependencias: 04-Arquitectura.md; 05-Arquitectura-Carpetas.md; 27-Flujos-de-Datos.md.
referencias: 25-Historias-de-Usuario.md; 26-Criterios-de-Aceptacion.md.
---

# 28 - Especificación de Diseño por Módulo

Cada módulo indica **qué debe ir en el código** (componentes, responsabilidades, funciones, datos, comportamientos). No es código; es la especificación de diseño que el implementador debe seguir.

## Módulo A — Agentes de endpoint (`agents/`)

**Responsabilidad:** capturar telemetría nativa por SO y emitir eventos OCSF con mínimos privilegios.

Debe contener:
- **Capturadores por SO:**
  - Windows: lector ETW (providers Kernel-Process/File/Network/Registry), receptor Sysmon (Event IDs 1,3,5,7,8,10,11,12/13/14,17/18,22,25), lector Windows Event Log Security (4624/4625/4672/4688/4720/4728/4732/5140/5145), habilitador PowerShell Script Block Logging (4104) y AMSI hook.
  - Linux: daemon auditd (`/etc/passwd`, `execve`) + cliente eBPF (Falco/Tracee/Tetragon) + lector Netfilter/nftables.
  - macOS: cliente ESF (suscripción a EXEC/FORK/OPEN/MMAP/MOUNT, requiere entitlement + Full Disk Access) + lector Unified Logging + FSEvents + lector TCC.db + enumerador launchd.
  - Android: app con VpnService (red), UsageStatsManager, NetworkStatsManager, Accessibility Service (opcional, consentimiento), MDM/Device Owner; modo lab Frida/Magisk/`logcat`/`dumpsys`.
- **Normalizador a OCSF:** mapea cada evento nativo al esquema común (ver `27-Flujos-de-Datos.md`).
- **Buffer local:** persistencia en SQLite embebido cuando el cerebro no está disponible; reenvío al reconectar.
- **Emisor seguro:** cliente mTLS que envía eventos al collector (gRPC o NATS/MQTT-TLS).
- **Enumerador de persistencia:** diff periódico contra baseline (Run keys, scheduled tasks, servicios, WMI, launchd).

## Módulo B — Transporte seguro (parte de agente/collector)

Debe contener:
- Configuración mTLS (cert/key del agente, CA del collector).
- Lógica de reconexión y reenvío de buffer.
- Soporte de gRPC directo o pub/sub NATS/MQTT sobre TLS.

## Módulo C — Collector (`collector/`)

**Responsabilidad:** recibir, normalizar y enrutar.

Debe contener:
- Configuración de Vector.dev (o Fluent Bit).
- Pipelines de normalización a OCSF.
- Enrutamiento a almacenamiento y a motor de detección.

## Módulo D — Almacenamiento (`storage/`)

**Responsabilidad:** full-text + series temporales.

Debe contener:
- Schemas de OpenSearch (índice de eventos OCSF, patrones de series temporales); ClickHouse a mayor volumen.
- Política de retención ≥90 días en caliente.
- Índices para consultas por host, tiempo, categoría ATT&CK, severidad.

## Módulo E — Motor de detección (`detection-engine/`)

**Responsabilidad:** evaluar reglas y baseline; mapear ATT&CK.

Debe contener:
- **Cargador de reglas Sigma** (vía `sigma-cli`/pySigma para traducir a queries del backend) en `rules/sigma/`.
- **Cargador de reglas YARA** (escaneo archivos/memoria) en `rules/yara/`.
- **Motor de correlación** (reglas + relaciones temporales entre eventos).
- **Motor de baseline de comportamiento** (anomalías sin firma, p. ej. "este host nunca corre PowerShell").
- **Mapeador MITRE ATT&CK** (técnica ↔ regla) y generador de matriz de cobertura.
- **Conector de threat intel** (AlienVault OTX, abuse.ch, MISP) para enriquecer IOCs.
- **Emisor de alertas** con severidad → Capa IA.

## Módulo F — Capa de IA (`ai-layer/`)

**Responsabilidad:** razonar sobre el contexto vía LLM (API Gateway remoto + modelo local GGUF en modo híbrido, Opción C) y proponer acciones.

Debe contener:
- **Resumidor/indexador:** convierte eventos crudos en resúmenes + embeddings; escribe en vector store (Qdrant/Chroma).
- **Local Runtime (modo híbrido):** carga el GGUF `Qwen2.5-0.5B-Instruct-GGUF` con un runtime local (llama.cpp / llama-cpp-python / Ollama) y expone un servidor OpenAI-compatible en loopback (`http://127.0.0.1:<puerto>/v1`). Ver `29-Arquitectura-IA-Hibrida.md`, `30-Descarga-Modelo-Local-Qwen25.md`.
- **Router híbrido:** decide enrutar cada petición a API Gateway o a Local Runtime según disponibilidad, privacidad, criticidad y tamaño de contexto (fallback local si remoto cae).
- **Implementaciones de las 6 tools** (`tools/`):
  - `query_events(filters)`
  - `get_process_tree(pid)`
  - `get_active_connections()`
  - `list_alerts(severity)`
  - `lookup_ioc(indicator)`
  - `explain_attck_technique(id)`
- **Gestor de prompts** (`prompts/`): system prompt versionado del analista (sección 6.3).
- **Router de failover** (`router/`): lista `providers` (Cerebras/Groq/OpenRouter), itera en excepción, lanza `RuntimeError("Los tres proveedores fallaron")` si todos fallan.
- **Validador de tool_calls:** rechaza herramientas peligrosas antes de ejecutar (anti-inyección).
- **Guard de privacidad:** anonymiza/hashea IPs, hostnames y patrones antes de enviar a `:free` (todos entrenan con prompts, Doc 4); bloquea secretos.
- **Empujador proactivo:** ante alerta alta, envía mensaje al chat sin esperar consulta.

## Módulo G — Motor de respuesta y switch (`response-engine/`)

**Responsabilidad:** ejecutar acciones gateadas por el switch; auditar.

Debe contener:
- **Catálogo de acciones** (`actions/`): las 7 documentadas (matar proceso, aislar host, bloquear IP/dominio, cuarentena archivo, revertir registro, deshabilitar cuenta, snapshot memoria) con riesgo y reversibilidad.
- **Máquina de estados del switch** (4 niveles OBSERVE/SUGGEST/SEMI-AUTO/FULL-AUTO):
  - OBSERVE: solo lectura.
  - SUGGEST: confirmación explícita acción por acción.
  - SEMI-AUTO: categorías de bajo riesgo pre-autorizadas; resto en SUGGEST.
  - FULL-AUTO: solo lab/testing.
- **Escritor de auditoría** (`audit-log/`): append-only con hash-chaining (Merkle); registra quién propuso, quién aprobó, timestamp, resultado.

## Módulo H — Chat UI y dashboard (`chat-ui/`)

**Responsabilidad:** interacción en tiempo real.

Debe contener:
- Cliente/servidor **WebSocket bidireccional**; sesión de contexto por host/incidente.
- Canal de **push de eventos** (WebSocket o SSE) sin refresco.
- Parser de comandos de acción ("aislá el host X") → dispara confirmación según nivel del switch.
- Dashboard básico de eventos/alertas (Fase 1, sin IA).

## Módulo I — Metodología / purple team (proceso, no código obligatorio)

Debe contener (como configuración/runbooks):
- Loop de detection engineering; runbooks IR; matriz ATT&CK; Atomic Red Team / CALDERA apuntando solo a lab propio.

> **Información no especificada en la documentación original.** No se especifican: lenguaje obligatorio por módulo (solo sugerencias Rust/Go/Swift y ejemplos Python/JS), interfaces/clases concretas, ni contratos de API interna entre módulos. Lo anterior es la especificación de *qué debe ir*, no su implementación.
