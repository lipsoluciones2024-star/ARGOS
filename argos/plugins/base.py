from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HookEvent(str, Enum):
    """Eventos del ciclo de vida sobre los que los plugins pueden engancharse."""

    PRE_DETECTION = "pre_detection"
    POST_DETECTION = "post_detection"
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"
    ON_ALERT = "on_alert"
    ON_PLUGIN_INSTALL = "on_plugin_install"
    ON_PLUGIN_UNINSTALL = "on_plugin_uninstall"
    ON_CONFIG_CHANGE = "on_config_change"

    @classmethod
    def all(cls) -> List["HookEvent"]:
        return list(cls)


class PluginCategory(str, Enum):
    DETECTION = "detection"
    RESPONSE = "response"
    ANALYTICS = "analytics"
    UI = "ui"
    INTEGRATION = "integration"


@dataclass
class PluginComponent:
    """Componentes que un plugin puede exponer al ecosistema ARGOS."""

    skills: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)


@dataclass
class PluginSource:
    type: str = "local"
    path: Optional[str] = None
    url: Optional[str] = None
    sha: Optional[str] = None


@dataclass
class PluginManifest:
    """Manifiesto declarativo de un plugin (plugin.json / marketplace.json)."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "ARGOS Team"
    license: str = "Apache-2.0"
    category: str = "detection"
    permissions: List[str] = field(default_factory=lambda: ["read"])
    dependencies: List[str] = field(default_factory=list)
    entry_point: Optional[str] = None
    components: PluginComponent = field(default_factory=PluginComponent)
    source: PluginSource = field(default_factory=PluginSource)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "category": self.category,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "components": {
                "skills": self.components.skills,
                "commands": self.components.commands,
                "agents": self.components.agents,
                "mcp_servers": self.components.mcp_servers,
                "hooks": self.components.hooks,
            },
            "source": {
                "type": self.source.type,
                "path": self.source.path,
                "url": self.source.url,
                "sha": self.source.sha,
            },
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        comp = data.get("components", {}) or {}
        src = data.get("source", {}) or {}
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "ARGOS Team"),
            license=data.get("license", "Apache-2.0"),
            category=data.get("category", "detection"),
            permissions=list(data.get("permissions", ["read"])),
            dependencies=list(data.get("dependencies", [])),
            entry_point=data.get("entry_point"),
            components=PluginComponent(
                skills=list(comp.get("skills", [])),
                commands=list(comp.get("commands", [])),
                agents=list(comp.get("agents", [])),
                mcp_servers=list(comp.get("mcp_servers", [])),
                hooks=list(comp.get("hooks", [])),
            ),
            source=PluginSource(
                type=src.get("type", "local"),
                path=src.get("path"),
                url=src.get("url"),
                sha=src.get("sha"),
            ),
            enabled=bool(data.get("enabled", True)),
        )
