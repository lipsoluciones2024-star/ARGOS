from __future__ import annotations

import json
from pathlib import Path

from argos.plugins.marketplace import _default_marketplace

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    data: dict = _default_marketplace()
    (here / "marketplace.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    plugins: list = data["plugins"]
    index = {
        "generated": True,
        "catalog": data["name"],
        "plugins": [p["name"] for p in plugins],
    }
    (here / "plugin-index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"marketplace.json y plugin-index.json escritos ({len(plugins)} plugins)")
