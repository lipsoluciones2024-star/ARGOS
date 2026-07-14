from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional


class AuthError(Exception):
    """Credencial inválida, expirada o sin rol suficiente."""


ROLES = ("operator", "admin")
ROLE_RANK = {"operator": 1, "admin": 2}


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(token: str) -> bytes:
    pad = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + pad)


def derive_secret(auth_secret: Optional[str], salt: str) -> str:
    """Deriva un secreto estable a partir de ARGOS_AUTH_SECRET o del data_dir."""
    if auth_secret:
        return hashlib.sha256(auth_secret.encode("utf-8")).hexdigest()
    return hashlib.sha256(("argos:" + salt).encode("utf-8")).hexdigest()


def sign_token(secret: str, role: str, sub: str = "cli", ttl: int = 0) -> str:
    """Firma un token HMAC con claims {role, sub, exp}.

    Formato: <b64(header)>.<b64(payload)>.<b64(sig)>. Sin librerías externas.
    """
    if role not in ROLES:
        raise AuthError(f"rol inválido: {role}")
    header = _b64u(json.dumps({"alg": "HS256", "typ": "ARGOS"}).encode("utf-8"))
    claims: dict = {"role": role, "sub": sub}
    if ttl > 0:
        claims["exp"] = int(time.time()) + ttl
    payload = _b64u(json.dumps(claims).encode("utf-8"))
    signing = f"{header}.{payload}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64u(sig)}"


def verify_token(token: str, secret: str, static_admin_token: Optional[str] = None) -> dict:
    """Devuelve los claims si el token es válido; lanza AuthError si no.

    Un token estático (ARGOS_API_TOKEN) siempre es admin.
    """
    if static_admin_token and token and hmac.compare_digest(token, static_admin_token):
        return {"role": "admin", "sub": "static", "static": True}
    if not token or token.count(".") != 2:
        raise AuthError("token mal formado")
    header, payload, sig = token.split(".")
    signing = f"{header}.{payload}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing, hashlib.sha256).digest()
    provided = _b64d(sig)
    if not hmac.compare_digest(expected, provided):
        raise AuthError("firma inválida")
    try:
        claims = json.loads(_b64d(payload))
    except Exception as exc:
        raise AuthError("payload ilegible") from exc
    exp = claims.get("exp")
    if exp and int(time.time()) > int(exp):
        raise AuthError("token expirado")
    if claims.get("role") not in ROLES:
        raise AuthError("rol inválido")
    return claims


def role_sufficient(actual: str, required: str) -> bool:
    return ROLE_RANK.get(actual, 0) >= ROLE_RANK.get(required, 0)


def generate_token_command(role: str, secret: str, sub: str = "cli", ttl: int = 0) -> str:
    return sign_token(secret, role, sub=sub, ttl=ttl)
