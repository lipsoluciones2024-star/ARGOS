from __future__ import annotations

import platform
from typing import Iterator

from argos.agent.sources.common import run_cmd
from argos.ocsf import EventCategory, OcsfEvent, Severity


def collect_persistence(host: str) -> Iterator[OcsfEvent]:
    """Recolecta mecanismos de persistencia (autoruns, tareas, servicios, claves Run)."""
    if platform.system() == "Windows":
        yield from _windows_persistence(host)
    else:
        yield from _linux_persistence(host)


def _windows_persistence(host: str) -> Iterator[OcsfEvent]:
    # Claves Run / RunOnce (T1547.001)
    raw = run_cmd([
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run','HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce','HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce' "
        "| Select-Object PSPath, Property, @{n='Value';e={$_.(($_.Property)[0])}} | ConvertTo-Json -Compress",
    ])
    for entry in _json_lines(raw):
        key = entry.get("PSPath") or ""
        value = entry.get("Value") or ""
        yield OcsfEvent(
            category=EventCategory.PERSISTENCE, host=host, source="registry_autorun",
            registry_key=key, registry_action="set", process_cmdline=value,
            attack_id="T1547.001", attack_technique="Registry Run Keys / Startup Folder",
            severity=Severity.LOW,
        )
    # Tareas programadas (T1053)
    raw = run_cmd([
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName,TaskPath,Actions | ConvertTo-Json -Compress",
    ])
    for entry in _json_lines(raw):
        actions = entry.get("Actions") or {}
        cmd = (actions.get("Execute") or "") if isinstance(actions, dict) else str(actions)
        yield OcsfEvent(
            category=EventCategory.PERSISTENCE, host=host, source="scheduled_task",
            process_name="schtasks", process_cmdline=cmd,
            registry_key=f"{entry.get('TaskPath','')}{entry.get('TaskName','')}".strip("\\"),
            attack_id="T1053", attack_technique="Scheduled Task/Job",
            severity=Severity.LOW,
        )
    # Servicios (T1543.003)
    raw = run_cmd([
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-CimInstance Win32_Service | Select-Object Name,PathName,StartMode,State | ConvertTo-Json -Compress",
    ])
    for entry in _json_lines(raw):
        if str(entry.get("StartMode")) != "Auto":
            continue
        yield OcsfEvent(
            category=EventCategory.PERSISTENCE, host=host, source="service",
            process_name=entry.get("Name"), process_image=entry.get("PathName"),
            process_cmdline=entry.get("PathName"),
            attack_id="T1543.003", attack_technique="Windows Service",
            severity=Severity.LOW,
        )
    # Suscripciones WMI EventSubscription
    raw = run_cmd([
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-WmiObject -Namespace root\\subscription -Class __EventFilter 2>$null | Select-Object Name,Query | ConvertTo-Json -Compress",
    ])
    for entry in _json_lines(raw):
        yield OcsfEvent(
            category=EventCategory.PERSISTENCE, host=host, source="wmi_subscription",
            process_cmdline=entry.get("Query"),
            attack_id="T1546.003", attack_technique="Windows Management Instrumentation Event Subscription",
            severity=Severity.MEDIUM,
        )


def _linux_persistence(host: str) -> Iterator[OcsfEvent]:
    # crontab del sistema
    raw = run_cmd(["bash", "-c", "cat /etc/crontab 2>/dev/null; ls /etc/cron.* 2>/dev/null"])
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield OcsfEvent(
                category=EventCategory.PERSISTENCE, host=host, source="cron",
                file_path="/etc/crontab", process_cmdline=line,
                attack_id="T1053.003", attack_technique="Cron",
                severity=Severity.LOW,
            )
    # unidades systemd enable
    raw = run_cmd(["bash", "-c", "systemctl list-unit-files --type=service --state=enabled 2>/dev/null | tail -n +2 | awk '{print $1}'"])
    for name in raw.splitlines():
        name = name.strip()
        if not name or ".service" not in name:
            continue
        yield OcsfEvent(
            category=EventCategory.PERSISTENCE, host=host, source="systemd_unit",
            process_name=name,
            attack_id="T1543.002", attack_technique="Systemd Service",
            severity=Severity.LOW,
        )
    # scripts de arranque del shell
    for prof in ("/etc/profile", "/etc/bash.bashrc", "/root/.bashrc", "/root/.profile"):
        raw = run_cmd(["bash", "-c", f"grep -nE 'curl|wget|nc|bash -i|python -c|nohup' {prof} 2>/dev/null"])
        for line in raw.splitlines():
            line = line.strip()
            if line:
                yield OcsfEvent(
                    category=EventCategory.PERSISTENCE, host=host, source="shell_profile",
                    file_path=prof, process_cmdline=line,
                    attack_id="T1546.004", attack_technique="Unix Shell Configuration Modification",
                    severity=Severity.MEDIUM,
                )


def _json_lines(raw: str) -> Iterator[dict]:
    raw = (raw or "").strip()
    if not raw:
        return
    try:
        import json

        data = json.loads(raw)
        if isinstance(data, dict):
            yield data
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
    except Exception:
        return
