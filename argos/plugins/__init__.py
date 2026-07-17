from __future__ import annotations

from pathlib import Path
from typing import Optional

from argos.plugins.manager import PluginManager
from argos.plugins.marketplace import MARKETPLACE
from argos.plugins.registry import PluginRegistry, registry_from_marketplace

__all__ = ["PluginRegistry", "PluginManager", "MARKETPLACE", "registry_from_marketplace", "build_plugin_runtime"]

_DEFAULT_INSTALLED = Path(__file__).resolve().parent / "installed"


def build_plugin_runtime(installed_dir: Optional[Path] = None) -> tuple[PluginRegistry, PluginManager]:
    """Construye el registry (plugins del marketplace) y el manager.

    El manager carga tambien plugins instalados previamente en disco bajo
    ``installed_dir`` (por defecto argos/plugins/installed).
    """
    registry = registry_from_marketplace()
    manager = PluginManager(registry, installed_dir or _DEFAULT_INSTALLED)
    manager.load_installed_from_disk()
    return registry, manager
