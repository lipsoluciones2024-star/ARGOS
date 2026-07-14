from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, List, Optional

from argos.config import Config


class RulesStore:
    """Reglas gestionadas por API (YARA/Sigma) con habilitar/deshabilitar y origen."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "argos.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                origin TEXT NOT NULL DEFAULT 'api',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_type ON rules(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_name ON rules(name)")
        self.conn.commit()

    def create(self, name: str, rtype: str, content: str, enabled: bool = True,
               origin: str = "api") -> dict[str, Any]:
        import secrets

        rid = secrets.token_hex(16)
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO rules (id, name, type, content, enabled, origin, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (rid, name, rtype, content, 1 if enabled else 0, origin, now, now),
        )
        self.conn.commit()
        return self.get(rid)  # type: ignore[return-value]

    def update(self, rule_id: str, content: str | None = None,
               enabled: bool | None = None, name: str | None = None) -> Optional[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone()
        if not cur:
            return None
        new_name = name if name is not None else cur["name"]
        new_content = content if content is not None else cur["content"]
        new_enabled = enabled if enabled is not None else bool(cur["enabled"])
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE rules SET name=?, content=?, enabled=?, updated_at=? WHERE id=?",
            (new_name, new_content, 1 if new_enabled else 0, now, rule_id),
        )
        self.conn.commit()
        return self.get(rule_id)

    def set_enabled(self, rule_id: str, enabled: bool) -> Optional[dict[str, Any]]:
        return self.update(rule_id, enabled=enabled)

    def delete(self, rule_id: str) -> bool:
        cur = self.conn.execute("SELECT id FROM rules WHERE id=?", (rule_id,)).fetchone()
        if not cur:
            return False
        self.conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
        self.conn.commit()
        return True

    def list_rules(self, rtype: str | None = None, limit: int = 200) -> List[dict[str, Any]]:
        if rtype:
            rows = self.conn.execute(
                "SELECT * FROM rules WHERE type=? ORDER BY name LIMIT ?", (rtype, limit)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM rules ORDER BY name LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def get(self, rule_id: str) -> Optional[dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone()
        return self._row(r) if r else None

    def get_enabled(self, rtype: str) -> List[dict[str, Any]]:
        return [r for r in self.list_rules(rtype=rtype) if r["enabled"]]

    @staticmethod
    def _row(r: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": r["id"], "name": r["name"], "type": r["type"],
            "content": r["content"], "enabled": bool(r["enabled"]),
            "origin": r["origin"], "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    def close(self) -> None:
        self.conn.close()
