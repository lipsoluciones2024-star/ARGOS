from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

from argos.ai.tools.registry import ToolExecutor


class ACPMessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    STATUS = "status"
    CANCEL = "cancel"


@dataclass
class ACPMessage:
    """Mensaje estandarizado del Agent Client Protocol (ACP)."""

    type: ACPMessageType
    sender: str
    recipient: str
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ACPMessage":
        return cls(
            type=ACPMessageType(data.get("type", "task")),
            sender=data.get("sender", "unknown"),
            recipient=data.get("recipient", "unknown"),
            task_id=data.get("task_id", uuid.uuid4().hex),
            session_id=data.get("session_id", ""),
            payload=data.get("payload", {}) or {},
            timestamp=data.get("timestamp", time.time()),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class ACPClient:
    """Cliente ACP que envía tareas y espera resultados de forma síncrona/local."""

    def __init__(self, agent_id: str, executor: ToolExecutor) -> None:
        self.agent_id = agent_id
        self.executor = executor

    def send_task(
        self,
        recipient: str,
        action: str,
        arguments: Dict[str, Any],
        role: str = "admin",
        session_id: str = "",
    ) -> ACPMessage:
        msg = ACPMessage(
            type=ACPMessageType.TASK,
            sender=self.agent_id,
            recipient=recipient,
            session_id=session_id,
            payload={"action": action, "arguments": arguments, "role": role},
        )
        return msg

    def handle(self, msg: ACPMessage) -> ACPMessage:
        """Procesa un mensaje entrante y produce la respuesta correspondiente."""
        if msg.type == ACPMessageType.TASK:
            action = msg.payload.get("action", "")
            arguments = msg.payload.get("arguments", {})
            role = msg.payload.get("role", "admin")
            result = self.executor.execute(action, arguments, role=role)
            return ACPMessage(
                type=ACPMessageType.RESULT,
                sender=self.agent_id,
                recipient=msg.sender,
                task_id=msg.task_id,
                session_id=msg.session_id,
                payload={"output": getattr(result, "output", result)},
            )
        if msg.type == ACPMessageType.CANCEL:
            return ACPMessage(
                type=ACPMessageType.STATUS,
                sender=self.agent_id,
                recipient=msg.sender,
                task_id=msg.task_id,
                session_id=msg.session_id,
                payload={"status": "cancelled"},
            )
        return ACPMessage(
            type=ACPMessageType.ERROR,
            sender=self.agent_id,
            recipient=msg.sender,
            task_id=msg.task_id,
            session_id=msg.session_id,
            payload={"error": f"tipo de mensaje no manejable: {msg.type.value}"},
        )
