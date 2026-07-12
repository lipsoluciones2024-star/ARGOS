---
título: 14 - Logging
objetivo: Documentar qué se registra, qué no, niveles, formato, ubicación y rotación, según la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,7,13; Docs/KiloGateway 02.
dependencias: 12-Seguridad.md; 13-Manejo-Errores.md.
referencias: 15-Persistencia.md.
---

# 14 - Logging

## Qué se registra

- **Eventos de telemetría** de cada SO (proceso, red, filesystem, kernel, identidad) en esquema común OCSF.
- **Toda acción de remediación** (autorizada o no): quién/qué la propuso, quién la aprobó, timestamp, resultado (sección 7).
- **Alertas de detección** (reglas Sigma/YARA, correlación, baseline).
- **Trazabilidad de API Gateway** (opcional): `X-KiloCode-TaskId`, `X-KiloCode-Version`, `x-kilocode-mode`.

## Qué NO se registra (explícitamente)

> **Información no especificada en la documentación original.** No se documenta qué no se debe registrar, salvo la recomendación de definir política ante captura sin querer de datos sensibles (credenciales en línea de comandos, sección 13).

## Niveles

- El documento no define niveles de log (DEBUG/INFO/WARN/ERROR) para ARGOS.
- En detección se referencia `level: high` (regla Sigma "PowerShell Encoded Command") y `priority: WARNING` (regla Falco "Terminal shell in container") como niveles de las reglas.
- En el switch, las alertas de "alta severidad" disparan push proactivo al chat.

## Formato

- Esquema común **OCSF** para eventos.
- **Log de auditoría append-only con hash-chaining estilo Merkle** (para detectar tampering e inmutabilidad).
- Trazabilidad de API vía headers.

## Ubicación

- Buffer local del agente (SQLite embebido sugerido) si se cae la conexión.
- Almacenamiento central: OpenSearch (o ClickHouse).
- Audit-log: `response-engine/audit-log/` (según estructura de repo).

## Rotación

> **Información no especificada en la documentación original.** No se especifica rotación de logs. Solo se indica retención: mínimo 90 días en caliente para investigación, más tiempo en frío para forense (sección 10).
