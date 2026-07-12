# Documento 3 — Seguridad, parámetros y buenas prácticas

> Orientado a usar la API con modelos gratuitos y de pago de forma segura.

## 1. Niveles de autenticación y riesgo

| Método | Requiere key | Riesgo | Uso |
|---|---|---|---|
| Anónimo (`:free`) | No | Bajo (limitado 200 req/h IP, sin historial persistente) | Pruebas, scripts personales |
| API key (Bearer) | Sí | Medio | Producción con tu cuenta/créditos |
| Organization token | Sí (org) | Bajo-Medio | Equipos, políticas centralizadas (expira 15 min) |
| BYOK | Tus keys de proveedor | Depende del proveedor | Sin markup de Kilo, facturación directa |

## 2. Qué tan seguros son los modelos (campo `mayTrainOnYourPrompts`)

18 de 340 modelos **pueden entrenar con tus prompts**. Son casi todos los `stealth/*` y variantes `:discounted` (ej. `deepseek/deepseek-v4-flash:discounted`, `stealth/claude-opus-4.7`). 

**Recomendación:** nunca envíes secretos, datos personales, código propietario ni credenciales a esos modelos. Los modelos `:free` probados (`tencent/hy3:free`, `nvidia/*`, `poolside/*`, `cohere/*`, `kilo-auto/free`, `openrouter/free`, `stepfun/*`) tienen `mayTrainOnYourPrompts: false` en la lista → más seguros para datos sensibles (aún así, evita secretos en cualquier LLM).

## 3. Moderación (`is_moderated`)

Algunos modelos (ej. `openai/gpt-*`) son moderados por el proveedor. Los gratuitos de esta prueba no lo son (`is_moderated: false`). Si necesitas filtrar salidas, usa `nvidia/nemotron-3.5-content-safety:free` como clasificador previo/posterior.

## 4. Headers de control (seguridad operativa)

- `X-KiloCode-OrganizationId`: aplica allow-list de modelos, restricciones de proveedor y límites de gasto por usuario.
- `X-KiloCode-TaskId`: key de prompt cache (evita recomputar, ahorra costo).
- `x-kilocode-mode`: hint de modo para el enrutador `kilo-auto`.
- Nunca expongas tu API key en frontend; usa proxy/backend o BYOK.

## 5. Rate limits y costos

- Anónimo: 200 req/hora/IP.
- Con key: depende de créditos y políticas de organización.
- Precisión de costo en microdólares (`pricing.prompt`, `pricing.completion`, `input_cache_read`). Los `:free` cuestan 0 en precio pero consumen tu cuota anónima.

## 6. Parámetros soportados (los más útiles)

Comunes en los gratuitos:
- `max_tokens`, `temperature`, `top_p`, `top_k`, `seed`, `stop`
- `tools`, `tool_choice` (function calling / MCP)
- `reasoning`, `include_reasoning` (modelos de razonamiento)
- `response_format`, `structured_outputs` (salida JSON tipada; no en todos)
- `frequency_penalty`, `presence_penalty`, `repetition_penalty` (según modelo)

Ejemplo de control de salida JSON:
```json
{"model":"tencent/hy3:free","messages":[{"role":"user","content":"Devuelve JSON"}],
 "response_format":{"type":"json_object"}}
```

## 7. Buenas prácticas de seguridad

1. **No hardcodees la API key.** Usa variable de entorno (`KILO_API_KEY`).
2. **Modelos gratuitos para datos no sensibles**; evita secretos en cualquier LLM.
3. **Evita `mayTrainOnYourPrompts: true`** para información confidencial.
4. **Usa Organization tokens** en equipos (expiración 15 min, políticas centralizadas).
5. **Valida `tool_calls`** antes de ejecutar funciones (evita inyección de prompt que invoque herramientas peligrosas).
6. **Pon límites** (`max_tokens`, timeouts de red 30s) para evitar respuestas colgadas.
7. **No confíes ciegamente en modelos `:free`** para decisiones críticas; réplica importante con modelo de pago.
8. **Cache con `X-KiloCode-TaskId`** para reducir costo y latencia.

## 8. Resumen de decisión

| Objetivo | Recomendación |
|---|---|
| Probar sin registrarte | `tencent/hy3:free` anónimo, leer `content` |
| Producción segura | API key + modelo con `mayTrainOnYourPrompts:false` |
| Equipo/empresa | Organization token + allow-list de modelos |
| Sin costo de proveedor | BYOK (tus keys, sin markup) |
| MCP/tools | Cualquier modelo con `tools` en `supported_parameters` |
| Moderación | `nvidia/nemotron-3.5-content-safety:free` |
