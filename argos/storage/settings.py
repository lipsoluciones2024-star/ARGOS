from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from argos.config import Config

DEFAULTS: dict[str, Any] = {
    "ai.enabled": True,
    "ai.mode": "hybrid",
    "ai.model": "",
    "ai.temperature": 0.2,
    "ai.max_tokens": 1024,
    "ai.streaming": True,
    "ai.system_prompt": "",
    "ai.local_enabled": False,
    "switch.default": "OBSERVE",
    "retention_days": 90,
    "scheduler.enabled": True,
    "scheduler.interval_sec": 60,
    "ui.theme": "midnight",
    "ui.refresh_sec": 5,
    "ui.density": "comfortable",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class SettingsStore:
    """Runtime-editable configuration persisted in SQLite.

    Acts as an overlay on top of the file/env ``Config``. Any key present here
    takes precedence over the static defaults. Unknown keys fall back to DEFAULTS.
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "settings.db"
        self.conn = _connect(self.db_path)
        self._init_schema()
        self._seed_defaults()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )
        self.conn.commit()

    def _seed_defaults(self) -> None:
        for key, val in DEFAULTS.items():
            if self.get_raw(key) is None:
                self._write(key, val)

    def _type_of(self, val: Any) -> str:
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, int):
            return "int"
        if isinstance(val, float):
            return "float"
        return "str"

    def _write(self, key: str, val: Any) -> None:
        from datetime import datetime, timezone

        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, type, updated_at) VALUES (?,?,?,?)",
            (key, json.dumps(val), self._type_of(val), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def get_raw(self, key: str) -> Optional[Any]:
        row = self.conn.execute("SELECT value, type FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        return json.loads(row["value"])

    def get(self, key: str, default: Any = None) -> Any:
        val = self.get_raw(key)
        if val is not None:
            return val
        return DEFAULTS.get(key, default)

    def set(self, key: str, value: Any) -> Any:
        self._write(key, value)
        return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on")
        return bool(val)

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key, default)
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self.get(key, default)
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def get_str(self, key: str, default: str = "") -> str:
        val = self.get(key, default)
        return "" if val is None else str(val)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in DEFAULTS:
            out[key] = self.get(key)
        return out

    def set_many(self, values: dict[str, Any]) -> dict[str, Any]:
        for k, v in values.items():
            if k in DEFAULTS:
                self.set(k, v)
        return self.as_dict()
