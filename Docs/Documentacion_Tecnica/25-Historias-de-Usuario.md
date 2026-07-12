---
título: 25 - Historias de Usuario
objetivo: Derivar las historias de usuario (épicas + stories) del sistema ARGOS a partir de los requisitos funcionales, casos de uso y principios documentados. Sin código.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 1-13; Docs/KiloGateway 01-04; 02-Requisitos-Funcionales.md; 18-Casos-Uso.md.
dependencias: 02-Requisitos-Funcionales.md; 26-Criterios-de-Aceptacion.md.
referencias: 27-Flujos-de-Datos.md; 28-Especificacion-Diseno-Modulos.md.
---

# 25 - Historias de Usuario

Personas (derivadas de la documentación):
- **Dueño del dispositivo / Usuario final**: persona que instala ARGOS en sus propios equipos.
- **Analista SOC (usuario senior)**: quien consulta, investiga y autoriza acciones.
- **Administrador del sistema (Owner)**: quien define policies, niveles del switch y retención.

Formato: *Como [rol], quiero [capacidad], para [beneficio].*

## Épica 1 — Observabilidad y telemetría (Módulo A/B)

- **US-A1:** Como dueño de un endpoint Windows, quiero que ARGOS capture eventos de kernel, proceso, red, filesystem e identidad, para tener visibilidad total del comportamiento.
- **US-A2:** Como dueño de un endpoint Linux, quiero telemetría vía auditd + eBPF, para captura de kernel sin overhead excesivo.
- **US-A3:** Como dueño de un endpoint macOS, quiero telemetría vía Endpoint Security Framework, para captura nativa autorizada.
- **US-A4:** Como dueño de un dispositivo Android, quiero telemetría de red vía VpnService y uso vía UsageStatsManager, para visibilidad sin root.
- **US-A5:** Como analista, quiero que todos los eventos se emitan en esquema común OCSF, para correlacionar fuentes dispares.
- **US-A6:** Como analista, quiero que el agente bufferee localmente (SQLite) si se cae la conexión y reenvíe al reconectar, para no perder telemetría ni quedar ciego (Fail-safe).
- **US-A7:** Como analista, quiero transporte mTLS agente↔collector, para confidencialidad e integridad.

## Épica 2 — Almacenamiento y detección (Módulos C/D/E)

- **US-D1:** Como analista, quiero búsqueda full-text de eventos, para investigación ad-hoc.
- **US-D2:** Como analista, quiero series temporales de eventos, para dashboards y anomalías.
- **US-D3:** Como analista, quiero retención de al menos 90 días en caliente, para investigación activa.
- **US-E1:** Como analista, quiero evaluar reglas Sigma importadas (SigmaHQ) + propias, para detección portable.
- **US-E2:** Como analista, quiero evaluar reglas YARA sobre archivos/memoria, para detectar patrones.
- **US-E3:** Como analista, quiero correlación + baseline de comportamiento, para detectar lo que no tiene firma.
- **US-E4:** Como analista, quiero mapeo de cobertura a MITRE ATT&CK, para ver puntos ciegos.
- **US-E5:** Como analista, quiero enriquecer con threat intel gratuita (OTX, abuse.ch, MISP), para contexto de IOCs.

## Épica 3 — Capa de IA y chat (Módulo F)

- **US-F1:** Como analista, quiero consultar en lenguaje natural ("¿qué pasa ahora?"), para obtener estado sin queries manuales.
- **US-F2:** Como analista, quiero que la IA invoque tools (`query_events`, `get_process_tree`, `get_active_connections`, `list_alerts`, `lookup_ioc`, `explain_attck_technique`), para respuestas basadas en datos reales.
- **US-F3:** Como analista, quiero que ante una alerta de alta severidad la IA empuje un mensaje proactivamente, para no esperar a preguntar.
- **US-F4:** Como analista, quiero que la IA proponga acciones pero nunca las ejecute directamente, para mantener el control humano.
- **US-F5:** Como analista, quiero que la IA no "mire" logs crudos sino resúmenes+embeddings, para no agotar la ventana de contexto.
- **US-F6:** Como analista, quiero fallover automático entre proveedores de IA, para disponibilidad continua.

## Épica 4 — Respuesta y switch de autonomía (Módulo G)

- **US-G1:** Como administrador, quiero 4 niveles de switch (OBSERVE/SUGGEST/SEMI-AUTO/FULL-AUTO), para controlar la autonomía.
- **US-G2:** Como administrador, quiero catálogo de acciones (matar proceso, aislar host, bloquear IP, cuarentena archivo, revertir registro, deshabilitar cuenta, snapshot memoria), para responder a incidentes.
- **US-G3:** Como administrador, quiero que en SUGGEST cada acción requiera mi confirmación explícita, para uso diario seguro.
- **US-G4:** Como administrador, quiero pre-autorizar categorías de bajo riesgo en SEMI-AUTO, para automatizar lo seguro.
- **US-G5:** Como administrador, quiero que FULL-AUTO quede restringido a lab/testing, para no usarlo en producción personal.
- **US-G6:** Como administrador, quiero auditoría inmutable (append-only + hash-chaining) de toda acción propuesta/aprobada/ejecutada, para trazabilidad forense.

## Épica 5 — Chat UI y dashboard (Módulo H)

- **US-H1:** Como analista, quiero chat WebSocket bidireccional en tiempo real, para interacción viva.
- **US-H2:** Como analista, quiero que los eventos nuevos se empujen por el mismo canal (o SSE) sin refrescar, para estar siempre al día.
- **US-H3:** Como analista, quiero sesión de contexto por host/incidente, para conversaciones enfocadas.
- **US-H4:** Como analista, quiero que "aislá el host X" dispare confirmación según el nivel del switch, para evitar acciones no deseadas.

## Épica 6 — Metodología y cumplimiento (Módulos I)

- **US-I1:** Como analista, quiero un loop de detection engineering (hipótesis→regla→test→tuning→deploy) con medición de falsos positivos, para calidad de detección.
- **US-I2:** Como analista, quiero threat hunting activo basado en técnicas ATT&CK no cubiertas, para no esperar alertas.
- **US-I3:** Como administrador, quiero runbooks de IR (contención→erradicación→recuperación→lecciones), para respuesta ordenada.
- **US-I4:** Como administrador, quiero ejercicios purple team (Atomic Red Team, CALDERA) solo contra mi lab propio, para validar detecciones.
- **US-I5:** Como dueño, quiero que ARGOS solo monitoree dispositivos propios/autorizados, para cumplir el marco legal.

> **Información no especificada en la documentación original.** No se documentan historias de usuario formales en la base; las anteriores se derivan de los RF, casos de uso y principios. No se especifican roles/RBAC internos, ni perfiles de privilegio del agente más allá de "mínimos privilegios necesarios".
