---
título: 10 - Configuración Local
objetivo: Documentar variables, archivos, configuraciones, dependencias, instalación, inicialización, compilación, ejecución y debug, basándose únicamente en la documentación.
alcance: `ARGOS_documento_maestro_arquitectura.md` secciones 3,12; Docs/KiloGateway 02,03.
dependencias: 08-API-Gateway.md; 11-Gestion-Configuracion.md.
referencias: 21-Dependencias.md; 22-Checklist-Desarrollo.md.
---

# 10 - Configuración Local

> **Contexto (AGENTS.md):** desarrollo e ejecución completamente local; la única salida externa es la API Gateway. Se documenta lo indicado en la base.

## 1. Variables de entorno

- `KILO_API_KEY` — API key de Kilo Gateway (Doc 3, buena práctica 1: no hardcodear).
- `<PROVIDER>_API_KEY` — donde `<PROVIDER>` ∈ {CEREBRAS, GROQ, OPENROUTER} usadas por el router de failover (`os.environ[f"{p['name'].upper()}_API_KEY"]`).
- `X-KiloCode-OrganizationId`, `X-KiloCode-TaskId`, `X-KiloCode-Version`, `x-kilocode-mode` — headers opcionales (cuenta org / cache / modo).
- **Modo híbrido (Opción C):** `ARGOS_LLM_MODE` (`hybrid`/`remote`/`local`), `ARGOS_LOCAL_MODEL_PATH` (ruta al GGUF), `ARGOS_LOCAL_BASE_URL` (`http://127.0.0.1:8080/v1`). Ver `30-Descarga-Modelo-Local-Qwen25.md`.

> **Información no especificada en la documentación original.** No se especifican nombres de archivos `.env`, rutas de configuración del agente, ni variables para endpoints locales (OpenSearch, Vector, etc.).

## 2. Archivos de configuración citados

- `sysmonconfig.xml` — config de referencia SwiftOnSecurity u Olaf Hartong para Sysmon (Windows).
- Reglas Sigma en `detection-engine/rules/sigma/` (ej. "PowerShell Encoded Command").
- Reglas YARA en `detection-engine/rules/yara/` (ej. "Suspicious_Download_Cradle").
- Config de Vector.dev en `collector/`.
- Schemas de OpenSearch/ClickHouse en `storage/`.
- System prompts versionados en `ai-layer/prompts/`.

## 3. Configuraciones por SO (comandos reales documentados)

### Windows
```powershell
auditpol /set /subcategory:"Process Creation" /success:enable
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit" /v ProcessCreationIncludeCmdLine_Enabled /t REG_DWORD /d 1
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Name EnableScriptBlockLogging -Value 1
sysmon64.exe -accepteula -i sysmonconfig.xml
```

### Linux
```bash
auditctl -w /etc/passwd -p wa -k identity_changes
auditctl -a always,exit -F arch=b64 -S execve -k exec_tracking
bpftrace -e 'tracepoint:syscalls:sys_enter_execve { printf("%s -> %s\n", comm, str(args->filename)); }'
journalctl -f -u sshd -o cat
```

### macOS
```bash
log stream --predicate 'eventType == "exec"' --style compact
launchctl list
sudo fs_usage -w -f filesys
```

### Android
```bash
adb logcat -v threadtime | grep -i "ActivityManager\|PackageManager"
adb shell dumpsys netstats
adb shell dumpsys package <package>
```

## 4. Dependencias

Ver `21-Dependencias.md`. Herramientas OSS: Sysmon, ETW, auditd, Falco/eBPF, ESF, VpnService; Vector.dev/Fluent Bit; OpenSearch/ClickHouse; Sigma/YARA; Qdrant/Chroma; SDK OpenAI.

## 5. Instalación / Inicialización / Compilación / Ejecución / Debug

> **Información no especificada en la documentación original.** La documentación base no provee pasos concretos de instalación, compilación, arranque ni debug del sistema ARGOS (no hay `README`, `package.json`, `Cargo.toml`, `Dockerfile`, ni comandos `run`). Solo se dan comandos de habilitación de telemetría por SO y ejemplos de código de consumo de la API. El roadmap (sección 12) describe fases pero no comandos de build.

## 6. Debug de la API (según Docs/KiloGateway)

- Verificar `401` → falta `Authorization: Bearer`.
- `content` vacío en `:free` → leer `message.reasoning`.
- `kilo-auto/free` ~11s → usar modelo fijo.
- `429` anónimo → usar API key o esperar.
