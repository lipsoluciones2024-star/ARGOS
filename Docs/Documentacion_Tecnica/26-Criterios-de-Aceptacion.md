---
título: 26 - Criterios de Aceptación
objetivo: Definir criterios de aceptación verificables por requisito, historia de usuario y fase del roadmap. Sin código.
alcance: 02-Requisitos-Funcionales.md; 25-Historias-de-Usuario.md; roadmap sección 12.
dependencias: 25-Historias-de-Usuario.md; 23-Checklist-Validacion.md.
referencias: 22-Checklist-Desarrollo.md; 28-Especificacion-Diseno-Modulos.md.
---

# 26 - Criterios de Aceptación

Cada criterio es verificable contra la documentación base. Formato: **Dado / Cuando / Entonces**.

## Por historia de usuario

| ID | Historia | Criterio de aceptación |
|---|---|---|
| AC-A1 | US-A1..A4 | Dado un SO soportado, cuando el agente arranca, entonces emite eventos de las fuentes documentadas para ese SO (ETW/Sysmon/Event Log/PS en Win; auditd/eBPF en Linux; ESF en macOS; VpnService/UsageStats en Android). |
| AC-A5 | US-A5 | Dado un evento crudo, cuando pasa por el collector, entonces se normaliza a esquema OCSF. |
| AC-A6 | US-A6 | Dado que el cerebro no está disponible, cuando el agente captura eventos, entonces los bufferea localmente y los reenvía al reconectar; nunca queda ciego ni actúa solo. |
| AC-A7 | US-A7 | Dado agente y collector, cuando transmiten, entonces usan mTLS. |
| AC-D1/D2 | US-D1/D2 | Dado el almacenamiento, cuando se consulta, entonces soporta full-text y series temporales. |
| AC-D3 | US-D3 | Dado el sistema operativo, cuando retiene eventos, entonces mantiene ≥90 días en caliente. |
| AC-E1/E2 | US-E1/E2 | Dado el motor de detección, cuando se cargan reglas Sigma/YARA, entonces se evalúan contra eventos. |
| AC-E3 | US-E3 | Dado un evento sin firma pero anómalo vs baseline, cuando se evalúa, entonces genera alerta. |
| AC-E4 | US-E4 | Dado el mapeo, cuando se revisa cobertura, entonces se visualiza matriz ATT&CK con puntos ciegos. |
| AC-F1 | US-F1 | Dado un analista, cuando pregunta en lenguaje natural, entonces recibe respuesta basada en eventos reales. |
| AC-F2 | US-F2 | Dado un LLM con tools, cuando necesita datos, entonces invoca `query_events`/`get_process_tree`/`get_active_connections`/`list_alerts`/`lookup_ioc`/`explain_attck_technique`. |
| AC-F3 | US-F3 | Dado un alert de alta severidad, cuando ocurre, entonces la IA empuja mensaje al chat sin esperar consulta. |
| AC-F4 | US-F4 | Dado que la IA propone una acción, entonces nunca la ejecuta directamente. |
| AC-F6 | US-F6 | Dado que un proveedor de IA falla, cuando se invoca, entonces el router prueba el siguiente; si los 3 fallan, lanza error controlado. |
| AC-G1 | US-G1 | Dado el switch, cuando se configura, entonces admite exactamente 4 niveles OBSERVE/SUGGEST/SEMI-AUTO/FULL-AUTO. |
| AC-G2 | US-G2 | Dado el catálogo, cuando se lista, entonces incluye las 7 acciones documentadas. |
| AC-G3 | US-G3 | Dado nivel SUGGEST, cuando la IA propone, entonces requiere confirmación explícita acción por acción. |
| AC-G5 | US-G5 | Dado nivel FULL-AUTO, cuando se habilita, entonces queda restringido a lab/testing (no default en producción). |
| AC-G6 | US-G6 | Dado cualquier acción, cuando se propone/aprueba/ejecuta, entonces se registra inmutable con quién propuso, quién aprobó, timestamp, resultado y hash-chaining. |
| AC-H1 | US-H1 | Dado el chat, cuando el analista envía mensaje, entonces la respuesta llega por WebSocket bidireccional. |
| AC-H2 | US-H2 | Dado un evento nuevo, cuando ocurre, entonces se empuja al UI sin refresco. |
| AC-I4 | US-I4 | Dado purple team, cuando se ejecuta, entonces corre solo contra sistemas de lab propios. |

## Por fase del roadmap (Definition of Done)

| Fase | Criterio de aceptación de cierre |
|---|---|
| Fase 0 | Repo con estructura sugerida; OCSF adoptado; un agente escribe a archivo local; catálogo de 7 acciones y 4 niveles definidos. |
| Fase 1 | Collector + OpenSearch reciben eventos reales de 1 host; dashboard básico sin IA. |
| Fase 2 | Reglas SigmaHQ + propias cargadas; matriz ATT&CK iniciada. |
| Fase 3 | Function calling operativo con las 6 tools; chat WebSocket; arranque en OBSERVE-only. |
| Fase 4 | Acciones de bajo riesgo implementadas; auditoría inmutable por hash-chain. |
| Fase 5 | Segundo/tercer/cuarto SO; Android al final. |
| Fase 6 | Atomic Red Team sobre lab propio; puntos ciegos cerrados. |

## Criterios transversales (no funcionales)

- **Seguridad:** ninguna remediación sin switch; mTLS; API key por variable de entorno; validación de `tool_calls`; no enviar secretos a `:free`.
- **Privacidad:** todo lo sensible enviado a IA debe poder anonymizarse/hashearse.
- **Tolerancia:** Fail-safe del agente; failover de IA de 3 proveedores.

> **Información no especificada en la documentación original.** No se especifican métricas numéricas de aceptación (p. ej. % máximo de falsos positivos, SLA de latencia, throughput mínimo de eventos/seg).
