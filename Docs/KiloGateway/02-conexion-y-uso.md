# Documento 2 — Cómo conectar y consumir la API (guía práctica)

> Resumen operativo. Base URL: `https://api.kilo.ai/api/gateway`
> Compatible con OpenAI: sirve el SDK de OpenAI, Vercel AI SDK o cualquier cliente OpenAI.

## 1. Autenticación (headers)

| Caso | Headers necesarios |
|---|---|
| Modelo `:free` (anonimo) | `Content-Type: application/json` — **sin Authorization** |
| Modelo de pago / tu key | `Authorization: Bearer <KILO_API_KEY>` + `Content-Type: application/json` |
| Cuenta organización | `+ X-KiloCode-OrganizationId: <org_id>` |
| Prompt cache / trazabilidad | `+ X-KiloCode-TaskId: <id>`, `X-KiloCode-Version: <ver>`, `x-kilocode-mode: <mode>` |

Límites anónimos: **200 requests/hora por IP**. Para producción usa API key.

## 2. cURL — lo mínimo que funciona

Modelo gratuito, sin key:
```bash
curl -X POST "https://api.kilo.ai/api/gateway/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tencent/hy3:free",
    "messages": [{"role":"user","content":"Explica qué es una closure en JS."}],
    "stream": false
  }'
```

Con API key (modelo de pago):
```bash
curl -X POST "https://api.kilo.ai/api/gateway/chat/completions" \
  -H "Authorization: Bearer $KILO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"anthropic/claude-sonnet-4.5","messages":[{"role":"user","content":"Hola"}],"stream":false}'
```

## 3. Python (OpenAI SDK) — recomendado

```python
from openai import OpenAI

# Sin key si usas modelo :free; si no, pon tu KILO_API_KEY
client = OpenAI(
    base_url="https://api.kilo.ai/api/gateway",
    api_key="SIN-KEY-SI-ES-FREE-O-TU-KEY",
)

r = client.chat.completions.create(
    model="tencent/hy3:free",
    messages=[{"role": "user", "content": "¿Cómo hago un GET en Python con requests?"}],
)
print(r.choices[0].message.content)
```

## 4. Node.js (OpenAI SDK)

```javascript
import OpenAI from "openai";
const client = new OpenAI({ base_url: "https://api.kilo.ai/api/gateway", api_key: "TU_KEY" });
const r = await client.chat.completions.create({
  model: "tencent/hy3:free",
  messages: [{ role: "user", content: "Hola" }],
});
console.log(r.choices[0].message.content);
```

## 5. Vercel AI SDK (streaming)

```javascript
import { streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import "dotenv/config";

const kilo = createOpenAI({ baseURL: "https://api.kilo.ai/api/gateway", apiKey: process.env.KILO_API_KEY });
const result = streamText({ model: kilo.chat("tencent/hy3:free"), prompt: "¿Qué es un decorador en Python?" });
for await (const p of result.textStream) process.stdout.write(p);
```

## 6. Streaming

Agrega `"stream": true`. La respuesta llega en chunk SSE (`data: {...}`). En OpenAI SDK basta con iterar `for await (const chunk of r)`. En cURL crudo verás líneas `data:`. Útil para UI en tiempo real.

## 7. Tool calling (function calling)

266 modelos lo soportan, incluidos 10 de 11 gratuitos. Ejemplo (probado en `tencent/hy3:free`):
```json
{
  "model": "tencent/hy3:free",
  "messages": [{"role":"user","content":"¿Qué hora es? usa get_time"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_time",
      "description": "Devuelve la hora actual",
      "parameters": {"type":"object","properties":{},"required":[]}
    }
  }]
}
```
El modelo responde con `message.tool_calls` (nombre + argumentos JSON). Tú ejecutas la función y devuelves el resultado como `role: "tool"`.

## 8. MCP (Model Context Protocol)

El gateway **no hospeda servidores MCP**, pero como expone tool calling estándar, cualquier cliente puente MCP→`tools` lo usa. Flujo:
1. Defines herramientas MCP en tu cliente (Kilo Code, CLI, o tu propio código).
2. El cliente traduce esas herramientas al array `tools` de la API.
3. El modelo gratuito invoca `tool_calls`; tú ejecutas la herramienta MCP y devuelves el resultado.
4. El gateway repara automáticamente duplicados/tool_calls huérfanos.

Resumen: para MCP necesitas un cliente que haga el puente; la API solo entiende `tools`/`tool_choice`.

## 9. FIM (Fill-in-the-middle, autocompletado de código)

Soportado vía **Mistral Codestral** (FIM), útil para editores/autocompletado. Consultar doc de Codestral en el gateway.

## 10. Errores comunes y solución

| Error | Causa | Solución |
|---|---|---|
| `401` | Falta key en modelo de pago | Agrega `Authorization: Bearer <key>` |
| `400` con `reasoning` | Formato de `reasoning` no aceptado por ese modelo | Quita el parámetro o usa `include_reasoning` |
| `content` vacío en modelo `:free` | Es modelo reasoning | Lee `message.reasoning` |
| Respuesta lenta (kilo-auto ~11s) | El router elige modelo | Usa un modelo fijo para latencia predecible |
| `429` anónimo | Superaste 200 req/h IP | Usa API key o espera |
