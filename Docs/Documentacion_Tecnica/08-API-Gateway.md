---
título: 08 - API Gateway
objetivo: Documentar únicamente lo indicado sobre la API Gateway (Kilo AI Gateway): autenticación, headers, tokens, timeouts, errores, payloads, requests, responses, manejo de errores y límites.
alcance: Docs/KiloGateway/01-04 (fuente única para esta sección).
dependencias: 09-Integracion-IA.md; 03-Requisitos-No-Funcionales.md.
referencias: 12-Seguridad.md; 13-Manejo-Errores.md.
---

# 08 - API Gateway

> Documentación exclusiva de `Docs/KiloGateway/01-04`. Base URL: `https://api.kilo.ai/api/gateway`. Compatible con OpenAI.

## 1. Endpoints

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/api/gateway/v1/models` | Listar modelos (340 modelos, 55 proveedores) |
| POST | `/api/gateway/chat/completions` | Chat completions |
| (FIM) | vía Mistral Codestral | Code completions (fill-in-the-middle) |

## 2. Autenticación

| Caso | Headers |
|---|---|
| Modelo `:free` (anónimo) | `Content-Type: application/json` — **sin Authorization** |
| Modelo de pago / tu key | `Authorization: Bearer <KILO_API_KEY>` + `Content-Type: application/json` |
| Cuenta organización | `+ X-KiloCode-OrganizationId: <org_id>` |
| Prompt cache / trazabilidad | `+ X-KiloCode-TaskId: <id>`, `X-KiloCode-Version: <ver>`, `x-kilocode-mode: <mode>` |

- Límites anónimos: **200 requests/hora por IP**.
- Organization token expira a los **15 minutos**.

## 3. Headers de control (seguridad operativa)

- `X-KiloCode-OrganizationId`: allow-list de modelos, restricciones de proveedor, límites de gasto por usuario.
- `X-KiloCode-TaskId`: key de prompt cache (evita recomputar, ahorra costo).
- `x-kilocode-mode`: hint de modo para el enrutador `kilo-auto`.

## 4. Tokens / API key

- Se usa `Authorization: Bearer <KILO_API_KEY>`.
- Nunca exponer la API key en frontend; usar proxy/backend o BYOK.
- BYOK: tus keys de proveedor, sin markup de Kilo, facturación directa.

## 5. Timeouts

- Documentación indica poner timeouts de red de **30s** para evitar respuestas colgadas (Doc 3, buena práctica 6).

## 6. Payloads / Requests

### cURL mínimo (`:free`, sin key)
```bash
curl -X POST "https://api.kilo.ai/api/gateway/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"tencent/hy3:free","messages":[{"role":"user","content":"..."}],"stream":false}'
```

### Con API key
```bash
curl -X POST "https://api.kilo.ai/api/gateway/chat/completions" \
  -H "Authorization: Bearer $KILO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"anthropic/claude-sonnet-4.5","messages":[{"role":"user","content":"Hola"}],"stream":false}'
```

### Tool calling (ejemplo `tencent/hy3:free`)
```json
{
  "model": "tencent/hy3:free",
  "messages": [{"role":"user","content":"¿Qué hora es? usa get_time"}],
  "tools": [{"type":"function","function":{"name":"get_time","description":"Devuelve la hora actual","parameters":{"type":"object","properties":{},"required":[]}}}]
}
```

## 7. Responses

- Modelos normales: `message.content`.
- Modelos de razonamiento (`kilo-auto/free`, `stepfun`, `poolside-m.1`, `openrouter/free`): respuesta final en `message.reasoning`.
- Tool calling: el modelo responde con `message.tool_calls` (nombre + argumentos JSON). Se ejecuta la función y se devuelve el resultado como `role: "tool"`.
- `content` vacío en `:free` razonamiento → leer `message.reasoning`.
- `nvidia/nemotron-3.5-content-safety:free`: es clasificador, no chat; usa campo propio de moderación.

## 8. Parámetros soportados

`max_tokens`, `temperature`, `top_p`, `top_k`, `seed`, `stop`, `tools`, `tool_choice`, `reasoning`, `include_reasoning`, `response_format`, `structured_outputs`, `frequency_penalty`, `presence_penalty`, `repetition_penalty` (según modelo).

Ejemplo JSON:
```json
{"model":"tencent/hy3:free","messages":[{"role":"user","content":"Devuelve JSON"}],"response_format":{"type":"json_object"}}
```

## 9. Streaming

`"stream": true` → respuesta en chunk SSE (`data: {...}`). En OpenAI SDK iterar `for await (const chunk of r)`. Útil para UI en tiempo real.

## 10. MCP

El gateway **no hospeda servidores MCP**. Expone tool calling estándar; un cliente puente traduce herramientas MCP al array `tools`. El gateway repara automáticamente duplicados / `tool_calls` huérfanos.

## 11. Errores y límites

| Error | Causa | Solución |
|---|---|---|
| `401` | Falta key en modelo de pago | Agrega `Authorization: Bearer <key>` |
| `400` con `reasoning` | Formato de `reasoning` no aceptado por ese modelo | Quita el parámetro o usa `include_reasoning` |
| `content` vacío en `:free` | Es modelo reasoning | Lee `message.reasoning` |
| Respuesta lenta (kilo-auto ~11s) | El router elige modelo | Usa modelo fijo para latencia predecible |
| `429` anónimo | Superaste 200 req/h IP | Usa API key o espera |

## 12. Rate limits y costos

- Anónimo: 200 req/hora/IP.
- Con key: depende de créditos y políticas de organización.
- Precisión de costo en microdólares (`pricing.prompt`, `pricing.completion`, `input_cache_read`). Los `:free` cuestan 0 pero consumen cuota anónima.

## 13. Escala de la API (datos reales Doc 1)

| Métrica | Cantidad |
|---|---|
| Modelos totales | 340 |
| Proveedores distintos | 55 |
| Modelos gratuitos (`:free`) | 11 |
| Modelos con tool calling | 266 |
| Modelos con entrada de imagen | 180 |
| Modelos que pueden entrenar con tus prompts | 18 |

## 14. Conflicto de fuentes (importante)

- **Doc 3** afirma que `tencent/hy3:free`, `nvidia/*`, `poolside/*`, `cohere/*`, `kilo-auto/free`, `openrouter/free`, `stepfun/*` tienen `mayTrainOnYourPrompts: false`.
- **Doc 4** (verificado en vivo 2026-07-11) corrige: **todos los 11 `:free` tienen `mayTrainOnYourPrompts: true`**.
- **Criterio aplicable:** no enviar secretos ni datos sensibles a ningún modelo `:free`. Para confidencialidad usar API key propia (BYOK) o modelos de pago con `mayTrainOnYourPrompts: false`.

> **Modo híbrido (Opción C, 2026-07-11).** Si la API Gateway no está disponible (caída, `429` por límite anónimo 200 req/h IP, timeout 30s) o por política de privacidad, ARGOS conmuta a un **modelo local GGUF** (Qwen2.5-0.5B-Instruct-GGUF) ejecutado en la máquina, sin salida de red. Ver `29-Arquitectura-IA-Hibrida.md` y `30-Descarga-Modelo-Local-Qwen25.md`.

> **Información no especificada en la documentación original.** No se especifican códigos de error adicionales (p. ej. `5xx`, `403`), ni esquema exacto de respuesta de error en JSON, ni reintentos/backoff del lado del cliente.
