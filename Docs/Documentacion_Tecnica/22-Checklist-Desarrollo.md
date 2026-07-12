---
título: 22 - Checklist de Desarrollo
objetivo: Crear un checklist completo y cronológico para implementar el proyecto, basado en el roadmap (sección 12).
alcance: `ARGOS_documento_maestro_arquitectura.md` sección 12.
dependencias: 05-Arquitectura-Carpetas.md; 21-Dependencias.md.
referencias: 23-Checklist-Validacion.md.
---

# 22 - Checklist de Desarrollo

Ordenado según el roadmap de desarrollo sugerido (sección 12). Cada tarea es marcable.

## Fase 0 — Fundación (1-2 semanas)
- [ ] Crear repo con estructura sugerida (`agents/`, `collector/`, `storage/`, `detection-engine/`, `ai-layer/`, `response-engine/`, `chat-ui/`, `docs/`).
- [ ] Adoptar esquema de eventos **OCSF** desde el día 1.
- [ ] Implementar un solo agente en el SO principal escribiendo a un archivo local.
- [ ] Definir el catálogo de acciones (7 acciones documentadas).
- [ ] Definir los 4 niveles del switch (OBSERVE/SUGGEST/SEMI-AUTO/FULL-AUTO), aunque no ejecuten nada aún.

## Fase 1 — Pipeline mínimo viable (2-4 semanas)
- [ ] Configurar Collector (Vector.dev) + almacenamiento (OpenSearch).
- [ ] Agentes emitiendo eventos reales de un solo host (Sysmon/auditd/ESF).
- [ ] Dashboard básico sin IA (ver los datos antes de razonar).

## Fase 2 — Motor de detección (2-3 semanas)
- [ ] Importar reglas de SigmaHQ + reglas propias.
- [ ] Empezar la matriz de cobertura ATT&CK (desde la taxonomía de la sección 4).

## Fase 3 — Capa de IA + chat (3-4 semanas)
- [ ] Function calling contra el store de eventos (6 tools documentadas).
- [ ] Chat en tiempo real (WebSocket).
- [ ] Arrancar en modo **OBSERVE-only**, sin acciones.

## Fase 4 — Motor de respuesta + switch (2-3 semanas)
- [ ] Implementar primero acciones de bajo riesgo (cuarentena de archivo, bloqueo de IP).
- [ ] Auditoría inmutable de cada acción propuesta/aprobada/ejecutada (hash-chain).

## Fase 5 — Multiplataforma (ongoing)
- [ ] Segundo SO, tercero, cuarto.
- [ ] Android al final (el más distinto arquitectónicamente).

## Fase 6 — Purple teaming + hardening
- [ ] Atomic Red Team contra el propio lab.
- [ ] Cerrar puntos ciegos de la matriz ATT&CK.

## Integración con API Gateway (transversal)
- [ ] Configurar consumo vía `https://api.kilo.ai/api/gateway` (compatible OpenAI).
- [ ] Implementar router de failover Cerebras → Groq → OpenRouter.
- [ ] No hardcodear API key (`KILO_API_KEY` en variable de entorno).
- [ ] No enviar datos sensibles a modelos `:free` (todos entrenan con prompts, Doc 4).
