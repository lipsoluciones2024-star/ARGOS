from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


class MemoryStore:
    """Memoria de investigaciones, resultados de acciones y feedback (G5 / T5.2-T5.4)."""

    def __init__(self, cfg: Any) -> None:
        self.db_path = cfg.data_dir / "memory.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS investigations ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, host TEXT, alert_id TEXT, "
            "attack_id TEXT, verdict TEXT, summary TEXT)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS action_outcomes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, proposal_id TEXT, action TEXT, "
            "target TEXT, status TEXT, outcome TEXT)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS feedback ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, target_type TEXT, target_id TEXT, "
            "rating TEXT, note TEXT)"
        )
        self.conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(text, source, rid UNINDEXED)"
        )
        self.conn.commit()

    def add_investigation(self, host: str, alert_id: Optional[str], attack_id: Optional[str],
                          verdict: str, summary: str = "") -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT INTO investigations (time, host, alert_id, attack_id, verdict, summary) "
            "VALUES (?,?,?,?,?,?)",
            (now, host, alert_id, attack_id, verdict, summary),
        )
        rid = cur.lastrowid
        self.conn.execute(
            "INSERT INTO memory_fts (rid, text, source) VALUES (?,?,?)",
            (rid, f"{verdict} {summary} {attack_id or ''}", "investigation"),
        )
        self.conn.commit()
        return rid or 0

    def add_action_outcome(self, proposal_id: Optional[str], action: str, target: str,
                           status: str, outcome: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO action_outcomes (time, proposal_id, action, target, status, outcome) "
            "VALUES (?,?,?,?,?,?)",
            (now, proposal_id, action, target, status, outcome),
        )
        self.conn.commit()

    def add_feedback(self, target_type: str, target_id: str, rating: str, note: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO feedback (time, target_type, target_id, rating, note) VALUES (?,?,?,?,?)",
            (now, target_type, target_id, rating, note),
        )
        self.conn.commit()

    def rate_for(self, action: str) -> float:
        """Puntaje (-1..1) del feedback para priorizar acciones (T5.4)."""
        rows = self.conn.execute(
            "SELECT rating FROM feedback WHERE target_type='action' AND target_id=?",
            (action,),
        ).fetchall()
        if not rows:
            return 0.0
        score = 0.0
        for r in rows:
            v = (r["rating"] or "").lower()
            score += 1.0 if v == "good" else -1.0 if v == "bad" else 0.0
        return score / len(rows)

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            rows = self.conn.execute(
                "SELECT id, time, host, attack_id, verdict, summary FROM investigations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        tokens = [t for t in q.replace('"', " ").split() if len(t) >= 3]
        out: list[dict[str, Any]] = []
        if tokens:
            match = " OR ".join(f'"{t}"' for t in tokens)
            ids = self.conn.execute(
                "SELECT rowid FROM memory_fts WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
            for r in ids:
                row = self.conn.execute(
                    "SELECT id, time, host, attack_id, verdict, summary FROM investigations WHERE id=?",
                    (r["rowid"],),
                ).fetchone()
                if row:
                    out.append(dict(row))
        if not out:
            like = " OR ".join("summary LIKE ?" for _ in tokens) or "1=1"
            params = [f"%{t}%" for t in tokens]
            rows = self.conn.execute(
                f"SELECT id, time, host, attack_id, verdict, summary FROM investigations "
                f"WHERE {like} ORDER BY id DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
            out = [dict(r) for r in rows]
        return out

    def recent_investigations(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, time, host, attack_id, verdict, summary FROM investigations "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def investigations(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.recent_investigations(limit)

    def outcomes(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, time, proposal_id, action, target, status, outcome FROM action_outcomes "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
