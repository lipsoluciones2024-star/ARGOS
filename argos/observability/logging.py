from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class StructuredLogFilter(logging.Filter):
    """Enriquecce cada registro con campos estructurados para trazabilidad."""

    def __init__(self, service: str = "argos") -> None:
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "meta"):
            record.meta = {}
        record.service = self.service
        return True


def configure_structured_logging(
    level: int = logging.INFO, service: str = "argos"
) -> logging.Logger:
    """Configura un logger con salida JSON estructurada (sin deps externas)."""

    logger = logging.getLogger(service)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(StructuredLogFilter(service))

    class JsonAdapter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload: Dict[str, Any] = {
                "ts": record.created,
                "level": record.levelname,
                "service": getattr(record, "service", service),
                "logger": record.name,
                "msg": record.getMessage(),
            }
            meta = getattr(record, "meta", None)
            if meta:
                payload["meta"] = meta
            if record.exc_info:
                payload["exc"] = self.formatException(record.exc_info)
            return json.dumps(payload, default=str)

    handler.setFormatter(JsonAdapter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Helper para emitir un log estructurado de un evento de dominio."""
    extra = {"meta": {"event": event, **fields}}
    logger.info(event, extra=extra)
