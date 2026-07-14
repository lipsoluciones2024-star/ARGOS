from __future__ import annotations

"""Wrapper para registrar ARGOS como Windows Service (T6.7).

Requiere pywin32. Si no está disponible, el módulo se importa igual pero
`install()`/`run()` informan claramente que falta la dependencia, en lugar de
fallar en silencio. Alternativa recomendada sin pywin32: usar nssm con
deploy/windows/install-service.ps1.
"""

import sys  # noqa: E402

try:
    import win32event  # type: ignore
    import win32service  # type: ignore
    import win32serviceutil  # type: ignore
    _HAS_WIN32 = True
except Exception:  # pragma: no cover - pywin32 solo en Windows
    _HAS_WIN32 = False


class ArgosService:  # pragma: no cover - depende de pywin32/Windows
    if _HAS_WIN32:
        _svc_name_ = "ARGOS"
        _svc_display_name_ = "ARGOS Autonomous Security"
        _svc_description_ = "Servidor/agente ARGOS de ciberdefensa autónoma"

    def __init__(self, args=None):
        if not _HAS_WIN32:
            raise RuntimeError("pywin32 no disponible; usa nssm (deploy/windows/install-service.ps1)")
        # pywin32 construye la clase de servicio con win32serviceutil.ServiceFramework
        import servicemanager  # type: ignore

        self._svc_name_ = ArgosService._svc_name_
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        servicemanager.LogInfoMsg("ARGOS service init")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        import subprocess

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        # Por defecto corre el server; el agente se instala como servicio aparte.
        subprocess.run([sys.executable, "-m", "argos.server"], check=False)
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def ReportServiceStatus(self, status):
        win32serviceutil.ServiceFramework.ReportServiceStatus(self, status)


def install(component: str = "server") -> None:
    if not _HAS_WIN32:
        raise RuntimeError(
            "pywin32 no instalado. Usa nssm: deploy/windows/install-service.ps1"
        )
    win32serviceutil.HandleCommandLine(ArgosService, argv=["argos-service", "install", "--startup", "auto"])


def main() -> None:
    if not _HAS_WIN32:
        print("pywin32 no disponible. Usa deploy/windows/install-service.ps1 (nssm).")
        raise SystemExit(1)
    win32serviceutil.HandleCommandLine(ArgosService)


if __name__ == "__main__":
    main()
