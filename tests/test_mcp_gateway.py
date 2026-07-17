from __future__ import annotations

import pytest

from argos.ai.tools.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from argos.ai.tools.registry import ToolExecutor
from argos.ai.tools.gateway import ToolGateway, ToolGatewayConfig
from argos.ai.tools.retry import with_retry, with_timeout
from argos.config import Config
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.storage.store import EventStore
from argos.mcp.server import MCPServer
from argos.mcp.protocol import MCPError


@pytest.fixture()
def executor():
    cfg = Config()
    store = EventStore(cfg)
    engine = DetectionEngine(cfg)
    intel = ThreatIntel(cfg)
    return ToolExecutor(store, engine, intel)


def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, timeout=10))

    def boom():
        raise ValueError("x")

    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(boom)
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(boom)


def test_circuit_breaker_recovers():
    import time

    cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, timeout=0.01, success_threshold=1))
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    # abierto
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(lambda: 1)
    # tras timeout pasa a half-open y un exito cierra
    time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state.value == "closed"


def test_with_retry_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("temp")
        return "done"

    assert with_retry(flaky, None) == "done"
    assert calls["n"] == 3


def test_with_timeout_raises():
    import time

    with pytest.raises(TimeoutError):
        with_timeout(lambda: time.sleep(1), 0.05)


def test_gateway_executes_real_tool(executor):
    gw = ToolGateway(executor, ToolGatewayConfig(rate_limit_per_min=1000))
    out = gw.execute("query_events", {"limit": 1}, role="admin")
    assert out.get("ok") is True
    assert "output" in out


def test_gateway_blocks_missing_permission(executor):
    gw = ToolGateway(executor, ToolGatewayConfig(enforce_permissions=True))
    # operator no tiene permiso 'execute'
    out = gw.execute("propose_block_ip", {"ip": "1.2.3.4"}, role="operator")
    assert out.get("ok") is False
    assert "permiso" in out.get("error", "").lower()


def test_gateway_metrics_recorded(executor):
    gw = ToolGateway(executor, ToolGatewayConfig(rate_limit_per_min=1000))
    gw.execute("query_events", {"limit": 1}, role="admin")
    snap = gw.metrics()
    assert "query_events" in snap["tools"]
    assert snap["tools"]["query_events"]["calls"] >= 1


def test_mcp_tools_list(executor):
    srv = MCPServer(executor)
    resp = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert "error" not in resp
    assert len(resp["result"]["tools"]) > 0


def test_mcp_ping(executor):
    srv = MCPServer(executor)
    resp = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert resp["result"]["status"] == "pong"


def test_mcp_invalid_method(executor):
    srv = MCPServer(executor)
    resp = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})
    assert resp["error"]["code"] == MCPError.METHOD_NOT_FOUND


def test_mcp_tool_call_returns_content(executor):
    srv = MCPServer(executor)
    resp = srv.handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "query_events", "arguments": {"limit": 1}},
    })
    assert "error" not in resp
    assert "content" in resp["result"]
