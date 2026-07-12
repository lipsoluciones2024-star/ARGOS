from __future__ import annotations

import ipaddress
import re

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HOST_RE = re.compile(r"\b([a-zA-Z0-9-]+\.(?:local|lan|home|internal|corp))\b")


def _anonymize_ip(text: str) -> str:
    def repl(m: re.Match) -> str:
        try:
            ip = ipaddress.ip_address(m.group(0))
        except ValueError:
            return m.group(0)
        if ip.is_private:
            return m.group(0)
        return "ANON-IP-" + str(int(ip) % 100000)

    return _IP_RE.sub(repl, text)


def _anonymize_host(text: str) -> str:
    return _HOST_RE.sub(lambda m: "ANON-HOST", text)


def anonymize(text: str) -> str:
    return _anonymize_host(_anonymize_ip(text))


SENSITIVE_PATTERNS = [
    re.compile(r"password\s*=\s*\S+", re.I),
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.I),
    re.compile(r"token\s*[:=]\s*\S+", re.I),
    re.compile(r"secret\s*[:=]\s*\S+", re.I),
]


def has_secret(text: str) -> bool:
    return any(p.search(text) for p in SENSITIVE_PATTERNS)


def scrub_secrets(text: str) -> str:
    for p in SENSITIVE_PATTERNS:
        text = p.sub(lambda m: m.group(0).split("=")[0].split(":")[0] + "=***REDACTED***", text)
    return text


def guard_privacy(text: str) -> str:
    return scrub_secrets(anonymize(text))
