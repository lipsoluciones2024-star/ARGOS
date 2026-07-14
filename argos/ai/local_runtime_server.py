from __future__ import annotations

import shutil
import subprocess
import time
from typing import Optional
from urllib.parse import urlparse

from argos.ai.router import LocalRuntime
from argos.config import Config


class LocalRuntimeServer:
    """Levanta un server OpenAI-compatible (p.ej. llama.cpp) como subproceso
    para servir el modelo GGUF localmente. Fail-safe: si el binario no existe
    o no arranca, registra y no rompe el arranque del servidor."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.proc: Optional[subprocess.Popen] = None
        self._runtime = LocalRuntime(cfg)

    def _port(self) -> tuple[str, int]:
        u = urlparse(self.cfg.local_base_url)
        return u.hostname or "127.0.0.1", u.port or 8080

    def _build_cmd(self) -> list[str]:
        host, port = self._port()
        bin_name = self.cfg.local_server_bin
        model = str(self.cfg.model_dir() / self.cfg.local_model_path)
        return [bin_name, "-m", model, "--host", host, "--port", str(port)]

    def available(self) -> bool:
        try:
            return self._runtime.available()
        except Exception:
            return False

    def start(self, timeout: float = 60.0) -> bool:
        if not self.cfg.local_autoserve:
            return False
        bin_name = self.cfg.local_server_bin.split()[0]
        if shutil.which(bin_name) is None:
            print(
                f"[local-runtime] binario '{bin_name}' no encontrado en PATH. "
                f"El cerebro local no se auto-servirá (usarás gateway). "
                f"Instala llama.cpp/llama-server o define ARGOS_LOCAL_SERVER_BIN."
            )
            return False
        cmd = self._build_cmd()
        print(f"[local-runtime] arrancando: {' '.join(cmd)}")
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            print(f"[local-runtime] no se pudo arrancar: {exc}")
            self.proc = None
            return False
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.available():
                print("[local-runtime] listo en " + self.cfg.local_base_url)
                return True
            time.sleep(1.0)
        print("[local-runtime] timeout esperando al server local; se continuará sin él.")
        return False

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
