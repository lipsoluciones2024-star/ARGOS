from __future__ import annotations

import platform
import subprocess
from typing import Iterator

from argos.ocsf import EventCategory, OcsfEvent, Severity


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return out.stdout or ""
    except Exception:
        return ""


def collect_processes(host: str) -> Iterator[OcsfEvent]:
    sysname = platform.system()
    if sysname == "Windows":
        raw = _run([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,"
            "Name,ExecutablePath,CommandLine | ConvertTo-Csv -NoTypeInformation",
        ])
        if raw.strip():
            rows = [r for r in raw.splitlines() if r.strip()]
            header = _split_csv(rows[0]) if rows else []
            for line in rows[1:]:
                cols = _split_csv(line)
                if len(cols) < 2 or not header:
                    continue
                rec = dict(zip(header, cols))
                pid = _to_int(rec.get("ProcessId"))
                ppid = _to_int(rec.get("ParentProcessId"))
                name = rec.get("Name") or "unknown"
                image = rec.get("ExecutablePath") or name
                cmd = rec.get("CommandLine")
                yield OcsfEvent(
                    category=EventCategory.PROCESS, host=host, source="agent",
                    process_name=name, process_pid=pid, process_parent_pid=ppid,
                    process_image=image, process_cmdline=cmd, severity=Severity.INFO,
                )
        else:
            raw = _run(["tasklist", "/FO", "CSV", "/NH"])
            for line in raw.splitlines():
                parts = _split_csv(line)
                if len(parts) >= 2:
                    yield OcsfEvent(
                        category=EventCategory.PROCESS, host=host, source="agent",
                        process_name=parts[0], process_pid=_to_int(parts[1]),
                        process_image=parts[0], severity=Severity.INFO,
                    )
    else:
        raw = _run(["ps", "-eo", "pid,ppid,comm,args"])
        for line in raw.splitlines()[1:]:
            cols = line.split(None, 3)
            if len(cols) >= 3:
                pid = _to_int(cols[0])
                ppid = _to_int(cols[1])
                comm = cols[2]
                cmd = cols[3] if len(cols) > 3 else comm
                yield OcsfEvent(
                    category=EventCategory.PROCESS, host=host, source="agent",
                    process_name=comm, process_pid=pid, process_parent_pid=ppid,
                    process_cmdline=cmd, process_image=comm, severity=Severity.INFO,
                )


def collect_network(host: str) -> Iterator[OcsfEvent]:
    sysname = platform.system()
    if sysname == "Windows":
        raw = _run(["netstat", "-n", "-o"])
        for line in raw.splitlines():
            cols = line.split()
            if len(cols) >= 5 and cols[0].lower() in ("tcp", "udp"):
                local, remote = cols[1], cols[2]
                pid = _to_int(cols[4]) if cols[4].isdigit() else None
                sip, sport = _split_host(local)
                dip, dport = _split_host(remote)
                yield OcsfEvent(
                    category=EventCategory.NETWORK, host=host, source="agent",
                    src_ip=sip, src_port=sport, dst_ip=dip, dst_port=dport,
                    protocol=cols[0].upper(), process_pid=pid, severity=Severity.INFO,
                )
    else:
        raw = _run(["ss", "-tunp"])
        if not raw:
            raw = _run(["netstat", "-tunp"])
        for line in raw.splitlines()[1:]:
            cols = line.split()
            if len(cols) >= 5 and cols[0].lower().startswith(("tcp", "udp")):
                local, remote = cols[3], cols[4]
                sip, sport = _split_host(local)
                dip, dport = _split_host(remote)
                pid = _extract_pid(cols[-1])
                yield OcsfEvent(
                    category=EventCategory.NETWORK, host=host, source="agent",
                    src_ip=sip, src_port=sport, dst_ip=dip, dst_port=dport,
                    protocol=cols[0].upper(), process_pid=pid, severity=Severity.INFO,
                )


def collect_logons(host: str) -> Iterator[OcsfEvent]:
    if platform.system() == "Windows":
        raw = _run(["wevtutil", "qe", "Security", "/c:20", "/rd:true",
                    "/q:*[System[(EventID=4625)]]"])
        if raw.strip():
            yield OcsfEvent(
                category=EventCategory.IDENTITY, host=host, source="windows_eventlog",
                user="unknown", logon_result="failure", severity=Severity.MEDIUM,
                attack_id="T1110", attack_technique="Brute Force",
            )


def _split_csv(line: str) -> list[str]:
    out: list[str] = []
    cur = ""
    in_q = False
    for ch in line:
        if ch == '"':
            in_q = not in_q
        elif ch == "," and not in_q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def _to_int(s: str | None) -> int | None:
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None


def _split_host(hostport: str) -> tuple[str | None, int | None]:
    if ":" not in hostport:
        return hostport, None
    host, _, port = hostport.rpartition(":")
    host = host.strip("[]")
    return host, _to_int(port)


def _extract_pid(token: str) -> int | None:
    if "pid=" in token:
        part = token.split("pid=")[1]
        num = "".join(ch for ch in part if ch.isdigit())
        return _to_int(num)
    return None
