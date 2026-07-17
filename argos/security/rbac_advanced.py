from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from argos.security.auth import ROLES as LEGACY_ROLES


class Permission(str, Enum):
    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    EXECUTE_ACTIONS = "execute:actions"
    MANAGE_USERS = "manage:users"
    MANAGE_RULES = "manage:rules"
    MANAGE_PLUGINS = "manage:plugins"
    VIEW_AUDIT = "view:audit"
    VIEW_METRICS = "view:metrics"
    SYSTEM_ADMIN = "system:admin"


class Role(str, Enum):
    OPERATOR = "operator"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OPERATOR: {Permission.READ_EVENTS, Permission.VIEW_AUDIT, Permission.VIEW_METRICS},
    Role.ANALYST: {
        Permission.READ_EVENTS, Permission.WRITE_EVENTS, Permission.VIEW_AUDIT,
        Permission.VIEW_METRICS, Permission.MANAGE_RULES,
    },
    Role.ADMIN: {
        Permission.READ_EVENTS, Permission.WRITE_EVENTS, Permission.EXECUTE_ACTIONS,
        Permission.MANAGE_USERS, Permission.MANAGE_RULES, Permission.MANAGE_PLUGINS,
        Permission.VIEW_AUDIT, Permission.VIEW_METRICS,
    },
    Role.SUPERADMIN: {
        Permission.READ_EVENTS, Permission.WRITE_EVENTS, Permission.EXECUTE_ACTIONS,
        Permission.MANAGE_USERS, Permission.MANAGE_RULES, Permission.MANAGE_PLUGINS,
        Permission.VIEW_AUDIT, Permission.VIEW_METRICS, Permission.SYSTEM_ADMIN,
    },
}

# Mapeo de roles heredados a permisos para no romper el RBAC actual.
LEGACY_ROLE_MAP: Dict[str, Set[Permission]] = {
    "operator": ROLE_PERMISSIONS[Role.OPERATOR],
    "admin": ROLE_PERMISSIONS[Role.ADMIN],
}

_ALL_PERMISSIONS = {p for perms in ROLE_PERMISSIONS.values() for p in perms}


def has_permission(role: str, permission: Permission) -> bool:
    perms = ROLE_PERMISSIONS.get(Role(role), LEGACY_ROLE_MAP.get(role))
    if perms is None:
        return False
    return permission in perms


def permissions_for(role: str) -> Set[Permission]:
    return set(ROLE_PERMISSIONS.get(Role(role), LEGACY_ROLE_MAP.get(role, set())))


def is_valid_role(role: str) -> bool:
    return role in LEGACY_ROLES or role in {r.value for r in Role}


def rank(role: str) -> int:
    order = ["operator", "analyst", "admin", "superadmin"]
    return order.index(role) if role in order else 0
