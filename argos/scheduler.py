from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from argos.config import Config
from argos.storage.settings import SettingsStore


class Scheduler:
    """Background housekeeping: retention purge, behavioral baseline training,
    proactive AI alert push, threat-intel refresh and live metrics snapshot."""

    def __init__(self, ctx: Any, settings: SettingsStore) -> None:
        self.ctx = ctx
        self.settings = settings
        self.cfg: Config = ctx.cfg
        self._task: Optional[asyncio.Task] = None
        self.last_run: Optional[str] = None
        self.run_count: int = 0
        self.purged_total: int = 0
        self.metrics: dict[str, Any] = {}
        self.recent_errors: list[str] = []

    def enabled(self) -> bool:
        return self.settings.get_bool("scheduler.enabled", True)

    async def start(self) -> None:
        if not self.enabled():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                self.run_once()
            except Exception as exc:  # keep the scheduler alive
                self.recent_errors.append(f"{datetime.now(timezone.utc).isoformat()} {exc}")
                self.recent_errors = self.recent_errors[-20:]
            interval = self.settings.get_int("scheduler.interval_sec", 60)
            await asyncio.sleep(max(5, interval))

    def run_once(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        purged = self.ctx.store.purge_old()
        self.purged_total += purged
        result["purged"] = purged

        if not self.ctx.engine.baseline.trained:
            events = self.ctx.store.query(limit=2000)
            self.ctx.engine.train_baseline(events)
            result["baseline_trained"] = len(events)

        try:
            self.ctx.intel.feed_sample()
        except Exception:
            pass

        pushed = self.ctx.orchestrator.push_high_alerts()
        result["proactive_alerts"] = len(pushed)

        try:
            self._network_monitor()
        except Exception as exc:  # keep the scheduler alive
            self.recent_errors.append(f"{datetime.now(timezone.utc).isoformat()} {exc}")
            self.recent_errors = self.recent_errors[-20:]

        self.metrics = self.snapshot_metrics()
        self.last_run = datetime.now(timezone.utc).isoformat()
        self.run_count += 1
        return result

    def _network_monitor(self) -> None:
        """Monitoreo continuo de red: escanea hosts en la lista de monitoreo y
        compara contra su línea de base (Fase K). Desactivado por defecto."""
        if not self.settings.get_bool("network_monitor.enabled", False):
            return
        interval = self.settings.get_int("network_monitor.interval_ticks", 1)
        if interval > 1 and (self.run_count % interval) != 0:
            return
        targets = self.ctx.net_baseline.list_targets()
        if not targets:
            return
        from argos.scan.monitor import run_monitor_scan

        for host in targets:
            try:
                run_monitor_scan(self.ctx, host, by="scheduler")
            except Exception as exc:  # do not break the loop on a single host
                self.recent_errors.append(
                    f"{datetime.now(timezone.utc).isoformat()} net_monitor {host}: {exc}"
                )
                self.recent_errors = self.recent_errors[-20:]

    def snapshot_metrics(self) -> dict[str, Any]:
        store = self.ctx.store
        total = store.count()
        series = store.time_series(hours=24)
        sev_counter: Counter[str] = Counter()
        for row in series:
            sev_counter[row["severity"]] += row["count"]
        recent = store.query(limit=500)
        hosts = Counter(e.host for e in recent if e.host)
        top_hosts = [{"host": h, "events": c} for h, c in hosts.most_common(10)]
        cats = Counter(e.category for e in recent if e.category)
        coverage = self.ctx.engine.coverage()
        matrix = coverage.get("matrix", {})
        covered = sum(1 for v in matrix.values() if v.get("status") == "covered")
        blind = sum(1 for v in matrix.values() if v.get("status") == "blind-spot")
        return {
            "total_events": total,
            "by_severity": dict(sev_counter),
            "by_category": dict(cats),
            "top_hosts": top_hosts,
            "series_24h": series,
            "attck_covered": covered,
            "attck_total": len(matrix),
            "attck_blind_spots": blind,
            "alerts_high": len(self.ctx.alert_store.high_or_critical(limit=50)),
            "switch": self.ctx.response.switch.level.value,
            "ai_channel": self.ctx.orchestrator.channel(),
            "retention_days": self.settings.get_int("retention_days", self.cfg.retention_days),
            "scheduler_runs": self.run_count,
            "last_run": self.last_run,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
