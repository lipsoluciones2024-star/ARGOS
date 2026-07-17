from __future__ import annotations

from argos.ai.prompts import (
    build_agent_messages,
    get_analysis_prompt,
    get_correlation_prompt,
    get_few_shot,
    get_system_prompt,
)
from argos.ai.prompts.safety import SAFETY_LAYER, safety_reminder
from argos.ai.prompts.specialized import specialized_prompt


def test_system_prompt_contains_context():
    p = get_system_prompt("commander", {"host": "WIN-01"})
    assert "WIN-01" in p
    assert "Commander" in p


def test_agent_instructions_variants():
    assert "Red Team" in specialized_prompt("red")
    assert "Blue Team" in specialized_prompt("blue")
    assert "Purple" in specialized_prompt("purple")


def test_safety_layer_present():
    assert "autonomia" in SAFETY_LAYER.lower()
    assert isinstance(safety_reminder(), str)


def test_analysis_prompt_renders_event():
    out = get_analysis_prompt({"host": "h1", "severity": "high"})
    assert "h1" in out


def test_correlation_prompt_renders_events():
    out = get_correlation_prompt([{"host": "h1"}, {"host": "h2"}])
    assert "h1" in out and "h2" in out


def test_few_shot_returns_list():
    fs = get_few_shot()
    assert isinstance(fs, list) and len(fs) > 0


def test_build_agent_messages_shape():
    msgs = build_agent_messages("blue", "analiza", use_few_shot=False)
    assert msgs[0]["role"] == "system"
    assert SAFETY_LAYER in msgs[0]["content"]
    assert msgs[-1]["role"] == "user"
