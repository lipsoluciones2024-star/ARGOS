from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path
from typing import Any

from argos.config import Config
from argos.detection.alerts import ACTION_REVERSIBLE, ACTION_RISK
from argos.util.cmd import run_command

RESPONSE_ACTIONS = list(ACTION_RISK.keys())


def _run(cmd: list[str]) -> dict[str, Any]:
    return run_command(cmd, timeout=30)


_REGISTRY_BACKUPS = "registry_backups.json"
_FIREWALL_BLOCKS = "firewall_blocks.json"


def _load_json(cfg: Config, name: str) -> dict[str, Any]:
    path = cfg.data_dir / name
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_json(cfg: Config, name: str, data: dict[str, Any]) -> None:
    (cfg.data_dir / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def execute_action(cfg: Config, action: str, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    if action == "kill_process":
        pid = params.get("pid") or target
        if platform.system() == "Windows":
            return _run(["taskkill", "/PID", str(pid), "/F"])
        return _run(["kill", "-9", str(pid)])
    if action == "block_ip":
        ip = target
        name = _block_rule_name(ip)
        if platform.system() == "Windows":
            res = _run(["netsh", "advfirewall", "firewall", "add", "rule",
                        f"name={name}", "dir=out", "action=block", f"remoteip={ip}"])
        else:
            res = _run(["iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"])
        _record_firewall_block(cfg, ip, name)
        res["rule_name"] = name
        return res
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
        backups = _load_json(cfg, _REGISTRY_BACKUPS)
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


def _block_rule_name(ip: str) -> str:
    return "ARGOS_BLOCK_" + ip.replace(".", "_").replace(":", "_").replace("/", "_")


def _record_firewall_block(cfg: Config, ip: str, name: str) -> None:
    blocks = _load_json(cfg, _FIREWALL_BLOCKS)
    blocks[ip] = name
    _save_json(cfg, _FIREWALL_BLOCKS, blocks)


def remove_firewall_block(cfg: Config, ip: str) -> dict[str, Any]:
    name = _block_rule_name(ip)
    if platform.system() == "Windows":
        res = _run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"])
    else:
        res = _run(["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"])
    blocks = _load_json(cfg, _FIREWALL_BLOCKS)
    blocks.pop(ip, None)
    _save_json(cfg, _FIREWALL_BLOCKS, blocks)
    res["removed_rule"] = name
    return res


def action_risk(action: str) -> str:
    return ACTION_RISK.get(action, "unknown")


def action_reversible(action: str) -> str:
    return ACTION_REVERSIBLE.get(action, "unknown")


def undo_action(cfg: Config, action: str, target: str, params: dict[str, Any] | None = None,
                exec_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Revierte una acción ejecutada (solo las reversibles)."""
    params = params or {}
    if action == "block_ip":
        return remove_firewall_block(cfg, target)
    if action == "quarantine_file":
        src = Path(target)
        moved = (exec_result or {}).get("moved")
        if moved:
            src = Path(moved)
        restore = params.get("restore_path") or target
        if src.exists():
            shutil.move(str(src), str(restore))
            return {"restored": str(restore)}
        return {"error": "archivo en cuarentena no encontrado"}
    if action == "disable_account":
        user = target
        if platform.system() == "Windows":
            return _run(["net", "user", user, "/active:yes"])
        return _run(["usermod", "-U", user])
    if action == "isolate_host":
        return _undo_isolate_host(cfg)
    return {"error": f"accion '{action}' no es reversible automaticamente",
            "reversible": action_reversible(action)}


def _undo_isolate_host(cfg: Config) -> dict[str, Any]:
    if platform.system() == "Windows":
        rules = [
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=ARGOS_ISO_IN"],
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=ARGOS_ISO_OUT"],
        ]
        results = [r for r in (_run(c) for c in rules)]
        return {"isolated": False, "platform": "windows", "results": results}
    results = [
        _run(["iptables", "-D", "OUTPUT", "-m", "state", "--state", "ESTABLISHED", "-j", "ACCEPT"]),
        _run(["iptables", "-P", "INPUT", "ACCEPT"]),
        _run(["iptables", "-P", "FORWARD", "ACCEPT"]),
    ]
    return {"isolated": False, "platform": "linux", "results": results}
