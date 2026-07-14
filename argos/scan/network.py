from __future__ import annotations

import ipaddress
import platform
import re
import shutil
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from argos.util.cmd import run_command

COMMON_SERVICES: dict[int, str] = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "domain", 80: "http", 110: "pop3", 111: "rpcbind", 135: "msrpc",
    139: "netbios-ssn", 143: "imap", 443: "https", 445: "microsoft-ds",
    993: "imaps", 995: "pop3s", 1433: "mssql", 1521: "oracle",
    3306: "mysql", 3389: "ms-wbt-server", 5432: "postgresql",
    5900: "vnc", 6379: "redis", 8080: "http-alt", 8443: "https-alt",
    9200: "elasticsearch", 11211: "memcached", 27017: "mongodb",
}

DEFAULT_PORTS: list[int] = sorted(COMMON_SERVICES.keys())


def _service_name(port: int) -> str:
    return COMMON_SERVICES.get(port, "unknown")


def _tcp_scan_port(host: str, port: int, timeout: float) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        state = "open"
    except (ConnectionRefusedError, socket.timeout, OSError):
        state = "closed"
    finally:
        sock.close()
    return {"port": port, "state": state, "service": _service_name(port)}


def tcp_port_scan(host: str, ports: Optional[list[int]] = None,
                  timeout: float = 1.0, max_workers: int = 100) -> list[dict[str, Any]]:
    """Escaneo TCP connect (sin privilegios) multihilo. No requiere dependencias."""
    ports = ports or DEFAULT_PORTS
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(ports)))) as ex:
        for r in ex.map(lambda p: _tcp_scan_port(host, p, timeout), ports):
            results.append(r)
    results.sort(key=lambda x: x["port"])
    return results


def ping(host: str, count: int = 3, timeout: float = 3.0) -> dict[str, Any]:
    """Ping ICMP multiplataforma (comando del SO). No requiere dependencias."""
    sysname = platform.system()
    if sysname == "Windows":
        out = run_command(
            ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), host],
            timeout=timeout * count + 5,
        ).get("stdout", "")
        received = 0
        rtt = None
        for line in out.splitlines():
            low = line.lower()
            if "bytes=" in low or "bytes=" in low:
                received += 1
            if "tiempo=" in low or "time=" in low:
                try:
                    rtt = float(low.split("time=")[-1].split("ms")[0].strip())
                except (ValueError, IndexError):
                    pass
        loss = round(100 * (count - received) / max(1, count))
        return {
            "host": host, "reachable": received > 0, "sent": count,
            "received": received, "loss_pct": loss, "rtt_avg_ms": rtt,
        }
    out = run_command(
        ["ping", "-c", str(count), "-W", str(int(timeout)), host],
        timeout=timeout * count + 5,
    ).get("stdout", "")
    received = 0
    rtt_sum = 0.0
    for line in out.splitlines():
        low = line.lower()
        if "icmp" in low and "seq" in low:
            received += 1
        if "time=" in low:
            try:
                rtt_sum += float(low.split("time=")[-1].split(" ")[0].replace("ms", ""))
            except (ValueError, IndexError):
                pass
    loss = round(100 * (count - received) / max(1, count))
    rtt_avg = round(rtt_sum / received, 2) if received else None
    return {
        "host": host, "reachable": received > 0, "sent": count,
        "received": received, "loss_pct": loss, "rtt_avg_ms": rtt_avg,
    }


def traceroute(host: str, max_hops: int = 30, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Traceroute multiplataforma (tracert / traceroute del SO)."""
    sysname = platform.system()
    if sysname == "Windows":
        out = run_command(
            ["tracert", "-d", "-h", str(max_hops), "-w", str(int(timeout * 1000)), host],
            timeout=max_hops * timeout + 10,
        ).get("stdout", "")
    else:
        out = run_command(
            ["traceroute", "-m", str(max_hops), "-w", str(int(timeout)), host],
            timeout=max_hops * timeout + 10,
        ).get("stdout", "")
    hops: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = line.split()
        try:
            hop = int(parts[0])
        except ValueError:
            continue
        addr = parts[1] if len(parts) > 1 and parts[1] != "*" else None
        hops.append({"hop": hop, "address": addr, "hostname": None, "rtt_ms": None})
    return hops


def dns_lookup(host: str) -> dict[str, Any]:
    """Resolución DNS directa e inversa (sin dependencias)."""
    result: dict[str, Any] = {"query": host, "addresses": [], "aliases": [], "reverse": None}
    try:
        info = socket.gethostbyname_ex(host)
        result["addresses"] = info[2]
        result["aliases"] = list(info[1])
    except (socket.gaierror, OSError):
        pass
    if result["addresses"]:
        try:
            result["reverse"] = socket.gethostbyaddr(result["addresses"][0])[0]
        except (socket.herror, OSError):
            pass
    return result


def whois(target: str) -> dict[str, Any]:
    """WHOIS usando el binario del SO si está disponible."""
    if not shutil.which("whois"):
        return {
            "target": target, "available": False,
            "note": "binario 'whois' no disponible en el sistema (instala whois para habilitar).",
            "raw": None,
        }
    out = run_command(["whois", target], timeout=20).get("stdout", "")
    return {"target": target, "available": bool(out.strip()), "raw": out or None}


_ADDR_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}|\[?[\da-fA-F:]+\]?):(\d+)")
_PROTO_RE = re.compile(r"^(tcp|udp|tcp6|udp6)", re.IGNORECASE)


def _is_private_or_local(ip: str) -> bool:
    if not ip or ip in ("*", "0.0.0.0", "::", "::1"):
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast


def connections() -> dict[str, Any]:
    """Enumera conexiones de red activas vía ``netstat`` (sin dependencias).

    Devuelve la lista de conexiones y el subconjunto de conexiones salientes a
    IPs externas (candidatas a C2 / exfiltración) en estado ESTABLISHED.
    """
    sysname = platform.system()
    cmd = ["netstat", "-ano"] if sysname == "Windows" else ["netstat", "-an"]
    raw = run_command(cmd, timeout=15).get("stdout", "")
    conns: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not _PROTO_RE.match(line):
            continue
        parts = line.split()
        # Forma: PROTO  Local  Foreign  State  PID   (Windows 5 cols; Linux 4-6)
        proto = parts[0].lower()
        local = parts[1] if len(parts) > 1 else ""
        remote = parts[2] if len(parts) > 2 else ""
        state = parts[3] if len(parts) > 3 and parts[3].isalpha() else ""
        pid = parts[-1] if parts[-1].isdigit() else None
        lr = _ADDR_RE.search(local)
        rr = _ADDR_RE.search(remote)
        local_addr = lr.group(1) if lr else None
        local_port = int(lr.group(2)) if lr else None
        remote_addr = rr.group(1) if rr else None
        remote_port = int(rr.group(2)) if rr else None
        entry = {
            "protocol": proto, "local_addr": local_addr, "local_port": local_port,
            "remote_addr": remote_addr, "remote_port": remote_port,
            "state": state.upper(), "pid": pid,
        }
        conns.append(entry)
        if (state or "").upper() == "ESTABLISHED" and remote_addr and not _is_private_or_local(remote_addr):
            external.append(entry)
    return {
        "count": len(conns),
        "connections": conns,
        "external_established": external,
        "external_count": len(external),
    }


def nmap_available() -> bool:
    return bool(shutil.which("nmap"))


def nmap_scan(target: str, args: str = "-sT -Pn -T4") -> dict[str, Any]:
    """Escaneo enriquecido con nmap si está instalado (opcional)."""
    if not nmap_available():
        return {"error": "nmap no instalado", "available": False}
    out = run_command(["nmap"] + args.split() + [target], timeout=120).get("stdout", "")
    return {"available": True, "target": target, "raw": out or None}


def network_scan(target: str, kinds: Optional[list[str]] = None,
                 ports: Optional[list[int]] = None, timeout: float = 1.0) -> dict[str, Any]:
    """Orquesta múltiples reconocimientos de red en un solo resultado."""
    kinds = kinds or ["portscan", "ping", "dns"]
    results: dict[str, Any] = {"target": target, "scanned_at": None, "results": {}}
    from datetime import datetime, timezone

    results["scanned_at"] = datetime.now(timezone.utc).isoformat()
    if "portscan" in kinds:
        results["results"]["portscan"] = tcp_port_scan(target, ports=ports, timeout=timeout)
        results["results"]["open_ports"] = [
            p["port"] for p in results["results"]["portscan"] if p["state"] == "open"
        ]
    if "ping" in kinds:
        results["results"]["ping"] = ping(target, timeout=timeout)
    if "traceroute" in kinds:
        results["results"]["traceroute"] = traceroute(target, timeout=timeout)
    if "dns" in kinds:
        results["results"]["dns"] = dns_lookup(target)
    if "whois" in kinds:
        results["results"]["whois"] = whois(target)
    if "connections" in kinds:
        results["results"]["connections"] = connections()
    if "nmap" in kinds:
        results["results"]["nmap"] = nmap_scan(target)
    return results


def capabilities() -> dict[str, Any]:
    return {
        "kinds": ["portscan", "ping", "traceroute", "dns", "whois", "connections", "nmap"],
        "default_ports": DEFAULT_PORTS,
        "nmap_available": nmap_available(),
        "whois_available": bool(shutil.which("whois")),
        "platform": platform.system(),
    }
