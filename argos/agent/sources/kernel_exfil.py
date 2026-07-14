from __future__ import annotations

import ipaddress
from typing import Iterator

from argos.agent.sources.common import _split_csv, collect_network, run_cmd
from argos.ocsf import EventCategory, OcsfEvent, Severity

_EXFIL_CONN_THRESHOLD = 8


def _is_external(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast)


def collect_kernel_exfil(host: str) -> Iterator[OcsfEvent]:
    """Detecta drivers sin firma (kernel) y posible exfiltración masiva (red/USB)."""
    yield from _unsigned_drivers(host)
    yield from _bulk_connections(host)


def _unsigned_drivers(host: str) -> Iterator[OcsfEvent]:
    raw = run_cmd(["driverquery", "/v", "/fo", "csv"], timeout=25)
    rows = [r for r in raw.splitlines() if r.strip()]
    if len(rows) < 2:
        return
    header = _split_csv(rows[0])
    for line in rows[1:]:
        cols = _split_csv(line)
        if len(cols) < len(header):
            continue
        rec = dict(zip(header, cols))
        signed = (rec.get("Signed") or "").strip().lower()
        if signed and signed not in ("signed", "true", "yes", ""):
            yield OcsfEvent(
                category=EventCategory.KERNEL, host=host, source="driverquery",
                process_name=rec.get("Module Name"),
                process_image=rec.get("Display Name"),
                attack_id="T1014", attack_technique="Rootkit",
                severity=Severity.HIGH,
                raw={"signed": rec.get("Signed")},
            )


def _bulk_connections(host: str) -> Iterator[OcsfEvent]:
    by_pid: dict[int, set[str]] = {}
    for conn in collect_network(host):
        if not _is_external(conn.dst_ip):
            continue
        pid = conn.process_pid or -1
        if conn.dst_ip:
            by_pid.setdefault(pid, set()).add(conn.dst_ip)
    for pid, dsts in by_pid.items():
        if len(dsts) >= _EXFIL_CONN_THRESHOLD:
            yield OcsfEvent(
                category=EventCategory.EXFILTRATION, host=host, source="exfil_heuristic",
                process_pid=pid if pid != -1 else None,
                attack_id="T1041", attack_technique="Exfiltration Over C2 Channel",
                severity=Severity.HIGH,
                raw={"distinct_external_dst": len(dsts)},
            )
