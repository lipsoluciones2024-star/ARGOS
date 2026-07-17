from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from argos.plugins.base import PluginManifest
from argos.plugins.registry import PluginRegistry

logger = logging.getLogger("argos.plugins.manager")


class PluginManager:
    """Instala, desinstala y gestiona plugins en runtime.

    Soporta plugins locales (copia de carpeta) y remotos (git clone con
    verificación de SHA para integridad). El registry se mantiene sincronizado.
    """

    def __init__(self, registry: PluginRegistry, installed_dir: Path) -> None:
        self.registry = registry
        self.installed_dir = Path(installed_dir)
        self.installed_dir.mkdir(parents=True, exist_ok=True)

    def install(self, manifest: PluginManifest) -> bool:
        try:
            if manifest.source.type == "local":
                ok = self._install_local(manifest)
            elif manifest.source.type == "remote":
                ok = self._install_remote(manifest)
            else:
                logger.error("Tipo de source desconocido: %s", manifest.source.type)
                return False
            if not ok:
                return False
            plugin = self.registry.load_from_manifest(manifest)
            if plugin is None:
                logger.error("Plugin %s instalado pero no pudo registrarse", manifest.name)
                return False
            self.registry.execute_hooks(
                __import__("argos.plugins.base", fromlist=["HookEvent"]).HookEvent.ON_PLUGIN_INSTALL,
                {"plugin": manifest.name},
            )
            return True
        except Exception as exc:
            logger.error("Instalación fallida de %s: %s", manifest.name, exc)
            return False

    def _install_local(self, manifest: PluginManifest) -> bool:
        if manifest.source.path is None:
            logger.error("Plugin local %s sin 'path'", manifest.name)
            return False
        source = Path(manifest.source.path)
        if not source.exists():
            logger.error("Ruta de plugin local inexistente: %s", source)
            return False
        target = self.installed_dir / manifest.name
        if target.exists():
            logger.error("Plugin %s ya instalado en %s", manifest.name, target)
            return False
        shutil.copytree(source, target)
        self._write_manifest(target, manifest)
        return True

    def _install_remote(self, manifest: PluginManifest) -> bool:
        if manifest.source.url is None:
            logger.error("Plugin remoto %s sin 'url'", manifest.name)
            return False
        target = self.installed_dir / manifest.name
        if target.exists():
            logger.error("Plugin %s ya instalado", manifest.name)
            return False
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", manifest.source.url, str(target)],
                check=True, capture_output=True, text=True,
            )
        except Exception as exc:
            logger.error("git clone falló para %s: %s", manifest.name, exc)
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            return False
        actual_sha = self._git_sha(target)
        expected = (manifest.source.sha or "").lower()
        if expected and actual_sha != expected:
            logger.error("SHA mismatch para %s: expected %s got %s", manifest.name, expected, actual_sha)
            shutil.rmtree(target, ignore_errors=True)
            return False
        return True

    def _git_sha(self, path: Path) -> str:
        try:
            out = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=path,
                check=True, capture_output=True, text=True,
            )
            return out.stdout.strip().lower()
        except Exception:
            return ""

    def _write_manifest(self, target: Path, manifest: PluginManifest) -> None:
        (target / "plugin.json").write_text(
            json.dumps(manifest.to_dict(), indent=2), encoding="utf-8",
        )

    def uninstall(self, name: str) -> bool:
        plugin = self.registry.plugins.get(name)
        if plugin is None:
            logger.error("Plugin %s no instalado", name)
            return False
        self.registry.unregister_plugin(name)
        target = self.installed_dir / name
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        self.registry.execute_hooks(
            __import__("argos.plugins.base", fromlist=["HookEvent"]).HookEvent.ON_PLUGIN_UNINSTALL,
            {"plugin": name},
        )
        return True

    def list_installed(self) -> List[Dict[str, Any]]:
        return self.registry.list_installed()

    def enable(self, name: str) -> bool:
        return self.registry.enable_plugin(name)

    def disable(self, name: str) -> bool:
        return self.registry.disable_plugin(name)

    def load_installed_from_disk(self) -> int:
        """Carga plugins previamente instalados en disco (plugin.json)."""
        count = 0
        for child in self.installed_dir.iterdir():
            manifest_path = child / "plugin.json"
            if not child.is_dir() or not manifest_path.exists():
                continue
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = PluginManifest.from_dict(data)
            except Exception as exc:
                logger.warning("No se pudo leer %s: %s", manifest_path, exc)
                continue
            if self.registry.load_from_manifest(manifest) is not None:
                count += 1
        return count
