# Documento 1 — Modelos disponibles y estado real (Kilo AI Gateway)

> Fuente: `GET https://api.kilo.ai/api/gateway/v1/models` (340 modelos) + pruebas en vivo del 2026-07-11.
> Base URL de uso: `https://api.kilo.ai/api/gateway`

## 1. Qué es

El Kilo AI Gateway es una API **compatible con OpenAI** que unifica cientos de modelos de distintos proveedores bajo un solo endpoint. Cambias de modelo cambiando una sola cadena de texto; no cambias de SDK.

Endpoints:
- Listar modelos: `GET https://api.kilo.ai/api/gateway/v1/models`
- Chat: `POST https://api.kilo.ai/api/gateway/chat/completions`
- FIM (code completions): vía Codestral (ver Doc 2)

## 2. Escala de la API (datos reales)

| Métrica | Cantidad |
|---|---|
| Modelos totales | 340 |
| Proveedores distintos | 55 |
| Modelos gratuitos (`:free`) | 11 |
| Modelos con tool calling | 266 |
| Modelos con entrada de imagen | 180 |
| Modelos que pueden entrenar con tus prompts | 18 |

## 3. Proveedores (top 15 por cantidad de modelos)

| Proveedor | Modelos |
|---|---|
| openai | 66 |
| qwen | 47 |
| google | 26 |
| mistralai | 19 |
| anthropic | 15 |
| deepseek | 13 |
| z-ai | 12 |
| meta-llama | 9 |
| nvidia | 8 |
| minimax | 8 |
| moonshotai | 6 |
| stealth | 5 |
| openrouter | 5 |
| amazon | 5 |
| kilo-auto | 5 |

Otros presentes: perplexity, cohere, thedrummer, bytedance-seed, nousresearch, sao10k, aion-labs, poolside, tencent, x-ai, inclusionai, arcee-ai, stepfun, relace, microsoft, morph, inflection, nex-agi, xiaomi, ibm-granite, rekaai, baidu, gryphe, mancer, undi95, perceptron, anthracite-org, allenai, deepcogito, inception, upstage, writer, bytedance, cognitivecomputations, ai21, kwaipilot.

> Nota: `stealth/*` y `~provider` son variantes de terceros (más baratas, pueden entrenar con tus prompts — ver Doc 3).

## 4. Los 11 modelos GRATUITOS (`:free`) — probados en vivo

Todos son accesibles **sin API key** (acceso anónimo, 200 req/hora por IP). Estado verificado:

| Modelo | Contexto | Tools | Estado real | Cómo leer la respuesta |
|---|---|---|---|---|
| `tencent/hy3:free` | 256k | ✅ | ✅ Online, `content` limpio | `message.content` |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 1M | ✅ | ✅ Online | `message.content` |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 256k | ✅ | ✅ Online | `message.content` |
| `nvidia/nemotron-3-super-120b-a12b:free` | 1M | ✅ | ✅ Online (filtra pensamiento en content) | `message.content` |
| `poolside/laguna-xs-2.1:free` | 256k | ✅ | ✅ Online (con `reasoning` off) | `message.content` |
| `cohere/north-mini-code:free` | 256k | ✅ | ✅ Online (con `reasoning` off) | `message.content` |
| `kilo-auto/free` | 200k | ✅ | ✅ Online, router automático | leer `message.reasoning` |
| `stepfun/step-3.7-flash:free` | 256k | ✅ | ✅ Online | leer `message.reasoning` |
| `poolside/laguna-m.1:free` | 256k | ✅ | ✅ Online | leer `message.reasoning` |
| `openrouter/free` | 200k | ✅ | ✅ Online (router a varios gratis) | leer `message.reasoning` |
| `nvidia/nemotron-3.5-content-safety:free` | 128k | ❌ | ✅ Online, pero es **clasificador** de seguridad, no chat | campo propio de moderación |

### Hallazgo importante sobre los modelos "reasoning"
En este gateway, los modelos de razonamiento (`kilo-auto/free`, `stepfun`, `poolside-m.1`, `openrouter/free`) devuelven la respuesta final en el campo **`reasoning`**, no en `content`. Para usarlos en chat normal:
- Pon `include_reasoning: true` y lee `message.reasoning` como la respuesta.
- O (en los que aplica, ej. poolside-xs, cohere) desactiva el razonamiento y obtienes `content` limpio.

`kilo-auto/free` y `stepfun` rechazan el parámetro `reasoning` con 400; úsalos leyendo `reasoning`.

## 5. Modelos de pago destacados (requieren API key / créditos)

No se probaron en vivo (no hay key en este entorno), pero figuran en la lista y son los más usados:
- `anthropic/claude-sonnet-4.5`, `anthropic/claude-opus-4.*`
- `openai/gpt-4`, `openai/gpt-4o`, `openai/gpt-3.5-turbo`
- `google/gemini-2.*`, `deepseek/deepseek-*` (incl. `deepseek-v4-flash:discounted`)
- `x-ai/grok-*`, `meta-llama/llama-*`, `qwen/*`, `mistralai/*`
- `kilo-auto/small` y `kilo-auto/*`: auto-router por tamaño (baratos).

## 6. Cómo elegir modelo según necesidad

| Necesidad | Modelo gratuito sugerido |
|---|---|
| Chat general rápido y fiable | `tencent/hy3:free` |
| Contexto muy largo (1M) | `nvidia/nemotron-3-ultra-550b-a55b:free` o `nvidia/nemotron-3-super-120b-a12b:free` |
| Código | `cohere/north-mini-code:free` |
| No saber cuál usar | `kilo-auto/free` o `openrouter/free` (router) |
| Moderación de contenido | `nvidia/nemotron-3.5-content-safety:free` |

Ver Documento 2 para conectar y Documento 3 para seguridad.
