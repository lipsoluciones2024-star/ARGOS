"""Launcher enterprise de ARGOS.

Arranca el servidor API + dashboard y el agente recolector como subprocess
ocultos (sin ventanas de consola sueltas), espera a que el servidor responda
el healthcheck y luego abre el navegador en la URL del dashboard.

Uso:
    python tools/launch.py [--no-browser] [--no-agent]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


def wait_for_health(host: str, port: int, timeout: float = 30.0) -> bool:
    import urllib.request

    url = f"http://{host}:{port}/api/v1/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def popen_hidden(module: str, env: dict[str, str], log_name: str) -> subprocess.Popen:
    pythonw = sys.executable
    log_path = ROOT / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logf = open(log_path, "a", encoding="utf-8")
    # CREATE_NO_WINDOW evita la consola suelta en Windows.
    flags = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.Popen(
        [pythonw, "-m", module],
        cwd=str(ROOT),
        env=env,
        stdout=logf,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-agent", action="store_true")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    env = load_env()
    host = args.host or env.get("ARGOS_SERVER_HOST", "127.0.0.1")
    port = args.port or int(env.get("ARGOS_SERVER_PORT", "8000"))

    print(f"[ARGOS] Arrancando servicios (host={host}, port={port})...")
    server = popen_hidden("argos.server", env, "server.out.log")
    print(f"[ARGOS] Servidor PID={server.pid} (log: logs/server.out.log)")

    agent = None
    if not args.no_agent:
        agent = popen_hidden("argos.agent", env, "agent.out.log")
        print(f"[ARGOS] Agente PID={agent.pid} (log: logs/agent.out.log)")

    print("[ARGOS] Esperando healthcheck del servidor...")
    if not wait_for_health(host, port):
        print("[ARGOS] ERROR: el servidor no respondió a tiempo. Revisa logs/server.out.log")
        return 1

    url = f"http://{host}:{port}/"
    print(f"[ARGOS] Servidor listo en {url}")
    if not args.no_browser:
        print("[ARGOS] Abriendo dashboard en el navegador...")
        webbrowser.open(url)
    print("[ARGOS] Todo iniciado. Cierre este launcher para detener los servicios.")
    try:
        server.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (server, agent):
            if p and p.poll() is None:
                p.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
