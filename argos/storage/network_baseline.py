from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from argos.config import Config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NetworkBaselineStore:
    """Línea de base y monitoreo continuo de red por host (SQLite, WAL).

    Permite fijar la superficie de puertos esperada de un host y detectar,
    en cada escaneo de monitoreo, puertos nuevos (exposición) y conexiones
    salientes nuevas a IPs externas (posible C2 / exfiltración).
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "network_baseline.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS net_baselines (
                host TEXT PRIMARY KEY,
                open_ports TEXT NOT NULL,
                services TEXT NOT NULL,
                snapshot_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS net_targets (
                host TEXT PRIMARY KEY,
                added_at TEXT NOT NULL,
                added_by TEXT
            );
            CREATE TABLE IF NOT EXISTS net_scans (
                id TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                open_ports TEXT NOT NULL,
                services TEXT NOT NULL,
                external_conns TEXT NOT NULL,
                scanned_at TEXT NOT NULL,
                new_ports TEXT NOT NULL,
                closed_ports TEXT NOT NULL,
                new_connections TEXT NOT NULL,
                baseline_state TEXT NOT NULL DEFAULT 'diff'
            );
            CREATE INDEX IF NOT EXISTS idx_net_scans_host ON net_scans(host);
            CREATE INDEX IF NOT EXISTS idx_net_scans_time ON net_scans(scanned_at);
            """
        )
        self.conn.commit()

    # ---- targets (hosts monitoreados) ----
    def add_target(self, host: str, by: str = "system") -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO net_targets (host, added_at, added_by) VALUES (?,?,?)",
            (host, _now(), by),
        )
        self.conn.commit()

    def remove_target(self, host: str) -> bool:
        cur = self.conn.execute("DELETE FROM net_targets WHERE host=?", (host,))
        self.conn.commit()
        return cur.rowcount > 0

    def list_targets(self) -> list[str]:
        rows = self.conn.execute("SELECT host FROM net_targets ORDER BY host").fetchall()
        return [r["host"] for r in rows]

    # ---- baseline ----
    def set_baseline(self, host: str, open_ports: list[int],
                     services: dict[int, str]) -> dict[str, Any]:
        self.conn.execute(
            "INSERT OR REPLACE INTO net_baselines (host, open_ports, services, snapshot_at) "
            "VALUES (?,?,?,?)",
            (host, json.dumps(sorted(set(open_ports))), json.dumps(services), _now()),
        )
        self.conn.commit()
        self.add_target(host, by="baseline")
        return self.get_baseline(host)  # type: ignore[return-value]

    def get_baseline(self, host: str) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM net_baselines WHERE host=?", (host,)
        ).fetchone()
        if not row:
            return None
        return {
            "host": row["host"],
            "open_ports": json.loads(row["open_ports"]),
            "services": json.loads(row["services"]),
            "snapshot_at": row["snapshot_at"],
        }

    def list_baselines(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM net_baselines ORDER BY host"
        ).fetchall()
        return [{
            "host": r["host"],
            "open_ports": json.loads(r["open_ports"]),
            "services": json.loads(r["services"]),
            "snapshot_at": r["snapshot_at"],
        } for r in rows]

    # ---- scans / diff ----
    def record_scan(self, host: str, open_ports: list[int],
                    services: dict[int, str],
                    external_conns: Optional[list[dict[str, Any]]] = None,
                    scan_id: Optional[str] = None) -> dict[str, Any]:
        external_conns = external_conns or []
        open_ports = sorted(set(open_ports))
        baseline = self.get_baseline(host)
        if baseline is None:
            self.set_baseline(host, open_ports, services)
            diff: dict[str, Any] = {
                "host": host, "baseline_state": "initialized",
                "new_ports": [], "closed_ports": [],
                "new_connections": [], "open_ports": open_ports,
            }
        else:
            # El drift se calcula contra el último escaneo real (no contra la
            # base dorada) para no re-alertar indefinidamente sobre lo ya visto.
            prev_ports = set(self._last_scan_open_ports(host)) or set(baseline["open_ports"])
            new_ports = [p for p in open_ports if p not in prev_ports]
            closed_ports = [p for p in prev_ports if p not in set(open_ports)]
            # Las conexiones externas previas se reconstruyen del último scan.
            prev = self._last_scan_external(host)
            prev_keys = {self._conn_key(c) for c in prev}
            new_connections = [
                c for c in external_conns
                if self._conn_key(c) not in prev_keys
            ]
            diff = {
                "host": host, "baseline_state": "diff",
                "new_ports": new_ports, "closed_ports": closed_ports,
                "new_connections": new_connections, "open_ports": open_ports,
            }
        self._insert_scan(host, open_ports, services, external_conns, diff, scan_id)
        return diff

    def _insert_scan(self, host: str, open_ports: list[int],
                     services: dict[int, str],
                     external_conns: list[dict[str, Any]], diff: dict[str, Any],
                     scan_id: Optional[str]) -> None:
        import uuid

        sid = scan_id or uuid.uuid4().hex[:16]
        self.conn.execute(
            "INSERT OR REPLACE INTO net_scans "
            "(id, host, open_ports, services, external_conns, scanned_at, "
             " new_ports, closed_ports, new_connections, baseline_state) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, host, json.dumps(open_ports), json.dumps(services),
             json.dumps(external_conns), _now(),
             json.dumps(diff.get("new_ports", [])),
             json.dumps(diff.get("closed_ports", [])),
             json.dumps(diff.get("new_connections", [])),
             diff.get("baseline_state", "diff")),
        )
        self.conn.commit()

    def _last_scan_open_ports(self, host: str) -> list[int]:
        row = self.conn.execute(
            "SELECT open_ports FROM net_scans WHERE host=? "
            "ORDER BY scanned_at DESC LIMIT 1", (host,)
        ).fetchone()
        if not row:
            return []
        return json.loads(row["open_ports"] or "[]")

    def _last_scan_external(self, host: str) -> list[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT external_conns FROM net_scans WHERE host=? "
            "ORDER BY scanned_at DESC LIMIT 1", (host,)
        ).fetchone()
        if not row:
            return []
        return json.loads(row["external_conns"] or "[]")

    @staticmethod
    def _conn_key(c: dict[str, Any]) -> tuple:
        return (c.get("protocol"), c.get("remote_addr"), c.get("remote_port"),
                c.get("local_addr"), c.get("local_port"))

    def list_scans(self, host: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        if host:
            rows = self.conn.execute(
                "SELECT * FROM net_scans WHERE host=? ORDER BY scanned_at DESC LIMIT ?",
                (host, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM net_scans ORDER BY scanned_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._scan_row(r) for r in rows]

    def get_changes(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM net_scans WHERE baseline_state='diff' "
            "ORDER BY scanned_at DESC LIMIT ?", (limit * 4,)
        ).fetchall()
        changes = []
        for r in rows:
            d = self._scan_row(r)
            if d["new_ports"] or d["new_connections"]:
                changes.append(d)
            if len(changes) >= limit:
                break
        return changes

    def _scan_row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["open_ports"] = json.loads(d.pop("open_ports") or "[]")
        d["services"] = json.loads(d.pop("services") or "{}")
        d["external_conns"] = json.loads(d.pop("external_conns") or "[]")
        d["new_ports"] = json.loads(d.pop("new_ports") or "[]")
        d["closed_ports"] = json.loads(d.pop("closed_ports") or "[]")
        d["new_connections"] = json.loads(d.pop("new_connections") or "[]")
        return d
