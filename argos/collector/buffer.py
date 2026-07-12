from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from argos.config import Config
from argos.ocsf import OcsfEvent


class LocalBuffer:
    def __init__(self, cfg: Config) -> None:
        self.path = cfg.data_dir / "agent_buffer.db"
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS buffer (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, payload TEXT)"
        )
        self.conn.commit()

    def push(self, events: Iterable[OcsfEvent]) -> None:
        rows = [(datetime.now(timezone.utc).isoformat(), ev.model_dump_json()) for ev in events]
        self.conn.executemany("INSERT INTO buffer (time, payload) VALUES (?, ?)", rows)
        self.conn.commit()

    def pending(self, limit: int = 500) -> list[OcsfEvent]:
        rows = self.conn.execute("SELECT payload FROM buffer ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
        return [OcsfEvent.model_validate_json(r["payload"]) for r in rows]

    def ack(self, count: int) -> None:
        self.conn.execute("DELETE FROM buffer WHERE id IN (SELECT id FROM buffer ORDER BY id ASC LIMIT ?)", (count,))
        self.conn.commit()

    def size(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM buffer").fetchone()[0])
