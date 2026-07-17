# Estado de Implementación — ARGOS

> Documento de verdad sobre el **stack realmente implementado** frente a la
> especificación de diseño descrita en `ARGOS_documento_maestro_arquitectura.md` y
> los módulos `Docs/Documentacion_Tecnica/*`.
>
> Objetivo: que un mantenedor nuevo sepa exactamente qué es producción y qué es
> workstream futuro, sin sorpresas ("la documentación miente").

Fecha: 2026-07-14 · Estado: **producción (MVP comercial terminado)**.

---

## 1. Resumen de decisiones adoptadas

| Ítem (doc) | Decisión adoptada | Motivo |
|---|---|---|
| Almacenamiento (OpenSearch/ClickHouse) | **SQLite + FTS5** (`storage/store.py`) | Cero dependencias externas, WAL, portable, suficiente para el volumen del producto. `detection-engine` ya usa SQLite en su pipeline. |
| Transporte agente↔servidor (mTLS / gRPC) | **HTTP plano + firma HMAC** (`security/auth.py`, `security/middleware.py`) cuando `require_auth` está activo | El servidor acepta OCSF firmado; el secreto se deriva de `ARGOS_AUTH_SECRET` o `data_dir`. mTLS queda como workstream futuro. |
| Recuperación de memoria (embeddings / Qdrant / Chroma) | **FTS5 SQLite** (`storage/memory.py`) | Búsqueda por palabra clave sobre investigaciones/feedback. Semántica real (RAG) es workstream futuro; no bloquea producción. |
| Sensores nativos (ETW / eBPF / ESF) | **Agente recolector simulado** (`collector/`, psutil/WMI) | Los sensores nativos requieren código por SO y privilegios; el esquema OCSF ya es compatible con un sensor real (ver §5). |
| Motor YARA | **Fallback Python puro** (`detection/yara_rules.py`) | `yara-python` no compila en Python 3.14. Se usa matcher propio (text/hex/regex + condiciones `N of them`/`all`/`any`) con degradación a nativo si está disponible. |
| Gestión de usuarios/roles | **Persistida** (`storage/users.py`, scrypt) | Roles `admin`/`operator`, CRUD por API, RBAC por endpoint. |

---

## 2. Backend — estado de producción

### 2.1 Endpoints (FastAPI, `argos/server.py`)
Todos los endpoints de la auditoría (`Auditoria_Completitud.md` §5, #1–#15) están
**implementados y testeados**:

`health`, `ingest`, `events`, `alerts`, `hosts`, `stats`, `metrics`, `coverage`,
`rules` (GET lista motor + GET `/rules/managed` reglas gestionadas), `actions`,
`switch` (GET/POST), `proposals`, `propose`, `confirm`, `audit`, `logs` (tail +
filtrable), `models`, `agents`, `ai/status`, `chat/*`, `memory/investigations`,
`feedback`, `settings` (GET/PUT), `version`, `auth/token`, `users` (CRUD),
`rules` (POST/PUT/DELETE + `/reload`), `alerts/{id}/ack`, `scan/yara`, `processes`,
`actions/execute`, `actions/undo`, `proposals/{id}/reject`, `audit/verify`,
`export`, `health/deep`, `switch/audit`, `settings/test`, `/ws`.

### 2.2 Detección
- **Sigma**: `detection/sigma_rules.py` carga `detection-engine/rules/sigma`, mapeo
  ATT&CK (`attack.py`), baseline, threat intel. Las reglas gestionadas de tipo sigma
  (creadas por API) se parsean con `DetectionEngine.add_sigma_rule_text` y se evalúan
  en `evaluate_batch`.
- **YARA**: `detection/yara_rules.py` (`YaraScanner`). Carga `detection-engine/rules/yara`
  y reglas gestionadas; `scan_file`/`scan_bytes`/`scan_path`; integrado en
  `engine.evaluate` y expuesto en `coverage`/`list_rules`. Endpoint `POST /scan/yara`
  con **sandbox** (solo `root`, `data_dir`, temp).

### 2.3 Almacenamiento
- `EventStore` (SQLite+FTS5, `process_inventory`).
- `AlertStore` (con `acknowledged/by/at`).
- `AuditLog` (hash-chain SHA-256 verificable con `verify_chain`).
- `UsersStore` (scrypt, roles, seed admin bootstrap).
- `RulesStore` (reglas gestionadas, enable/disable, origen).
- `SettingsStore`, `ChatLog`, `MemoryStore`.

### 2.4 Seguridad
- Auth HMAC HS256 (`sign_token`/`verify_token`), roles `operator`/`admin`.
- RBAC por endpoint (`_auth(request, min_role)` + `security/rbac.py`).
- Middleware de autenticación + rate limit (`security/middleware.py`,
  `security/ratelimit.py`) + CORS restrictivo.
- Ingesta firmada por HMAC cuando `require_auth` está activo; eventos sin firma válida
  son rechazados.
- Sin secretos hardcodeados: `derive_secret` desde `ARGOS_AUTH_SECRET`/`data_dir`.

### 2.5 Respuesta (human-in-the-loop)
- 7 acciones (`response/actions.py`), 4 niveles de switch.
- `POST /actions/execute` (`force_execute`) + `POST /actions/undo` (reversibles) +
  `POST /proposals/{id}/reject`, con registro en auditoría inmutable.
- Cola de propuestas con approve/reject en UI (chat + tarjeta).

---

## 3. Frontend — estado de producción

SPA Vanilla JS (`dashboard/`), 7 vistas cableadas (sin botones muertos):

| Vista | Contenido |
|---|---|
| Resumen | métricas, throughput, alertas/eventos recientes |
| Seguridad | matriz ATT&CK, reglas del motor, **alertas con Ack**, catálogo de acciones |
| Red | eventos de red + resumen |
| Hosts | inventario + detalle por host |
| Auditoría | propuestas, feed proactivo, log de auditoría, investigaciones, feedback |
| Configuración | switch, estado IA, modelos, ajustes, agentes, métricas, historial chat |
| **Administración** | **Usuarios (CRUD + activar/desactivar), Reglas gestionadas (alta/edición/baja/recargar), Procesos, Escaneo YARA (lanzar+resultados), Salud profunda, Auditoría de switch, Export (json/csv), Logs filtrables** |

Comunicación WS + REST con auth Bearer automática, login overlay, consola del
sistema, voz (Web Speech API), splitters y paneles colapsables.

---

## 4. Verificación (gates verdes)

| Gate | Resultado |
|---|---|
| `python -m ruff check argos dashboard` | ✅ limpio |
| `python -m mypy argos` | ✅ sin errores (92 archivos) |
| `python -m pytest tests/test_server.py -q` | ✅ 26 tests verdes |
| `node --check dashboard/js/*.js` | ✅ sintaxis válida |

---

## 5. Workstreams futuros (fuera de alcance del entorno actual)

1. **Sensores nativos** (RF-A3..A6): ETW/Sysmon (Windows), auditd/eBPF (Linux),
   EndpointSecurity (macOS). El contrato OCSF ya está definido y el servidor ya
   acepta eventos firmados por HMAC, por lo que el transporte está listo.
2. **mTLS agente↔servidor** (RF-B1/B2): reemplazar firma HMAC por TLS mutuo.
3. **Vector store semántico** (RF-F1): embeddings reales + Qdrant/Chroma en vez de FTS5.
4. **Backends de almacenamiento escalables** (RF-D1/D2): OpenSearch/ClickHouse detrás
   de la misma interfaz de `storage/`.
5. **Purple teaming** (RF-I1..I6): Atomic Red Team / CALDERA / runbooks.

Ninguno de los anteriores bloquea el uso en producción del núcleo (recolección
simulada → detección Sigma+YARA → respuesta con switch → auditoría inmutable →
panel administrativo completo).

---

## 6. Cómo operar

- Arranque: `argos server` (o `python -m argos.server`).
- Token admin: `argos auth token --role admin` (o variable `ARGOS_API_TOKEN`).
- Recarga de reglas tras editar archivos: `POST /api/v1/rules/reload` (re-añade
  también las reglas gestionadas habilitadas).
- Verificación de auditoría: `GET /api/v1/audit/verify` → `chain_valid`.
- Export: `GET /api/v1/export?kind=events|alerts|audit&fmt=json|csv`.
