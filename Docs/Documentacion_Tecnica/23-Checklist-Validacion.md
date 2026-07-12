---
título: 23 - Checklist de Validación
objetivo: Listar lo necesario para comprobar que la implementación cumple exactamente con la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1-13; Docs/KiloGateway 01-04.
dependencias: 02-Requisitos-Funcionales.md; 03-Requisitos-No-Funcionales.md.
referencias: 22-Checklist-Desarrollo.md.
---

# 23 - Checklist de Validación

Marque cada ítem al verificarlo contra la documentación base.

## Principios (sección 1)
- [ ] No es antivirus; es Full Endpoint Observability.
- [ ] Human-in-the-loop: ninguna remediación sin switch de autonomía.
- [ ] 100% free & open source (licencias válidas).
- [ ] Agente nativo por SO (no wrapper Electron).
- [ ] IA = copiloto (lectura vía function calling; ejecución gobernada).
- [ ] Detección por comportamiento + MITRE ATT&CK.
- [ ] Eventos auditables e inmutables (hash-chaining Merkle).
- [ ] Fail-safe, no fail-open (buffer local si cae conexión).

## Requisitos funcionales (ver `02`)
- [ ] Agentes por SO capturan telemetría documentada (ETW/Sysmon/Linux/macOS/Android).
- [ ] Eventos en esquema OCSF.
- [ ] mTLS + buffer local (SQLite).
- [ ] Collector normaliza/enruta (Vector.dev/Fluent Bit).
- [ ] Almacenamiento full-text + series temporales (OpenSearch/ClickHouse).
- [ ] Motor de detección: Sigma + YARA + baseline + ATT&CK + threat intel.
- [ ] Capa de IA: resumidor→vector store; 6 tools; push proactivo; propone solo.
- [ ] Switch de 4 niveles + catálogo de 7 acciones + auditoría inmutable.
- [ ] Chat WebSocket + dashboard + push de eventos.

## Requisitos no funcionales (ver `03`)
- [ ] mTLS transporte.
- [ ] Inmutabilidad de auditoría.
- [ ] Failover IA (Cerebras/Groq/OpenRouter).
- [ ] Límites API (200 req/h IP anónimo; timeout 30s).
- [ ] No enviar secretos a `:free`.

## API Gateway (ver `08`)
- [ ] Base URL `https://api.kilo.ai/api/gateway`.
- [ ] `GET /v1/models` y `POST /chat/completions`.
- [ ] Auth: `:free` sin Authorization; pago con Bearer.
- [ ] Tool calling, streaming SSE, FIM (Codestral), MCP vía puente.
- [ ] Manejo de `401/400/429`, `content` vacío → `reasoning`.
- [ ] Confirmar conflicto Doc3/Doc4: todos los `:free` entrenan con prompts.

## Integración IA (ver `09`)
- [ ] Router de failover con 3 proveedores y `RuntimeError` si todos fallan.
- [ ] Validación de `tool_calls` antes de ejecutar.
- [ ] Validación de IOCs contra fuentes reales.

## Seguridad y legal (ver `12`)
- [ ] Switch bloquea ejecución no autorizada.
- [ ] API key por variable de entorno, no hardcodeada.
- [ ] Retención 90 días en caliente.
- [ ] Alcance legal: solo dispositivos propios/autorizados; purple team solo en lab.

## Restricción de AGENTS.md
- [ ] Todo lo anterior proviene de la documentación base; nada inventado.
- [ ] Lo no especificado está marcado como "Información no especificada en la documentación original".
