from __future__ import annotations

import argparse
import sys

from argos import get_config
from argos.config import SwitchLevel
from argos.ocsf import EventCategory, OcsfEvent, Severity
from argos.server import AppContext


def _ctx() -> AppContext:
    return AppContext(get_config())


def cmd_status(args, ctx: AppContext) -> None:
    print(f"eventos={ctx.store.count()} switch={ctx.response.switch.level.value} reglas={len(ctx.engine.rules)}")


def cmd_chat(args, ctx: AppContext) -> None:
    print(ctx.orchestrator.chat(args.message))


def cmd_switch(args, ctx: AppContext) -> None:
    ctx.response.set_level(SwitchLevel(args.level))
    print(f"switch -> {ctx.response.switch.level.value}")


def cmd_propose(args, ctx: AppContext) -> None:
    p = ctx.response.propose(action=args.action, target=args.target, proposed_by="cli")
    print(f"proposal {p.id}: {p.status}")


def cmd_coverage(args, ctx: AppContext) -> None:
    cov = ctx.engine.coverage()
    matrix = cov.get("matrix", {})
    blind = [k for k, v in matrix.items() if v.get("status") == "blind-spot"]
    total = cov.get("total", len(matrix))
    covered = cov.get("covered", sum(1 for v in matrix.values() if v.get("status") == "covered"))
    print(f"tecnicas={total} cubiertas={covered} puntos_ciegos={len(blind)}")
    for t in blind[:10]:
        print(f"  - {t} {matrix[t].get('name', '')}")


def cmd_demo(args, ctx: AppContext) -> None:
    host = args.host
    samples = [
        OcsfEvent(category=EventCategory.PROCESS, host=host, source="demo",
                  process_name="powershell.exe",
                  process_cmdline="powershell.exe -enc JABjAD0AVwBvAHIAbQAgAGUA..."),
        OcsfEvent(category=EventCategory.NETWORK, host=host, source="demo",
                  process_name="rundll32.exe", dst_ip="185.220.101.1", dst_port=443,
                  protocol="TCP", attack_id="T1071", attack_technique="Application Layer Protocol"),
        OcsfEvent(category=EventCategory.IDENTITY, host=host, source="demo",
                  user="admin", logon_result="failure", attack_id="T1110",
                  attack_technique="Brute Force", severity=Severity.MEDIUM),
    ]
    n = ctx.ingest([s.model_dump() for s in samples])
    print(f"ingestados {n} eventos demo (host={host})")


def cmd_ingest(args, ctx: AppContext) -> None:
    import json

    raw = json.load(sys.stdin)
    n = ctx.ingest(raw if isinstance(raw, list) else raw.get("events", []))
    print(f"ingestados {n}")


def cmd_auth(args, ctx: AppContext) -> None:
    from argos.security import derive_secret, sign_token

    secret = derive_secret(ctx.cfg.auth_secret, str(ctx.cfg.data_dir))
    role = args.role
    ttl = args.ttl
    tok = sign_token(secret, role, sub="cli", ttl=ttl)
    print(tok)
    print(f"# rol={role} ttl={ttl or 'infinito'}s  (envía como 'Authorization: Bearer <token>')", file=sys.stderr)


def cmd_bootstrap(args, ctx: AppContext) -> None:
    from argos.ai.local_bootstrap import ensure_model

    try:
        path = ensure_model(ctx.cfg, url=args.url, sha256=args.sha256)
        print(f"modelo local listo: {path}")
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


def cmd_setup(args, ctx: AppContext) -> None:
    from pathlib import Path

    env_path = Path(".env")
    if env_path.exists() and not args.force:
        print(f"{env_path} ya existe. Usa --force para sobrescribir.")
        return
    secret = ctx.cfg.auth_secret or "cambiame-en-produccion"
    content = (
        "# ARGOS .env (generado por 'argos-cli setup')\n"
        "ARGOS_REQUIRE_AUTH=true\n"
        f"ARGOS_AUTH_SECRET={secret}\n"
        "ARGOS_SERVER_HOST=127.0.0.1\n"
        "ARGOS_SERVER_PORT=8000\n"
        "ARGOS_LLM_MODE=hybrid\n"
        "ARGOS_AUTONOMY_ENABLED=true\n"
        "ARGOS_AUTONOMY_MAX_ACTIONS_PER_HOUR=10\n"
        "ARGOS_REALTIME_ENABLED=false\n"
        "# KILO_API_KEY=...\n"
        "# ARGOS_LOCAL_MODEL_URL=...  (para modo offline)\n"
    )
    env_path.write_text(content, encoding="utf-8")
    print(f"Archivo {env_path} creado. Edítalo y luego: argos-server / argos-agent")


def cmd_install_service(args, ctx: AppContext) -> None:
    import platform
    import shutil
    import subprocess
    from pathlib import Path

    component = args.component
    if platform.system() == "Windows":
        ps = shutil.which("powershell") or "powershell.exe"
        script = Path(__file__).resolve().parent.parent / "deploy" / "windows" / "install-service.ps1"
        try:
            subprocess.run([ps, "-ExecutionPolicy", "Bypass", "-File", str(script),
                            "-Component", component], check=True)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR instalando servicio: {exc}")
            raise SystemExit(1)
    else:
        units = Path(__file__).resolve().parent.parent / "deploy" / "systemd"
        unit = "argos-agent.service" if component == "agent" else "argos-server.service"
        print(f"Para Linux/systemd copia y habilita la unidad:\n"
              f"  sudo cp {units / unit} /etc/systemd/system/\n"
              f"  sudo systemctl daemon-reload\n"
              f"  sudo systemctl enable --now {unit}\n"
              f"(crea antes el usuario 'argos' y /var/lib/argos)")


def cmd_plugins(args, ctx: AppContext) -> None:
    print("Plugins instalados:")
    for p in ctx.plugin_registry.list_installed():
        print(f"  - {p['name']} v{p['version']} [{ 'on' if p['enabled'] else 'off' }] hooks={p.get('hook_count',0)}")
    avail = ctx.plugin_registry.available_in_marketplace()
    if avail:
        print("\nDisponibles en marketplace:")
        for p in avail:
            print(f"  + {p['name']} ({p['category']}) - {p['description']}")


def cmd_plugin_install(args, ctx: AppContext) -> None:
    from argos.plugins.base import PluginManifest
    from argos.plugins.marketplace import MARKETPLACE

    m = MARKETPLACE.get(args.name)
    if m is None:
        print(f"plugin '{args.name}' no encontrado en el marketplace")
        raise SystemExit(1)
    ok = ctx.plugin_manager.install(m if isinstance(m, PluginManifest) else PluginManifest.from_dict(m))
    print(f"instalado={ok} {args.name}")


def cmd_plugin_uninstall(args, ctx: AppContext) -> None:
    ok = ctx.plugin_manager.uninstall(args.name)
    print(f"desinstalado={ok} {args.name}")


def cmd_plugin_enable(args, ctx: AppContext) -> None:
    print(f"habilitado={ctx.plugin_manager.enable(args.name)} {args.name}")


def cmd_plugin_disable(args, ctx: AppContext) -> None:
    print(f"deshabilitado={ctx.plugin_manager.disable(args.name)} {args.name}")


def cmd_mcp(args, ctx: AppContext) -> None:
    print(f"MCP tools expuestas: {len(ctx.mcp.registry.list_tools())}")
    for t in ctx.mcp.registry.list_tools():
        print(f"  - {t['name']}: {t['description']}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="argos", description="ARGOS CLI")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status").set_defaults(func=cmd_status)
    c = sub.add_parser("chat")
    c.add_argument("message")
    c.set_defaults(func=cmd_chat)
    s = sub.add_parser("switch")
    s.add_argument("level", choices=[lv.value for lv in SwitchLevel])
    s.set_defaults(func=cmd_switch)
    pr = sub.add_parser("propose")
    pr.add_argument("action")
    pr.add_argument("target")
    pr.set_defaults(func=cmd_propose)
    sub.add_parser("coverage").set_defaults(func=cmd_coverage)
    d = sub.add_parser("demo")
    d.add_argument("--host", default="demo-host")
    d.set_defaults(func=cmd_demo)
    i = sub.add_parser("ingest")
    i.set_defaults(func=cmd_ingest)
    a = sub.add_parser("auth", help="genera un token firmado (admin/operator)")
    a.add_argument("role", choices=["admin", "operator"], nargs="?", default="admin")
    a.add_argument("--ttl", type=int, default=0, help="segundos de validez (0=infinito)")
    a.set_defaults(func=cmd_auth)
    b = sub.add_parser("bootstrap", help="descarga/verifica el modelo GGUF local")
    b.add_argument("--url", default=None, help="URL del GGUF")
    b.add_argument("--sha256", default=None, help="checksum SHA256 esperado")
    b.set_defaults(func=cmd_bootstrap)
    s = sub.add_parser("setup", help="genera .env con valores por defecto")
    s.add_argument("--force", action="store_true", help="sobrescribe .env existente")
    s.set_defaults(func=cmd_setup)
    i = sub.add_parser("install-service", help="instala como servicio (systemd/Windows)")
    i.add_argument("component", choices=["server", "agent"], nargs="?", default="server")
    i.set_defaults(func=cmd_install_service)
    pg = sub.add_parser("plugins", help="lista plugins instalados y disponibles")
    pg.set_defaults(func=cmd_plugins)
    pi = sub.add_parser("plugin-install", help="instala un plugin del marketplace")
    pi.add_argument("name")
    pi.set_defaults(func=cmd_plugin_install)
    pu = sub.add_parser("plugin-uninstall", help="desinstala un plugin")
    pu.add_argument("name")
    pu.set_defaults(func=cmd_plugin_uninstall)
    pe = sub.add_parser("plugin-enable", help="habilita un plugin")
    pe.add_argument("name")
    pe.set_defaults(func=cmd_plugin_enable)
    pd = sub.add_parser("plugin-disable", help="deshabilita un plugin")
    pd.add_argument("name")
    pd.set_defaults(func=cmd_plugin_disable)
    mc = sub.add_parser("mcp", help="lista tools expuestas via MCP")
    mc.set_defaults(func=cmd_mcp)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return
    ctx = _ctx()
    args.func(args, ctx)


if __name__ == "__main__":
    main()
