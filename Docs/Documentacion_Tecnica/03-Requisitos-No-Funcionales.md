---
título: 03 - Requisitos No Funcionales
objetivo: Extraer los requisitos no funcionales (rendimiento, seguridad, escalabilidad, portabilidad, mantenibilidad, compatibilidad, memoria, CPU, concurrencia, tolerancia a fallos) según la documentación base.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,2,7,9,13; Docs/KiloGateway 02,03,04.
dependencias: 01-Resumen-Ejecutivo.md; 12-Seguridad.md.
referencias: 21-Dependencias.md; 16-Estados-Sistema.md.
---

# 03 - Requisitos No Funcionales

Extraídos estrictamente de la documentación. Donde la documentación no declara un valor numérico, se marca como no especificado.

## Rendimiento

- **RNF-REN-1:** El agente debe minimizar su footprint para "no convertirse vos mismo en el proceso sospechoso" (principio de agente Windows).
- **RNF-REN-2:** Latencia mínima en el chat interactivo: Groq (hardware LPU) se indica como la latencia más baja del mercado.
- **RNF-REN-3:** Para respuestas de latencia predecible se recomienda usar un modelo fijo en lugar de `kilo-auto/free` (cuyo router elige modelo y tarda ~11s).
- **RNF-REN-4:** ClickHouse es más eficiente que OpenSearch para eventos de alto volumen (si el volumen crece mucho).

> **Información no especificada en la documentación original.** No se especifican SLA numéricos, throughput objetivo de eventos/seg, ni tiempos máximos de detección.

## Seguridad

- **RNF-SEG-1:** Transporte agente↔collector con mTLS.
- **RNF-SEG-2:** Todo evento auditable e inmutable (write-once log, idealmente hash-chaining estilo Merkle para detectar tampering).
- **RNF-SEG-3:** Ninguna acción de remediación se ejecuta sin pasar por el switch de autonomía.
- **RNF-SEG-4:** La IA tiene acceso de lectura completo vía function calling; la ejecución está gobernada por policy + switch.
- **RNF-SEG-5 (API Gateway):** No exponer la API key en frontend; usar proxy/backend o BYOK.
- **RNF-SEG-6 (API Gateway):** Validar `tool_calls` antes de ejecutar funciones (evitar inyección de prompt que invoque herramientas peligrosas).
- **RNF-SEG-7 (API Gateway):** Poner límites (`max_tokens`, timeout de red 30s) para evitar respuestas colgadas.
- **RNF-SEG-8:** No enviar secretos ni datos sensibles a modelos `:free` (todos `mayTrainOnYourPrompts: true` según Doc 4 verificado).
- **RNF-SEG-9:** Para telemetría de seguridad real con free tier que entrena, anonymizar/hashear campos antes de enviar al LLM.

## Escalabilidad

- **RNF-ESC-1:** Adoptar OCSF para no reinventar el formato de eventos al agregar fuentes nuevas.
- **RNF-ESC-2:** Si el volumen crece mucho, migrar almacenamiento a ClickHouse.
- **RNF-ESC-3 (API):** Rate limit anónimo de 200 req/h por IP; para automatizaciones usar API key.

## Portabilidad

- **RNF-POR-1:** Multiplataforma real con agente nativo por SO (Windows, Linux, macOS, Android), no un wrapper Electron.
- **RNF-POR-2:** 100% free & open source con licencias OSS reales (Apache 2.0, MIT, GPL, AGPL) o free tier sostenible.

## Mantenibilidad

- **RNF-MAN-1:** Cada sección numerada del documento raíz puede convertirse en su propio deep-dive técnico.
- **RNF-MAN-2:** System prompts versionados (carpeta `prompts/`).
- **RNF-MAN-3:** No hardcodear un modelo específico sin un plan B (el catálogo de modelos rota).
- **RNF-MAN-4:** El router de failover entre proveedores es un simple cambio de `base_url` (todos compatibles con SDK OpenAI).

## Compatibilidad

- **RNF-COM-1:** API Gateway compatible con OpenAI: soporta SDK de OpenAI, Vercel AI SDK o cualquier cliente OpenAI.
- **RNF-COM-2:** Los tres proveedores de IA (Cerebras, Groq, OpenRouter) exponen API compatible con el SDK de OpenAI.
- **RNF-COM-3:** Android: compatibilidad con políticas de Play Store (VpnService, UsageStatsManager, etc., sin root).

## Uso de memoria / CPU

> **Información no especificada en la documentación original.** No se especifican límites de memoria ni CPU. Se menciona eBPF como "el presente de la telemetría de kernel en Linux, sin el overhead de auditd" (implicación de eficiencia, no un valor).

## Concurrencia

- **RNF-CON-1:** Pub/sub real vía NATS/MQTT sobre TLS como alternativa a gRPC directo (implica manejo de múltiples suscriptores/eventos).

> **Información no especificada en la documentación original.** No se especifica grado de concurrencia de agentes/hosts ni modelo de threading.

## Tolerancia a fallos

- **RNF-TOL-1 (Fail-safe, no fail-open):** Si el agente pierde conexión con el cerebro central, sigue coleccionando y bufferea local — nunca se queda "ciego" ni empieza a actuar solo.
- **RNF-TOL-2 (IA):** Failover automático: Cerebras (principal), Groq (chat, latencia), OpenRouter (fallback). Si uno cae/cambia límites/deprecía modelo, probar el siguiente.
- **RNF-TOL-3 (IA):** No confiar ciegamente en modelos `:free` para decisiones críticas; réplica con modelo de pago.
- **RNF-TOL-4 (API):** El gateway repara automáticamente duplicados / `tool_calls` huérfanos.
