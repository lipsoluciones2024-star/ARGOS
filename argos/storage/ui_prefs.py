from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from argos.config import Config

DEFAULT_PREFS: Dict[str, Any] = {
    "ui.theme": "midnight",
    "ui.density": "comfortable",
    "ui.layout": "default",
    "ui.panels": {},
    "ui.refresh_sec": 5,
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class UiPrefsStore:
    """Preferencias de UI persistidas (tema, densidad, layout de paneles).

    Reutiliza ``settings.db`` para no introducir otra base. Las claves usan el
    prefijo ``ui.`` y son editables por el usuario desde el dashboard.
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "settings.db"
        self.conn = _connect(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS ui_prefs (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.conn.commit()

    def get_all(self) -> Dict[str, Any]:
        rows = self.conn.execute("SELECT key, value FROM ui_prefs").fetchall()
        out: Dict[str, Any] = dict(DEFAULT_PREFS)
        for r in rows:
            try:
                out[r["key"]] = json.loads(r["value"])
            except (json.JSONDecodeError, TypeError):
                out[r["key"]] = r["value"]
        return out

    def update(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in prefs.items():
            if not key.startswith("ui."):
                continue
            self.conn.execute(
                "INSERT INTO ui_prefs(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )
        self.conn.commit()
        return self.get_all()
