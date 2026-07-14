from __future__ import annotations

from typing import Any

from argos.security.auth import ROLES, role_sufficient


def get_claims(request: Any) -> dict:
    """Devuelve los claims del request. Si no hay (modo inseguro / require_auth=False),
    asume rol admin para no romper la operación de administración."""
    claims = getattr(request.state, "claims", None)
    if not claims:
        return {"role": "admin", "sub": "insecure", "static": True}
    return claims


def has_role(request: Any, min_role: str) -> bool:
    claims = get_claims(request)
    actual = claims.get("role", "operator")
    return role_sufficient(actual, min_role)


def require_role(request: Any, min_role: str) -> tuple[bool, dict]:
    """(ok, claims) — ok=True si el rol alcanza el mínimo requerido."""
    claims = get_claims(request)
    actual = claims.get("role", "operator")
    if actual not in ROLES:
        return False, claims
    return role_sufficient(actual, min_role), claims
