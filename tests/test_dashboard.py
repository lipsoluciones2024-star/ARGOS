from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argos.config import Config, LlmMode
from argos.server import AppContext, create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    cfg.llm_mode = LlmMode.LOCAL
    cfg.local_base_url = "http://127.0.0.1:9/v1"  # nada escuchando: fallback rapido y offline
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    return TestClient(app)


def test_dashboard_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "ARGOS" in r.text
    assert "/static/js/app.js" in r.text


def test_dashboard_static_assets(client):
    for path in ("/static/js/app.js", "/static/css/layout.css"):
        r = client.get(path)
        assert r.status_code == 200


def test_ws_chat_roundtrip(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "message": "hola argos"})
        msg = ws.receive_json()
        assert msg["type"] == "chat"
        assert msg["role"] == "assistant"
        assert isinstance(msg["content"], str) and len(msg["content"]) > 0


def test_ws_switch_and_proposal_flow(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "switch", "level": "SUGGEST"})
        switched = ws.receive_json()
        assert switched["type"] == "switch"
        assert switched["level"] == "SUGGEST"

        # Proponer una acción via REST y confirmarla via WS (human-in-the-loop)
        p = client.post("/api/v1/propose", json={"action": "block_ip", "target": "1.2.3.4"})
        pid = p.json()["id"]
        assert p.json()["status"] == "pending"

        ws.send_json({"type": "confirm", "id": pid, "approved_by": "operator"})
        # El servidor hace broadcast del proposal actualizado
        proposal = ws.receive_json()
        assert proposal["type"] == "proposal"
        assert proposal["status"] == "executed"
