---
título: 04 - Arquitectura
objetivo: Documentar completamente los componentes, capas, responsabilidades, dependencias, flujos, interacciones, ciclo de vida, inicialización y apagado del sistema.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 2,6,7,8,12; Docs/KiloGateway 01-04.
dependencias: 01-Resumen-Ejecutivo.md; 05-Arquitectura-Carpetas.md; 06-Arquitectura-Codigo.md; 17-Diagramas.md.
referencias: 07-Flujo-General.md; 08-API-Gateway.md; 09-Integracion-IA.md.
---

# 04 - Arquitectura

## 1. Componentes y capas

La arquitectura se describe como una cadena de arriba a abajo (A→H). Cada letra es un componente con responsabilidad explícita.

| ID | Componente | Capa | Responsabilidad |
|---|---|---|---|
| A | Agentes de endpoint (sensors) | Captura | Binario nativo por SO, mínimos privilegios, emite eventos en esquema común OCSF |
| B | Transporte seguro | Transporte | mTLS agente↔collector; buffer local (SQLite) si cae; gRPC o NATS/MQTT sobre TLS |
| C | Collector / event bus | Ingesta | Recibe, normaliza, enruta (Vector.dev o Fluent Bit) |
| D | Almacenamiento | Datos | OpenSearch (full-text + series temporales) o ClickHouse a escala |
| E | Motor de detección | Detección | Sigma + YARA + correlación + baseline de comportamiento |
| F | Capa de IA (cerebro) | Inteligencia | LLM con function calling sobre el store de eventos (vía API Gateway + modelo local GGUF en modo híbrido, Opción C) |
| G | Motor de respuesta (SOAR ligero) | Respuesta | Catálogo de acciones gateado por switch de autonomía |
| H | Chat + dashboard | Presentación | WebSocket bidireccional entre UI y backend |

## 2. Responsabilidades por componente

- **A (sensors):** uno por SO. Windows: ETW + Sysmon + Event Log + PowerShell + AMSI. Linux: auditd + eBPF. macOS: ESF + Unified Logging + FSEvents. Android: VpnService + UsageStatsManager + NetworkStatsManager (+ MDM).
- **B (transporte):** asegura confidencialidad/integridad (mTLS) y continuidad (buffer local).
- **C (collector):** normaliza a OCSF y enruta a almacenamiento/detección.
- **D (storage):** dos patrones de acceso — full-text (investigación) y series temporales (dashboards/anomalías).
- **E (detección):** reglas portables (Sigma), escaneo por patrones (YARA), correlación y baseline; mapeo ATT&CK.
- **F (IA):** resumidor/indexador → vector store; tools bajo demanda; push proactivo de alertas; propuesta de acciones.
- **G (respuesta):** catálogo de acciones de riesgo creciente, todo auditado e inmutable.
- **H (chat/dashboard):** WebSocket bidireccional, sesión de contexto por host/incidente, push de eventos (o SSE).

## 3. Dependencias entre componentes

- B depende de A (recibe sus eventos).
- C depende de B (transporta eventos).
- D y E dependen de C (almacenamiento y detección consumen eventos normalizados).
- F depende de D (lee eventos vía tools) y de la **API Gateway** (salida externa para el LLM remoto); en modo híbrido (Opción C) también usa un **modelo local GGUF** (Qwen2.5-0.5B-Instruct-GGUF) como fallback/privacy-guard, sin salida de red. Ver `29-Arquitectura-IA-Hibrida.md`.
- G depende de F (recibe propuestas) y del switch de autonomía (autorización del usuario).
- H depende de F (chat) y de D/E (dashboards, eventos en vivo).

## 4. Flujos e interacciones

Ver `07-Flujo-General.md` y `17-Diagramas.md`. Resumen:

1. Captura (A) → Transporte (B) → Collector (C) → Almacenamiento (D) + Detección (E).
2. Detección (E) genera alertas → IA (F) empuja al chat (H) y/o propone acción a Respuesta (G).
3. Respuesta (G) ejecuta solo si el switch de autonomía lo autoriza; audita en log inmutable.

## 5. Ciclo de vida

> **Información no especificada en la documentación original.** No se documentan explícitamente secuencias de inicialización ni apagado de los componentes A-H, ni orden de arranque/cierre. Lo inferible de la arquitectura:
> - El agente (A) inicia recolectando y buffereando si el cerebro no está disponible (Fail-safe).
> - La IA (F) consume vía API Gateway; si los tres proveedores fallan, se lanza error (ver `09-Integracion-IA.md`, `call_with_failover` → `RuntimeError("Los tres proveedores fallaron")`).

## 6. Inicialización

> **Información no especificada en la documentación original.** No se especifican procedimientos de arranque, healthchecks ni secuencia de orden de los servicios.

## 7. Apagado

> **Información no especificada en la documentación original.** No se especifica procedimiento de apagado, graceful shutdown ni flush del buffer local.
