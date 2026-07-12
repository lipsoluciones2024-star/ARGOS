---
título: 11 - Gestión de Configuración
objetivo: Documentar archivos de configuración, variables de entorno, constantes, configuración dinámica y persistente.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 6,7,12; Docs/KiloGateway 02,03.
dependencias: 10-Configuracion-Local.md; 08-API-Gateway.md.
referencias: 21-Dependencias.md.
---

# 11 - Gestión de Configuración

## 1. Archivos de configuración

| Archivo / ruta | Propósito |
|---|---|
| `agents/windows/sysmonconfig.xml` | Config de referencia Sysmon (SwiftOnSecurity u Olaf Hartong) |
| `collector/` (Vector.dev config) | Normalización a OCSF |
| `storage/` (schemas) | Schemas OpenSearch / ClickHouse |
| `detection-engine/rules/sigma/` | Reglas Sigma |
| `detection-engine/rules/yara/` | Reglas YARA |
| `ai-layer/prompts/` | System prompts versionados |
| `ai-layer/router/` | Config de proveedores y failover |

## 2. Variables de entorno

- `KILO_API_KEY` — key de Kilo Gateway.
- `CEREBRAS_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` — usadas por `call_with_failover`.
- Headers opcionales: `X-KiloCode-OrganizationId`, `X-KiloCode-TaskId`, `X-KiloCode-Version`, `x-kilocode-mode`.

## 3. Constantes

- **Base URL API Gateway:** `https://api.kilo.ai/api/gateway`.
- **Límite anónimo:** 200 req/hora/IP.
- **Expiración Organization token:** 15 minutos.
- **Niveles de switch:** OBSERVE (default), SUGGEST, SEMI-AUTO, FULL-AUTO.
- **Retención de logs:** mínimo 90 días en caliente.
- **Timeouts de red:** 30s (buena práctica Doc 3).

## 4. Configuración dinámica

- **Switch de autonomía:** cambia en runtime el comportamiento de respuesta (OBSERVE → FULL-AUTO). Es la configuración dinámica más relevante del sistema.
- **Catálogo de acciones pre-autorizadas (SEMI-AUTO):** el usuario pre-autoriza categorías de bajo riesgo (ej. "bloqueá automáticamente IPs de threat intel público").
- **Failover:** el router itera la lista `providers` dinámicamente; si un proveedor cae/cambia límites/deprecía modelo, prueba el siguiente.

## 5. Configuración persistente

- **Log de auditoría append-only con hash-chaining (estilo Merkle):** las acciones propuestas/aprobadas/ejecutadas se persisten inmutablemente (quién propuso, quién aprobó, timestamp, resultado). Esto es la configuración/estado persistente de cumplimiento del sistema.
- **Baseline de comportamiento:** se diffea periódicamente contra un baseline (ej. persistencia en registry, launchd, etc.).

> **Información no especificada en la documentación original.** No se especifican archivos de configuración persistente del propio ARGOS (p. ej. `config.yaml`, base de datos de settings, ni formato del hash-chain).
