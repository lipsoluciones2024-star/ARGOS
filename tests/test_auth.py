from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argos.config import Config
from argos.security import derive_secret, role_sufficient, sign_token, verify_token
from argos.security.auth import AuthError
from argos.server import AppContext, create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def auth_client(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = True
    cfg.api_token = "static-admin-token"
    cfg.auth_secret = "test-secret"
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    return TestClient(app)


def test_token_sign_and_verify():
    secret = derive_secret("mysecret", "salt")
    tok = sign_token(secret, "operator", sub="alice")
    claims = verify_token(tok, secret)
    assert claims["role"] == "operator"
    assert claims["sub"] == "alice"


def test_token_wrong_secret_rejected():
    secret = derive_secret("a", "s")
    tok = sign_token(secret, "admin")
    with pytest.raises(AuthError):
        verify_token(tok, derive_secret("b", "s"))


def test_static_admin_token_is_admin():
    secret = derive_secret("x", "s")
    claims = verify_token("static-admin-token", secret, static_admin_token="static-admin-token")
    assert claims["role"] == "admin"


def test_role_sufficient():
    assert role_sufficient("admin", "operator")
    assert not role_sufficient("operator", "admin")


def test_unauthenticated_rejected(auth_client):
    r = auth_client.post("/api/v1/ingest", json={"events": []})
    assert r.status_code == 401


def test_authenticated_ingest_works(auth_client):
    r = auth_client.post(
        "/api/v1/ingest", json={"events": []},
        headers={"Authorization": "Bearer static-admin-token"},
    )
    assert r.status_code == 200


def test_operator_cannot_change_switch(auth_client):
    secret = derive_secret("test-secret", str(auth_client.app.state.ctx.cfg.data_dir))
    op_token = sign_token(secret, "operator", sub="bob")
    r = auth_client.post(
        "/api/v1/switch", json={"level": "FULL-AUTO"},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert r.status_code == 403


def test_admin_can_change_switch(auth_client):
    r = auth_client.post(
        "/api/v1/switch", json={"level": "SUGGEST"},
        headers={"Authorization": "Bearer static-admin-token"},
    )
    assert r.status_code == 200
    assert r.json()["level"] == "SUGGEST"


def test_rate_limit_kicks_in(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = True
    cfg.api_token = "tok"
    cfg.rate_limit_per_hour = 1
    ctx = AppContext(cfg)
    app = create_app(cfg)
    app.state.ctx = ctx
    client = TestClient(app)
    h = {"Authorization": "Bearer tok"}
    assert client.get("/api/v1/events", headers=h).status_code == 200
    assert client.get("/api/v1/events", headers=h).status_code == 429


def test_health_is_public(auth_client):
    assert auth_client.get("/api/v1/health").status_code == 200
