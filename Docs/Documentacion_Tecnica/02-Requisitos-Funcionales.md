---
título: 02 - Requisitos Funcionales
objetivo: Extraer y enumerar todos los requisitos funcionales del sistema, agrupados por módulo, según la documentación base.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1-13; documentación KiloGateway 01-04.
dependencias: 01-Resumen-Ejecutivo.md; 04-Arquitectura.md; 08-API-Gateway.md; 09-Integracion-IA.md.
referencias: 03-Requisitos-No-Funcionales.md; 18-Casos-Uso.md.
---

# 02 - Requisitos Funcionales

Todos los requisitos extraídos de la documentación base. Agrupados por módulo.

## Módulo A — Agentes de endpoint (sensors)

- **RF-A1:** Captar telemetría a nivel kernel, proceso, red, filesystem e identidad por cada SO.
- **RF-A2:** Emitir eventos en un esquema común. Se recomienda adoptar **OCSF** desde el día 1.
- **RF-A3 (Windows):** Captar vía ETW (providers `Microsoft-Windows-Kernel-Process`, `-Kernel-File`, `-Kernel-Network`, `-Kernel-Registry`), Sysmon (Event IDs 1,3,5,7,8,10,11,12/13/14,17/18,22,25), Windows Event Log (Security 4624,4625,4672,4688,4720,4728/4732,5140/5145), PowerShell logging (4104 Script Block), AMSI, y enumerar superficie de persistencia (Run keys, Scheduled Tasks, servicios, WMI, Winlogon Helper DLLs).
- **RF-A4 (Linux):** Captar vía auditd (`/etc/passwd`, `execve`), eBPF (Falco/Tracee/Tetragon) y Netfilter/nftables logging.
- **RF-A5 (macOS):** Captar vía Endpoint Security Framework (ESF) con eventos `ES_EVENT_TYPE_NOTIFY_EXEC/FORK/OPEN/MMAP/MOUNT`, Unified Logging (`os_log`), FSEvents, TCC.db, y enumerar persistencia launchd (LaunchAgents/LaunchDaemons).
- **RF-A6 (Android):** Captar vía VpnService API (red), UsageStatsManager, NetworkStatsManager, Accessibility Service API (opcional, requiere consentimiento) y Device Owner/MDM. Modo lab: Frida, Magisk, `logcat`, `dumpsys`.
- **RF-A7:** Bufferear eventos localmente (SQLite embebido sugerido) si se cae la conexión y reenviar al reconectar.

## Módulo B — Transporte seguro

- **RF-B1:** Establecer mTLS entre agente y collector.
- **RF-B2:** Soportar gRPC directo o NATS/MQTT sobre TLS para el bus de eventos.

## Módulo C — Collector / event bus

- **RF-C1:** Recibir, normalizar y enrutar eventos. Candidatos: Vector.dev o Fluent Bit.

## Módulo D — Almacenamiento

- **RF-D1:** Proveer búsqueda full-text para investigación ad-hoc.
- **RF-D2:** Proveer series temporales para dashboards/anomalías. Candidato: OpenSearch; ClickHouse a mayor volumen.

## Módulo E — Motor de detección

- **RF-E1:** Evaluar reglas Sigma (traducidas con `sigma-cli`/pySigma).
- **RF-E2:** Evaluar reglas YARA (escaneo de archivos/memoria por patrones).
- **RF-E3:** Correlacionar eventos y aplicar baseline de comportamiento (anomalías sin firma).
- **RF-E4:** Mapear cobertura a MITRE ATT&CK Navigator.
- **RF-E5:** Integrar threat intel gratuita (AlienVault OTX, abuse.ch, MISP).

## Módulo F — Capa de IA (el cerebro)

- **RF-F1:** Resumir/indexar eventos crudos en resúmenes + embeddings guardados en vector store OSS (Qdrant o Chroma).
- **RF-F2:** Exponer tools/functions al LLM: `query_events(filters)`, `get_process_tree(pid)`, `get_active_connections()`, `list_alerts(severity)`, `lookup_ioc(indicator)`, `explain_attck_technique(id)`.
- **RF-F3:** Empujar proactivamente un mensaje al chat cuando ocurre un alert de alta severidad.
- **RF-F4:** El LLM propone acciones de remediación pero nunca las ejecuta directamente.
- **RF-F5:** Consumir la IA únicamente vía la API Gateway (compatible OpenAI).

## Módulo G — Motor de respuesta y switch de autonomía

- **RF-G1:** Implementar 4 niveles de switch: OBSERVE (default), SUGGEST, SEMI-AUTO, FULL-AUTO.
- **RF-G2:** Catálogo de acciones: matar proceso, aislar host, bloquear IP/dominio, cuarentena de archivo, revertir cambio de registro, deshabilitar cuenta, snapshot forense de memoria.
- **RF-G3:** Auditar toda acción (propuesta, aprobación, ejecución) con quién/qué propuso, quién aprobó, timestamp y resultado.
- **RF-G4:** Log de auditoría append-only con hash-chaining (estilo Merkle) para inmutabilidad.

## Módulo H — Chat interactivo + dashboard

- **RF-H1:** Chat en lenguaje natural en tiempo real ("¿qué está pasando ahora?", "¿quién intentó loguearse y falló en las últimas 2 horas?", "mostrame el árbol de procesos de PID X", "¿esta IP es conocida como maliciosa?", "explicame esta técnica ATT&CK").
- **RF-H2:** WebSocket bidireccional entre UI y backend; sesión de contexto por host/incidente.
- **RF-H3:** Empujar eventos nuevos vía el mismo canal (o SSE) sin que el usuario refresque.
- **RF-H4:** Acción de chat como "aislá el host X" dispara confirmación según nivel del switch.

## Módulo I — Metodologías y purple team

- **RF-I1:** Detection Engineering loop (hipótesis → regla → test → tuning → deploy) con medición de falsos positivos.
- **RF-I2:** Threat Hunting activo basado en técnicas ATT&CK no cubiertas.
- **RF-I3:** Runbooks de Incident Response (contención → erradicación → recuperación → lecciones).
- **RF-I4:** Retención mínima de 90 días en caliente.
- **RF-I5:** Atomic Red Team y MITRE CALDERA contra sistemas de laboratorio propios.
- **RF-I6:** Matriz de cobertura ATT&CK construida desde la taxonomía de eventos.

## Módulo J — API Gateway (consumo de IA)

- **RF-J1:** Listar modelos vía `GET /api/gateway/v1/models`.
- **RF-J2:** Chat completions vía `POST /api/gateway/chat/completions`.
- **RF-J3:** Soportar tool calling / function calling (266 modelos lo soportan; 10 de 11 `:free`).
- **RF-J4:** Soportar streaming SSE (`stream: true`).
- **RF-J5:** Soportar FIM vía Mistral Codestral (autocompletado).
- **RF-J6:** Soportar MCP mediante cliente puente que traduce herramientas al array `tools`.
- **RF-J7:** Soportar parámetros `max_tokens`, `temperature`, `top_p`, `top_k`, `seed`, `stop`, `tools`, `tool_choice`, `reasoning`, `include_reasoning`, `response_format`, `structured_outputs`, penalties.

> **Información no especificada en la documentación original.**
> - No se enumeran requisitos funcionales de gestión de usuarios/roles de la propia aplicación ARGOS más allá del switch de autonomía.
> - No se especifican requisitos de exportación/backup de la telemetría.
