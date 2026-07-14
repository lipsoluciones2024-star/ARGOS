from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


class ChatLog:
    """Persistencia de conversaciones de chat por sesión (cierra G5 / T5.1)."""

    def __init__(self, cfg: Any) -> None:
        self.db_path = cfg.data_dir / "chat.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS chat_messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT, role TEXT, "
            "content TEXT, time TEXT)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS chat_sessions ("
            "session TEXT PRIMARY KEY, title TEXT, created TEXT, last TEXT)"
        )
        self.conn.commit()

    def new_session(self, title: str = "chat") -> str:
        import uuid

        sid = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO chat_sessions (session, title, created, last) VALUES (?,?,?,?)",
            (sid, title, now, now),
        )
        self.conn.commit()
        return sid

    def add(self, session: str, role: str, content: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session, title, created, last) "
            "VALUES (?,?,?,?)", (session, "chat", now, now)
        )
        self.conn.execute(
            "INSERT INTO chat_messages (session, role, content, time) VALUES (?,?,?,?)",
            (session, role, content, now),
        )
        self.conn.execute(
            "UPDATE chat_sessions SET last=? WHERE session=?", (now, session)
        )
        self.conn.commit()

    def history(self, session: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT role, content, time FROM chat_messages WHERE session=? "
            "ORDER BY id ASC LIMIT ?",
            (session, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"], "time": r["time"]} for r in rows]

    def sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT session, title, created, last FROM chat_sessions ORDER BY last DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session: str) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT session, title, created, last FROM chat_sessions WHERE session=?",
            (session,),
        ).fetchone()
        return dict(row) if row else None
