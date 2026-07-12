---
título: 12 - Seguridad
objetivo: Documentar completamente autenticación, autorización, validaciones, manejo seguro de credenciales, almacenamiento, protección de datos, logs y errores, según la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,7,13; Docs/KiloGateway 03,04.
dependencias: 08-API-Gateway.md; 03-Requisitos-No-Funcionales.md.
referencias: 09-Integracion-IA.md; 13-Manejo-Errores.md.
---

# 12 - Seguridad

## 1. Autenticación

### API Gateway
- Modelos `:free`: acceso anónimo, **sin Authorization** (limitado a 200 req/h por IP).
- Modelos de pago: `Authorization: Bearer <KILO_API_KEY>`.
- Organization token: `X-KiloCode-OrganizationId` (expira 15 min).
- BYOK: tus keys de proveedor, facturación directa, sin markup.

### Sistema ARGOS
- **Switch de autonomía:** mecanismo de autorización central. Ninguna acción de remediación (matar proceso, aislar host, bloquear IP, deshabilitar cuenta) se ejecuta sin pasar por él.
- **Human-in-the-loop:** la IA solo propone; la ejecución está gobernada por policy + switch.

## 2. Autorización (niveles del switch)

| Nivel | Capacidad | Uso |
|---|---|---|
| 🔴 OBSERVE (default) | Solo lectura | Siempre por defecto |
| 🟡 SUGGEST | Propone y requiere confirmación explícita | Uso diario |
| 🟢 SEMI-AUTO | Pre-autoriza categorías de bajo riesgo | Confianza media |
| ⚫ FULL-AUTO | Máxima automatización en playbooks | Solo lab/testing |

## 3. Validaciones

- **Validar `tool_calls` antes de ejecutar funciones** (evita inyección de prompt que invoque herramientas peligrosas) — Doc 3 BP5.
- **Validar IOCs/alertas contra fuentes reales** (VirusTotal, CVE, MISP) — Doc 4.
- **No confiar ciegamente en `:free`** para decisiones críticas — Doc 3 BP7.

## 4. Manejo seguro de credenciales

- No hardcodear la API key; usar variable de entorno `KILO_API_KEY` — Doc 3 BP1.
- Nunca exponer la API key en frontend; usar proxy/backend o BYOK — Doc 3 BP/§4.
- Organization tokens para equipos (expiración 15 min, políticas centralizadas) — Doc 3 BP4.

## 5. Almacenamiento y protección de datos

- mTLS entre agente y collector (transporte seguro).
- Eventos auditables e inmutables: write-once log, idealmente hash-chaining estilo Merkle para detectar tampering (sección 1.7).
- Log de auditoría append-only con hash-chaining para que un atacante que compromete el endpoint no pueda editar su historial (sección 7).
- **Datos sensibles:** definir política de retención (recomendado 90 días en caliente) y qué hacer si se capturan sin querer datos sensibles (credenciales en línea de comandos) — sección 13.

## 6. Protección de datos al enviar a la IA

- **Todos los 11 `:free` tienen `mayTrainOnYourPrompts: true`** (Doc 4, verificado 2026-07-11). NO enviar secretos reales, hashes de producción, tokens, claves ni datos de vulnerabilidades activas a modelos gratuitos.
- Usar datos ofuscados / sintéticos / ejemplos para análisis con `:free`.
- Para trabajo real con confidencialidad: API key propia (BYOK) o modelos de pago con `mayTrainOnYourPrompts: false`.
- Anonymizar/hashear IPs, hostnames y patrones de red antes de enviar al LLM en free tier que entrena.
- `cohere/north-mini-code:free` es el único `:free` `is_moderated: true`.
- **Modo híbrido (Opción C):** el modelo local GGUF (Qwen2.5-0.5B-Instruct-GGUF) corre en la máquina **sin red** y no entrena con prompts; sirve como privacy-guard / fallback offline. El servidor local debe escuchar solo en loopback (`127.0.0.1`). Ver `29-Arquitectura-IA-Hibrida.md`.

## 7. Logs y errores

- Toda acción (autorizada o no) se audita: quién/qué propuso, quién aprobó, timestamp, resultado.
- Ver `14-Logging.md` y `13-Manejo-Errores.md`.

## 8. Consideraciones legales (sección 13)

- ARGOS solo monitorea/actúa sobre dispositivos propios o con autorización explícita.
- Android Accessibility Service sin consentimiento informado = spyware técnico.
- Ejercicios purple team solo contra sistemas de laboratorio propios.
- Cumplir legislación de privacidad aplicable en contexto laboral.

> **Información no especificada en la documentación original.** No se especifican mecanismos de cifrado en reposo, gestión de secretos local (vault), ni roles/RBAC dentro de la propia aplicación ARGOS.
