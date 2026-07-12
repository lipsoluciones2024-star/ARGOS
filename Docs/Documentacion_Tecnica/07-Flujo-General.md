---
título: 07 - Flujo General del Sistema
objetivo: Documentar todos los flujos del sistema desde el inicio hasta el cierre, con diagramas en Markdown.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 2,6,7,8; Docs/KiloGateway 02.
dependencias: 04-Arquitectura.md; 17-Diagramas.md.
referencias: 18-Casos-Uso.md; 19-Casos-Error.md.
---

# 07 - Flujo General del Sistema

## Flujo 1 — Ingesta y detección (telemetría)

```mermaid
flowchart TD
    A[Agente endpoint por SO] -->|eventos OCSF| B[Transporte mTLS + buffer local]
    B --> C[Collector: Vector.dev / Fluent Bit]
    C -->|normaliza| D[Almacenamiento: OpenSearch/ClickHouse]
    C -->|enruta| E[Motor de detección: Sigma+YARA+baseline]
    E -->|alertas| F[Capa de IA]
```

## Flujo 2 — Consulta en lenguaje natural (chat)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant H as Chat UI (WebSocket)
    participant F as Capa de IA (LLM)
    participant G as API Gateway
    participant D as Almacenamiento/Eventos
    U->>H: "¿qué está pasando ahora?"
    H->>F: mensaje
    F->>G: chat/completions (modelo)
    G-->>F: respuesta
    F->>D: query_events / get_process_tree (tool)
    D-->>F: resultados
    F-->>H: respuesta en lenguaje natural
    H-->>U: mensaje
```

## Flujo 3 — Alerta de alta severidad (push proactivo)

```mermaid
flowchart LR
    E[Motor de detección] -->|alerta alta| F[Capa de IA]
    F -->|empuja mensaje| H[Chat UI]
    F -->|propone acción| G2[Motor de respuesta]
    G2 -->|requiere autorización| S[Switch de autonomía]
    S -->|OBSERVE/SUGGEST| U[Usuario confirma]
    S -->|SEMI/FULL| X[Ejecuta acción]
```

## Flujo 4 — Ejecución de acción de remediación (switch de autonomía)

1. La IA propone una acción (ej. "aislá el host HOST-02").
2. El nivel del switch determina el comportamiento:
   - **OBSERVE:** solo lectura, no ejecuta.
   - **SUGGEST:** requiere confirmación explícita acción por acción.
   - **SEMI-AUTO:** categorías de bajo riesgo pre-autorizadas; el resto en SUGGEST.
   - **FULL-AUTO:** máxima automatización dentro de playbooks predefinidos (solo lab/testing).
3. La acción se audita (quién propuso, quién aprobó, timestamp, resultado) en log append-only con hash-chaining.

## Flujo 5 — Arranque (inferido de la arquitectura)

> **Información no especificada en la documentación original.** No se documenta secuencia de inicialización. Por el principio Fail-safe (sección 1.8), el agente inicia recolectando y buffereando localmente si el cerebro no está disponible.

## Flujo 6 — Cierre

> **Información no especificada en la documentación original.** No se documenta procedimiento de apagado.
