from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from argos.config import Config, SwitchLevel
from argos.detection.alerts import ACTION_CATALOG
from argos.response.actions import action_risk, execute_action, undo_action
from argos.response.switch import AutonomySwitch, Decision
from argos.storage.memory import MemoryStore
from argos.storage.store import AuditLog


@dataclass
class Proposal:
    id: str
    action: str
    target: str
    proposed_by: str
    params: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[dict[str, Any]] = None


class ResponseOrchestrator:
    def __init__(self, cfg: Config, audit: AuditLog, switch: AutonomySwitch | None = None,
                 memory: MemoryStore | None = None) -> None:
        self.cfg = cfg
        self.audit = audit
        self.switch = switch or AutonomySwitch(cfg.default_switch)
        self.memory = memory
        self._proposals: dict[str, Proposal] = {}

    def propose(self, action: str, target: str, proposed_by: str = "ai", params: dict[str, Any] | None = None) -> Proposal:
        if action not in ACTION_CATALOG:
            raise ValueError(f"unknown action {action}")
        risk = action_risk(action)
        decision = self.switch.decide(action, risk)
        pid = uuid.uuid4().hex
        proposal = Proposal(id=pid, action=action, target=target, proposed_by=proposed_by, params=params or {})
        self._proposals[pid] = proposal
        if decision == Decision.DENY:
            proposal.status = "denied"
            self.audit.append(action, proposed_by, "system", "denied",
                              {"target": target, "risk": risk, "reason": "OBSERVE mode: no execution"})
        elif decision == Decision.EXECUTE:
            self._execute(proposal, approved_by="switch:SEMI-AUTO/FULL-AUTO")
        else:
            self.audit.append(action, proposed_by, "pending", "proposed", {"target": target, "risk": risk})
        return proposal

    def confirm(self, proposal_id: str, approved_by: str) -> Proposal:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError("unknown proposal")
        if proposal.status != "pending":
            return proposal
        self._execute(proposal, approved_by=approved_by)
        return proposal

    def _execute(self, proposal: Proposal, approved_by: str) -> None:
        if self.switch.level == SwitchLevel.FULL_AUTO:
            self.audit.append(proposal.action, proposal.proposed_by, approved_by, "executing-full-auto",
                              {"target": proposal.target, "risk": action_risk(proposal.action),
                               "warning": "FULL-AUTO is for lab/testing only"})
        try:
            result = execute_action(self.cfg, proposal.action, proposal.target, proposal.params)
            proposal.result = result
            proposal.status = "executed"
            self.audit.append(proposal.action, proposal.proposed_by, approved_by, "executed",
                              {"target": proposal.target, "risk": action_risk(proposal.action), "result": result})
            self._record_outcome(proposal, "executed", str(result))
        except Exception as exc:
            proposal.status = "error"
            self.audit.append(proposal.action, proposal.proposed_by, approved_by, "error",
                              {"target": proposal.target, "error": str(exc)})
            self._record_outcome(proposal, "error", str(exc))

    def _record_outcome(self, proposal: Proposal, status: str, outcome: str) -> None:
        if self.memory:
            try:
                self.memory.add_action_outcome(proposal.id, proposal.action, proposal.target, status, outcome)
            except Exception:
                pass

    def set_level(self, level: SwitchLevel) -> None:
        self.switch.set_level(level)
        self.audit.append("set_switch_level", "admin", "admin", "executed", {"level": level.value})

    def force_execute(self, action: str, target: str, params: dict[str, Any] | None, by: str) -> Proposal:
        if action not in ACTION_CATALOG:
            raise ValueError(f"unknown action {action}")
        pid = uuid.uuid4().hex
        proposal = Proposal(id=pid, action=action, target=target, proposed_by=by, params=params or {})
        self._proposals[pid] = proposal
        self.audit.append(action, by, by, "manual-trigger",
                          {"target": target, "risk": action_risk(action)})
        self._execute(proposal, approved_by=by)
        return proposal

    def reject(self, proposal_id: str, by: str) -> Proposal:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError("unknown proposal")
        if proposal.status != "pending":
            return proposal
        proposal.status = "rejected"
        self.audit.append(proposal.action, proposal.proposed_by, by, "rejected",
                          {"target": proposal.target})
        return proposal

    def undo(self, proposal_id: str, by: str) -> tuple[Proposal, dict[str, Any]]:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError("unknown proposal")
        if proposal.status != "executed":
            raise ValueError("solo se puede deshacer una acción ejecutada")
        result = undo_action(self.cfg, proposal.action, proposal.target, proposal.params,
                             proposal.result)
        proposal.status = "undone"
        self.audit.append(proposal.action, proposal.proposed_by, by, "undone",
                          {"target": proposal.target, "result": result})
        return proposal, result

    def pending_proposals(self) -> list[Proposal]:
        return [p for p in self._proposals.values() if p.status == "pending"]

    def all_proposals(self) -> list[Proposal]:
        return list(self._proposals.values())

    def catalog(self) -> list[dict[str, str]]:
        return [{"action": a, "risk": action_risk(a)} for a in ACTION_CATALOG]
