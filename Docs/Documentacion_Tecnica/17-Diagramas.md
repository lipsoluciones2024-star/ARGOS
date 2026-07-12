---
título: 17 - Diagramas
objetivo: Generar diagramas Mermaid para arquitectura general, flujo principal, secuencia, estados, dependencias, comunicación, inicialización, apagado e integración API.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 2,6,7,8; Docs/KiloGateway 02.
dependencias: 04-Arquitectura.md; 07-Flujo-General.md; 08-API-Gateway.md; 09-Integracion-IA.md.
referencias: 16-Estados-Sistema.md.
---

# 17 - Diagramas

## Arquitectura general
```mermaid
flowchart TD
    A[Agentes endpoint por SO] --> B[Transporte mTLS + buffer local]
    B --> C[Collector: Vector.dev / Fluent Bit]
    C --> D[Almacenamiento: OpenSearch / ClickHouse]
    C --> E[Motor detección: Sigma + YARA + baseline]
    D --> F[Capa de IA - LLM vía API Gateway]
    E --> F
    F -->|propuesta| G[Motor de respuesta + switch]
    G -->|WebSocket| H[Chat + dashboard]
    F -->|push alerta| H
```

## Flujo principal
```mermaid
flowchart LR
    Tele[Telemetría SO] --> Norm[Normalización OCSF]
    Norm --> Alm[Almacenar]
    Norm --> Det[Detectar]
    Det -->|alerta| IA[IA razona]
    IA -->|propone| Resp[Respuesta gateada por switch]
```

## Secuencia (chat + tool calling)
```mermaid
sequenceDiagram
    participant U as Usuario
    participant UI as Chat UI
    participant IA as LLM (API GW)
    participant EV as Eventos/Almacenamiento
    U->>UI: pregunta
    UI->>IA: messages
    IA->>IA: tool_calls (get_process_tree)
    IA->>EV: ejecuta tool
    EV-->>IA: resultado
    IA-->>UI: respuesta
    UI-->>U: mensaje
```

## Estados (switch de autonomía)
```mermaid
stateDiagram-v2
    [*] --> OBSERVE
    OBSERVE --> SUGGEST
    SUGGEST --> SEMI_AUTO
    SEMI_AUTO --> FULL_AUTO
    FULL_AUTO --> OBSERVE
    SEMI_AUTO --> OBSERVE
    SUGGEST --> OBSERVE
```

## Dependencias
```mermaid
graph TD
    ARGOS[ARGOS] --> APIGW[Kilo AI Gateway]
    ARGOS --> OCSF[OCSF]
    ARGOS --> VECTOR[Vector.dev/Fluent Bit]
    ARGOS --> STORE[OpenSearch/ClickHouse]
    ARGOS --> DETECT[Sigma/YARA/SigmaHQ]
    ARGOS --> VSTORE[Qdrant/Chroma]
    APIGW --> CERE[Cerebras]
    APIGW --> GROQ[Groq]
    APIGW --> OR[OpenRouter]
```

## Comunicación
```mermaid
flowchart LR
    A[Agente] -- mTLS --> C[Collector]
    C -- gRPC/NATS-TLS --> D[Storage]
    F[IA] -- HTTPS OpenAI-compatible --> APIGW[Kilo Gateway]
    H[UI] -- WebSocket --> F
```

## Inicialización
```mermaid
flowchart TD
    START([Inicio]) --> AG[Agente recolecta]
    AG --> BUF{¿Cerebro disponible?}
    BUF -- No --> LOCAL[Buffer local SQLite]
    BUF -- Sí --> NORM[Normalizar OCSF]
    NORM --> IA[IA en OBSERVE-only]
```

## Apagado
> **Información no especificada en la documentación original.** No se documenta procedimiento de apagado. Se deja diagrama placeholder.
```mermaid
flowchart TD
    STOP([Señal de apagado]) --> FLUSH{¿Buffer pendiente?}
    FLUSH -- Sí --> REENV[Reenviar]
    FLUSH -- No --> END([Fin])
```

## Integración API
```mermaid
sequenceDiagram
    participant C as Cliente ARGOS
    participant G as Kilo Gateway
    participant P as Proveedor (Cerebras/Groq/OR)
    C->>G: POST /chat/completions (model, messages, tools)
    G->>P: reenvía
    P-->>G: completion
    G-->>C: message.content / message.reasoning / tool_calls
```

## Arquitectura híbrida (Opción C, 2026-07-11)

> Extiende la integración con un **modelo local GGUF** (Qwen2.5-0.5B-Instruct-GGUF) que corre en la máquina sin salida de red. Ver `29-Arquitectura-IA-Hibrida.md` y `30-Descarga-Modelo-Local-Qwen25.md`.

```mermaid
flowchart TD
    C[Capa IA / Router híbrido] -->|por defecto| GW[Kilo AI Gateway]
    C -->|fallback / privacidad| LOC[(Local Runtime: Qwen2.5-0.5B GGUF)]
    GW --> CERE[Cerebras]
    GW --> GROQ[Groq]
    GW --> OR[OpenRouter]
    LOC -. sin red .- X[(loopback 127.0.0.1)]
```

## Arquitectura híbrida (Opción C, 2026-07-11)

> Extiende la integración con un **modelo local GGUF** (Qwen2.5-0.5B-Instruct-GGUF) que corre en la máquina sin salida de red. Ver `29-Arquitectura-IA-Hibrida.md` y `30-Descarga-Modelo-Local-Qwen25.md`.

```mermaid
flowchart TD
    C[Capa IA / Router híbrido] -->|por defecto| GW[Kilo AI Gateway]
    C -->|fallback / privacidad| LOC[(Local Runtime: Qwen2.5-0.5B GGUF)]
    GW --> CERE[Cerebras]
    GW --> GROQ[Groq]
    GW --> OR[OpenRouter]
    LOC -. sin red .- X[(loopback 127.0.0.1)]
```
