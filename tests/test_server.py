from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argos.config import Config, SwitchLevel
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.server import AppContext, create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
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
    assert "T1059.001" in r.json()


def test_audit_immutable(client):
    client.post("/api/v1/switch", json={"level": "SUGGEST"})
    p = client.post("/api/v1/propose", json={"action": "block_ip", "target": "5.6.7.8"})
    client.post("/api/v1/confirm", json={"id": p.json()["id"], "approved_by": "analyst"})
    r = client.get("/api/v1/audit")
    assert any("block_ip" in a["action"] for a in r.json())
