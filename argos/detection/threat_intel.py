from __future__ import annotations

from argos.config import Config

IOC_TYPES = ("ip", "domain", "hash", "url")


class ThreatIntel:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.store_path = cfg.data_dir / "ioc.txt"
        self.iocs: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.store_path.exists():
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.iocs.add(line.lower())

    def list(self) -> list[str]:
        return sorted(self.iocs)

    def remove(self, indicator: str) -> bool:
        indicator = indicator.strip().lower()
        if indicator in self.iocs:
            self.iocs.discard(indicator)
            self._rewrite()
            return True
        return False

    def _rewrite(self) -> None:
        try:
            self.store_path.write_text(
                "\n".join(sorted(self.iocs)) + ("\n" if self.iocs else ""), encoding="utf-8"
            )
        except Exception:
            pass

    def add(self, indicator: str) -> None:
        indicator = indicator.strip().lower()
        if not indicator:
            return
        self.iocs.add(indicator)
        with self.store_path.open("a", encoding="utf-8") as f:
            f.write(indicator + "\n")

    def lookup(self, indicator: str) -> dict:
        indicator = indicator.strip().lower()
        matched = indicator in self.iocs
        return {
            "indicator": indicator,
            "malicious": matched,
            "source": "local-ioc-store" if matched else "unknown",
            "note": "Matched against local threat intel store." if matched else "No local match. Validate against OTX/abuse.ch/MISP.",
        }

    def feed_sample(self) -> None:
        samples = [
            "185.220.101.1",
            "45.155.205.233",
            "malware-c2.example.com",
            "0x5a1f9b2c",
        ]
        for s in samples:
            self.add(s)
