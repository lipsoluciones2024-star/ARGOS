from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from argos.ai.router import HybridRouter, LocalRuntime
from argos.config import Config, LlmMode
from argos.server import AppContext

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_LOCAL_RESP = {
    "id": "chatcmpl-local",
    "object": "chat.completion",
    "model": "local-gguf",
    "choices": [{"index": 0, "message": {"role": "assitant", "content": "respuesta local"},
                "finish_reason": "stop"}],
}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silenciar
        pass

    def do_GET(self):
        if self.path.endswith("/v1/models"):
            body = json.dumps({"data": [{"id": "local-gguf"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        self.rfile.read(ln)
        body = json.dumps(_LOCAL_RESP).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def local_server():
    srv = HTTPServer(("127.0.0.1", 8099), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:8099/v1"
    srv.shutdown()


def _cfg(tmp_path, **kw):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def test_local_runtime_available(local_server, tmp_path):
    cfg = _cfg(tmp_path, local_base_url=local_server)
    rt = LocalRuntime(cfg)
    assert rt.available() is True
    resp = rt.chat([], model="local-gguf")
    assert resp.content == "respuesta local"


def test_offline_local_mode_works(local_server, tmp_path):
    cfg = _cfg(tmp_path, llm_mode=LlmMode.LOCAL, local_base_url=local_server)
    ctx = AppContext(cfg)
    resp = ctx.orchestrator.router.chat([], runtime={"mode": "local", "model": "local-gguf"})
    assert resp.content == "respuesta local"
    assert ctx.orchestrator.router.channel() == "local"


def test_fallback_to_local_when_gateway_down(local_server, tmp_path):
    cfg = _cfg(tmp_path, llm_mode=LlmMode.HYBRID, local_base_url=local_server)
    # Gateway con URL imposible para forzar fallo.
    cfg.gateway_base_url = "http://127.0.0.1:1/nope"
    router = HybridRouter(cfg)

    def fake_gateway_chat(*a, **k):
        raise RuntimeError("gateway caído")

    router.gateway.chat = fake_gateway_chat
    resp = router.chat([], runtime={"mode": "hybrid"})
    assert resp.content == "respuesta local"
    assert router.channel() == "local-fallback"


def test_local_runtime_server_no_binary_is_safe(tmp_path):
    from argos.ai.local_runtime_server import LocalRuntimeServer

    cfg = _cfg(tmp_path, local_server_bin="this-binary-does-not-exist-xyz")
    srv = LocalRuntimeServer(cfg)
    assert srv.start() is False  # no rompe, devuelve False
    srv.stop()
