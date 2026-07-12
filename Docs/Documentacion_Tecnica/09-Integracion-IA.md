---
título: 09 - Integración con IA
objetivo: Documentar completamente cómo se realiza la llamada a la IA, qué datos envía, qué recibe, cómo se procesa, cómo se validan respuestas, qué errores contempla y qué estados existen.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 6,7; Docs/KiloGateway 01-04.
dependencias: 08-API-Gateway.md; 04-Arquitectura.md.
referencias: 03-Requisitos-No-Funcionales.md; 12-Seguridad.md.
---

# 09 - Integración con IA

> **Extensión híbrida (Opción C, 2026-07-11).** El documento base establece que la IA se consume *únicamente* vía API Gateway. Por decisión del usuario se adopta la **Opción C (Híbrida)**: se mantiene la API Gateway como canal remoto principal y se añade un **modelo local GGUF** (Qwen2.5-0.5B-Instruct-GGUF) como fallback/privacy-guard. Ver `29-Arquitectura-IA-Hibrida.md` y `30-Descarga-Modelo-Local-Qwen25.md`.

## 1. Cómo se realiza la llamada

- La IA se consume **principalmente mediante la API Gateway** (Kilo AI Gateway), compatible OpenAI.
- **Modo híbrido:** cuando la API Gateway no está disponible (caída, `429`, timeout 30s) o por política de privacidad, el **Router híbrido** conmuta a un **modelo local GGUF** ejecutado en la máquina (sin salida de red). Ver `29-Arquitectura-IA-Hibrida.md` §4.
- Arquitectura recomendada de tres proveedores (todos compatibles con SDK OpenAI, failover = cambio de `base_url`):
  - **Cerebras** como motor principal para análisis continuo (volumen diario alto).
  - **Groq** para respuestas del chat interactivo (latencia mínima, hardware LPU).
  - **OpenRouter** como failover automático.

### Router de failover (esqueleto documentado)
```python
providers = [
    {"name": "cerebras", "base_url": "https://api.cerebras.ai/v1", "model": "llama-4-scout"},
    {"name": "groq",     "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    {"name": "openrouter","base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-oss-120b:free"},
]
def call_with_failover(messages, tools):
    for p in providers:
        try:
            client = OpenAI(base_url=p["base_url"], api_key=os.environ[f"{p['name'].upper()}_API_KEY"])
            return client.chat.completions.create(model=p["model"], messages=messages, tools=tools)
        except Exception:
            continue
    raise RuntimeError("Los tres proveedores fallaron")
```

## 2. Qué datos envía

- `messages`: historial de conversación (roles `user`, `assistant`, `tool`, `system`).
- `tools`: definiciones de function calling (las 6 tools de la sección 6.1).
- `model`: identificador de modelo.
- Parámetros opcionales: `max_tokens`, `temperature`, `stream`, `response_format`, `reasoning`/`include_reasoning`, etc.
- **No enviar secretos ni datos sensibles** a modelos `:free` (todos entrenan con prompts, según Doc 4). Anonymizar/hashear IPs, hostnames, patrones de red antes de enviar.

## 3. Qué recibe

- Respuesta del LLM vía `chat.completions.create`.
- Campo de texto: `message.content` (modelos normales) o `message.reasoning` (modelos razonamiento `:free`).
- `message.tool_calls`: nombre + argumentos JSON cuando el modelo invoca una tool.
- Para moderación (`nvidia/nemotron-3.5-content-safety:free`): campo propio de moderación (es clasificador, no chat).

## 4. Cómo se procesa

1. El LLM no "mira" logs crudos (agotaría la ventana de contexto). Un **resumidor/indexador** convierte eventos crudos en resúmenes + embeddings, guardados en vector store OSS (Qdrant o Chroma).
2. El LLM invoca tools bajo demanda (`query_events`, `get_process_tree`, etc.).
3. El código ejecuta la tool y devuelve el resultado como `role: "tool"`.
4. Cuando ocurre un alert de alta severidad, el sistema **empuja proactivamente** un mensaje al chat.
5. Toda acción de remediación que el LLM quiera ejecutar pasa por el motor de respuesta / switch de autonomía.

## 5. Cómo se validan respuestas

- **Validar `tool_calls` antes de ejecutar funciones** (evita inyección de prompt que invoque herramientas peligrosas) — Doc 3, buena práctica 5.
- **No confiar ciegamente en modelos `:free`** para decisiones críticas; réplica con modelo de pago — Doc 3, buena práctica 7.
- **Validar IOC/alertas contra fuentes reales** (VirusTotal, CVE, MISP); el modelo no es fuente de verdad — Doc 4.

## 6. Errores contemplados

- Excepción de cualquier proveedor en `call_with_failover` → se prueba el siguiente.
- Todos los proveedores fallan → `RuntimeError("Los tres proveedores fallaron")`.
- `400` con `reasoning` (modelo no acepta) → quitar parámetro o usar `include_reasoning`.
- `content` vacío en `:free` razonamiento → leer `message.reasoning`.
- `401` (falta key en pago) / `429` (límite anónimo 200 req/h IP).
- Alucinaciones en IOC → validar contra fuentes reales.
- Latencia alta (`kilo-auto/free` ~11s) → usar modelo fijo.

## 7. Estados de la integración

| Estado | Descripción |
|---|---|
| OBSERVE | IA solo lectura; no ejecuta acciones |
| SUGGEST | IA propone; usuario confirma acción por acción |
| SEMI-AUTO | Categorías de bajo riesgo pre-autorizadas |
| FULL-AUTO | Automatización máxima en playbooks (solo lab) |
| Failover activo | Un proveedor cae → se usa el siguiente |
| Todos fallan | `RuntimeError` → degradación (ver manejo de errores) |
| Híbrido activo | Ambos canales (API Gateway + local) disponibles; remoto por defecto |
| Fallback Local | API Gateway caído/limitado → inferencia local degradada (ver `29-Arquitectura-IA-Hibrida.md`) |

## 8. Modelos gratuitos relevantes (Doc 1 / Doc 4)

- `tencent/hy3:free` (256k, tools, `content` limpio): chat general, código, razonamiento.
- `nvidia/nemotron-3-ultra-550b-a55b:free` / `nemotron-3-super-120b-a12b:free` (1M): logs largos.
- `cohere/north-mini-code:free` (256k): código; único `:free` `is_moderated: true`.
- `kilo-auto/free` / `openrouter/free`: routers automáticos (leen `message.reasoning`).
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`: único que acepta audio+imagen+video.
- `nvidia/nemotron-3.5-content-safety:free`: clasificador de seguridad (no chat).

> **Información no especificada en la documentación original.** No se especifica un modelo por defecto obligatorio para ARGOS, ni esquema de reintentos/backoff, ni política de cache de embeddings.
