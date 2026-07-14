from __future__ import annotations

import re
from typing import Iterator

from argos.agent.sources.common import collect_processes
from argos.ocsf import EventCategory, OcsfEvent, Severity

# Binarios "vivos" (LOLBin) y su técnica ATT&CK asociada.
_LOLBIN_TECHNIQUE: dict[str, tuple[str, str]] = {
    "powershell.exe": ("T1059.001", "PowerShell"),
    "pwsh.exe": ("T1059.001", "PowerShell"),
    "powershell": ("T1059.001", "PowerShell"),
    "pwsh": ("T1059.001", "PowerShell"),
    "cmd.exe": ("T1059.003", "Windows Command Shell"),
    "cmd": ("T1059.003", "Windows Command Shell"),
    "certutil.exe": ("T1218", "System Binary Proxy Execution"),
    "certutil": ("T1218", "System Binary Proxy Execution"),
    "mshta.exe": ("T1218.005", "Mshta"),
    "mshta": ("T1218.005", "Mshta"),
    "wscript.exe": ("T1218.005", "Mshta"),
    "wscript": ("T1218.005", "Mshta"),
    "cscript.exe": ("T1218.005", "Mshta"),
    "cscript": ("T1218.005", "Mshta"),
    "bitsadmin.exe": ("T1218", "System Binary Proxy Execution"),
    "bitsadmin": ("T1218", "System Binary Proxy Execution"),
    "rundll32.exe": ("T1218.011", "Rundll32"),
    "rundll32": ("T1218.011", "Rundll32"),
    "regsvr32.exe": ("T1218.010", "Regsvr32"),
    "regsvr32": ("T1218.010", "Regsvr32"),
    "wmic.exe": ("T1218", "System Binary Proxy Execution"),
    "wmic": ("T1218", "System Binary Proxy Execution"),
    "msiexec.exe": ("T1218.007", "Msiexec"),
    "msiexec": ("T1218.007", "Msiexec"),
    "odbcconf.exe": ("T1218.008", "Odbcconf"),
    "odbcconf": ("T1218.008", "Odbcconf"),
    "forfiles.exe": ("T1218", "System Binary Proxy Execution"),
    "forfiles": ("T1218", "System Binary Proxy Execution"),
    "esentutl.exe": ("T1218", "System Binary Proxy Execution"),
    "esentutl": ("T1218", "System Binary Proxy Execution"),
}

_SUSPICIOUS = re.compile(
    r"(downloadstring|downloadfile|webclient|frombase64|base64|"
    r"-enc|encodedcommand|iex|invoke-expression|"
    r"/url:|/f:|http[s]?://|"
    r"bypass|-nop|-noni|hidden|-w hidden|"
    r"net user|net localgroup|add-user|"
    r"whoami|systeminfo|nltest|/c:|/k |/r |schtasks|sc create|"
    r"vssadmin|wbadmin|bcdedit|shadow copy)",
    re.IGNORECASE,
)


def collect_lotl(host: str) -> Iterator[OcsfEvent]:
    """Detecta binarios vivos (LOLBin/LotL) con línea de comando sospechosa."""
    for proc in collect_processes(host):
        name = (proc.process_name or "").lower()
        tech = _LOLBIN_TECHNIQUE.get(name)
        if tech is None:
            continue
        cmd = proc.process_cmdline or ""
        if not _SUSPICIOUS.search(cmd):
            continue
        attack_id, attack_technique = tech
        yield OcsfEvent(
            category=EventCategory.LOTL, host=host, source="lotl_scanner",
            process_name=proc.process_name, process_pid=proc.process_pid,
            process_parent_pid=proc.process_parent_pid,
            process_image=proc.process_image, process_cmdline=cmd,
            attack_id=attack_id, attack_technique=attack_technique,
            severity=Severity.HIGH,
            raw={"base_category": proc.category.value},
        )
