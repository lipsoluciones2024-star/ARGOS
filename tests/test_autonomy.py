from __future__ import annotations

from pathlib import Path

from argos.ai.client import ToolCall
from argos.autonomy.limits import ActionLimiter
from argos.config import Config
from argos.server import AppContext

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _ctx(tmp_path):
    cfg = Config()
    cfg.root = PROJECT_ROOT
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.require_auth = False
    return AppContext(cfg)


def test_action_limiter_global_and_cooldown(tmp_path):
    lim = ActionLimiter(max_per_hour=2, cooldown_per_host_sec=100)
    assert lim.allow("h1") is True
    assert lim.allow("h1") is False  # cooldown per host
    assert lim.allow("h2") is True
    assert lim.allow("h3") is False  # global max/hora
    lim.reset()
    assert lim.allow("h1") is True


def test_investigator_proposes_on_high_alert(tmp_path):
    ctx = _ctx(tmp_path)
    # Forzar SUGGEST para que la propuesta quede 'pending' y sea detectable.
    ctx.response.set_level(__import__("argos.config", fromlist=["SwitchLevel"]).SwitchLevel.SUGGEST)

    alert = {
        "id": "a1", "host": "h1", "title": "C2 beacon", "attack_id": "T1071",
        "summary": "conexión sospechosa a IP maliciosa", "severity": "high",
    }
    inv = ctx.autonomy.investigator

    # Router falso que llama a propose_block_ip (simula razonamiento del LLM).
    class _FakeResp:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    def fake_chat(messages, tools=None, runtime=None):
        return _FakeResp(tool_calls=[ToolCall(id="c1", name="propose_block_ip",
                                            arguments={"ip": "185.220.101.1"})])

    inv.orch.router.chat = fake_chat
    result = inv.investigate(alert)
    assert result["host"] == "h1"
    assert any(p["action"] == "block_ip" for p in result["proposals"])
    pid = next(p["id"] for p in result["proposals"])
    assert any(p.id == pid for p in ctx.response.pending_proposals())


def test_autonomy_loop_processes_alert(tmp_path):
    ctx = _ctx(tmp_path)
    loop = ctx.autonomy
    loop.enabled = True

    class _FakeResp:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    def fake_chat(messages, tools=None, runtime=None):
        return _FakeResp(content="dictamen de prueba")

    loop.investigator.orch.router.chat = fake_chat
    import asyncio

    async def run():
        await loop._process({"id": "x", "host": "h9", "title": "test", "attack_id": "T1059"})
        return ctx.autonomy.processed

    loop2 = asyncio.new_event_loop()
    try:
        got = loop2.run_until_complete(run())
    finally:
        loop2.close()
    assert got == 1
