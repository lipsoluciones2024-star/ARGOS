from __future__ import annotations

import pytest

from argos.plugins.base import HookEvent, PluginManifest, PluginSource
from argos.plugins.hooks.base import BaseHook
from argos.plugins.hooks.lifecycle import PreDetectionHook
from argos.plugins.marketplace import MARKETPLACE
from argos.plugins.registry import PluginRegistry, registry_from_marketplace


def test_marketplace_loaded():
    assert len(MARKETPLACE.plugins) >= 9


def test_registry_from_marketplace_loads_plugins():
    reg = registry_from_marketplace()
    names = {p.name for p in reg.plugins.values()}
    assert "events-query" in names
    assert "event-correlation" in names


def test_plugin_manifest_roundtrip():
    m = PluginManifest(
        name="x", version="1.2.3", category="analytics",
        entry_point="argos.plugins.compat:ThreatIntelPlugin",
        source=PluginSource(type="local", path="./x"),
    )
    d = m.to_dict()
    m2 = PluginManifest.from_dict(d)
    assert m2.name == m.name
    assert m2.version == m.version
    assert m2.source.type == "local"


def test_hooks_execute_in_priority_order():
    reg = PluginRegistry()
    calls: list[str] = []

    class Hook(BaseHook):
        def __init__(self, tag: str, prio: int) -> None:
            super().__init__(HookEvent.PRE_DETECTION, prio)
            self.tag = tag

        def execute(self, context):
            calls.append(self.tag)
            return context

    reg.register_plugin(_fake_plugin("low", Hook("low", 5)))
    reg.register_plugin(_fake_plugin("high", Hook("high", 50)))
    reg.execute_hooks(HookEvent.PRE_DETECTION, {"event": {}})
    assert calls == ["high", "low"]


def test_pre_detection_hook_enriches():
    hook = PreDetectionHook()
    out = hook.execute({"event": {"host": "h1"}})
    assert out.get("enriched") is True


def test_hook_exception_does_not_propagate():
    reg = PluginRegistry()

    class Boom(BaseHook):
        def __init__(self) -> None:
            super().__init__(HookEvent.ON_ALERT, 10)

        def execute(self, context):
            raise RuntimeError("boom")

    reg.register_plugin(_fake_plugin("boom", Boom()))
    # No debe lanzar
    reg.execute_hooks(HookEvent.ON_ALERT, {"alert": {}})


def _fake_plugin(name: str, hook: BaseHook):
    from argos.plugins.base import PluginComponent
    from argos.plugins.registry import PluginInstance

    man = PluginManifest(
        name=name, entry_point=None,
        components=PluginComponent(hooks=[hook.event.value]),
    )
    inst = PluginInstance(man, [hook])
    return inst
