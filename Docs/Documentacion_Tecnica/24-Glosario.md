---
título: 24 - Glosario Técnico
objetivo: Definir todos los términos, siglas y conceptos utilizados en la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md`; Docs/KiloGateway 01-04.
dependencias: 21-Dependencias.md.
referencias: 01-Resumen-Ejecutivo.md.
---

# 24 - Glosario Técnico

| Término | Definición (según documentación) |
|---|---|
| **ARGOS** | Sistema Agéntico de Observabilidad Total y Ciberdefensa Autónoma Multiplataforma. Codename sugerido (reemplazable). |
| **Full Endpoint Observability** | Visibilidad total de comportamiento (proceso, red, filesystem, kernel, memoria, identidad) + correlación + IA. |
| **OCSF** | Open Cybersecurity Schema Framework; estándar abierto de formato de eventos. |
| **mTLS** | Mutual TLS; transporte seguro agente↔collector. |
| **ETW** | Event Tracing for Windows; fuente de kernel en Windows. |
| **Sysmon** | Sysinternals; base de EDR gratuito en Windows. |
| **AMSI** | Antimalware Scan Interface; hook para inspeccionar scripts. |
| **auditd** | Linux Audit Framework; syscall auditing. |
| **eBPF** | Tecnología de telemetría de kernel en Linux sin overhead de auditd. |
| **Falco/Tracee/Tetragon** | Proyectos eBPF de referencia. |
| **ESF** | Endpoint Security Framework (macOS); reemplazó Kauth/OpenBSM. |
| **FSEvents** | Monitoreo de filesystem a bajo costo en macOS. |
| **TCC.db** | Base de permisos de cámara/micrófono/accesibilidad en macOS. |
| **launchd** | Sistema de persistencia #1 en macOS (LaunchAgents/LaunchDaemons). |
| **VpnService API** | Inspección de red por app en Android sin root. |
| **UsageStatsManager / NetworkStatsManager** | Uso de apps / consumo de datos por app en Android. |
| **Accessibility Service API** | API sensible en Android; vector de spyware si se abusa. |
| **MDM / Device Owner** | Gestión de dispositivos Android empresariales. |
| **Sigma** | Formato genérico de reglas de detección. |
| **YARA** | Escaneo de archivos/memoria por patrones. |
| **SigmaHQ** | Repositorio de reglas Sigma públicas. |
| **MITRE ATT&CK** | Matriz de tácticas/técnicas de adversario. |
| **Threat Intel** | AlienVault OTX, abuse.ch (URLhaus, MalwareBazaar, ThreatFox), MISP. |
| **Vector store** | Qdrant o Chroma; guarda embeddings para RAG. |
| **Function calling / Tools** | Herramientas que el LLM invoca (query_events, get_process_tree, etc.). |
| **Switch de autonomía** | Mecanismo de 4 niveles que autoriza acciones de remediación. |
| **OBSERVE / SUGGEST / SEMI-AUTO / FULL-AUTO** | Niveles del switch. |
| **SOAR ligero** | Motor de respuesta con catálogo de acciones. |
| **Hash-chaining (Merkle)** | Log append-only inmutable para auditoría. |
| **Fail-safe, no fail-open** | El agente bufferea y nunca actúa solo si pierde conexión. |
| **Kilo AI Gateway** | API compatible OpenAI que unifica modelos bajo un endpoint. |
| **`:free`** | Modelos gratuitos sin API key (200 req/h IP). Todos entrenan con prompts (Doc 4). |
| **BYOK** | Bring Your Own Key; tus keys de proveedor, sin markup. |
| **FIM** | Fill-in-the-middle; autocompletado de código (Codestral). |
| **MCP** | Model Context Protocol; requiere cliente puente al array `tools`. |
| **Reasoning models** | Modelos cuya respuesta final está en `message.reasoning`. |
| **Atomic Red Team / CALDERA** | Herramientas de purple team/simulación. |
| **RAG** | Retrieval-Augmented Generation (resúmenes+embeddings). |
| **Purple team** | Ejercicios de emulación de adversarios contra lab propio. |
