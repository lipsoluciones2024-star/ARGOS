from __future__ import annotations

import sqlite3

from argos import get_config
from argos.config import Config
from argos.ocsf import OcsfEvent
from argos.security.auth import derive_secret, sign_token, verify_token
from argos.server import create_app
from fastapi.testclient import TestClient


def _client(tmp_path, require_auth=False):
    cfg = get_config()
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = require_auth
    return TestClient(create_app(cfg))


def test_ws_chat_gateway_down_returns_controlled_message(tmp_path):
    """Modo avion (gateway/local caidos): el chat WS devuelve mensaje controlado (T3.4 / T6.3)."""
    cfg = get_config()
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    cfg.gateway_base_url = "http://127.0.0.1:1/no-gateway"
    cfg.local_base_url = "http://127.0.0.1:1/no-local"
    with TestClient(create_app(cfg)) as c:
        with c.websocket_connect("/ws") as ws:
            ws.send_json({"type": "chat", "message": "hola"})
            msg = ws.receive_json()
            assert msg["type"] == "chat"
            assert isinstance(msg["content"], str) and len(msg["content"]) > 0
            # No debe ser una excepcion cruda sin tratarar; menciona el fallo controlado
            assert "[ARGOS]" in msg["content"]


def test_audit_chain_survives_corruption(tmp_path):
    """Cadena de auditoria verificable; corrupta el ultimo hash y falla (T6.3)."""
    from argos.storage.store import AuditLog

    cfg = Config()
    cfg.data_dir = tmp_path / "audit_data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    a = AuditLog(cfg)
    a.append("x", "ai", "sys", "ok", {"v": 1})
    a.append("y", "ai", "sys", "ok", {"v": 2})
    assert a.verify_chain() is True
    # Corromper el hash del ultimo registro
    db_path = cfg.data_dir / "audit.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE audit SET hash='deadbeef' WHERE seq=(SELECT MAX(seq) FROM audit)")
    conn.commit()
    conn.close()
    assert AuditLog(cfg).verify_chain() is False


def test_buffer_resilient_under_load(tmp_path):
    """El buffer local tolera muchos eventos sin crashear (T6.3)."""
    from argos.collector.buffer import LocalBuffer

    b = LocalBuffer(Config(data_dir=tmp_path))
    evs = [OcsfEvent(category="process", host="h", process_name="x")]
    for _ in range(500):
        b.push(evs)
    assert b.size() >= 500
    b.ack(b.size())
    assert b.size() == 0


def test_auth_token_roles(tmp_path):
    secret = derive_secret("test-secret", "salt")
    admin = sign_token(secret, "admin", sub="a")
    op = sign_token(secret, "operator", sub="o")

    assert verify_token(admin, secret)["role"] == "admin"
    assert verify_token(op, secret)["role"] == "operator"
