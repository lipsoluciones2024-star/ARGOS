from __future__ import annotations

import pytest
from argos.config import Config
from argos.detection.alerts import Alert
from argos.detection.behavioral import AnomalyConfig, AnomalyDetector, BehavioralBaselineStore
from argos.detection.ti_correlation import ThreatIntelCorrelator, enrich_event
from argos.detection.ti_feeds import classify, is_ip, load_feeds
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.security.rbac_advanced import Permission, Role, has_permission, is_valid_role, permissions_for
from argos.server import AppContext
from argos.storage.ui_prefs import UiPrefsStore


def _event(host="h1", process="powershell.exe", dst="8.8.8.8"):
    return OcsfEvent(
        category=EventCategory.PROCESS, host=host, process_name=process,
        src_ip="10.0.0.5", dst_ip=dst, attack_id="T1059.001",
    )


def test_behavioral_baseline_flags_novel_process():
    store = BehavioralBaselineStore()
    for _ in range(5):
        store.train([_event(process="cmd.exe"), _event(process="services.exe")])
    assert store.score(_event(process="cmd.exe")) == 0.0
    assert store.score(_event(process="ransomware.exe")) > 0.0


def test_anomaly_detector_emits_alert():
    store = BehavioralBaselineStore()
    store.train([_event(process="cmd.exe") for _ in range(5)])
    det = AnomalyDetector(store, AnomalyConfig(threshold=0.3, enabled=True))
    alert = det.evaluate(_event(process="neverseen.exe"))
    assert isinstance(alert, Alert)
    assert alert.source == "behavioral"


def test_ti_correlation_hits_ioc():
    cfg = Config()
    from argos.detection.threat_intel import ThreatIntel

    intel = ThreatIntel(cfg)
    intel.add("8.8.8.8")
    corr = ThreatIntelCorrelator(intel).correlate(_event(dst="8.8.8.8"))
    assert corr.hit
    enriched = enrich_event(_event(dst="8.8.8.8"), intel)
    assert "threat_intel" in enriched


def test_ti_feeds_and_classify():
    feeds = load_feeds()
    assert len(feeds) >= 1
    assert is_ip("1.2.3.4")
    assert classify("evil.com") == "domain"
    assert classify("http://x.com/p") == "url"


def test_rbac_advanced_permissions():
    assert has_permission("admin", Permission.EXECUTE_ACTIONS)
    assert not has_permission("operator", Permission.EXECUTE_ACTIONS)
    assert has_permission("superadmin", Permission.SYSTEM_ADMIN)
    assert Permission.MANAGE_PLUGINS in permissions_for("admin")
    assert is_valid_role("analyst")
    assert not is_valid_role("god")


def test_acp_client_roundtrip():
    from argos.ai.acp import ACPClient, ACPMessage, ACPMessageType
    from argos.ai.tools.registry import ToolExecutor
    from argos.detection.threat_intel import ThreatIntel
    from argos.storage.store import EventStore
    from argos.detection.engine import DetectionEngine

    cfg = Config()
    store = EventStore(cfg)
    engine = DetectionEngine(cfg)
    intel = ThreatIntel(cfg)
    exec = ToolExecutor(store, engine, intel)
    client = ACPClient("agent-a", exec)
    msg = client.send_task("agent-b", "list_alerts", {"limit": 3})
    assert msg.type == ACPMessageType.TASK
    resp = client.handle(msg)
    assert resp.type == ACPMessageType.RESULT


def test_mcp_adapter_lists_tools():
    from argos.ai.mcp import MCPServer
    from argos.ai.tools.registry import ToolExecutor
    from argos.detection.threat_intel import ThreatIntel
    from argos.storage.store import EventStore
    from argos.detection.engine import DetectionEngine

    cfg = Config()
    exec = ToolExecutor(EventStore(cfg), DetectionEngine(cfg), ThreatIntel(cfg))
    srv = MCPServer(exec)
    tools = srv.list_tools()
    assert len(tools) >= 1
    assert any(t.name == "list_alerts" for t in tools)


def test_ui_prefs_persist():
    cfg = Config()
    store = UiPrefsStore(cfg)
    out = store.update({"ui.density": "compact", "ui.layout": "wide"})
    assert out["ui.density"] == "compact"
    again = store.get_all()
    assert again["ui.density"] == "compact"


def test_appcontext_exposes_refactor_components():
    cfg = Config()
    ctx = AppContext(cfg)
    assert ctx.gateway is not None
    assert ctx.mcp is not None
    assert ctx.ui_prefs is not None
    assert ctx.detection_hook is not None
