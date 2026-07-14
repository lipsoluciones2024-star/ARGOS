from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from argos.config import Config
from argos.ocsf import OcsfEvent


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class EventStore:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "argos.db"
        self.conn = _connect(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                time TEXT NOT NULL,
                category TEXT NOT NULL,
                host TEXT NOT NULL,
                source TEXT,
                process_name TEXT,
                process_pid INTEGER,
                process_parent_pid INTEGER,
                process_cmdline TEXT,
                process_image TEXT,
                process_hash TEXT,
                src_ip TEXT,
                dst_ip TEXT,
                dst_port INTEGER,
                src_port INTEGER,
                dns TEXT,
                protocol TEXT,
                file_path TEXT,
                file_action TEXT,
                registry_key TEXT,
                registry_action TEXT,
                user TEXT,
                logon_result TEXT,
                attack_id TEXT,
                attack_technique TEXT,
                severity TEXT NOT NULL,
                raw TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(time);
            CREATE INDEX IF NOT EXISTS idx_events_host ON events(host);
            CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
            CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
            CREATE INDEX IF NOT EXISTS idx_events_attack ON events(attack_id);

            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts_ix USING fts5(text, event_id UNINDEXED);
            """
        )
        self.conn.commit()

    def ingest(self, event: OcsfEvent) -> None:
        d = event.as_dict()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO events (
                event_id, time, category, host, source, process_name, process_pid,
                process_parent_pid, process_cmdline, process_image, process_hash,
                src_ip, dst_ip, dst_port, src_port, dns, protocol, file_path,
                file_action, registry_key, registry_action, user, logon_result,
                attack_id, attack_technique, severity, raw
            ) VALUES (
                :event_id, :time, :category, :host, :source, :process_name, :process_pid,
                :process_parent_pid, :process_cmdline, :process_image, :process_hash,
                :src_ip, :dst_ip, :dst_port, :src_port, :dns, :protocol, :file_path,
                :file_action, :registry_key, :registry_action, :user, :logon_result,
                :attack_id, :attack_technique, :severity, :raw
            )
            """,
            {
                "event_id": d["event_id"], "time": d["time"], "category": d["category"],
                "host": d["host"], "source": d["source"], "process_name": d["process_name"],
                "process_pid": d["process_pid"], "process_parent_pid": d["process_parent_pid"],
                "process_cmdline": d["process_cmdline"], "process_image": d["process_image"],
                "process_hash": d["process_hash"], "src_ip": d["src_ip"], "dst_ip": d["dst_ip"],
                "dst_port": d["dst_port"], "src_port": d["src_port"], "dns": d["dns"],
                "protocol": d["protocol"], "file_path": d["file_path"], "file_action": d["file_action"],
                "registry_key": d["registry_key"], "registry_action": d["registry_action"],
                "user": d["user"], "logon_result": d["logon_result"], "attack_id": d["attack_id"],
                "attack_technique": d["attack_technique"], "severity": d["severity"],
                "raw": json.dumps(d.get("raw")) if d.get("raw") is not None else None,
            },
        )
        self.conn.execute(
            "DELETE FROM events_fts_ix WHERE event_id = ?",
            (d["event_id"],),
        )
        self.conn.execute(
            "INSERT INTO events_fts_ix (event_id, text) VALUES (?, ?)",
            (d["event_id"], event.to_fts_text()),
        )
        self.conn.commit()

    def ingest_many(self, events: Iterable[OcsfEvent]) -> int:
        n = 0
        for ev in events:
            self.ingest(ev)
            n += 1
        return n

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def hosts(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT host, COUNT(*) AS c, MAX(time) AS last "
            "FROM events GROUP BY host ORDER BY c DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"host": r["host"], "events": r["c"], "last_seen": r["last"]} for r in rows]

    def query(self, filters: Optional[dict[str, Any]] = None, limit: int = 100, offset: int = 0) -> list[OcsfEvent]:
        filters = filters or {}
        where: list[str] = []
        params: list[Any] = []
        for key in ("category", "host", "source", "severity", "attack_id", "user"):
            if key in filters and filters[key] is not None:
                where.append(f"{key} = ?")
                params.append(filters[key])
        if filters.get("since"):
            where.append("time >= ?")
            params.append(filters["since"])
        if filters.get("text"):
            return self._full_text_query(filters["text"], limit, offset)
        sql = "SELECT * FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def _full_text_query(self, text: str, limit: int, offset: int) -> list[OcsfEvent]:
        ids = self.conn.execute(
            "SELECT event_id FROM events_fts_ix WHERE events_fts_ix MATCH ? "
            "ORDER BY rank LIMIT ? OFFSET ?",
            (text, limit, offset),
        ).fetchall()
        out: list[OcsfEvent] = []
        for r in ids:
            row = self.conn.execute("SELECT * FROM events WHERE event_id = ?", (r["event_id"],)).fetchone()
            if row:
                out.append(self._row_to_event(row))
        return out

    def time_series(self, bucket: str = "hour", category: Optional[str] = None, hours: int = 24) -> list[dict[str, Any]]:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        where = "WHERE time >= ?"
        params: list[Any] = [since]
        if category:
            where += " AND category = ?"
            params.append(category)
        sql = f"""
            SELECT substr(time, 1, {10 if bucket == 'day' else 13 if bucket == 'hour' else 16}) AS b,
                   severity, COUNT(*) AS c
            FROM events {where}
            GROUP BY b, severity ORDER BY b
        """
        rows = self.conn.execute(sql, params).fetchall()
        return [{"bucket": r["b"], "severity": r["severity"], "count": r["c"]} for r in rows]

    def get(self, event_id: str) -> Optional[OcsfEvent]:
        row = self.conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        return self._row_to_event(row) if row else None

    def process_inventory(self, limit: int = 200, host: str | None = None) -> list[dict[str, Any]]:
        """Inventario de procesos únicos derivado de los eventos (process_name/pid/host/imagen)."""
        sql = """
            SELECT process_name, process_pid, host, process_image, process_cmdline, MAX(time) AS last_seen, COUNT(*) AS sightings
            FROM events
            WHERE category='process' AND process_name IS NOT NULL AND process_name <> ''
        """
        params: list[Any] = []
        if host:
            sql += " AND host = ?"
            params.append(host)
        sql += " GROUP BY host, process_name, process_pid ORDER BY sightings DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def active_connections(self) -> list[OcsfEvent]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE category='network' ORDER BY time DESC LIMIT 200"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def process_tree(self, pid: Optional[int] = None) -> list[OcsfEvent]:
        if pid is None:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE category='process' ORDER BY time DESC LIMIT 500"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE category='process' AND (process_pid=? OR process_parent_pid=?) "
                "ORDER BY time DESC LIMIT 500", (pid, pid)
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def purge_old(self) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.cfg.retention_days)).isoformat()
        cur = self.conn.execute("SELECT event_id FROM events WHERE time < ?", (cutoff,))
        ids = [r["event_id"] for r in cur.fetchall()]
        for eid in ids:
            self.conn.execute("DELETE FROM events_fts_ix WHERE event_id=?", (eid,))
        self.conn.execute("DELETE FROM events WHERE time < ?", (cutoff,))
        self.conn.commit()
        return len(ids)

    def _row_to_event(self, row: sqlite3.Row) -> OcsfEvent:
        d = dict(row)
        d.pop("raw", None)
        d["raw"] = {}
        return OcsfEvent(**{k: v for k, v in d.items() if k in OcsfEvent.model_fields})


class AlertStore:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "argos.db"
        self.conn = _connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                time TEXT NOT NULL,
                title TEXT,
                severity TEXT,
                event_id TEXT,
                host TEXT,
                attack_id TEXT,
                attack_technique TEXT,
                summary TEXT,
                source TEXT
            )
            """
        )
        self.conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(alerts)").fetchall()}
        if "acknowledged" not in cols:
            self.conn.execute("ALTER TABLE alerts ADD COLUMN acknowledged INTEGER NOT NULL DEFAULT 0")
        if "acknowledged_by" not in cols:
            self.conn.execute("ALTER TABLE alerts ADD COLUMN acknowledged_by TEXT")
        if "acknowledged_at" not in cols:
            self.conn.execute("ALTER TABLE alerts ADD COLUMN acknowledged_at TEXT")
        self.conn.commit()

    def add(self, alert) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO alerts (id, time, title, severity, event_id, host, attack_id, attack_technique, summary, source) "
            "VALUES (:id, :time, :title, :severity, :event_id, :host, :attack_id, :attack_technique, :summary, :source)",
            alert.as_dict(),
        )
        self.conn.commit()

    def ack(self, alert_id: str, by: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT id FROM alerts WHERE id=?", (alert_id,)).fetchone()
        if not row:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE alerts SET acknowledged=1, acknowledged_by=?, acknowledged_at=? WHERE id=?",
            (by, now, alert_id),
        )
        self.conn.commit()
        return self.get(alert_id)

    def get(self, alert_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["acknowledged"] = bool(d.get("acknowledged"))
        return d

    def recent(self, limit: int = 50, severity: str | None = None) -> list[dict[str, Any]]:
        if severity:
            rows = self.conn.execute(
                "SELECT * FROM alerts WHERE severity=? ORDER BY time DESC LIMIT ?",
                (severity, limit),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM alerts ORDER BY time DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["acknowledged"] = bool(d.get("acknowledged"))
            out.append(d)
        return out

    def high_or_critical(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM alerts WHERE severity IN ('high','critical') ORDER BY time DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["acknowledged"] = bool(d.get("acknowledged"))
            out.append(d)
        return out


class AuditLog:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "audit.db"
        self.conn = _connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL,
                time TEXT NOT NULL,
                action TEXT NOT NULL,
                proposed_by TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT
            )
            """
        )
        self.conn.commit()
        self._chain_head = "0" * 64

    def append(self, action: str, proposed_by: str, approved_by: str, status: str, detail: Optional[dict] = None) -> dict[str, Any]:
        prev = self._read_head()
        record: dict[str, Any] = {
            "prev_hash": prev,
            "time": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "proposed_by": proposed_by,
            "approved_by": approved_by,
            "status": status,
            "detail": detail or {},
        }
        detail_blob = json.dumps(record["detail"], default=str)
        chain_input = prev + record["time"] + action + proposed_by + approved_by + status + detail_blob
        h = hashlib.sha256(chain_input.encode()).hexdigest()
        record["hash"] = h
        self.conn.execute(
            "INSERT INTO audit (prev_hash, hash, time, action, proposed_by, approved_by, status, detail) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (prev, h, record["time"], action, proposed_by, approved_by, status, json.dumps(record["detail"], default=str)),
        )
        self.conn.commit()
        self._chain_head = h
        return record

    def _read_head(self) -> str:
        row = self.conn.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        return row["hash"] if row else self._chain_head

    def verify_chain(self) -> bool:
        cols = "prev_hash, hash, time, action, proposed_by, approved_by, status, detail"
        rows = self.conn.execute(
            f"SELECT {cols} FROM audit ORDER BY seq ASC"
        ).fetchall()
        prev = "0" * 64
        for r in rows:
            expected = hashlib.sha256(
                (prev + r["time"] + r["action"] + r["proposed_by"] + r["approved_by"] + r["status"] + r["detail"]).encode()
            ).hexdigest()
            if expected != r["hash"] or r["prev_hash"] != prev:
                return False
            prev = r["hash"]
        return True

    def all(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM audit ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
