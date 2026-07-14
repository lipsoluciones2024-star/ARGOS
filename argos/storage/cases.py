from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from argos.config import Config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CasesStore:
    """Gestión de incidentes/casos SOC (SQLite, independiente de eventos)."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "cases.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'open',
                created TEXT NOT NULL,
                updated TEXT NOT NULL,
                assigned_to TEXT,
                description TEXT,
                linked_alerts TEXT,
                linked_hosts TEXT,
                notes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
            """
        )
        self.conn.commit()

    def create(self, title: str, severity: str = "medium", status: str = "open",
               assigned_to: Optional[str] = None, description: Optional[str] = None,
               linked_alerts: Optional[list[str]] = None,
               linked_hosts: Optional[list[str]] = None) -> dict[str, Any]:
        cid = uuid.uuid4().hex[:16]
        now = _now()
        self.conn.execute(
            "INSERT INTO cases (id, title, severity, status, created, updated, assigned_to, "
            "description, linked_alerts, linked_hosts, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, title, severity, status, now, now, assigned_to, description,
             json.dumps(linked_alerts or []), json.dumps(linked_hosts or []), json.dumps([])),
        )
        self.conn.commit()
        return self.get(cid)  # type: ignore[return-value]

    def list(self, status: Optional[str] = None, limit: int = 200) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM cases WHERE status=? ORDER BY updated DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM cases ORDER BY updated DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(r) for r in rows]

    def get(self, case_id: str) -> Optional[dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return self._row(row) if row else None

    def update(self, case_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        allowed = {"title", "severity", "status", "assigned_to", "description",
                    "linked_alerts", "linked_hosts", "notes"}
        sets = []
        vals: list[Any] = []
        for k, v in fields.items():
            if k not in allowed or v is None:
                continue
            sets.append(f"{k}=?")
            vals.append(json.dumps(v) if k in ("linked_alerts", "linked_hosts", "notes") else v)
        if not sets:
            return self.get(case_id)
        sets.append("updated=?")
        vals.append(_now())
        vals.append(case_id)
        self.conn.execute(f"UPDATE cases SET {', '.join(sets)} WHERE id=?", vals)
        self.conn.commit()
        return self.get(case_id)

    def add_note(self, case_id: str, author: str, text: str) -> Optional[dict[str, Any]]:
        case = self.get(case_id)
        if not case:
            return None
        notes = case["notes"]
        notes.append({"time": _now(), "author": author, "text": text})
        return self.update(case_id, **{"notes": notes})  # type: ignore[arg-type]

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["linked_alerts"] = json.loads(d.pop("linked_alerts") or "[]")
        d["linked_hosts"] = json.loads(d.pop("linked_hosts") or "[]")
        d["notes"] = json.loads(d.pop("notes") or "[]")
        return d
