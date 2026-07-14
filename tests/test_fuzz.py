from __future__ import annotations

from argos import get_config
from argos.config import SwitchLevel
from argos.server import create_app
from fastapi.testclient import TestClient


def _client(tmp_path):
    cfg = get_config()
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    return TestClient(create_app(cfg))


def test_malformed_ingest_does_not_crash(tmp_path):
    """Payloads OCSF malformados no deben producir 500 (T6.9)."""
    with _client(tmp_path) as c:
        payloads = [
            {"events": [{"category": "process"}]},                       # faltan campos obligatorios
            {"events": [{"category": 12345, "host": None}]},             # tipos erroneos
            {"events": "not-a-list"},                                    # estructura incorrecta
            {"events": [{"category": "process", "host": "h", "garbage": {"x": [1, 2]}}]},  # extra ok
            {},                                                          # vacio
            {"events": [{"this": "is", "not": "ocsf"}]},
        ]
        for p in payloads:
            r = c.post("/api/v1/ingest", json=p)
            assert r.status_code in (200, 400, 422), r.status_code
        # el server sigue vivo
        assert c.get("/api/v1/health").status_code == 200


def test_valid_event_still_ingested_among_garbage(tmp_path):
    with _client(tmp_path) as c:
        good = {"category": "process", "host": "h", "process_name": "x"}
        body = {"events": [{"category": "process"}, good, {"nope": True}]}
        r = c.post("/api/v1/ingest", json=body)
        assert r.status_code == 200
        # el server no crashea y al menos ingestó el evento valido
        assert r.json()["ingested"] >= 1


def test_switch_invalid_level_rejected(tmp_path):
    with _client(tmp_path) as c:
        # set_switch via endpoint no expuesto en test; validamos enum directo
        assert SwitchLevel("OBSERVE") == SwitchLevel.OBSERVE
        try:
            SwitchLevel("NOPE")
            assert False, "debia fallar"
        except ValueError:
            pass
