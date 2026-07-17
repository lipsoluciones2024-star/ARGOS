from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from argos.plugins.base import HookEvent


class BaseHook(ABC):
    """Interfaz base para todos los hooks de plugins.

    Un hook enriquece o reacciona a un evento del ciclo de vida de ARGOS.
    Debe ser seguro: cualquier excepción se captura en el registry y no
    debe interrumpir el flujo principal.
    """

    def __init__(self, event: HookEvent, priority: int = 10) -> None:
        self.event = event
        self.priority = priority
        self.enabled = True

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """Ejecuta la lógica del hook. Puede devolver un contexto modificado."""
        raise NotImplementedError

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def __repr__(self) -> str:
        return f"<{type(self).__name__} event={self.event.value} priority={self.priority}>"
