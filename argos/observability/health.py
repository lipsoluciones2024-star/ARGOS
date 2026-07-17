from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class HealthCheck:
    name: str
    fn: Callable[[], Dict[str, Any]]
    critical: bool = True


class HealthRegistry:
    """Registro de health checks profundos para /health/deep y observabilidad."""

    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}

    def register(self, name: str, fn: Callable[[], Dict[str, Any]], critical: bool = True) -> None:
        self._checks[name] = HealthCheck(name=name, fn=fn, critical=critical)

    def run(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        status = "ok"
        for name, check in self._checks.items():
            try:
                detail = check.fn()
                detail = detail or {}
                results[name] = {"status": detail.get("status", "ok"), **detail}
                if check.critical and results[name]["status"] != "ok":
                    status = "degraded"
            except Exception as exc:
                results[name] = {"status": "error", "error": str(exc)}
                if check.critical:
                    status = "degraded"
        results["status"] = status
        return results


health = HealthRegistry()
