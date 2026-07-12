---
título: 13 - Manejo de Errores
objetivo: Documentar todos los errores posibles, clasificados por origen, tratamiento, respuesta y recuperación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1,6,7; Docs/KiloGateway 02,03,04.
dependencias: 08-API-Gateway.md; 09-Integracion-IA.md.
referencias: 12-Seguridad.md; 19-Casos-Error.md.
---

# 13 - Manejo de Errores

## Clasificación por origen

### A. Errores de transporte / conectividad (agente ↔ cerebro)
- **Origen:** caída de conexión del agente con el cerebro central.
- **Tratamiento:** Fail-safe, no fail-open. El agente sigue coleccionando y bufferea local (SQLite embebido sugerido) y reenvía al reconectar. Nunca se queda "ciego" ni actúa solo.
- **Respuesta/Recuperación:** buffer local + reenvío automático al reconectar.

### B. Errores de API Gateway / LLM
| Error | Origen | Tratamiento | Respuesta |
|---|---|---|---|
| `401` | Falta key en modelo de pago | Agregar `Authorization: Bearer <key>` | Reintentar con auth |
| `400` con `reasoning` | Modelo no acepta parámetro | Quitar `reasoning` o usar `include_reasoning` | Ajustar request |
| `content` vacío en `:free` | Es modelo reasoning | Leer `message.reasoning` | Mostrar `reasoning` |
| `429` anónimo | >200 req/h IP | Usar API key o esperar | Backoff por cuota |
| Respuesta lenta (kilo-auto ~11s) | Router elige modelo | Usar modelo fijo | Latencia predecible |
| Excepción de proveedor | Caída/límite/deprecación | `call_with_failover` prueba el siguiente | Failover |
| Todos fallan | 3 proveedores caídos | `raise RuntimeError("Los tres proveedores fallaron")` | Degradación controlada |

### C. Errores de tool calling / inyección
- **Origen:** `tool_calls` peligrosos por inyección de prompt.
- **Tratamiento:** validar `tool_calls` antes de ejecutar funciones.
- **Respuesta:** rechazar ejecución de herramientas no autorizadas.

### D. Errores de calidad de IA (alucinaciones)
- **Origen:** modelo inventa IOCs/hashes/IPs.
- **Tratamiento:** validar contra fuentes reales (VirusTotal, CVE, MISP). El modelo no es fuente de verdad.
- **Respuesta:** no actuar sobre IOC no verificado.

### E. Errores de confidencialidad
- **Origen:** envío de datos sensibles a `:free` (todos entrenan con prompts).
- **Tratamiento:** nunca enviar secretos; anonymizar/hashear; usar BYOK/pago para confidencialidad.
- **Respuesta:** rechazar/enviar dato ofuscado.

### F. Errores de acción de remediación no autorizada
- **Origen:** IA intenta ejecutar acción sin pasar por switch.
- **Tratamiento:** el switch de autonomía bloquea ejecución fuera de policy.
- **Respuesta:** acción no ejecutada; registrada en auditoría.

## Recuperación general

- Failover automático entre Cerebras/Groq/OpenRouter (cambio de `base_url`).
- Buffer local del agente ante pérdida de conexión.
- Auditoría inmutable de toda acción (propiedad forense tras incidente).
