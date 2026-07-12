# ARGOS

**ARGOS** — *Agentic Runtime for Global Observation & Self-defense* — es un sistema de
**observabilidad total de endpoints + ciberdefensa autónoma** multiplataforma (Windows/Linux/macOS),
100% open-source, con **human-in-the-loop** y un cerebro de IA híbrido (API Gateway + IA local).

> Documentación de autoridad: [`Docs/Documentacion_Tecnica/`](Docs/Documentacion_Tecnica/00-Indice-Maestro.md).
> Cualquier decisión de arquitectura o contrato no reflejada allí no existe para este proyecto.

## Características principales

- **Observabilidad total (Módulo C/A/B):** colección de procesos, red, logon, persistencia y lotl;
  normalización a esquema **OCSF**; almacenamiento SQLite con **FTS5** + buffer local tolerante a caídas.
- **Detección (Módulo D):** reglas **Sigma** + **YARA** + baseline + mapeo **MITRE ATT&CK**.
  Motor con catálogo de 7 acciones de respuesta y cobertura por técnica.
- **Auditoría inmutable:** `AuditLog` con **hash-chaining** SHA-256 verificable (`verify_chain()`).
- **IA híbrida (Módulo E/F) — Opción C 2026-07-11:** API Gateway (Kilo AI Gateway, OpenAI-compatible)
  con failover a proveedores directos (Cerebras → Groq → OpenRouter) y **runtime local** (Qwen2.5-0.5B GGUF)
  como fallback. El runtime local **nunca** hace llamadas de red.
- **Switch de autonomía (Módulo G):** 4 niveles — `OBSERVE`, `SUGGEST`, `SEMI-AUTO`, `FULL-AUTO`.
  **Fail-safe, no fail-open:** sin switch en nivel adecuado, la acción queda `REQUIRES_APPROVAL`.
- **6 herramientas de solo lectura** para el LLM (`query_events`, `get_process_tree`,
  `get_active_connections`, `list_alerts`, `lookup_ioc`, `explain_attck_technique`).
  El LLM **propone**, nunca ejecuta.
- **UI de chat + dashboard (Módulo H):** FastAPI sirve API REST + WebSocket y la SPA en
  `chat-ui/` (abrir `/` en el navegador).

## Requisitos

- Python ≥ 3.10
- Red opcional: para el cerebro remoto usa `KILO_API_KEY` (o `CEREBRAS_API_KEY` / `GROQ_API_KEY` /
  `OPENROUTER_API_KEY`). **Nada de claves hardcodeadas.**
- Para IA local: un servidor OpenAI-compatible (Kilo Gateway local / llama.cpp) en `http://localhost:8080/v1`.

## Instalación

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Uso

```bash
# Servidor API + dashboard (http://localhost:8000)
argos-server            # o: python -m argos.server

# Agente recolector (en otro terminal)
argos-agent             # o: python -m argos.agent

# CLI
argos-cli status
argos-cli switch semi-auto
argos-cli chat "¿Hay conexiones a IPs maliciosas?"
argos-cli propose kill_process 1234
```

Scripts listos (Windows): `run_server.ps1`, `run_agent.ps1`.

## Tests / Calidad

```bash
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check argos
.\.venv\Scripts\python -m mypy argos
```

## Licencia

Apache-2.0
