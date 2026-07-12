# Documento 4 — Ciberseguridad y análisis multimodal con modelos gratuitos (Kilo Gateway)

> Complementa los docs 01-03. Base URL: `https://api.kilo.ai/api/gateway`
> Datos de modalidades y límites verificados en vivo el 2026-07-11.

## 0. ADVERTENCIA CRÍTICA (leer primero)

**Todos los 11 modelos `:free` tienen `mayTrainOnYourPrompts: true`.** Esto significa que tus prompts y respuestas *pueden* usarse para entrenar al proveedor.

Para ciberseguridad esto implica:
- ❌ **NO envíes secretos reales**, hashes de producción, tokens, claves, ni datos de vulnerabilidades activas a modelos gratuitos.
- ❌ **NO pegues código fuente propietario sensible** tal cual.
- ✅ Usa **datos ofuscados / sintéticos / ejemplos** para análisis.
- ✅ Para trabajo real con confidencialidad, usa **API key propia (BYOK)** o modelos de pago con `mayTrainOnYourPrompts: false`.
- ✅ `cohere/north-mini-code:free` es el único gratuito marcado `is_moderated: true`.

> Corrección a Doc 3: allí se indicó que varios `:free` eran `mayTrainOnYourPrompts: false`. La verificación directa del endpoint confirma que **todos son `true`**. Aplicar el criterio de "no enviar datos sensibles" a todos los gratuitos.

## 1. ¿Qué modelo gratuito sirve para ciberseguridad?

| Tarea de ciberseguridad | Modelo gratuito recomendado | Por qué |
|---|---|---|
| Revisión de código / bugs / secretos hardcodeados | `cohere/north-mini-code:free`, `tencent/hy3:free` | Especializados en código; soportan `tools` para leer archivos |
| Análisis largo de logs / amenazas (mucho contexto) | `nvidia/nemotron-3-ultra-550b-a55b:free` (1M), `nvidia/nemotron-3-super-120b-a12b:free` (1M) | Ventana de contexto enorme |
| Razonamiento sobre exploit / cadena de ataque | `tencent/hy3:free`, `nvidia/nemotron-3-super-120b-a12b:free` | Buen razonamiento + JSON estructurado |
| Clasificación de contenido malicioso / moderación | `nvidia/nemotron-3.5-content-safety:free` | Es un **clasificador**, no chat; entra texto+imagen |
| Análisis de capturas / diagramas de red / fotos de evidencia | `stepfun/step-3.7-flash:free`, `openrouter/free` | Aceptan **imagen** de entrada |
| Análisis forense de audio (grabaciones) / video | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | **Único gratuito** que acepta audio+imagen+video |
| No saber por dónde empezar (router) | `kilo-auto/free`, `openrouter/free` | Eligen modelo automáticamente |

## 2. Multimodal: qué pueden "leer" realmente

| Modalidad | Modelos gratuitos que la aceptan (entrada) | Salida generada |
|---|---|---|
| Texto | Todos (11) | texto |
| Imagen / fotos | `stepfun`, `openrouter/free`, `nemotron-3.5-content-safety`, `nemotron-3-nano-omni` | texto (descripción/análisis) |
| Audio (oír/transcribir) | **solo `nemotron-3-nano-omni`** | texto |
| Video | **solo `nemotron-3-nano-omni`** | texto |
| Voz / hablar (TTS) | **ninguno** | — |
| Generar imágenes | **ninguno** | — |

Conclusión multimodal: para **fotos** usa `stepfun`/`openrouter/free`; para **audio o video** solo existe `nemotron-3-nano-omni`. Ninguno "habla" ni pinta imágenes.

## 3. ¿Se pueden mezclar varios modelos? SÍ (y se recomienda)

Un solo modelo no es óptimo para todo. La arquitectura recomendada es **orquestación de varios modelos gratuitos en pipeline**, donde tú (el agente) enrutes cada subtarea al modelo adecuado.

### Patrón A — Pipeline secuencial (análisis de evidencia mixta)
```
[Ingesta: imagen/audio/log]
        │
        ├─ nano-omni:free  ──► transcribe audio / describe video / foto
        │       (salida texto)
        ▼
   tencent/hy3:free  ──► razona sobre el texto, extrae IOCs,
   o nemotron-3-super     propone hipótesis de ataque
        │
        ▼
   cohere/north-mini-code:free ──► revisa el script/decode del payload
        │
        ▼
   nemotron-3.5-content-safety:free ──► clasifica si es malicioso
        │
        ▼
   [Reporte final en texto]
```

### Patrón B — Router + especialistas (con `kilo-auto/free`)
Usa `kilo-auto/free` o `openrouter/free` como primer filtro que deriva a un especialista según el tipo de entrada. Útil cuando no quieres decidir el modelo a mano.

### Patrón C — Agente con tools (el modelo "tiene efecto")
Dale al modelo herramientas (`tools`): `leer_archivo`, `grep_repo`, `ejecutar_comando`, `consultar_cve`. El modelo pide `tool_calls`; **tu código** los ejecuta y devuelve resultados. Así el agente puede, por ejemplo, escanear un repo en busca de secretos y pedir a `cohere` que los revise. 10/11 gratuitos soportan `tools`.

## 4. Ejemplo de orquestación (esqueleto Python)

```python
from openai import OpenAI
k = OpenAI(base_url="https://api.kilo.ai/api/gateway", api_key="SIN-KEY-SI-ES-FREE")

def call(model, prompt, img_b64=None):
    msgs = [{"role":"user","content":[]}]
    if img_b64:
        msgs[0]["content"] = [
            {"type":"text","text":prompt},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}}
        ]
    else:
        msgs[0]["content"] = prompt
    r = k.chat.completions.create(model=model, messages=msgs, max_tokens=2000)
    return (r.choices[0].message.content or r.choices[0].message.reasoning or "")

# 1) Foto/audio -> nano-omni (multimodal)
desc = call("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "Transcribe y resume esta evidencia.", img_b64)

# 2) Razonamiento -> tencent
hip = call("tencent/hy3:free", f"Analiza esta evidencia y extrae IOCs:\n{desc}")

# 3) Revisión de código -> cohere
rev = call("cohere/north-mini-code:free", f"Revisa este fragmento sospechoso:\n{hip}")

# 4) Clasificación -> content-safety
verd = call("nvidia/nemotron-3.5-content-safety:free", f"¿Es malicioso? {rev}")
print(verd)
```

## 5. Límites y riesgos en ciberseguridad

- **Fuga de datos:** todos los `:free` entrenan con prompts → nunca datos reales confidenciales.
- **Alucinaciones en IOCs:** valida hashes/IPs contra fuentes reales (VirusTotal, CVE, MISP); el modelo no es fuente de verdad.
- **Sin TTS/imagen generada:** no esperes que "dibuje" un diagrama; genera descripción en texto (usa Mermaid/Graphviz aparte).
- **Latencia:** `kilo-auto/free` ~11s (elige modelo); usa modelos fijos para respuestas predecibles.
- **Rate limit anónimo:** 200 req/h IP → para automatizaciones usa API key.
- **content-safety** no es chat: úsalo solo como clasificador binario/etiquetador.

## 6. Matriz de decisión rápida

| Quieres… | Usa |
|---|---|
| Analizar una **foto** de evidencia | `stepfun` / `openrouter/free` |
| Analizar **audio o video** | `nemotron-3-nano-omni` (único) |
| Revisar **código** sospechoso | `cohere/north-mini-code` / `tencent/hy3` |
| Leer **logs gigantes** (1M ctx) | `nemotron-3-ultra` / `nemotron-3-super` |
| **Clasificar** si es malicioso | `nemotron-3.5-content-safety` |
| Un **agente** que ejecute acciones | cualquier modelo con `tools` + tus funciones |
| No decidir modelo | `kilo-auto/free` / `openrouter/free` (router) |
