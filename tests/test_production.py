from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argos.config import Config, SwitchLevel
from argos.detection.alerts import ACTION_CATALOG
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.response.orchestrator import ResponseOrchestrator
from argos.server import AppContext, create_app
from argos.storage.settings import SettingsStore
from argos.storage.store import AlertStore, AuditLog, EventStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def make_cfg(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    return cfg


@pytest.fixture
def client(tmp_path):
    cfg = make_cfg(tmp_path)
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    return TestClient(app)


# ---------------- Settings ----------------
def test_settings_defaults_and_overlay(tmp_path):
    cfg = make_cfg(tmp_path)
    s = SettingsStore(cfg)
    assert s.get_bool("ai.enabled") is True
    assert s.get_int("retention_days", 0) == 90
    assert s.get_str("ai.mode") == "hybrid"
    s.set("ai.temperature", 0.5)
    assert s.get_float("ai.temperature") == 0.5
    s.set("switch.default", "SEMI-AUTO")
    assert s.get_str("switch.default") == "SEMI-AUTO"
    assert "ai.temperature" in s.as_dict()


# ---------------- Response actions (no stubs) ----------------
def test_actions_are_real_not_stubs(tmp_path):
    cfg = make_cfg(tmp_path)
    from argos.response.actions import execute_action

    res = execute_action(cfg, "kill_process", "999999")
    assert isinstance(res, dict)
    assert "rc" in res

    iso = execute_action(cfg, "isolate_host", "host-1")
    assert isinstance(iso, dict) and "isolated" in iso

    bad = execute_action(cfg, "memory_snapshot", "not-a-pid")
    assert isinstance(bad, dict) and "error" in bad

    rev = execute_action(cfg, "revert_registry", "HKLM:\\Software\\Argos", {})
    assert isinstance(rev, dict)
    assert "requires a stored baseline snapshot" not in str(rev)

    dis = execute_action(cfg, "disable_account", "ghostuser")
    assert isinstance(dis, dict) and "rc" in dis


def test_all_seven_actions_present(tmp_path):
    cfg = make_cfg(tmp_path)
    ro = ResponseOrchestrator(cfg, AuditLog(cfg))
    assert {a["action"] for a in ro.catalog()} == set(ACTION_CATALOG)
    assert len(ACTION_CATALOG) == 7


# ---------------- Scheduler metrics ----------------
def test_scheduler_metrics(tmp_path):
    cfg = make_cfg(tmp_path)
    store = EventStore(cfg)
    store.ingest(OcsfEvent(category=EventCategory.NETWORK, host="h1", dst_ip="1.2.3.4", attack_id="T1071"))
    ctx = AppContext(cfg)
    m = ctx.scheduler.snapshot_metrics()
    assert m["total_events"] == 1
    assert m["top_hosts"][0]["host"] == "h1"
    assert m["by_category"].get("network") == 1
    assert "attck_covered" in m and "attck_total" in m


def test_scheduler_purges_old(tmp_path):
    cfg = make_cfg(tmp_path)
    store = EventStore(cfg)
    old = OcsfEvent(category=EventCategory.PROCESS, host="h1", time="2020-01-01T00:00:00Z")
    store.ingest(old)
    assert store.count() == 1
    assert store.purge_old() == 1
    assert store.count() == 0


# ---------------- Admin endpoints ----------------
def test_settings_endpoints(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200 and "ai.enabled" in r.json()
    r2 = client.put("/api/v1/settings", json={"ai.temperature": 0.75})
    assert r2.status_code == 200
    assert r2.json()["ai.temperature"] == 0.75


def test_metrics_rules_hosts_status_logs(client):
    assert client.get("/api/v1/metrics").status_code == 200
    assert client.get("/api/v1/rules").status_code == 200
    assert client.get("/api/v1/hosts").status_code == 200
    assert client.get("/api/v1/ai/status").status_code == 200
    assert client.get("/api/v1/logs").status_code == 200


def test_switch_persists_to_settings(client):
    client.post("/api/v1/switch", json={"level": "SEMI-AUTO"})
    assert client.get("/api/v1/settings").json()["switch.default"] == "SEMI-AUTO"
    client.post("/api/v1/switch", json={"level": "OBSERVE"})


# ---------------- Streaming orchestrator ----------------
class _FakeResp:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def test_orchestrator_stream_yields_tokens(client):
    orch = client.app.state.ctx.orchestrator

    def fake_stream(messages, tools=None, runtime=None):
        yield _FakeResp(content="Hola ")
        yield _FakeResp(content="mundo")

    orch.router.stream = fake_stream
    out = list(orch.chat_stream("hola", []))
    types = [c["type"] for c in out]
    assert "begin" in types and "token" in types and "done" in types
    tokens = "".join(c["content"] for c in out if c["type"] == "token")
    assert tokens == "Hola mundo"


def test_orchestrator_stream_with_tool_call(client):
    orch = client.app.state.ctx.orchestrator
    from argos.ai.client import ToolCall

    state = {"n": 0}

    def fake_stream(messages, tools=None, runtime=None):
        state["n"] += 1
        if state["n"] == 1:
            yield _FakeResp(tool_calls=[ToolCall(id="c1", name="list_alerts", arguments={})])
        else:
            yield _FakeResp(content="respuesta final")

    orch.router.stream = fake_stream
    out = list(orch.chat_stream("analiza", []))
    assert any(c["type"] == "tool" for c in out)
    assert out[-1]["type"] == "done"
    assert "respuesta final" in out[-1]["content"]
