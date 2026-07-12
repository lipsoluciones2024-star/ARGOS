---
título: 05 - Arquitectura de Carpetas
objetivo: Generar la estructura completa de directorios y explicar cada carpeta y archivo, basándose únicamente en la documentación base.
alcance: `ARGOS_documento_maestro_arquitectura.md` sección 12 (estructura de repo sugerida).
dependencias: 04-Arquitectura.md; 06-Arquitectura-Codigo.md.
referencias: 21-Dependencias.md.
---

# 05 - Arquitectura de Carpetas

Estructura sugerida en la documentación base (sección 12, "Estructura de repo sugerida"). Es la única estructura de carpetas documentada.

```
argos/
├── agents/
│   ├── windows/        # Sysmon config + servicio en Rust o Go
│   ├── linux/           # eBPF/auditd + daemon
│   ├── macos/            # cliente ESF en Swift
│   └── android/          # app con VpnService + módulo MDM opcional
├── collector/              # Vector.dev config + normalización a OCSF
├── storage/                  # schemas de OpenSearch / ClickHouse
├── detection-engine/
│   ├── rules/sigma/
│   └── rules/yara/
├── ai-layer/
│   ├── tools/               # definiciones de function calling
│   ├── prompts/              # system prompts versionados
│   └── router/                 # failover entre Groq/Cerebras/OpenRouter
├── response-engine/
│   ├── actions/                 # catálogo de acciones
│   └── audit-log/                 # hash-chain de auditoría
├── chat-ui/                         # frontend del chat + dashboard
└── docs/                              # este documento y los deep-dives por módulo
```

## Explicación por carpeta

| Carpeta | Explicación (según documentación) |
|---|---|
| `agents/` | Agentes de endpoint nativos por SO. `windows/` usa Sysmon config + servicio en Rust o Go. `linux/` usa eBPF/auditd + daemon. `macos/` es cliente ESF en Swift. `android/` es app con VpnService + módulo MDM opcional. |
| `collector/` | Configuración de Vector.dev y normalización de eventos a OCSF. |
| `storage/` | Schemas de OpenSearch (o ClickHouse a escala). |
| `detection-engine/` | Motor de detección. `rules/sigma/` y `rules/yara/` contienen las reglas. |
| `ai-layer/` | Capa de IA. `tools/` son definiciones de function calling. `prompts/` son system prompts versionados. `router/` implementa el failover entre Groq/Cerebras/OpenRouter. |
| `response-engine/` | Motor de respuesta. `actions/` es el catálogo de acciones. `audit-log/` implementa el hash-chain de auditoría. |
| `chat-ui/` | Frontend del chat + dashboard. |
| `docs/` | El documento raíz y los deep-dives por módulo. |

## Archivos específicos citados

- `agents/windows/sysmonconfig.xml` — config de referencia (SwiftOnSecurity u Olaf Hartong) para Sysmon.
- `collector/` (Vector.dev config) — implícito en la normalización.
- `ai-layer/router/` — contiene el esqueleto del router de failover (`providers = [...]`, `call_with_failover`).
- `ai-layer/prompts/` — system prompt de referencia del analista (sección 6.3).
- `detection-engine/rules/sigma/` — regla Sigma "PowerShell Encoded Command".
- `detection-engine/rules/yara/` — regla YARA "Suspicious_Download_Cradle".

> **Información no especificada en la documentación original.** No se especifican nombres de archivos fuente exactos dentro de cada carpeta (salvo los ejemplos de config y reglas mencionados), ni estructura de tests, ni `package.json`/`Cargo.toml`/archivos de build.
