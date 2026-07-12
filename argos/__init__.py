from __future__ import annotations

from argos.config import Config, load_config

__version__ = "0.1.0"

_config = load_config()

logger = None


def get_config() -> Config:
    return _config
