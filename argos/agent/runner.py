from __future__ import annotations

import platform
import time

import httpx

from argos import get_config
from argos.agent.sources.common import collect_logons, collect_network, collect_processes
from argos.collector.buffer import LocalBuffer
from argos.logging_setup import setup_logging
from argos.ocsf import OcsfEvent


def collect_all(host: str) -> list[OcsfEvent]:
    events: list[OcsfEvent] = []
    events.extend(collect_processes(host))
    events.extend(collect_network(host))
    events.extend(collect_logons(host))
    return events


def send_to_server(cfg, events: list[OcsfEvent]) -> bool:
    url = f"http://{cfg.server_host}:{cfg.server_port}/api/v1/ingest"
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=[e.model_dump() for e in events])
            return r.status_code == 200
    except Exception:
        return False


def run() -> None:
    cfg = get_config()
    logger = setup_logging(cfg, "argos.agent")
    buffer = LocalBuffer(cfg)
    host = platform.node()
    logger.info("ARGOS agent started on host %s", host)
    while True:
        try:
            events = collect_all(host)
            buffer.push(events)
            logger.info("collected %d events (buffer pending=%d)", len(events), buffer.size())
            if send_to_server(cfg, buffer.pending()):
                buffer.ack(buffer.size())
        except Exception as exc:  # pragma: no cover
            logger.error("agent loop error: %s", exc)
        time.sleep(cfg.agent_poll_interval)


def main() -> None:
    run()
