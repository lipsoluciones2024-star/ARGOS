from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from argos.ocsf import EventCategory, OcsfEvent, Severity


def _hash_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


class FimStore:
    """Baseline de integridad de archivos (local al agente)."""

    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS fim_baseline ("
            "host TEXT, path TEXT, hash TEXT, mtime TEXT, PRIMARY KEY (host, path))"
        )
        self.conn.commit()

    def lookup(self, host: str, path: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM fim_baseline WHERE host=? AND path=?", (host, path)
        ).fetchone()

    def record(self, host: str, path: str, h: str, mtime: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO fim_baseline (host, path, hash, mtime) VALUES (?,?,?,?)",
            (host, path, h, mtime),
        )
        self.conn.commit()


def collect_fim(host: str, store: FimStore, paths: list[str]) -> Iterator[OcsfEvent]:
    """Compara archivos críticos contra el baseline; emite evento al cambiar."""
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            continue
        h = _hash_file(path)
        if h is None:
            continue
        prev = store.lookup(host, path)
        if prev is None:
            store.record(host, path, h, str(mtime))
            continue
        if prev["hash"] == h:
            continue
        store.record(host, path, h, str(mtime))
        yield OcsfEvent(
            category=EventCategory.FILESYSTEM, host=host, source="fim",
            file_path=path, file_action="modified",
            attack_id="T1565.001", attack_technique="Stored Data Manipulation",
            severity=Severity.HIGH,
            raw={"fim_prev_hash": prev["hash"], "fim_new_hash": h},
        )
