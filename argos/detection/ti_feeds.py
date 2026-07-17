from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("argos.detection.ti_feeds")


@dataclass
class ThreatIntelFeed:
    name: str
    url: str
    format: str = "txt"  # txt | json
    enabled: bool = True


# Feeds publicos de referencia (solo metadatos; la descarga es opcional y
# requiere conectividad explicita del operador).
DEFAULT_FEEDS: List[ThreatIntelFeed] = [
    ThreatIntelFeed(name="abuse.ch_feodo", url="https://feodotracker.abuse.ch/downloads/ipblocklist.txt", format="txt"),
    ThreatIntelFeed(name="emerging_threats", url="https://rules.emergingthreats.net/blockrules/compromised-ips.txt", format="txt"),
    ThreatIntelFeed(name="alienvault_otx", url="https://otx.alienvault.com/api/v1/indicators/", format="json"),
]


def load_feeds() -> List[ThreatIntelFeed]:
    return list(DEFAULT_FEEDS)


def is_ip(indicator: str) -> bool:
    try:
        ipaddress.ip_address(indicator)
        return True
    except ValueError:
        return False


def classify(indicator: str) -> str:
    if is_ip(indicator):
        return "ip"
    if indicator.startswith("http://") or indicator.startswith("https://"):
        return "url"
    if "." in indicator and " " not in indicator:
        return "domain"
    return "hash"
