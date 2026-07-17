# ARGOS BUILD LOG

Registro autónomo de construcción de ARGOS (agente constructor). Cada entrada es append-only.

---

## 2026-07-11 — ARGOS COMPLETO (MVP a producción)

**Estado:** Construcción finalizada y verificada.

### Módulos entregados
- **A — Agente recolector:** `argos/agent/` (runner + `sources/common.py` multiplataforma:
  procesos, red, logon, persistencia, lotl).
- **B — Normalización/Ingesta/Buffer:** `argos/collector/` (Normalizer OCSF, Collector, LocalBuffer
  SQLite tolerante a caídas).
- **C — Almacenamiento:** `argos/storage/store.py` — `EventStore` (SQLite+FTS5), `AlertStore`,
  `AuditLog` (hash-chain SHA-256 verificable).
- **D — Detección:** `argos/detection/` — `DetectionEngine` (Sigma+YARA+baseline+ATT&CK),
  `threat_intel` (IOC sample), `alerts` (7 acciones), reglas en `detection-engine/rules/`.
- **E — Cliente/Gateway:** `argos/ai/client.py` (auth anónima, campo `reasoning`, `tool_calls`)
  + `router.py` (GatewayFailover → DirectProviderFailover → LocalRuntime → HybridRouter).
- **F — Capa IA:** `argos/ai/` — `prompts`, `privacy` (scrub secrets), `tools` (6 herramientas solo
  lectura + `ToolExecutor`), `orchestrator`.
- **G — Respuesta:** `argos/response/` — `switch` (4 niveles), `actions` (7), `orchestrator`
  (gating fail-safe).
- **H — UI/Servidor:** `argos/server.py` (FastAPI REST+WS), `argos/chat/ws.py`, `argos/cli.py`,
  dashboard SPA en `chat-ui/`.

### Decisiones aplicadas
- **IA híbrida Opción C (2026-07-11):** API Gateway (Kilo AI Gateway, OpenAI-compatible) +
  fallback local Qwen2.5-0.5B GGUF. El runtime local no hace llamadas de red.
- **Sin claves hardcodeadas:** `KILO_API_KEY` / `CEREBRAS_API_KEY` / `GROQ_API_KEY` /
  `OPENROUTER_API_KEY` vía entorno.
- **Fail-safe not fail-open:** sin switch adecuado, acción = `REQUIRES_APPROVAL`.
- **Auditoría inmutable:** `verify_chain()` valida integridad del log de decisiones.

### Verificación
- `pytest`: 18/18 tests verdes (`tests/test_core.py`, `tests/test_server.py`).
- `ruff check argos`: All checks passed.
- `mypy argos`: Success (35 source files).

### Artefactos de entrega
- `README.md`, `Dockerfile`, `run_server.ps1`, `run_agent.ps1`.
- `pyproject.toml` con scripts `argos-server` / `argos-agent` / `argos-cli`.

### Pendiente opcional (fuera de MVP)
- Empaquetado del binario nativo del agente para despliegue masivo.
- Autenticación del servidor (la UI/API quedan abiertas en localhost por defecto).

---

## 2026-07-11 (tarde) — PRUEBA EN VIVO, DEPURACIÓN Y REPARACIÓN

Se ejecutó ARGOS de extremo a extremo en la VM (servidor + agente + UI + chat por WS),
monitoreando procesos/red reales y reparando bugs encontrados.

### Bugs encontrados y reparados
1. **Puerto erróneo:** `Config.server_port = 8742` → corregido a `8000`.
2. **UI nunca montada:** `UI_DIR` subía 3 niveles (`C:\chat-ui`) → corregido a
   `Path(__file__).resolve().parent.parent / "chat-ui"`.
3. **Agente no ingería (crash):** `LocalBuffer.pending()` indexaba tuplas con `r["payload"]`
   → seteó `row_factory = sqlite3.Row`.
4. **Ingesta rechazada (422):** endpoint `/ingest` tipaba `payload: dict` y el agente enviaba
   una **lista** → acepta ahora `Any = Body(...)` (lista o `{events:[...]}`).
5. **Windows no capturaba cmdline:** `collect_processes` usaba `tasklist` (sin command line),
   por lo que Sigma `powershell_encoded_command` nunca matcheaba → ahora usa
   `Get-CimInstance Win32_Process` (ExecutablePath + CommandLine), con fallback a tasklist.
6. **attack_id mal parseado:** tag `attack.T1059.001` daba `attack_id='001'` →
   `'.'.join(t.split('.')[1:]).upper()` → `T1059.001` (técnica resuelta correctamente).
7. **Chat por WS colgaba (timeout):** el handler corría el LLM sincrónicamente dentro del
   event loop → offload con `asyncio.to_thread`.
8. **Herramientas del LLM "se interrumpían":** (a) el mensaje de resultado de tool usaba `name=`
   en vez de `tool_call_id` (OpenAI lo requiere) → se agregó `tool_call_id` en `ChatMessage`
   y se propagó en el orchestrator; (b) los tools devolvían eventos completos (hasta 1000),
   saturando el contexto → ahora devuelven payload slim + `total_events` y límite máx 50.
9. **UI sin botones de remediación:** se agregó `GET /api/v1/proposals`, formulario de
   propuesta y botón "Confirmar" en `app.js`/`index.html`.
10. **Event loop bloqueado por ingest masivo:** `ingest` sincrónico congelaba el loop con lotes
    de ~500 eventos → offload con `asyncio.to_thread` (DB ya usa `check_same_thread=False` + WAL).
11. **Observabilidad en logs:** `AppContext.ingest` ahora loguea `ingest: N eventos` (DEBUG) y
    `ALERTA <SEV>: <titulo> en <host> (<attack_id>)` (INFO).

### Verificación en vivo (resultados)
- Agente monitorea procesos REALES (MsMpEng.exe, Code.exe, paths completos) y conexiones
  reales (GitHub 140.82.x, Cloudflare 104.21.x). `total_events` > 13k acumulados.
- Detección: inyectar `powershell.exe -enc ...` → alerta HIGH + push `proactive_alert` por WS + entrada en `/api/v1/alerts`.
- Auditoría: hash-chain verificable (`verify_chain() == True`); OBSERVE deniega, SEMI-AUTO
  ejecuta, SUGGEST deja pendiente y se confirma vía UI/API.
- Chat SOC por WS usa `query_events` con datos reales (confirmado: el modelo razonó sobre
  `total_events` global vs filtrado).
- Responsividad: 15 GET concurrentes + propuesta responden 200 sin timeouts.
- Calidad: `pytest` 18/18, `ruff` limpio, `mypy` limpio (post-reparación).

### Estado
ARGOS operativo de extremo a extremo en la VM. Servidor en `:8000`, agente recolectando,
UI funcional (dashboard + chat + switch + propuesta/confirmación de remediación).
