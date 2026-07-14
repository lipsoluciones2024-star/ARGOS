from __future__ import annotations

from typing import Any, Optional


class ContextRetriever:
    """Recupera contexto histórico relevante (RAG-lite) para chat/investigación (T5.3)."""

    def __init__(self, memory: Any, chatlog: Any) -> None:
        self.memory = memory
        self.chatlog = chatlog

    def build(self, query: str, session: Optional[str] = None, limit: int = 4) -> str:
        parts: list[str] = []
        try:
            facts = self.memory.recall(query, limit=limit)
            for f in facts:
                head = f"[{f.get('time','')}] investigación en {f.get('host','?')}"
                if f.get("attack_id"):
                    head += f" ({f['attack_id']})"
                body = f.get('verdict', '')
                if f.get('summary'):
                    body += f" — {f['summary']}"
                parts.append(f"{head}: {body}")
        except Exception:
            pass
        if session:
            try:
                recent = self.chatlog.history(session, limit=6)
                for m in recent[-6:]:
                    if m["role"] in ("user", "assistant"):
                        parts.append(f"chat({m['role']}): {m['content']}")
            except Exception:
                pass
        if not parts:
            return ""
        return "CONTEXTO HISTÓRICO RELEVANTE:\n" + "\n".join(f"- {p}" for p in parts)
