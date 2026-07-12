---
título: 06 - Arquitectura del Código
objetivo: Documentar módulos, servicios, interfaces, clases, componentes, repositorios, adaptadores, DTO, modelos, utilidades y helpers especificados en la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 6,7,12; Docs/KiloGateway 01-04.
dependencias: 04-Arquitectura.md; 05-Arquitectura-Carpetas.md.
referencias: 09-Integracion-IA.md.
---

# 06 - Arquitectura del Código

> **Nota metodológica:** La documentación base es un documento de arquitectura de alto nivel; **no define clases, interfaces ni firmas de métodos concretas**. Lo que sí especifica son componentes, módulos, herramientas (tools) y esqueletos de código. Se documentan aquí exactamente esos elementos y se marca como no especificado lo no definido.

## 1. Módulos / servicios (según estructura de repo)

Ver `05-Arquitectura-Carpetas.md`. Módulos: `agents`, `collector`, `storage`, `detection-engine`, `ai-layer`, `response-engine`, `chat-ui`.

## 2. Interfaces / tools (function calling) — Capa de IA

La IA expone las siguientes **tools/functions** (sección 6.1). No se da lenguaje ni firma, pero sí el nombre y propósito:

| Tool | Propósito (según documento) |
|---|---|
| `query_events(filters)` | Consultar eventos con filtros |
| `get_process_tree(pid)` | Obtener árbol de procesos de un PID |
| `get_active_connections()` | Listar conexiones activas |
| `list_alerts(severity)` | Listar alertas por severidad |
| `lookup_ioc(indicator)` | Buscar indicador de compromiso |
| `explain_attck_technique(id)` | Explicar técnica MITRE ATT&CK por id |

## 3. Componentes / adaptadores

- **Resumidor/indexador** (sección 6.1): convierte eventos crudos en resúmenes + embeddings, guardados en vector store OSS (Qdrant o Chroma).
- **Router de failover** (sección 6.2): `providers = [...]` con `{"name","base_url","model"}`; función `call_with_failover(messages, tools)` que itera proveedores y cae al siguiente en caso de excepción; lanza `RuntimeError("Los tres proveedores fallaron")` si todos fallan.
- **Cliente puente MCP**: traduce herramientas MCP al array `tools` de la API (Doc 2, sección 8). La API solo entiende `tools`/`tool_choice`.
- **Local Runtime (modo híbrido):** adaptador que carga el GGUF `Qwen2.5-0.5B-Instruct-GGUF` con runtime local (llama.cpp / llama-cpp-python / Ollama) y expone endpoint OpenAI-compatible en loopback; el **Router híbrido** conmuta a él cuando el canal API Gateway falla o por privacidad. Ver `29-Arquitectura-IA-Hibrida.md`.

## 4. Modelos / DTO

- **Esquema de eventos OCSF**: formato común de eventos. No se especifican campos individuales del DTO en la documentación base.
- **Registro de auditoría (audit-log)**: cada entrada debe contener quién/qué propuso, quién aprobó, timestamp y resultado (sección 7). No se especifica esquema de tabla/clase.
- **Respuesta de API Gateway**: `message.content`, `message.reasoning`, `message.tool_calls` (Doc 2). En modelos `:free` de razonamiento la respuesta final está en `message.reasoning`.

## 5. Utilidades / helpers

- `sigma-cli` / pySigma: traducen reglas Sigma a queries del backend.
- `auditpol`, `reg add`, `sysmon64.exe -i`, `auditctl`, `ausearch`, `bpftrace`, `journalctl`, `log stream`, `launchctl`, `adb` — comandos reales documentados por SO (sección 3).

## 6. Repositorios

> **Información no especificada en la documentación original.** No se definen clases repositorio, ORMs ni capa de acceso a datos. Solo se mencionan sistemas de almacenamiento (OpenSearch/ClickHouse) y vector store (Qdrant/Chroma).

## 7. Clases

> **Información no especificada en la documentación original.** No se especifica ninguna clase concreta (nombre, atributos, métodos). Los únicos fragmentos de código son: esqueleto ESF en Swift (`es_new_client`, `es_subscribe`), router de failover en Python, y ejemplos de orquestación en Python/JS.
