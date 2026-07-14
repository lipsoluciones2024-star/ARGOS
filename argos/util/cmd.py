from __future__ import annotations

import subprocess
from typing import Any


def run_command(cmd: list[str], timeout: float = 30) -> dict[str, Any]:
    """Ejecuta un comando externo de forma segura y devuelve un resultado estructurado.

    Devuelve ``{"rc", "stdout", "stderr", "error"}``. En caso de excepción ``rc`` es ``-1``
    y ``error`` contiene el mensaje. Se usa desde el recolector de agentes y desde el
    motor de respuesta, evitando duplicar la lógica de ``subprocess.run``.
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "rc": r.returncode,
            "stdout": (r.stdout or "")[:4000],
            "stderr": (r.stderr or "")[:4000],
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - cualquier fallo se reporta como dict
        return {"rc": -1, "stdout": "", "stderr": "", "error": str(exc)}
