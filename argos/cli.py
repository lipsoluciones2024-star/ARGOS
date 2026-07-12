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
    blind = [k for k, v in cov.items() if v["status"] == "blind-spot"]
    print(f"tecnicas={len(cov)} puntos_ciegos={len(blind)}")
    for t in blind[:10]:
        print(f"  - {t} {cov[t]['name']}")


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
