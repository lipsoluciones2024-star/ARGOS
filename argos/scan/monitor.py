from __future__ import annotations

from typing import Any, Optional

from argos.detection.alerts import Alert, Severity
from argos.scan import network as net_scan


def _build_alert(ctx: Any, host: str, diff: dict[str, Any]) -> Optional[Alert]:
    new_ports = diff.get("new_ports") or []
    new_conns = diff.get("new_connections") or []
    if not new_ports and not new_conns:
        return None
    parts: list[str] = []
    if new_ports:
        parts.append(f"puertos nuevos abiertos: {', '.join(str(p) for p in new_ports)}")
    if new_conns:
        conn_desc = ", ".join(
            f"{c.get('local_addr')} -> {c.get('remote_addr')}:{c.get('remote_port')}"
            for c in new_conns[:5]
        )
        parts.append(f"conexiones externas nuevas: {conn_desc}")
    title = f"Anomalía de red en {host}"
    severity = Severity.HIGH if new_conns else Severity.MEDIUM
    return Alert(
        title=title,
        severity=severity,
        host=host,
        attack_id="T1046" if new_ports else "T1071",
        attack_technique="Network Service Discovery" if new_ports else "Application Layer Protocol",
        summary="; ".join(parts),
        source="network_monitor",
    )


def run_monitor_scan(ctx: Any, target: str, kinds: Optional[list[str]] = None,
                     ports: Optional[list[int]] = None, timeout: float = 1.0,
                     by: str = "system") -> dict[str, Any]:
    """Ejecuta un escaneo de monitoreo de red, compara contra la línea de base y
    emite alertas si aparecen puertos nuevos o conexiones externas nuevas.

    Devuelve el resultado del escaneo y el diff calculado.
    """
    kinds = kinds or ["portscan", "ping", "dns", "connections"]
    result = net_scan.network_scan(target, kinds=kinds, ports=ports, timeout=timeout)
    results = result.get("results", {})
    open_ports = results.get("open_ports", [])
    services = {
        p["port"]: p["service"]
        for p in results.get("portscan", [])
    }
    external = results.get("connections", {}).get("external_established", []) \
        if isinstance(results.get("connections"), dict) else []
    diff = ctx.net_baseline.record_scan(target, open_ports, services, external_conns=external)
    ctx.net_baseline.add_target(target, by=by)

    alert = _build_alert(ctx, target, diff)
    if alert is not None:
        ctx.alert_store.add(alert)
        try:
            ctx._push({"type": "proactive_alert", "alert": alert.as_dict(),
                       "message": f"[ALERTA {alert.severity.value.upper()}] {alert.title}"})
        except Exception:
            pass
        try:
            ctx.autonomy.enqueue(alert.as_dict())
        except Exception:
            pass
        ctx.audit.append("network_anomaly", by, by, "detected", alert.as_dict())
    return {"scan": result, "diff": diff}
