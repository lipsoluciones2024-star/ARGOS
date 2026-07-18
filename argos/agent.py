"""Recolector ARGOS (agente).

Este agente simula la recolección de telemetría endpoint y la envía al servidor
vía HTTP plano + HMAC (protocolo OCSF firmado) usando el endpoint ``/api/v1/ingest``.

Según el diseño documentado (Docs/Estado_Implementacion.md §5, Fase G), los
sensores nativos ETW/eBPF/ESF son un workstream futuro; el transporte ya está
listo. Este módulo produce un flujo realista de eventos (procesos, red, logon,
persistencia) firmados, de modo que el servidor, la detección y el dashboard
puedan ejercitarse de extremo a extremo sin dependencias de SO.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
import uuid
from typing import Any

import httpx

from argos import get_config
from argos.config import Config
from argos.logging_setup import setup_logging
from argos.ocsf import OcsfEvent


def _make_token(secret: str | None, static_token: str | None) -> str | None:
    """Token Bearer para autenticar el agente contra el servidor.
    Prioriza el token estático; si no, firma uno con el secreto HMAC."""
    if static_token:
        return static_token
    if secret:
        from argos.security.auth import sign_token

        return sign_token(secret, "admin", sub="agent")
    return None


def _sim_process_event(host: str, seed: int) -> dict[str, Any]:
    names = ["powershell.exe", "cmd.exe", "svchost.exe", "explorer.exe",
             "chrome.exe", "python.exe", "lsass.exe", "runtimebroker.exe"]
    name = names[seed % len(names)]
    pid = 1000 + seed * 7
    return {
        "class_uid": 1001,  # Process Activity
        "category_uid": 1,
        "type_uid": 100101,  # Process Create
        "time": int(time.time() * 1000),
        "metadata": {"version": "1.0.0", "product": {"name": "ARGOS Agent"}},
        "host": {"hostname": host},
        "process": {"pid": pid, "name": name,
                    "cmd_line": f"{name} --arg {seed}",
                    "parent_process": {"pid": 500 + seed, "name": "services.exe"}},
    }


def _sim_network_event(host: str, seed: int) -> dict[str, Any]:
    ips = ["8.8.8.8", "1.1.1.1", "192.168.1.50", "10.0.0.12", "203.0.113.7"]
    dst = ips[seed % len(ips)]
    return {
        "class_uid": 1002,  # Network Activity
        "category_uid": 4,
        "type_uid": 100204,  # Network Connection
        "time": int(time.time() * 1000),
        "metadata": {"version": "1.0.0", "product": {"name": "ARGOS Agent"}},
        "host": {"hostname": host},
        "connection_info": {"protocol_name": "tcp"},
        "src_endpoint": {"ip": "127.0.0.1", "port": 40000 + seed},
        "dst_endpoint": {"ip": dst, "port": 443},
    }


def _sim_logon_event(host: str, seed: int) -> dict[str, Any]:
    users = ["SYSTEM", "Administrator", "svc_backup", "jdoe"]
    return {
        "class_uid": 3002,  # Authentication
        "category_uid": 3,
        "type_uid": 300201,  # Logon
        "time": int(time.time() * 1000),
        "metadata": {"version": "1.0.0", "product": {"name": "ARGOS Agent"}},
        "host": {"hostname": host},
        "user": {"name": users[seed % len(users)]},
        "auth_result": "success" if seed % 5 else "failure",
    }


def generate_batch(host: str, seq: int) -> list[dict[str, Any]]:
    return [
        _sim_process_event(host, seq),
        _sim_network_event(host, seq + 1),
        _sim_logon_event(host, seq + 2),
    ]


def run(cfg: Config, interval: float, secret: str | None, static_token: str | None = None, quiet: bool = False) -> None:
    logger = setup_logging(cfg, "argos.agent")
    host = socket.gethostname()
    base = f"http://{cfg.server_host}:{cfg.server_port}/api/v1/ingest"
    token = _make_token(secret, static_token)
    seq = 0
    if not quiet:
        logger.info("ARGOS agent iniciado: envío a %s (host=%s, intervalo=%.1fs)", base, host, interval)
    try:
        while True:
            batch = generate_batch(host, seq)
            seq += 1
            payload = json.dumps({"events": batch}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            try:
                with httpx.Client(timeout=10.0) as client:
                    r = client.post(base, content=payload, headers=headers)
                    if not quiet:
                        logger.debug("batch %d -> %s %s", seq, r.status_code, r.text[:80])
            except Exception as exc:
                logger.warning("no se pudo enviar batch: %s", exc)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("ARGOS agent detenido.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ARGOS collector agent")
    parser.add_argument("--host", default=None, help="host del servidor ARGOS")
    parser.add_argument("--port", type=int, default=None, help="puerto del servidor")
    parser.add_argument("--interval", type=float, default=None, help="segundos entre lotes")
    parser.add_argument("--secret", default=None, help="secreto HMAC opcional")
    parser.add_argument("--quiet", action="store_true", help="menos logs")
    args = parser.parse_args()

    cfg = get_config()
    if args.host:
        cfg.server_host = args.host
    if args.port:
        cfg.server_port = args.port
    interval = args.interval or cfg.agent_poll_interval
    secret = args.secret or cfg.auth_secret
    run(cfg, interval, secret, static_token=cfg.api_token, quiet=args.quiet)


if __name__ == "__main__":
    main()
