from __future__ import annotations

import json
import logging
import os
import sys

from argos.config import Config


def setup_logging(cfg: Config, name: str = "argos") -> logging.Logger:
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    log_path = cfg.data_dir / "argos.log"
    logger = logging.getLogger(name)
    level_name = os.environ.get("ARGOS_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def log_struct(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, default=str))
