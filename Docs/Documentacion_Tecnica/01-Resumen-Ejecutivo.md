---
título: 01 - Resumen Ejecutivo
objetivo: Describir completamente el proyecto ARGOS, sus objetivos, alcance, limitaciones, dependencias y arquitectura general, según la documentación base.
alcance: Documento raíz `ARGOS_documento_maestro_arquitectura.md` (secciones 0-14) y documentación de Kilo AI Gateway (`Docs/KiloGateway/01-04`).
dependencias: ARGOS_documento_maestro_arquitectura.md; Docs/KiloGateway/01-modelos-y-estado.md; Docs/KiloGateway/02-conexion-y-uso.md; Docs/KiloGateway/03-seguridad-y-parametros.md; Docs/KiloGateway/04-ciberseguridad-multimodal.md.
referencias: 04-Arquitectura.md; 21-Dependencias.md; 24-Glosario.md.
---

# 01 - Resumen Ejecutivo

## 1. Descripción completa del proyecto

ARGOS es un **Sistema Agéntico de Observabilidad Total y Ciberdefensa Autónoma Multiplataforma**. No es un antivirus: es una plataforma de **Full Endpoint Observability**.

Componentes definidos en la documentación base:

- **Agente nativo por sistema operativo** que capta lo que pasa a nivel de kernel, proceso, red, filesystem e identidad.
- **Backend** que normaliza y correlaciona eventos contra un motor de detección basado en comportamiento (no solo firmas).
- **Capa de IA** que se consulta en lenguaje natural, en tiempo real ("¿qué está pasando ahora?", "¿quién me está atacando?", "¿qué hizo este proceso?") con el nivel de respuesta de un analista SOC senior.

La pieza diferenciadora (contrato de diseño no negociable): **ningún componente ejecuta una acción de remediación sin pasar por un switch de autonomía que el usuario controla**. La IA observa, correlaciona y propone; el usuario autoriza.

## 2. Objetivos

- Visibilidad total de comportamiento (proceso, red, filesystem, kernel, memoria, identidad) + correlación + IA razonando sobre el contexto en tiempo real.
- Detección basada en comportamiento y mapeada a **MITRE ATT&CK**, no solo firmas.
- Human-in-the-loop por diseño mediante un switch de autonomía de 4 niveles.
- 100% free & open source.
- Multiplataforma real (Windows / Linux / macOS / Android), con un agente nativo por SO.
- Auditabilidad e inmutabilidad de todo evento (write-once log con hash-chaining estilo Merkle).
- Fail-safe, no fail-open: si se pierde conexión con el "cerebro", el agente sigue recolectando y bufferea local.

## 3. Alcance

- Desarrollo e **ejecución completamente local** (según directiva de `AGENTS.md`).
- La **única comunicación externa permitida** es mediante la **API Gateway** (Kilo AI Gateway) ya definida en la documentación, por donde se consume la IA.
- Toda la lógica restante ocurre localmente.
- No se agregan microservicios, servidores adicionales ni bases de datos adicionales fuera de lo documentado.

## 4. Limitaciones

- Para Android sin root no existe equivalencia a `auditd`; las fuentes son `VpnService API`, `UsageStatsManager`, `NetworkStatsManager`, `Accessibility Service API` (sensible, requiere consentimiento) y `Device Owner / Android Enterprise (MDM)`. El modo laboratorio requiere root (Frida, Magisk, `logcat`, `dumpsys`).
- Los proveedores gratuitos de LLM pueden cambiar límites o deprecar modelos sin aviso (según lo investigado en la documentación).
- En free tier de algunos LLMs (Google Gemini Flash, según sección 6.2) el proveedor puede usar prompts para entrenar; se recomienda anonymizar telemetría.
- **Conflicto de fuentes documentado:** `Doc 3` indica que varios `:free` son `mayTrainOnYourPrompts: false`; `Doc 4` (verificado en vivo 2026-07-11) corrige que **todos los 11 `:free` son `mayTrainOnYourPrompts: true`**. Criterio aplicable: no enviar datos sensibles a ningún modelo gratuito.

> **Información no especificada en la documentación original.**
> - No se especifica un nombre de producto final definitivo (se usa "ARGOS" como sugerido, reemplazable).
> - No se especifican lenguajes de programación obligatorios para todo el sistema (solo se sugieren Rust/Go para el agente Windows, Swift para macOS, y se dan ejemplos en Python/Node.js para la capa IA).
> - No se especifica un modelo de despliegue exacto (la arquitectura describe componentes tipo collector/almacenamiento que en la práctica local pueden ejecutarse en la misma máquina).

## 5. Dependencias

- **Esquema de eventos:** OCSF (Open Cybersecurity Schema Framework).
- **Transporte:** mTLS entre agente y collector; buffer local (SQLite embebido sugerido); gRPC directo o NATS/MQTT sobre TLS.
- **Collector:** Vector.dev o Fluent Bit.
- **Almacenamiento:** OpenSearch (o ClickHouse a escala).
- **Motor de detección:** Sigma + YARA + SigmaHQ ruleset + baseline de comportamiento; threat intel (AlienVault OTX, abuse.ch, MISP).
- **Vector store:** Qdrant o Chroma.
- **IA / API Gateway:** Kilo AI Gateway (`https://api.kilo.ai/api/gateway`), compatible OpenAI.
- **Purple team:** Atomic Red Team, MITRE CALDERA.
- **DFIR complementario:** Velociraptor, osquery.

## 6. Arquitectura general

Cadena completa documentada (de arriba a abajo):

| Letra | Componente | Responsabilidad |
|---|---|---|
| A | Agentes de endpoint (sensors) | Binario nativo por SO, mínimos privilegios, emite eventos en esquema común (OCSF) |
| B | Transporte seguro | mTLS agente↔collector; buffer local si cae conexión; gRPC o NATS/MQTT sobre TLS |
| C | Collector / event bus central | Recibe, normaliza, enruta (Vector.dev o Fluent Bit) |
| D | Almacenamiento | OpenSearch (full-text + series temporales) o ClickHouse |
| E | Motor de detección | Sigma + YARA + correlación + baseline de comportamiento |
| F | Capa de IA (el cerebro) | LLM con function calling sobre el store de eventos |
| G | Motor de respuesta (SOAR ligero) | Catálogo de acciones gateado por el switch de autonomía |
| H | Chat en tiempo real + dashboard | WebSocket bidireccional |

Ver detalle en `04-Arquitectura.md` y diagramas en `17-Diagramas.md`.
