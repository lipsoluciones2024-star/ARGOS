---
título: 18 - Casos de Uso
objetivo: Extraer todos los casos de uso con actor, objetivo, precondiciones, flujo, postcondiciones y errores.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 6,7,8; Docs/KiloGateway 02.
dependencias: 02-Requisitos-Funcionales.md; 07-Flujo-General.md.
referencias: 19-Casos-Error.md.
---

# 18 - Casos de Uso

## CU-01 — Consultar estado en tiempo real
- **Actor:** Usuario (analista senior)
- **Objetivo:** "¿Qué está pasando ahora mismo en mi laptop?"
- **Precondiciones:** Agente recolectando; chat conectado; IA en cualquier nivel de switch.
- **Flujo:** Usuario pregunta → IA invoca `query_events`/`get_active_connections` → responde en lenguaje natural.
- **Postcondiciones:** Usuario recibe estado actual.
- **Errores:** caída de proveedor (failover); `400`/`429`.

## CU-02 — Investigar logones fallidos
- **Actor:** Usuario
- **Objetivo:** "¿Quién intentó loguearse y falló en las últimas 2 horas?"
- **Precondiciones:** Eventos de identidad recolectados.
- **Flujo:** Pregunta → `query_events(filters)` → resumen.
- **Postcondiciones:** Lista de logones fallidos.

## CU-03 — Árbol de procesos
- **Actor:** Usuario
- **Objetivo:** "Mostrame el árbol de procesos de PID 4821"
- **Flujo:** Pregunta → `get_process_tree(pid)`.
- **Postcondiciones:** Árbol mostrado.

## CU-04 — Verificar IOC
- **Actor:** Usuario
- **Objetivo:** "¿Esta IP 45.x.x.x es conocida como maliciosa?"
- **Flujo:** Pregunta → `lookup_ioc(indicator)` → IA valida contra fuentes reales.
- **Errores:** alucinación de IOC → validar con VirusTotal/CVE/MISP.

## CU-05 — Explicar técnica ATT&CK
- **Actor:** Usuario
- **Objetivo:** "Explicame en criollo qué técnica de MITRE ATT&CK es esta"
- **Flujo:** Pregunta → `explain_attck_technique(id)`.

## CU-06 — Aislar host (acción de remediación)
- **Actor:** Usuario
- **Objetivo:** "Aislá el host HOST-02 de la red"
- **Precondiciones:** Switch en SUGGEST/SEMI/FULL.
- **Flujo:** Pregunta → IA propone → switch dispara confirmación (según nivel) → ejecuta → audita.
- **Postcondiciones:** Host aislado (si autorizado) y auditado.
- **Errores:** nivel OBSERVE bloquea ejecución.

## CU-07 — Alerta proactiva de alta severidad
- **Actor:** Sistema (sin interacción previa)
- **Objetivo:** Empujar mensaje al chat ante alerta alta.
- **Precondiciones:** Motor de detección genera alerta alta.
- **Flujo:** Detección → IA empuja mensaje vía WebSocket/SSE.
- **Postcondiciones:** Usuario notificado.

## CU-08 — Consumir API Gateway con `:free`
- **Actor:** Cliente ARGOS
- **Objetivo:** Llamar al LLM sin API key.
- **Precondiciones:** modelo `:free`; límite 200 req/h IP.
- **Flujo:** POST `/chat/completions` sin Authorization.
- **Errores:** `429` si supera cuota; `content` vacío → leer `reasoning`.

## CU-09 — Failover entre proveedores
- **Actor:** Router de failover
- **Objetivo:** Mantener disponibilidad de IA.
- **Flujo:** itera `providers` (Cerebras→Groq→OpenRouter); ante excepción prueba siguiente.
- **Errores:** todos fallan → `RuntimeError("Los tres proveedores fallaron")`.
