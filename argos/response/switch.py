from __future__ import annotations

from enum import Enum

from argos.config import SwitchLevel


class Decision(str, Enum):
    EXECUTE = "execute"
    CONFIRM = "confirm"
    DENY = "deny"


SEMI_AUTO_APPROVED = {"block_ip", "quarantine_file", "memory_snapshot"}


class AutonomySwitch:
    def __init__(self, initial: SwitchLevel = SwitchLevel.OBSERVE) -> None:
        self.level = initial

    def set_level(self, level: SwitchLevel) -> None:
        self.level = level

    def decide(self, action: str, risk: str) -> Decision:
        if self.level == SwitchLevel.OBSERVE:
            return Decision.DENY
        if self.level == SwitchLevel.SUGGEST:
            return Decision.CONFIRM
        if self.level == SwitchLevel.SEMI_AUTO:
            if action in SEMI_AUTO_APPROVED:
                return Decision.EXECUTE
            return Decision.CONFIRM
        return Decision.EXECUTE

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level.value}
