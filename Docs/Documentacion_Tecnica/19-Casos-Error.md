---
título: 19 - Casos de Error
objetivo: Documentar todos los escenarios de error descritos en la documentación, sin inventar.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,6,7; Docs/KiloGateway 02,03,04.
dependencias: 13-Manejo-Errores.md; 08-API-Gateway.md.
referencias: 18-Casos-Uso.md.
---

# 19 - Casos de Error

Todos los escenarios documentados. Nada inventado.

## CE-01 — Pérdida de conexión agente ↔ cerebro central
- **Escenario:** el agente pierde conexión con el cerebro central.
- **Comportamiento documentado:** Fail-safe, no fail-open. Sigue coleccionando y bufferea local (SQLite), nunca se queda ciego ni actúa solo.
- **Recuperación:** reenvía al reconectar.

## CE-02 — Proveedor LLM caído / cambia límites / deprecia modelo
- **Escenario:** uno de Cerebras/Groq/OpenRouter cae, cambia límites o deprecia modelo.
- **Comportamiento:** `call_with_failover` captura excepción y prueba el siguiente proveedor.
- **Recuperación:** failover automático.

## CE-03 — Los tres proveedores fallan
- **Escenario:** ningún proveedor responde.
- **Comportamiento:** `raise RuntimeError("Los tres proveedores fallaron")`.
- **Recuperación:** degradación controlada (no especificada en detalle).

## CE-04 — `401` en modelo de pago
- **Causa:** falta `Authorization: Bearer <key>`.
- **Solución:** agregar header.

## CE-05 — `400` con parámetro `reasoning`
- **Causa:** formato no aceptado por ese modelo (ej. `kilo-auto/free`, `stepfun` lo rechazan).
- **Solución:** quitar parámetro o usar `include_reasoning`.

## CE-06 — `content` vacío en modelo `:free`
- **Causa:** es modelo de razonamiento.
- **Solución:** leer `message.reasoning`.

## CE-07 — Respuesta lenta (kilo-auto ~11s)
- **Causa:** el router elige modelo.
- **Solución:** usar modelo fijo para latencia predecible.

## CE-08 — `429` anónimo
- **Causa:** supera 200 req/h por IP.
- **Solución:** usar API key o esperar.

## CE-09 — Alucinaciones en IOCs
- **Escenario:** el modelo inventa hashes/IPs.
- **Comportamiento:** validar contra fuentes reales (VirusTotal, CVE, MISP). El modelo no es fuente de verdad.

## CE-10 — Inyección de prompt en tool calling
- **Escenario:** prompt invoca herramientas peligrosas.
- **Comportamiento:** validar `tool_calls` antes de ejecutar funciones.

## CE-11 — Fuga de datos a modelo `:free`
- **Escenario:** envío de secretos/credenciales a `:free`.
- **Comportamiento documentado:** todos los 11 `:free` tienen `mayTrainOnYourPrompts: true`. Nunca enviar datos reales confidenciales; usar BYOK/pago o datos ofuscados.

## CE-12 — Sin TTS / imagen generada
- **Escenario:** se espera que el modelo "hable" o "dibuje".
- **Comportamiento:** ningún `:free` genera voz ni imágenes; genera descripción en texto (usar Mermaid/Graphviz aparte).

## CE-13 — content-safety usado como chat
- **Escenario:** se usa `nvidia/nemotron-3.5-content-safety:free` como chat.
- **Comportamiento:** es clasificador, no chat; usar solo como clasificador binario/etiquetador.

> **Información no especificada en la documentación original.** No se documentan escenarios de error de: corrupción del hash-chain de auditoría, fallo de almacenamiento (OpenSearch/ClickHouse), fallo del collector, ni recuperación ante `5xx` del gateway.
