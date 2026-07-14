from __future__ import annotations

from pathlib import Path

from argos.ai.context import ContextRetriever
from argos.config import Config
from argos.storage.chatlog import ChatLog
from argos.storage.memory import MemoryStore


def _cfg(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.data_dir = tmp_path / "data"
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def test_chatlog_add_and_history(tmp_path):
    cl = ChatLog(_cfg(tmp_path))
    cl.add("s1", "user", "hola")
    cl.add("s1", "assistant", "respuesta")
    hist = cl.history("s1")
    assert [m["role"] for m in hist] == ["user", "assistant"]
    assert hist[0]["content"] == "hola"


def test_chatlog_sessions(tmp_path):
    cl = ChatLog(_cfg(tmp_path))
    cl.add("s1", "user", "a")
    cl.add("s2", "user", "b")
    sessions = {s["session"] for s in cl.sessions()}
    assert sessions == {"s1", "s2"}


def test_chatlog_persists_cold(tmp_path):
    cfg = _cfg(tmp_path)
    cl1 = ChatLog(cfg)
    cl1.add("s1", "user", "x")
    cl2 = ChatLog(cfg)
    assert cl2.history("s1")[0]["content"] == "x"


def test_memory_investigations(tmp_path):
    ms = MemoryStore(_cfg(tmp_path))
    iid = ms.add_investigation(
        host="h1", alert_id="a1", attack_id="T1059",
        verdict="malicious", summary="powershell download",
    )
    invs = ms.investigations()
    assert any(i["id"] == iid for i in invs)
    rec = ms.recall("powershell")
    assert any("powershell" in (r.get("summary", "") + r.get("verdict", "")) for r in rec)


def test_memory_action_outcomes(tmp_path):
    ms = MemoryStore(_cfg(tmp_path))
    ms.add_action_outcome(proposal_id="p1", action="block_ip", target="1.2.3.4",
                          status="executed", outcome="ok")
    outs = ms.outcomes()
    assert any(o["action"] == "block_ip" for o in outs)


def test_memory_feedback_rate(tmp_path):
    ms = MemoryStore(_cfg(tmp_path))
    ms.add_feedback("action", "block_ip", "good")
    ms.add_feedback("action", "block_ip", "bad")
    score = ms.rate_for("block_ip")
    assert score == 0.0


def test_context_retriever(tmp_path):
    ms = MemoryStore(_cfg(tmp_path))
    ms.add_investigation(
        host="h1", alert_id="a1", attack_id="T1059",
        verdict="malicious", summary="certutil download c2",
    )
    cr = ContextRetriever(ms, None)
    ctx = cr.build("¿hubo descarga con certutil?")
    assert "certutil" in ctx
