from __future__ import annotations

import os
import platform
import time

import httpx

from argos import get_config
from argos.agent.realtime import RealtimeCollector
from argos.agent.sources import common
from argos.agent.sources.fim import FimStore, collect_fim
from argos.agent.sources.kernel_exfil import collect_kernel_exfil
from argos.agent.sources.lotl import collect_lotl
from argos.agent.sources.persistence import collect_persistence
from argos.agent.sources.usb import UsbTracker
from argos.collector.buffer import LocalBuffer
from argos.logging_setup import setup_logging
from argos.ocsf import OcsfEvent


def collect_all(host: str, cfg, fim_store: FimStore, usb_tracker: UsbTracker) -> list[OcsfEvent]:
    events: list[OcsfEvent] = []
    sources = set(cfg.agent_sources)
    if "process" in sources:
        events.extend(common.collect_processes(host))
    if "network" in sources:
        events.extend(common.collect_network(host))
    if "logon" in sources:
        events.extend(common.collect_logons(host))
    if "persistence" in sources:
        events.extend(collect_persistence(host))
    if "fim" in sources and cfg.fim_enabled:
        events.extend(collect_fim(host, fim_store, cfg.fim_paths))
    if "usb" in sources:
        events.extend(usb_tracker.scan(host))
    if "lotl" in sources:
        events.extend(collect_lotl(host))
    if "kernel_exfil" in sources:
        events.extend(collect_kernel_exfil(host))
    return events


def _agent_token() -> str | None:
    return os.environ.get("ARGOS_AGENT_TOKEN") or os.environ.get("ARGOS_API_TOKEN") or None


def send_to_server(cfg, events: list[OcsfEvent]) -> bool:
    url = f"http://{cfg.server_host}:{cfg.server_port}/api/v1/ingest"
    headers = {"Content-Type": "application/json"}
    token = _agent_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json={"events": [e.model_dump() for e in events]}, headers=headers)
            return r.status_code == 200
    except Exception:
        return False


def run() -> None:
    cfg = get_config()
    logger = setup_logging(cfg, "argos.agent")
    buffer = LocalBuffer(cfg)
    fim_store = FimStore(cfg.data_dir / "fim.db")
    usb_tracker = UsbTracker(cfg.data_dir / "usb.db")
    host = platform.node()
    logger.info("ARGOS agent started on host %s (sources=%s, realtime=%s)", host, cfg.agent_sources, cfg.realtime_enabled)

    def cycle() -> list[OcsfEvent]:
        return collect_all(host, cfg, fim_store, usb_tracker)

    def flush(events: list[OcsfEvent]) -> None:
        if not events:
            return
        buffer.push(events)
        pending = buffer.pending()
        if send_to_server(cfg, pending):
            buffer.ack(len(pending))

    if cfg.realtime_enabled:
        rt = RealtimeCollector(lambda: collect_all(host, cfg, fim_store, usb_tracker), flush, cfg.realtime_interval)
        rt.start()
        try:
            while True:
                time.sleep(cfg.agent_poll_interval)
        except KeyboardInterrupt:
            rt.stop()
    else:
        while True:
            try:
                events = cycle()
                buffer.push(events)
                logger.info("collected %d events (buffer pending=%d)", len(events), buffer.size())
                if send_to_server(cfg, buffer.pending()):
                    buffer.ack(buffer.size())
            except Exception as exc:  # pragma: no cover
                logger.error("agent loop error: %s", exc)
            time.sleep(cfg.agent_poll_interval)


def main() -> None:
    run()
