from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, List, Optional

from argos.plugins.base import HookEvent, PluginManifest
from argos.plugins.hooks.base import BaseHook
from argos.plugins.marketplace import MARKETPLACE

logger = logging.getLogger("argos.plugins.registry")


class PluginInstance:
    """Wrapper en runtime de un plugin cargado desde su entry_point."""

    def __init__(self, manifest: PluginManifest, hooks: Optional[List[BaseHook]] = None) -> None:
        self.manifest = manifest
        self.hooks: List[BaseHook] = hooks or []
        self.enabled = manifest.enabled

    @property
    def name(self) -> str:
        return self.manifest.name

    def to_dict(self) -> Dict[str, Any]:
        d = self.manifest.to_dict()
        d["enabled"] = self.enabled
        d["hook_count"] = len(self.hooks)
        return d


class PluginRegistry:
    """Registro central de plugins instalados y sus hooks por evento."""

    def __init__(self) -> None:
        self.plugins: Dict[str, PluginInstance] = {}
        self.hooks: Dict[HookEvent, List[BaseHook]] = {e: [] for e in HookEvent.all()}

    def register_plugin(self, plugin: PluginInstance) -> None:
        self.plugins[plugin.name] = plugin
        for hook in plugin.hooks:
            if hook.enabled and plugin.enabled:
                self.hooks[hook.event].append(hook)
        self._resort(hook.event for hook in plugin.hooks)
        logger.info("Plugin registrado: %s (hooks=%d)", plugin.name, len(plugin.hooks))

    def unregister_plugin(self, name: str) -> None:
        self.plugins.pop(name, None)
        for event in self.hooks:
            self.hooks[event] = [h for h in self.hooks[event] if getattr(h, "plugin_name", None) != name]
        logger.info("Plugin desregistrado: %s", name)

    def load_from_manifest(self, manifest: PluginManifest) -> Optional[PluginInstance]:
        try:
            hooks = self._instantiate_hooks(manifest)
            plugin = PluginInstance(manifest, hooks)
            self.register_plugin(plugin)
            return plugin
        except Exception as exc:
            logger.error("No se pudo cargar el plugin %s: %s", manifest.name, exc)
            return None

    def _instantiate_hooks(self, manifest: PluginManifest) -> List[BaseHook]:
        hooks: List[BaseHook] = []
        if not manifest.entry_point:
            return hooks
        module_path, class_name = manifest.entry_point.rsplit(":", 1)
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            logger.warning("No se pudo importar entry_point %s: %s", manifest.entry_point, exc)
            return hooks
        plugin_cls = getattr(module, class_name, None)
        if plugin_cls is None:
            return hooks
        instance = plugin_cls()
        for hook_spec in manifest.components.hooks:
            hook = self._build_hook(hook_spec, instance)
            if hook is not None:
                hook.plugin_name = manifest.name  # type: ignore[attr-defined]
                hooks.append(hook)
        return hooks

    def _build_hook(self, hook_spec: str, plugin_instance: Any) -> Optional[BaseHook]:
        builder = getattr(plugin_instance, f"build_{hook_spec}", None)
        if callable(builder):
            try:
                return builder()
            except Exception as exc:
                logger.warning("Hook builder %s falló: %s", hook_spec, exc)
        return None

    def enable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin is None:
            return False
        plugin.enabled = True
        for hook in plugin.hooks:
            hook.enable()
            if hook.event in self.hooks and hook not in self.hooks[hook.event]:
                self.hooks[hook.event].append(hook)
        self._resort_all()
        return True

    def disable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin is None:
            return False
        plugin.enabled = False
        for hook in plugin.hooks:
            hook.disable()
            self.hooks[hook.event] = [h for h in self.hooks[hook.event] if h is not hook]
        return True

    def execute_hooks(self, event: HookEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        for hook in list(self.hooks.get(event, [])):
            if not hook.enabled:
                continue
            try:
                result = hook.execute(context)
                if result is not None:
                    context = result
            except Exception as exc:
                logger.error("Hook %s falló en %s: %s", hook, event.value, exc)
        return context

    def list_installed(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.plugins.values()]

    def available_in_marketplace(self) -> List[Dict[str, Any]]:
        installed = set(self.plugins.keys())
        return [m.to_dict() for m in MARKETPLACE.plugins if m.name not in installed]

    def _resort(self, events: Any) -> None:
        for event in events:
            if isinstance(event, HookEvent):
                self.hooks[event].sort(key=lambda h: h.priority, reverse=True)

    def _resort_all(self) -> None:
        for event in self.hooks:
            self.hooks[event].sort(key=lambda h: h.priority, reverse=True)


def registry_from_marketplace() -> PluginRegistry:
    """Construye un registry precargado con los plugins locales del marketplace."""
    reg = PluginRegistry()
    for manifest in MARKETPLACE.plugins:
        if manifest.source.type == "local" and manifest.entry_point:
            reg.load_from_manifest(manifest)
    return reg
