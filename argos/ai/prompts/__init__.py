from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Compatibilidad con el sistema legacy (argos.ai.prompts.FEW_SHOT / system_prompt).
_legacy = Path(__file__).resolve().parent.parent / "prompts_legacy.py"
import importlib.util

_spec = importlib.util.spec_from_file_location("_argos_prompts_legacy", _legacy)
assert _spec is not None and _spec.loader is not None
_legacy_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy_mod)
sys.modules.setdefault("argos.ai.prompts._legacy", _legacy_mod)

FEW_SHOT = _legacy_mod.FEW_SHOT
system_prompt = _legacy_mod.system_prompt

from argos.ai.prompts.few_shot import get_few_shot
from argos.ai.prompts.grok4_system import (
    get_analysis_prompt,
    get_correlation_prompt,
    get_system_prompt,
)
from argos.ai.prompts.safety import SAFETY_CHECKLIST, SAFETY_LAYER, safety_reminder
from argos.ai.prompts.specialized import (
    CHAIN_OF_THOUGHT,
    CONTEXT_MANAGEMENT_GUIDE,
    context_management_guide,
    specialized_prompt,
)

__all__ = [
    "get_system_prompt",
    "get_analysis_prompt",
    "get_correlation_prompt",
    "get_few_shot",
    "specialized_prompt",
    "safety_reminder",
    "SAFETY_LAYER",
    "SAFETY_CHECKLIST",
    "CHAIN_OF_THOUGHT",
    "CONTEXT_MANAGEMENT_GUIDE",
    "context_management_guide",
    "build_agent_messages",
]


def build_agent_messages(
    agent: str,
    user_message: str,
    context: Optional[Dict] = None,
    use_few_shot: bool = True,
) -> List[Dict[str, Any]]:
    """Construye el listado de mensajes (system + few-shot + user) para un agente.

    Combina el system prompt Grok 4, la capa de seguridad, el prompt especializado,
    la guia de CoT/contexto y los few-shot examples. Mantiene compatibilidad con el
    formato de mensajes esperado por la API de chat (OpenAI-style).
    """
    system = get_system_prompt(agent, context)
    system = f"{system}\n\n{SAFETY_LAYER}\n\n{specialized_prompt(agent)}\n\n{CHAIN_OF_THOUGHT}\n{CONTEXT_MANAGEMENT_GUIDE}"

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    if use_few_shot:
        messages.extend(get_few_shot())
    messages.append({"role": "user", "content": user_message})
    return messages
