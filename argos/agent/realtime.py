from __future__ import annotations

import logging
import threading
from typing import Callable

from argos.ocsf import OcsfEvent

Emit = Callable[[list[OcsfEvent]], None]


class RealtimeCollector:
    """Recolección en tiempo real con fallback a polling rápido.

    En plataformas con soporte nativo (ETW en Windows / inotify+fanotify en Linux)
    se usaría el bucle de eventos del SO; sin esas dependencias (o sin privilegios)
    degrada a un poll de alta frecuencia sobre las fuentes habilitadas. Esto garantiza
    que la creación de un proceso o un cambio de archivo se refleje en <``interval`` s.
    """

    def __init__(self, collect_cycle: Callable[[], list[OcsfEvent]], emit: Emit, interval: float = 1.0) -> None:
        self._collect = collect_cycle
        self._emit = emit
        self._interval = max(0.1, interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._native = self._try_native()

    def _try_native(self) -> bool:
        # Punto de extensión para ETW (pywin32) / inotify (watchfiles). Por ahora
        # no se cuenta con dependencia nativa obligatoria, así que usamos polling.
        return False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="argos-realtime", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        logging.getLogger("argos.realtime").info(
            "realtime collector activo (modo=%s, interval=%.1fs)", "native" if self._native else "poll", self._interval
        )
        while not self._stop.is_set():
            try:
                events = self._collect()
                if events:
                    self._emit(events)
            except Exception as exc:  # keep the loop alive
                logging.getLogger("argos.realtime").error("realtime error: %s", exc)
            self._stop.wait(self._interval)
