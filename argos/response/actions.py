from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from argos.config import Config
from argos.detection.alerts import ACTION_REVERSIBLE, ACTION_RISK

RESPONSE_ACTIONS = list(ACTION_RISK.keys())


def _run(cmd: list[str]) -> dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {"rc": r.returncode, "stdout": r.stdout[:2000], "stderr": r.stderr[:2000]}
    except Exception as exc:
        return {"rc": -1, "error": str(exc)}


def _registry_backups(cfg: Config) -> Path:
    return cfg.data_dir / "registry_backups.json"


def _load_backups(cfg: Config) -> dict[str, Any]:
    path = _registry_backups(cfg)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_backups(cfg: Config, data: dict[str, Any]) -> None:
    _registry_backups(cfg).write_text(json.dumps(data, indent=2), encoding="utf-8")


def execute_action(cfg: Config, action: str, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    if action == "kill_process":
        pid = params.get("pid") or target
        if platform.system() == "Windows":
            return _run(["taskkill", "/PID", str(pid), "/F"])
        return _run(["kill", "-9", str(pid)])
    if action == "block_ip":
        ip = target
        if platform.system() == "Windows":
            return _run(["netsh", "advfirewall", "firewall", "add", "rule",
                         "name=ARGOS_BLOCK", "dir=out", "action=block", f"remoteip={ip}"])
        return _run(["iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"])
    if action == "quarantine_file":
        src = Path(target)
        if src.exists():
            qdir = cfg.data_dir / "quarantine"
            qdir.mkdir(parents=True, exist_ok=True)
            dst = qdir / src.name
            shutil.move(str(src), str(dst))
            return {"moved": str(dst)}
        return {"error": "file not found"}
    if action == "revert_registry":
        return _revert_registry(cfg, target, params)
    if action == "disable_account":
        user = target
        if platform.system() == "Windows":
            return _run(["net", "user", user, "/active:no"])
        return _run(["usermod", "-L", user])
    if action == "isolate_host":
        return _isolate_host(cfg, target, params)
    if action == "memory_snapshot":
        return _memory_snapshot(cfg, target, params)
    return {"error": f"unknown action {action}"}


def _revert_registry(cfg: Config, target: str, params: dict[str, Any]) -> dict[str, Any]:
    key = params.get("key") or target
    if "value" in params and params["value"] is not None:
        value = params["value"]
    else:
        backups = _load_backups(cfg)
        if key not in backups:
            return {"error": f"no registry backup stored for {key}; provide 'value' to restore"}
        value = backups[key]["value"]
    if platform.system() != "Windows":
        return {"error": "registry revert is only supported on Windows hosts", "key": key}
    out = _run(["reg", "add", key, "/f", "/d", str(value)])
    out["reverted_key"] = key
    out["reverted_value"] = value
    return out


def _isolate_host(cfg: Config, target: str, params: dict[str, Any]) -> dict[str, Any]:
    if platform.system() == "Windows":
        rules = [
            ["netsh", "advfirewall", "set", "allprofiles", "state", "on"],
            ["netsh", "advfirewall", "firewall", "add", "rule", "name=ARGOS_ISO_IN",
             "dir=in", "action=block"],
            ["netsh", "advfirewall", "firewall", "add", "rule", "name=ARGOS_ISO_OUT",
             "dir=out", "action=block"],
        ]
        results = [r for r in (_run(c) for c in rules)]
        return {"isolated": target, "platform": "windows", "results": results}
    results = [
        _run(["iptables", "-P", "INPUT", "DROP"]),
        _run(["iptables", "-P", "FORWARD", "DROP"]),
        _run(["iptables", "-A", "OUTPUT", "-m", "state", "--state", "ESTABLISHED", "-j", "ACCEPT"]),
    ]
    return {"isolated": target, "platform": "linux", "results": results}


def _memory_snapshot(cfg: Config, target: str, params: dict[str, Any]) -> dict[str, Any]:
    pid = params.get("pid") or target
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return {"error": "memory_snapshot requires a numeric PID", "target": target}
    out = cfg.data_dir / "snapshots" / f"pid_{pid}.dump"
    out.parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Linux":
        res = _run(["gcore", "-o", str(out), str(pid)])
        if res.get("rc") != 0 and shutil.which("gcore") is None:
            return {"error": "gcore not available on this host; install gdb to capture memory",
                    "target": target}
        return {"snapshot": str(out), "tool": "gcore", "result": res}
    if platform.system() == "Windows":
        res = _run(["procdump", "-ma", str(pid), str(out)])
        if res.get("rc") != 0 and shutil.which("procdump") is None:
            return {"error": "procdump not available on this host; install Sysinternals",
                    "target": target}
        return {"snapshot": str(out), "tool": "procdump", "result": res}
    return {"error": f"memory capture not supported on {platform.system()}", "target": target}


def action_risk(action: str) -> str:
    return ACTION_RISK.get(action, "unknown")


def action_reversible(action: str) -> str:
    return ACTION_REVERSIBLE.get(action, "unknown")
