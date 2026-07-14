from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

# Intentamos usar yara nativo; si no está disponible (p.ej. Python 3.14 donde
# yara-python no compila), caemos a un matcher Python puro para text/hex.
try:  # pragma: no cover - depende del entorno
    import yara

    _HAS_YARA = True
except Exception:  # pragma: no cover
    yara = None
    _HAS_YARA = False


_STRING_RE = re.compile(
    r"\$(?P<name>[A-Za-z0-9_]+)\s*=\s*"
    r"(?P<quote>[\"\{/])(?P<body>.*?)(?P=quote)"
    r"(?P<mods>[^\n]*?)(?=\n|\r|$)"
)
_META_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)\s*=\s*(?P<val>.+)")
_HEX_TOKEN_RE = re.compile(r"[0-9A-Fa-f]{2}|\?")


class ParsedRule:
    def __init__(self, name: str, meta: dict[str, Any], strings: list[dict[str, Any]],
                 condition: str) -> None:
        self.name = name
        self.meta = meta
        self.strings = strings
        self.condition = condition


def _parse_hex(hex_body: str) -> list[Optional[int]]:
    """Convierte 'DE AD BE EF ? ?' en lista de bytes con wildcard None."""
    tokens = _HEX_TOKEN_RE.findall(hex_body.replace(" ", ""))
    out: list[Optional[int]] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "?":
            out.append(None)
        else:
            out.append(int(t, 16))
        i += 1
    return out


def _hex_search(pattern: list[Optional[int]], data: bytes) -> bool:
    if not pattern:
        return False
    plen = len(pattern)
    for start in range(0, len(data) - plen + 1):
        ok = True
        for j, pb in enumerate(pattern):
            if pb is None:
                continue
            if data[start + j] != pb:
                ok = False
                break
        if ok:
            return True
    return False


def parse_rule(text: str) -> ParsedRule | None:
    m = re.search(r"rule\s+([A-Za-z0-9_]+)\s*\{", text)
    if not m:
        return None
    name = m.group(1)
    block = text[m.end():]
    # meta
    meta: dict[str, Any] = {}
    mm = re.search(r"meta\s*:(.*?)(strings|condition)\s*:", block, re.S)
    if mm:
        for line in mm.group(1).splitlines():
            km = _META_RE.search(line)
            if km:
                val = km.group("val").strip().strip('"').strip()
                meta[km.group("key")] = val
    # strings
    strings: list[dict[str, Any]] = []
    sm = re.search(r"strings\s*:(.*?)condition\s*:", block, re.S)
    if sm:
        for sm_match in _STRING_RE.finditer(sm.group(1)):
            kind = sm_match.group("quote")
            body = sm_match.group("body")
            mods = sm_match.group("mods").lower()
            entry: dict[str, Any] = {
                "name": "$" + sm_match.group("name"),
                "nocase": "nocase" in mods,
                "wide": "wide" in mods,
                "ascii": "ascii" in mods,
            }
            if kind == '"':
                entry["type"] = "text"
                entry["value"] = body
            elif kind == "{":
                entry["type"] = "hex"
                entry["value"] = _parse_hex(body)
            else:
                entry["type"] = "regex"
                entry["value"] = body
            strings.append(entry)
    # condition
    cm = re.search(r"condition\s*:(.*?)\}", block, re.S)
    condition = cm.group(1).strip() if cm else "all of them"
    return ParsedRule(name, meta, strings, condition)


def _match_string(entry: dict[str, Any], data: bytes) -> bool:
    if entry["type"] == "text":
        needle = entry["value"].encode("utf-8")
        if entry.get("nocase"):
            needle = needle.lower()
            hay = data.lower()
        else:
            hay = data
        if entry.get("wide"):
            wneedle = entry["value"].encode("utf-16-le")
            if wneedle in (data.lower() if entry.get("nocase") else data):
                return True
        return needle in hay
    if entry["type"] == "hex":
        return _hex_search(entry["value"], data)
    if entry["type"] == "regex":
        flags = re.IGNORECASE if entry.get("nocase") else 0
        return re.search(entry["value"], data.decode("latin-1", errors="ignore"), flags) is not None
    return False


def _eval_condition(condition: str, matched: dict[str, bool], data_len: int) -> bool:
    expr = condition
    # "N of them"
    expr = re.sub(r"(\d+)\s+of\s+them", r"sum(1 for _v in matched.values() if _v) >= \1", expr)
    expr = re.sub(r"all\s+of\s+them", "all(matched.values())", expr)
    expr = re.sub(r"any\s+of\s+them", "any(matched.values())", expr)
    # referencias $id -> matched["$id"]
    expr = re.sub(r"\$([A-Za-z0-9_]+)", r'matched["$\1"]', expr)
    expr = expr.replace("filesize", "filesize")
    try:
        env = {"matched": matched, "filesize": data_len, "all": all, "any": any, "sum": sum}
        return bool(eval(expr, {"__builtins__": {}}, env))  # noqa: S307 (parser confinado)
    except Exception:
        return False


class YaraScanner:
    """Carga reglas YARA y escanea bytes/archivos. Prefiere yara nativo; si no,
    usa un matcher Python puro (text/hex/regex + condiciones básicas)."""

    def __init__(self) -> None:
        self.use_native = _HAS_YARA
        self.rules: list[ParsedRule] = []
        self._native_rules: list[Any] = []

    def load_rules_from_dir(self, path: Path) -> int:
        count = 0
        if path.is_dir():
            for f in sorted(path.glob("*.yar")) + sorted(path.glob("*.yara")):
                count += self.load_rule_text(f.read_text(encoding="utf-8", errors="replace"), f.name)
        return count

    def load_rule_text(self, text: str, name: str = "rule") -> int:
        parsed = parse_rule(text)
        if not parsed:
            return 0
        self.rules.append(parsed)
        if self.use_native:
            try:  # pragma: no cover
                self._native_rules.append(yara.compile(source=text))
            except Exception:
                self.use_native = False  # degrada a fallback si una regla falla
        return 1

    def scan_bytes(self, data: bytes) -> list[dict[str, Any]]:
        if isinstance(data, str):
            data = data.encode("utf-8", errors="replace")
        results: list[dict[str, Any]] = []
        if self.use_native:
            for rules in self._native_rules:  # pragma: no cover
                try:
                    for m in rules.match(data=data):
                        results.append({"rule": m.rule, "meta": dict(m.meta or {}),
                                        "strings": [s.identifier for s in m.strings]})
                except Exception:
                    continue
            if results:
                return results
        for rule in self.rules:
            matched = {s["name"]: _match_string(s, data) for s in rule.strings}
            if rule.strings and _eval_condition(rule.condition, matched, len(data)):
                results.append({
                    "rule": rule.name,
                    "meta": rule.meta,
                    "strings": [n for n, v in matched.items() if v],
                })
        return results

    def scan_file(self, path: Path) -> list[dict[str, Any]]:
        try:
            data = Path(path).read_bytes()
        except Exception:
            return []
        return self.scan_bytes(data)


def scan_path(scanner: YaraScanner, root: Path, max_files: int = 5000) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    scanned = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if scanned >= max_files:
            break
        scanned += 1
        for hit in scanner.scan_file(p):
            hits.append({"file": str(p), **hit})
    return hits
