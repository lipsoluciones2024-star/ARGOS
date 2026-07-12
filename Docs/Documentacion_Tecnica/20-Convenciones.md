---
título: 20 - Convenciones
objetivo: Documentar nombres, estructura, organización y buenas prácticas, solo si aparecen documentadas.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,6,12; Docs/KiloGateway 03.
dependencias: 05-Arquitectura-Carpetas.md; 21-Dependencias.md.
referencias: 11-Gestion-Configuracion.md.
---

# 20 - Convenciones

Solo se documentan convenciones explícitamente presentes en la base.

## 1. Principios de diseño (no negociables) — sección 1
1. No es antivirus, es Full Endpoint Observability.
2. Human-in-the-loop por diseño (switch de autonomía).
3. 100% free & open source (licencias Apache 2.0, MIT, GPL, AGPL, o free tier sostenible).
4. Multiplataforma real, no "compatible" (agente nativo por SO).
5. La IA es copiloto, no oráculo ciego (lectura vía function calling; ejecución gobernada por policy + switch).
6. Detección basada en comportamiento y MITRE ATT&CK.
7. Todo evento auditable e inmutable (write-once log, hash-chaining Merkle).
8. Fail-safe, no fail-open.

## 2. Nombres / esquemas
- **Esquema de eventos:** OCSF (Open Cybersecurity Schema Framework) adoptado desde el día 1.
- **Codename:** ARGOS (sugerido, reemplazable) — por Argos Panoptes.
- **Niveles del switch:** OBSERVE, SUGGEST, SEMI-AUTO, FULL-AUTO.

## 3. Estructura / organización
- Estructura de repo sugerida (`agents/`, `collector/`, `storage/`, `detection-engine/`, `ai-layer/`, `response-engine/`, `chat-ui/`, `docs/`). Ver `05-Arquitectura-Carpetas.md`.
- System prompts **versionados** en `ai-layer/prompts/`.
- Reglas separadas en `rules/sigma/` y `rules/yara/`.

## 4. Buenas prácticas de seguridad (Doc 3)
1. No hardcodear la API key (usar `KILO_API_KEY`).
2. Modelos gratuitos para datos no sensibles; evitar secretos en cualquier LLM.
3. Evitar `mayTrainOnYourPrompts: true` para información confidencial.
4. Usar Organization tokens en equipos (expiración 15 min).
5. Validar `tool_calls` antes de ejecutar funciones.
6. Poner límites (`max_tokens`, timeouts 30s).
7. No confiar ciegamente en `:free` para decisiones críticas.
8. Cache con `X-KiloCode-TaskId`.

## 5. Convenciones de metodología
- Detection Engineering loop: hipótesis → regla → test → tuning → deploy.
- Runbooks IR: contención → erradicación → recuperación → lecciones.
- Purple team: un ejercicio ligero por sprint/mes.

> **Información no especificada en la documentación original.** No se especifican convenciones de nomenclatura de código (camelCase/snake_case), estilo de commits, ni linting/formato.
