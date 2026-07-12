---
título: 21 - Dependencias
objetivo: Extraer lenguajes, frameworks, SDK, librerías, versiones y herramientas del documento.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 3,5,6,9,12; Docs/KiloGateway 01-04.
dependencias: 04-Arquitectura.md; 08-API-Gateway.md.
referencias: 10-Configuracion-Local.md.
---

# 21 - Dependencias

## Lenguajes (mencionados en ejemplos / sugerencias)
- **Rust o Go** — sugeridos para el servicio del agente Windows.
- **Swift** — cliente ESF en macOS.
- **Python** — ejemplos de router de failover y orquestación.
- **JavaScript / Node.js** — ejemplos de OpenAI SDK y Vercel AI SDK.
- **Bash / PowerShell** — comandos de telemetría por SO.

> **Información no especificada en la documentación original.** No se declara un lenguaje obligatorio para todo el sistema; las menciones son sugerencias/ejemplos.

## Frameworks / SDK
| Componente | Herramienta | Licencia |
|---|---|---|
| Telemetría Windows | Sysmon + ETW | Gratis (Microsoft Sysinternals) |
| Telemetría Linux | auditd + Falco/eBPF | GPL / Apache 2.0 |
| Telemetría macOS | Endpoint Security Framework | Gratis (Apple, requiere entitlement) |
| Telemetría Android | VpnService + UsageStatsManager | Gratis (Android SDK) |
| Collector | Vector.dev o Fluent Bit | MPL 2.0 / Apache 2.0 |
| Almacenamiento | OpenSearch (o ClickHouse) | Apache 2.0 |
| Detección | Sigma + YARA + SigmaHQ ruleset | DRL / BSD |
| Threat Intel | AlienVault OTX, abuse.ch | Gratis |
| DFIR / hunting | Velociraptor, osquery | AGPL / GPL |
| LLM APIs | Groq + Cerebras + OpenRouter | Free tier |
| Vector store | Qdrant o Chroma | Apache 2.0 |
| Purple team | Atomic Red Team, MITRE CALDERA | MIT / Apache 2.0 |
| Chat UI | WebSocket + framework a elección | — |
| Runtime IA local (híbrido) | llama.cpp / llama-cpp-python / Ollama | MIT / Apache 2.0 |
| Runtime IA local (híbrido) | llama.cpp / llama-cpp-python / Ollama | MIT / Apache 2.0 |

## SDK de IA / API
- **SDK OpenAI** (Python/Node) — compatible con Kilo Gateway.
- **Vercel AI SDK** (`ai`, `@ai-sdk/openai`) — streaming.
- **Kilo AI Gateway** — Base URL `https://api.kilo.ai/api/gateway`, compatible OpenAI.

## Librerías / herramientas destacadas
- `sigma-cli` / pySigma — traducción de reglas Sigma.
- `auditpol`, `auditctl`, `ausearch`, `bpftrace`, `journalctl`, `log stream`, `launchctl`, `adb`, `sysmon64`.
- Falco (CNCF), Tracee (Aqua), Tetragon (Isovalent/Cilium).
- MITRE ATT&CK Navigator, MISP.

## Modelos (API Gateway, estado julio 2026)
- **Gratuitos (`:free`, 11):** `tencent/hy3:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `poolside/laguna-xs-2.1:free`, `cohere/north-mini-code:free`, `kilo-auto/free`, `stepfun/step-3.7-flash:free`, `poolside/laguna-m.1:free`, `openrouter/free`, `nvidia/nemotron-3.5-content-safety:free`.
- **Pago destacados:** `anthropic/claude-sonnet-4.5`, `openai/gpt-4*`, `google/gemini-2.*`, `deepseek/*`, `x-ai/grok-*`, `meta-llama/llama-*`, `kilo-auto/small`.

## Modelo local (modo híbrido, Opción C — 2026-07-11)
- **Local GGUF:** `Qwen/Qwen2.5-0.5B-Instruct-GGUF` (licencia apache-2.0, contexto 8192, arquitectura qwen2). Cuantización recomendada: `q4_k_m`. Se ejecuta con runtime local OpenAI-compatible (llama.cpp / llama-cpp-python / Ollama) en loopback. No es salida de red. Ver `30-Descarga-Modelo-Local-Qwen25.md`.

## Versiones
> **Información no especificada en la documentación original.** No se fijan versiones de librerías/frameworks (salvo `sysmon schemaversion="4.90"` en un ejemplo de config). El documento advierte explícitamente: "el catálogo de modelos rota — no hardcodees un modelo específico sin un plan B".
