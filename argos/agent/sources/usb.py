from __future__ import annotations

import platform
import sqlite3
from pathlib import Path
from typing import Iterator

from argos.agent.sources.common import run_cmd
from argos.ocsf import EventCategory, OcsfEvent, Severity


def _enumerate_usb() -> list[dict[str, str]]:
    if platform.system() == "Windows":
        raw = run_cmd([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-PnpDevice -Class USB,DiskDrive,WPD 2>$null | Select-Object InstanceId, FriendlyName, Status | ConvertTo-Json -Compress",
        ])
        return _json_list(raw)
    # Linux
    raw = run_cmd([
        "bash", "-c",
        "for d in /sys/bus/usb/devices/*/product; do dev=$(dirname $d); "
        "echo \"$(cat $dev/idVendor):$(cat $dev/idProduct) $(cat $d)\"; done 2>/dev/null",
    ])
    out: list[dict[str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            out.append({"InstanceId": line, "FriendlyName": line})
    return out


class UsbTracker:
    """Detecta inserciones de almacenamiento extraíble comparando contra lo visto."""

    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS usb_seen (host TEXT, dev_id TEXT, PRIMARY KEY (host, dev_id))"
        )
        self.conn.commit()

    def _seen(self, host: str, dev_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM usb_seen WHERE host=? AND dev_id=?", (host, dev_id)
        ).fetchone() is not None

    def _mark(self, host: str, dev_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO usb_seen (host, dev_id) VALUES (?,?)", (host, dev_id)
        )
        self.conn.commit()

    def scan(self, host: str) -> Iterator[OcsfEvent]:
        for dev in _enumerate_usb():
            dev_id = dev.get("InstanceId") or dev.get("FriendlyName") or ""
            if not dev_id:
                continue
            if self._seen(host, dev_id):
                continue
            self._mark(host, dev_id)
            yield OcsfEvent(
                category=EventCategory.USB, host=host, source="usb_tracker",
                process_name=dev.get("FriendlyName") or dev_id,
                attack_id="T1029", attack_technique="Remote Data Storage",
                severity=Severity.LOW,
            )


def _json_list(raw: str) -> list[dict[str, str]]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        import json

        data = json.loads(raw)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
    except Exception:
        return []
    return []
