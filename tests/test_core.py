from __future__ import annotations

from pathlib import Path

from argos.config import Config, SwitchLevel
from argos.detection.alerts import ACTION_CATALOG
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.ocsf import EventCategory, OcsfEvent
from argos.response.orchestrator import ResponseOrchestrator
from argos.response.switch import AutonomySwitch, Decision
from argos.storage.store import AlertStore, AuditLog, EventStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def make_cfg(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def test_event_store_ingest_and_query(tmp_path):
    cfg = make_cfg(tmp_path)
    store = EventStore(cfg)
    ev = OcsfEvent(category=EventCategory.NETWORK, host="h1", dst_ip="1.2.3.4", attack_id="T1071")
    store.ingest(ev)
    assert store.count() == 1
    out = store.query(filters={"category": "network"})
    assert len(out) == 1
    assert out[0].dst_ip == "1.2.3.4"


def test_event_store_full_text(tmp_path):
    cfg = make_cfg(tmp_path)
    store = EventStore(cfg)
    store.ingest(OcsfEvent(category=EventCategory.PROCESS, host="h1",
                           process_cmdline="powershell.exe -enc ABCD"))
    res = store.query(filters={"text": "powershell"})
    assert len(res) == 1


def test_audit_hash_chain_verifies(tmp_path):
    cfg = make_cfg(tmp_path)
    audit = AuditLog(cfg)
    audit.append("kill_process", "ai", "user", "executed", {"pid": 123})
    audit.append("block_ip", "ai", "user", "denied", {})
    assert audit.verify_chain() is True


def test_switch_levels():
    sw = AutonomySwitch(SwitchLevel.OBSERVE)
    assert sw.decide("kill_process", "medium") == Decision.DENY
    sw.set_level(SwitchLevel.SUGGEST)
    assert sw.decide("kill_process", "medium") == Decision.CONFIRM
    sw.set_level(SwitchLevel.SEMI_AUTO)
    assert sw.decide("block_ip", "low") == Decision.EXECUTE
    assert sw.decide("kill_process", "medium") == Decision.CONFIRM


def test_response_catalog_has_seven_actions(tmp_path):
    cfg = make_cfg(tmp_path)
    ro = ResponseOrchestrator(cfg, AuditLog(cfg))
    assert len(ro.catalog()) == 7
    assert set(ACTION_CATALOG) == {a["action"] for a in ro.catalog()}


def test_response_observe_denies(tmp_path):
    cfg = make_cfg(tmp_path)
    audit = AuditLog(cfg)
    ro = ResponseOrchestrator(cfg, audit, AutonomySwitch(SwitchLevel.OBSERVE))
    p = ro.propose("kill_process", "999")
    assert p.status == "denied"


def test_response_suggest_requires_confirm(tmp_path):
    cfg = make_cfg(tmp_path)
    audit = AuditLog(cfg)
    ro = ResponseOrchestrator(cfg, audit, AutonomySwitch(SwitchLevel.SUGGEST))
    p = ro.propose("kill_process", "999")
    assert p.status == "pending"
    p2 = ro.confirm(p.id, "soc-analyst")
    assert p2.status == "executed"


def test_sigma_rule_match(tmp_path):
    cfg = make_cfg(tmp_path)
    engine = DetectionEngine(cfg)
    ev = OcsfEvent(category=EventCategory.PROCESS, host="h1",
                   process_image=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                   process_cmdline="powershell.exe -EncodedCommand JABjAD0A")
    alerts = engine.evaluate(ev)
    assert any(a.title == "PowerShell Encoded Command" for a in alerts)


def test_attack_coverage_blind_spots(tmp_path):
    cfg = make_cfg(tmp_path)
    engine = DetectionEngine(cfg)
    cov = engine.coverage()
    assert cov["total"] >= 1
    assert cov["covered"] <= cov["total"]
    assert any(v["status"] == "blind-spot" for v in cov["matrix"].values())
    assert "T1059" in cov["matrix"]


def test_privacy_guard_redacts_secret():
    from argos.ai.privacy import has_secret, scrub_secrets

    text = "api_key=sk-1234567890abcdef"
    assert has_secret(text)
    assert "sk-1234567890abcdef" not in scrub_secrets(text)


def test_tool_executor_read_and_action_tools(tmp_path):
    from argos.ai.tools import ALLOWED_TOOLS, ToolExecutor

    cfg = make_cfg(tmp_path)
    store = EventStore(cfg)
    engine = DetectionEngine(cfg, alert_store=AlertStore(cfg))

    intel = ThreatIntel(cfg)
    intel.feed_sample()
    ex = ToolExecutor(store, engine, intel)
    read_tools = {
        "query_events", "get_process_tree", "get_active_connections",
        "list_alerts", "lookup_ioc", "explain_attck_technique",
    }
    action_tools = {
        "propose_kill_process", "propose_block_ip", "propose_quarantine_file",
        "propose_revert_registry", "propose_disable_account",
        "propose_isolate_host", "propose_memory_snapshot",
    }
    new_tools = {
        "get_hosts", "get_host_detail", "alerts_by_host", "get_audit_log",
        "pending_proposals", "query_fim_events", "ip_reputation",
        "detection_rules", "get_coverage", "undo_action", "notify", "run_playbook",
        "network_recon", "scan_yara", "correlate",
    }
    assert read_tools <= ALLOWED_TOOLS
    assert action_tools <= ALLOWED_TOOLS
    assert new_tools <= ALLOWED_TOOLS
    assert len(ALLOWED_TOOLS) == len(read_tools) + len(action_tools) + len(new_tools)
    assert ex.validate("query_events") is True
    assert ex.validate("propose_kill_process") is True
    assert ex.validate("rm_tree") is False
    res = ex.execute("lookup_ioc", {"indicator": "185.220.101.1"})
    assert res.output["malicious"] is True
