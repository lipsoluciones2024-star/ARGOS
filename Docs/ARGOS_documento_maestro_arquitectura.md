# ARGOS — Documento Maestro de Arquitectura
## Sistema Agéntico de Observabilidad Total y Ciberdefensa Autónoma Multiplataforma

**Versión:** 0.1 · Documento raíz — fundacional
**Fecha:** Julio 2026
**Owner:** Lucho
**Codename:** ARGOS (sugerido, reemplazable) — por Argos Panoptes, el gigante de cien ojos que nunca duerme

> Este es el documento raíz. Cada sección numerada es un módulo que puede convertirse en su propio deep-dive técnico. Al final (sección 14) están los próximos documentos sugeridos.

---

## Índice

0. Resumen ejecutivo
1. Principios de diseño (no negociables)
2. Arquitectura general
3. Telemetría por sistema operativo (Windows / Linux / macOS / Android)
4. Taxonomía de eventos (mapeo a MITRE ATT&CK)
5. Motor de detección
6. Capa de inteligencia artificial — el cerebro
7. Motor de respuesta y el switch de autonomía
8. Chat interactivo en tiempo real
9. Stack tecnológico recomendado (100% free/open source)
10. Metodología blue team integrada
11. Metodología purple team integrada
12. Roadmap de desarrollo sugerido + estructura de repo
13. Alcance y consideraciones legales
14. Próximos documentos sugeridos

---

## 0. Resumen ejecutivo

ARGOS no es un antivirus. Un antivirus busca firmas de malware conocido — es reactivo y ciego a todo lo que no haya visto antes. ARGOS es una plataforma de **Full Endpoint Observability**: un agente nativo por sistema operativo que capta lo que pasa a nivel de kernel, proceso, red, filesystem e identidad; un backend que normaliza y correlaciona esos eventos contra un motor de detección basado en comportamiento (no solo firmas); y una capa de IA que interrogás en lenguaje natural, en tiempo real — "¿qué está pasando ahora?", "¿quién me está atacando?", "¿qué hizo este proceso?" — con el nivel de respuesta de un analista SOC senior.

La pieza que lo hace *tuyo* y no un juguete peligroso: **ningún componente ejecuta una acción de remediación sin pasar por un switch de autonomía que vos controlás.** La IA observa, correlaciona y propone. Vos autorizás. Ese es el contrato de diseño no negociable de todo el proyecto — lo pediste vos mismo y es, además, la única forma responsable de construir algo así.

---

## 1. Principios de diseño (no negociables)

1. **No es antivirus, es Full Endpoint Observability.** Antivirus = firma de malware conocido. ARGOS = visibilidad total de comportamiento (proceso, red, filesystem, kernel, memoria, identidad) + correlación + una IA razonando sobre eso en contexto.
2. **Human-in-the-loop por diseño.** Ninguna acción de remediación (matar proceso, aislar host, bloquear IP, deshabilitar cuenta) se ejecuta sin pasar por el switch de autonomía (sección 7).
3. **100% free & open source.** Cada componente del stack tiene que tener licencia OSS real (Apache 2.0, MIT, GPL, AGPL) o un free tier genuinamente sostenible — no un trial de 14 días disfrazado de "gratis".
4. **Multiplataforma real, no "compatible".** Un agente nativo por SO, no un wrapper Electron intentando leer `/proc` en Windows.
5. **La IA es copiloto, no oráculo ciego.** El LLM tiene acceso de *lectura* completo al contexto en tiempo real vía function calling. Puede *proponer* acciones. La *ejecución* está gobernada por policy + el switch.
6. **Detección basada en comportamiento y MITRE ATT&CK**, no solo en firmas — así se detecta lo que todavía no tiene firma conocida.
7. **Todo evento es auditable e inmutable.** Un atacante que compromete el endpoint no debería poder borrar su propio rastro (write-once log, idealmente con hash-chaining tipo Merkle para detectar tampering).
8. **Fail-safe, no fail-open.** Si el agente pierde conexión con el cerebro central, sigue coleccionando y bufferea local — nunca se queda "ciego" ni, mucho menos, empieza a actuar solo por las dudas.

---

## 2. Arquitectura general

*(Ver el diagrama de arriba para la vista de alto nivel.)*

La cadena completa, de arriba a abajo:

**A. Agentes de endpoint (sensors)** — un binario nativo por SO, con los mínimos privilegios necesarios, que emite eventos en un esquema común. Recomendado adoptar **OCSF (Open Cybersecurity Schema Framework)** desde el día 1 — es el estándar abierto que ya usan AWS, Splunk y Palo Alto justamente para no reinventar el formato de eventos cada vez que agregás una fuente nueva.

**B. Transporte seguro** — mTLS entre agente y collector. Si se cae la conexión, el agente bufferea local (SQLite embebido, por ejemplo) y reenvía al reconectar. Para el bus de eventos: gRPC directo, o NATS/MQTT sobre TLS si querés pub/sub real.

**C. Collector / event bus central** — recibe, normaliza, enruta. Candidatos OSS maduros y con throughput real: **Vector.dev** (Rust, hecho justo para esto) o **Fluent Bit**.

**D. Almacenamiento** — necesitás dos patrones de acceso: búsqueda full-text para investigación ad-hoc, y series temporales para dashboards/anomalías. **OpenSearch** (fork libre de Elasticsearch bajo Apache 2.0) cubre ambos razonablemente para un despliegue personal. Si el volumen crece mucho, **ClickHouse** es más eficiente para eventos de alto volumen.

**E. Motor de detección** — reglas Sigma + YARA + correlación + baseline de comportamiento (sección 5).

**F. Capa de IA (el cerebro)** — LLM con function calling sobre el store de eventos (sección 6).

**G. Motor de respuesta (SOAR ligero)** — catálogo de acciones gateado por el switch de autonomía (sección 7).

**H. Chat en tiempo real + dashboard** — WebSocket bidireccional (sección 8).

---

## 3. Telemetría por sistema operativo

### 3.1 Windows

De la fuente más profunda a la más superficial:

- **ETW (Event Tracing for Windows)** — la fuente de kernel más rica que existe en Windows. Providers clave: `Microsoft-Windows-Kernel-Process`, `Microsoft-Windows-Kernel-File`, `Microsoft-Windows-Kernel-Network`, `Microsoft-Windows-Kernel-Registry`. El provider `Microsoft-Windows-Threat-Intelligence` es el que usan los EDR comerciales de verdad, pero requiere firma ELAM — quedate con los providers estándar para un proyecto personal.
- **Sysmon (Sysinternals)** — la base real de cualquier EDR gratuito en Windows. Event IDs clave:

| Event ID | Qué captura | Por qué importa |
|---|---|---|
| 1 | Process Create (hash + línea de comandos completa) | El evento más importante de todos |
| 3 | Network Connection | Detecta C2, exfiltración |
| 5 | Process Terminate | Contexto de vida del proceso |
| 7 | Image Loaded (DLLs) | DLL sideloading/hijacking |
| 8 | CreateRemoteThread | Process injection clásico |
| 10 | ProcessAccess | Acceso a `lsass.exe` = posible credential dumping |
| 11 | FileCreate | Drops de payloads |
| 12/13/14 | Registry (create/modify/rename) | Persistencia vía registry |
| 17/18 | Pipe Created/Connected | C2 vía named pipes |
| 22 | DNS Query | Beaconing, DGA |
| 25 | ProcessTampering | Process hollowing |

- **Windows Event Log (Security)** — 4624 (logon exitoso), 4625 (logon fallido), 4672 (privilegios especiales asignados), 4688 (creación de proceso, si la audit policy lo habilita), 4720 (usuario creado), 4728/4732 (agregado a grupo), 5140/5145 (acceso a share de red).
- **PowerShell logging** — Script Block Logging (Event ID 4104), Module Logging, Transcription. Crítico: PowerShell con comandos encoded/ofuscados es una de las técnicas más comunes en el mundo real.
- **AMSI (Antimalware Scan Interface)** — hook para inspeccionar scripts antes de ejecutarse (PowerShell, VBScript, JScript, macros de Office).
- **Superficie de persistencia** — Run keys del registro, Scheduled Tasks, servicios, WMI Event Subscriptions, Winlogon Helper DLLs. Hay que enumerarlos periódicamente y diffear contra un baseline.

Comandos reales:

```powershell
# Habilitar auditoría de creación de procesos con línea de comando completa
auditpol /set /subcategory:"Process Creation" /success:enable
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit" `
  /v ProcessCreationIncludeCmdLine_Enabled /t REG_DWORD /d 1

# Consultar logones fallidos (posible brute force)
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 50

# Habilitar Script Block Logging de PowerShell
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" `
  -Name EnableScriptBlockLogging -Value 1

# Instalar Sysmon con una config de referencia (SwiftOnSecurity u Olaf Hartong)
sysmon64.exe -accepteula -i sysmonconfig.xml
```

Fragmento de config Sysmon para detectar acceso sospechoso a `lsass.exe` (posible dumping de credenciales):

```xml
<Sysmon schemaversion="4.90">
  <EventFiltering>
    <RuleGroup name="" groupRelation="or">
      <ProcessAccess onmatch="include">
        <TargetImage condition="end with">\lsass.exe</TargetImage>
        <GrantedAccess condition="is">0x1010</GrantedAccess>
      </ProcessAccess>
    </RuleGroup>
  </EventFiltering>
</Sysmon>
```

### 3.2 Linux

- **auditd (Linux Audit Framework)** — el estándar de facto para syscall auditing.
- **eBPF** — el presente de la telemetría de kernel en Linux, sin el overhead de auditd. Proyectos de referencia: **Falco** (CNCF, graduado), **Tracee** (Aqua Security), **Tetragon** (Isovalent/Cilium).
- **Netfilter/nftables logging** para tráfico de red.

Comandos reales:

```bash
# Vigilar cambios en /etc/passwd y trackear todo execve del sistema
auditctl -w /etc/passwd -p wa -k identity_changes
auditctl -a always,exit -F arch=b64 -S execve -k exec_tracking

# Buscar eventos por key
ausearch -k exec_tracking -ts recent

# bpftrace: tracear en vivo todos los execve del sistema
bpftrace -e 'tracepoint:syscalls:sys_enter_execve { printf("%s -> %s\n", comm, str(args->filename)); }'

# journald: seguir intentos de login SSH en vivo
journalctl -f -u sshd -o cat
```

Regla Falco de ejemplo (detecta una shell interactiva dentro de un contenedor — patrón clásico de post-explotación):

```yaml
- rule: Terminal shell in container
  desc: Se generó una shell interactiva dentro de un contenedor
  condition: spawned_process and container and shell_procs and proc.tty != 0
  output: "Shell en contenedor (usuario=%user.name contenedor=%container.name shell=%proc.name)"
  priority: WARNING
```

### 3.3 macOS

- **Endpoint Security Framework (ESF)** — la API oficial de Apple para esto (reemplazó a Kauth/OpenBSM). Requiere el entitlement `com.apple.developer.endpoint-security.client` y Full Disk Access. Eventos clave: `ES_EVENT_TYPE_NOTIFY_EXEC`, `ES_EVENT_TYPE_NOTIFY_FORK`, `ES_EVENT_TYPE_NOTIFY_OPEN`, `ES_EVENT_TYPE_NOTIFY_MMAP` (posible inyección), `ES_EVENT_TYPE_NOTIFY_MOUNT`.
- **Unified Logging (os_log)** — reemplazo de syslog desde macOS 10.12.
- **FSEvents** para monitoreo de filesystem a bajo costo.
- **TCC.db** — quién tiene permisos de cámara/micrófono/accesibilidad. Vector de persistencia y abuso muy común.
- **launchd** — LaunchAgents (`~/Library/LaunchAgents`) y LaunchDaemons (`/Library/LaunchDaemons`) son el vector de persistencia #1 en macOS, por lejos.

Comandos reales:

```bash
# Stream de logs unificados filtrando por eventos de ejecución
log stream --predicate 'eventType == "exec"' --style compact

# Enumerar persistencia activa
launchctl list
ls -la ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons

# Syscalls de filesystem en vivo (requiere sudo)
sudo fs_usage -w -f filesys
```

Esqueleto de cliente ESF (Swift) suscribiéndose a eventos de ejecución:

```swift
var client: OpaquePointer?
es_new_client(&client) { _, message in
    // procesar message.event.exec, etc.
}
es_subscribe(client!, [ES_EVENT_TYPE_NOTIFY_EXEC], 1)
```

### 3.4 Android

Sin root, Android es un sandbox por diseño — no existe un equivalente a auditd. Las opciones legítimas y sostenibles (compatibles con las políticas de Play Store) son:

- **VpnService API** — permite inspeccionar tráfico de red a nivel de app sin root. Así funcionan apps de firewall como NetGuard. Es la mejor fuente de telemetría de red en Android sin privilegios elevados.
- **UsageStatsManager** — qué apps se usan, cuánto tiempo, foreground/background.
- **NetworkStatsManager** — consumo de datos por app/interfaz.
- **Accessibility Service API** — la más sensible de todas. Google exige justificación explícita y revisión de Play Store porque es el vector #1 de spyware/stalkerware en Android. Solo tiene sentido con consentimiento explícito e informado del usuario del dispositivo, y conviene evaluar si de verdad la necesitás antes de ir por acá.
- **Device Owner / Android Enterprise (MDM)** — si vas a gestionar tus propios dispositivos como "device owner", tenés acceso a APIs de gestión mucho más profundas (políticas, inventario de apps, restricciones). Es el camino "serio" para una flota de dispositivos propios.
- **Modo laboratorio (dispositivo propio, rooteado)** — Frida para instrumentación dinámica, módulos de Magisk, `logcat`, `dumpsys`. Solo en un dispositivo tuyo de investigación, nunca en producción de terceros sin autorización.

Comandos reales:

```bash
adb logcat -v threadtime | grep -i "ActivityManager\|PackageManager"
adb shell dumpsys netstats
adb shell dumpsys package <package>   # inventario de permisos concedidos
```

---

## 4. Taxonomía de eventos (mapeo a MITRE ATT&CK)

Esta tabla es la que después se convierte en tu matriz de cobertura de detección (sección 11).

| Categoría | Qué capturar | Táctica ATT&CK relacionada |
|---|---|---|
| Ejecución de procesos | Proceso padre-hijo, línea de comandos completa, hash, firma digital | Execution (TA0002) |
| Red | Conexiones salientes/entrantes, DNS, puertos en escucha, beaconing | Command and Control (TA0011) |
| Filesystem | Creación/modificación/borrado en rutas sensibles, ejecutables en Temp/Downloads | Persistence (TA0003) |
| Persistencia | Run keys, servicios, scheduled tasks, cron, launchd, WMI subscriptions | Persistence (TA0003) |
| Identidad/Auth | Logon/logoff, fallos repetidos, escalación de privilegios, cuentas nuevas | Credential Access (TA0006), Privilege Escalation (TA0004) |
| Kernel/Drivers | Carga de drivers no firmados, módulos de kernel nuevos | Defense Evasion (TA0005) |
| Memoria | Process injection, hollowing, memoria ejecutable sin backing (vía ETW-TI o ESF) | Defense Evasion (TA0005) |
| Living off the land | Uso de binarios legítimos del SO con fines maliciosos (PowerShell, certutil, mshta, rundll32) | Defense Evasion (TA0005) |
| USB/Hardware | Inserción de dispositivos, nuevos drivers de HID | Initial Access (TA0001) |
| Exfiltración | Volumen anómalo de subida, uso de servicios cloud no corporativos | Exfiltration (TA0010) |

---

## 5. Motor de detección

- **Sigma rules** — formato de detección genérico y portable, se traduce a queries de tu backend con `sigma-cli`/pySigma. [SigmaHQ](https://github.com/SigmaHQ/sigma) en GitHub tiene miles de reglas públicas listas para importar.
- **YARA** — para escaneo de archivos/memoria por patrones.
- **MITRE ATT&CK Navigator** — para mapear qué técnicas detectás y cuáles son puntos ciegos.
- **Baseline de comportamiento** — ej. "este host nunca corre PowerShell; si aparece, es una anomalía aunque no matchee ninguna firma."
- **Threat Intel gratuita** — AlienVault OTX, abuse.ch (URLhaus, MalwareBazaar, ThreatFox), MISP si querés correlacionar con feeds propios.

Regla Sigma de ejemplo (PowerShell con comando encoded — uno de los patrones más comunes en el mundo real):

```yaml
title: PowerShell Encoded Command
status: stable
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith: '\powershell.exe'
    CommandLine|contains:
      - '-enc'
      - '-EncodedCommand'
  condition: selection
level: high
```

Regla YARA de ejemplo (patrón clásico de download cradle en memoria/script):

```yara
rule Suspicious_Download_Cradle
{
    meta:
        description = "Detecta patrones típicos de download cradle en PowerShell"
        severity = "medium"
    strings:
        $a = "IEX" nocase
        $b = "Net.WebClient" nocase
        $c = "DownloadString" nocase
    condition:
        2 of them
}
```

---

## 6. Capa de inteligencia artificial — el cerebro

### 6.1 Diseño funcional

El LLM no "mira" logs crudos directamente — eso agotaría cualquier ventana de contexto en minutos. En cambio:

1. Un **resumidor/indexador** convierte eventos crudos en resúmenes + embeddings, guardados en un vector store OSS (Qdrant o Chroma).
2. El LLM tiene **tools/functions** que invoca bajo demanda: `query_events(filters)`, `get_process_tree(pid)`, `get_active_connections()`, `list_alerts(severity)`, `lookup_ioc(indicator)`, `explain_attck_technique(id)`.
3. Cuando ocurre un alert de alta severidad, el sistema **empuja proactivamente** un mensaje al chat — no espera a que preguntes.
4. Toda acción de remediación que el LLM "quiera" ejecutar pasa por el motor de respuesta (sección 7): el LLM propone, el switch autoriza.

### 6.2 APIs de LLM gratuitas / open — estado real verificado julio 2026

| Proveedor | Costo | Límites free tier (jul 2026) | Modelos destacados | Tool calling | Nota clave |
|---|---|---|---|---|---|
| **Groq** | Gratis, sin tarjeta | ~30 RPM, ~1.000 RPD por modelo (varía) | Llama 3.3 70B, GPT-OSS 120B, Qwen3 32B | Sí (API compatible OpenAI) | Solo modelos open-weight. Hardware LPU propio → la latencia más baja del mercado, ideal para el chat en vivo |
| **Cerebras** | Gratis, sin tarjeta | 1.000.000 tokens/día, ~30 RPM | Llama 4 Scout, Qwen3 32B, GPT-OSS | Sí (SDK compatible OpenAI) | El mayor volumen diario gratis del mercado, ideal para un agente que corre 24/7. El catálogo de modelos rota — no hardcodees un modelo específico sin un plan B |
| **Google Gemini (AI Studio)** | Gratis (Flash / Flash-Lite) | ~15 RPM, ~1.500 RPD, contexto 1M tokens | Gemini 3 Flash, Flash-Lite | Sí | ⚠️ En el free tier, Google puede usar tus prompts para entrenar modelos. Para telemetría de seguridad real, anonymizá antes de mandar. Gemini Pro ya no tiene free tier (removido abril 2026) |
| **OpenRouter** | Gratis (subset rotativo, ~20-29 modelos) | ~20 RPM, ~200 RPD | Qwen3-Coder, Llama 3.3 70B, GPT-OSS 120B (rota semanalmente) | Sí | Broker: un solo endpoint, docenas de modelos. Ideal como capa de fallback automático |

**Arquitectura recomendada:** Cerebras como motor principal para el análisis continuo (volumen diario alto), Groq para las respuestas del chat interactivo (latencia mínima), y OpenRouter como failover automático si alguno de los dos cae, cambia límites, o deprecia un modelo sin aviso — cosa que, según lo investigado, pasa seguido en este ecosistema. Los tres exponen API compatible con el SDK de OpenAI, así que el router de failover es un simple cambio de `base_url`.

```python
# Esqueleto del router de failover (compatible OpenAI en los tres)
providers = [
    {"name": "cerebras", "base_url": "https://api.cerebras.ai/v1", "model": "llama-4-scout"},
    {"name": "groq",     "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    {"name": "openrouter","base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-oss-120b:free"},
]

def call_with_failover(messages, tools):
    for p in providers:
        try:
            client = OpenAI(base_url=p["base_url"], api_key=os.environ[f"{p['name'].upper()}_API_KEY"])
            return client.chat.completions.create(model=p["model"], messages=messages, tools=tools)
        except Exception:
            continue  # probar el siguiente proveedor
    raise RuntimeError("Los tres proveedores fallaron")
```

### 6.3 System prompt de referencia (persona del analista)

```
Sos el analista de seguridad senior de ARGOS, un sistema de observabilidad total
de endpoints. Tenés acceso de LECTURA en tiempo real a todos los eventos del
sistema vía tus tools. Respondé con la precisión de un equipo SOC de primer nivel:
- Nunca inventes datos. Si necesitás un evento que no tenés, llamá a la tool correspondiente.
- Explicá técnicas en términos de MITRE ATT&CK cuando aplique.
- Si detectás algo de severidad alta o crítica, avisá proactivamente sin esperar
  a que te pregunten.
- Podés PROPONER acciones de remediación, nunca ejecutarlas directamente.
  Toda acción pasa por el switch de autonomía del usuario.
- Sé directo y técnico. El usuario es senior, no necesita que le expliques
  qué es un proceso.
```

---

## 7. Motor de respuesta y el switch de autonomía

Esta es la sección que convierte el proyecto de "juguete peligroso" a "herramienta seria" — es literalmente el requisito que vos mismo pediste como no negociable.

### Niveles del switch

| Nivel | Qué puede hacer la IA | Cuándo usarlo |
|---|---|---|
| 🔴 **OBSERVE** (default) | Solo lectura. Colecciona, analiza, chatea. Cero ejecución. | Estado por defecto, siempre |
| 🟡 **SUGGEST** | Propone una acción específica ("¿aíslo este host?") y requiere tu confirmación explícita, acción por acción | Uso diario normal |
| 🟢 **SEMI-AUTO** | Vos pre-autorizás categorías de bajo riesgo (ej. "bloqueá automáticamente IPs de threat intel público"); el resto sigue en SUGGEST | Cuando ya confiás en el sistema |
| ⚫ **FULL-AUTO** | Máxima automatización dentro de playbooks predefinidos | Solo lab/testing, nunca default en producción personal |

### Catálogo de acciones

| Acción | Riesgo | Reversible |
|---|---|---|
| Matar proceso | Medio | Parcial (se puede re-lanzar) |
| Aislar host de la red | Alto | Sí |
| Bloquear IP/dominio | Bajo | Sí |
| Cuarentena de archivo | Bajo | Sí |
| Revertir cambio de registro | Medio | Depende |
| Deshabilitar cuenta de usuario | Alto | Sí |
| Snapshot forense de memoria | Ninguno | N/A |

Toda acción — autorizada o no — se **audita**: quién/qué la propuso, quién la aprobó, timestamp, resultado. Idealmente en un log append-only con hash-chaining (estilo Merkle) para que un atacante que compromete el endpoint no pueda editar su propio historial.

---

## 8. Chat interactivo en tiempo real

Ejemplos de interacciones que el chat tiene que soportar de entrada:

- "¿Qué está pasando ahora mismo en mi laptop?"
- "¿Quién intentó loguearse y falló en las últimas 2 horas?"
- "Mostrame el árbol de procesos de PID 4821"
- "¿Esta IP 45.x.x.x es conocida como maliciosa?"
- "Explicame en criollo qué técnica de MITRE ATT&CK es esta"
- "Aislá el host HOST-02 de la red" → dispara confirmación según el nivel del switch

**Arquitectura:** WebSocket bidireccional entre UI y backend. El backend mantiene una sesión de contexto por host/incidente. Los eventos nuevos se empujan vía el mismo canal (o SSE) sin que el usuario tenga que refrescar ni preguntar.

---

## 9. Stack tecnológico recomendado (100% free / open source)

| Capa | Herramienta | Licencia |
|---|---|---|
| Telemetría Windows | Sysmon + ETW | Gratis (Microsoft Sysinternals) |
| Telemetría Linux | auditd + Falco/eBPF | GPL / Apache 2.0 |
| Telemetría macOS | Endpoint Security Framework | Gratis (Apple, requiere entitlement) |
| Telemetría Android | VpnService + UsageStatsManager | Gratis (Android SDK) |
| Collector | Vector.dev o Fluent Bit | MPL 2.0 / Apache 2.0 |
| Almacenamiento | OpenSearch (o ClickHouse a escala) | Apache 2.0 |
| Detección | Sigma + YARA + SigmaHQ ruleset | DRL / BSD |
| Threat Intel | AlienVault OTX, abuse.ch | Gratis |
| DFIR / hunting complementario | Velociraptor, osquery | AGPL / GPL |
| LLM APIs | Groq + Cerebras + OpenRouter | Free tier (ver sección 6.2) |
| Vector store | Qdrant o Chroma | Apache 2.0 |
| Purple team | Atomic Red Team, MITRE CALDERA | MIT / Apache 2.0 |
| Chat UI | WebSocket + framework a elección | — |

**Nota sobre Velociraptor y osquery:** ambos siguen genuinamente vivos y mantenidos en 2026. Velociraptor sigue bajo licencia AGPL incluso después de que Rapid7 lo adquirió en 2021 — Rapid7 mantiene la versión open source separada de su producto comercial integrado, y hasta CISA lo lista como recurso oficial para agencias federales. Son excelentes como capa complementaria de hunting/DFIR bajo demanda, corriendo junto a tu pipeline principal en vez de reemplazarlo.

---

## 10. Metodología blue team integrada

- **Detection Engineering loop:** hipótesis → regla → test → tuning → deploy. Cada regla nueva se prueba contra tráfico/eventos reales antes de ir a producción para medir falsos positivos.
- **Threat Hunting:** no esperes a que salte una alerta. Cazá activamente basado en técnicas ATT&CK que todavía no tenés cubiertas — la matriz de cobertura (sección 11) te dice por dónde empezar.
- **Runbooks de Incident Response:** contención → erradicación → recuperación → lecciones aprendidas. Escribilos ANTES de que los necesites, no durante el incidente.
- **Retención de logs:** mínimo 90 días en caliente para investigación activa, más tiempo en frío para forense posterior.

---

## 11. Metodología purple team integrada

- **Atomic Red Team** (MITRE-afiliado, open source) — biblioteca de tests atómicos y seguros, uno por técnica ATT&CK. Disparás una técnica controlada contra tu propio lab y verificás si tu detección la agarra. Es exactamente la herramienta diseñada para esto.
- **MITRE CALDERA** — plataforma de emulación de adversarios automatizada, open source, para purple teaming a mayor escala cuando ya tengas varias detecciones que validar juntas.
- **Matriz de cobertura ATT&CK** — trackeá qué porcentaje de técnicas tenés cubiertas y cuáles son puntos ciegos. Esto se construye directamente de la tabla de la sección 4.
- **Cadencia sugerida:** un ejercicio purple team ligero por sprint/mes, no algo que se hace una vez y se olvida.

⚠️ Estas herramientas de simulación corren **únicamente** contra tus propios sistemas de laboratorio/desarrollo — nunca contra infraestructura de terceros sin autorización explícita. Es la regla de "scope y autorización" estándar en cualquier ejercicio profesional de este tipo.

---

## 12. Roadmap de desarrollo sugerido

**Fase 0 — Fundación (1-2 semanas)**
Repo + esquema de eventos (adoptar OCSF desde el día 1 ahorra un refactor doloroso después). Un solo agente, en tu SO principal, escribiendo a un archivo local. Definir el catálogo de acciones y los 4 niveles del switch, aunque todavía no ejecuten nada.

**Fase 1 — Pipeline mínimo viable (2-4 semanas)**
Collector (Vector.dev) + almacenamiento (OpenSearch). Sysmon/auditd/ESF emitiendo eventos reales de un solo host. Dashboard básico sin IA todavía — necesitás *ver* los datos antes de razonar sobre ellos.

**Fase 2 — Motor de detección (2-3 semanas)**
Importar reglas de SigmaHQ + reglas propias. Empezar la matriz de cobertura ATT&CK.

**Fase 3 — Capa de IA + chat (3-4 semanas)**
Function calling contra el store de eventos. Chat en tiempo real. Arrancar en modo OBSERVE-only, sin ninguna acción todavía.

**Fase 4 — Motor de respuesta + switch (2-3 semanas)**
Implementar primero el catálogo de acciones de bajo riesgo (cuarentena de archivo, bloqueo de IP). Auditoría inmutable de cada acción propuesta/aprobada/ejecutada.

**Fase 5 — Multiplataforma (ongoing)**
Segundo SO, tercero, cuarto. Android al final — es el más distinto arquitectónicamente de todos.

**Fase 6 — Purple teaming + hardening**
Atomic Red Team contra tu propio lab. Cerrar los puntos ciegos que aparezcan en la matriz ATT&CK.

### Estructura de repo sugerida

```
argos/
├── agents/
│   ├── windows/        # Sysmon config + servicio en Rust o Go
│   ├── linux/           # eBPF/auditd + daemon
│   ├── macos/            # cliente ESF en Swift
│   └── android/          # app con VpnService + módulo MDM opcional
├── collector/              # Vector.dev config + normalización a OCSF
├── storage/                  # schemas de OpenSearch / ClickHouse
├── detection-engine/
│   ├── rules/sigma/
│   └── rules/yara/
├── ai-layer/
│   ├── tools/               # definiciones de function calling
│   ├── prompts/              # system prompts versionados
│   └── router/                 # failover entre Groq/Cerebras/OpenRouter
├── response-engine/
│   ├── actions/                 # catálogo de acciones
│   └── audit-log/                 # hash-chain de auditoría
├── chat-ui/                         # frontend del chat + dashboard
└── docs/                              # este documento y los deep-dives por módulo
```

---

## 13. Alcance y consideraciones legales

Esto no es un sermón — es la sección de "reglas de engagement" que cualquier documento profesional de seguridad tiene:

- **ARGOS solo puede monitorear/actuar sobre dispositivos que sean tuyos o donde tengas autorización explícita.** Aplica en particular al módulo Android: Accessibility Service y APIs similares son, sin consentimiento informado del usuario del dispositivo, la definición técnica de spyware. Si en algún momento gestionás dispositivos de otras personas (familia, empleados, clientes), necesitás consentimiento informado y, si es contexto laboral, cumplir con la legislación de privacidad aplicable.
- **Los ejercicios purple team (Atomic Red Team, CALDERA) corren únicamente contra tus propios sistemas de laboratorio.** Nunca contra infraestructura de terceros sin autorización explícita por escrito.
- **Retención de datos:** definí una política clara de cuánto guardás telemetría (recomendado 90 días en caliente) y qué hacés si el sistema captura sin querer datos sensibles — credenciales en línea de comandos, por ejemplo, es un problema real y conocido en cualquier EDR.
- **Free tier de LLMs y datos sensibles:** como viste en la sección 6.2, algunos proveedores gratuitos usan tus prompts para entrenar modelos. Si tu telemetría incluye IPs, hostnames o patrones de tu red que preferís no compartir, vale la pena anonymizar/hashear esos campos antes de mandarlos al LLM, o directamente elegir el proveedor con la política de datos más restrictiva para ese tipo de contenido.

---

## 14. Próximos documentos sugeridos

Este es el documento raíz. Los siguientes deep-dives tienen sentido como próximos pasos — decime cuál atacamos primero:

1. **Spec completa del agente Windows** — arquitectura del servicio, integración ETW + Sysmon, cómo minimizar el footprint para no convertirte vos mismo en "el proceso sospechoso"
2. **Spec completa del agente Linux/macOS** — eBPF vs auditd en profundidad, cliente ESF completo
3. **Diseño del esquema de eventos (OCSF) + pipeline de normalización**
4. **Prompt engineering completo de la capa de IA** — system prompt extendido, definición de cada tool, manejo de contexto largo con RAG
5. **Motor de respuesta en profundidad** — catálogo completo de acciones, máquina de estados del switch, sistema de auditoría con hash-chaining
6. **Módulo Android en detalle** — arquitectura MDM/device owner, límites reales sin root
7. **Matriz de cobertura MITRE ATT&CK inicial** — qué técnicas cubrís desde el día 1, cuáles son tus puntos ciegos
