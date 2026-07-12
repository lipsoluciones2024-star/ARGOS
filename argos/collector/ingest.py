from __future__ import annotations

from argos.collector.buffer import LocalBuffer
from argos.collector.normalize import Normalizer
from argos.config import Config
from argos.ocsf import OcsfEvent
from argos.storage.store import EventStore


class Collector:
    def __init__(self, cfg: Config, store: EventStore) -> None:
        self.cfg = cfg
        self.store = store
        self.normalizer = Normalizer()

    def ingest_raw(self, raw_events: list[dict]) -> int:
        events = [self.normalizer.normalize(r) for r in raw_events]
        return self.store.ingest_many(events)

    def ingest_events(self, events: list[OcsfEvent]) -> int:
        return self.store.ingest_many(events)

    def flush_agent_buffer(self, buffer: LocalBuffer) -> int:
        pending = buffer.pending()
        if not pending:
            return 0
        n = self.ingest_events(pending)
        buffer.ack(n)
        return n
