from __future__ import annotations

from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from argos.config import Config
from argos.security.auth import AuthError, verify_token
from argos.security.ratelimit import RateLimiter

# Rutas públicas que no requieren token (salud, UI estática y SPA).
_PUBLIC_PREFIXES = ("/api/v1/health", "/static", "/docs", "/openapi.json", "/redoc")
_PUBLIC_EXACT = ("/",)


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    """Protege todas las rutas salvo las públicas. Requiere Bearer token válido,
    aplica rate limiting por IP y expone los claims en request.state.claims."""

    def __init__(self, app, cfg: Config, secret: str, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.cfg = cfg
        self.secret = secret
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _is_public(path) or not self.cfg.require_auth:
            return await call_next(request)

        client_ip = request.client.host if request.client else "anon"
        if not self.limiter.is_allowed(client_ip):
            return JSONResponse(status_code=429, content={"error": "rate limit exceeded"})

        auth = request.headers.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        try:
            claims = verify_token(token, self.secret, self.cfg.api_token)
        except AuthError:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        request.state.claims = claims
        return await call_next(request)


def ws_token_from_request(request: Any) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("token", "")


def authorize_ws(cfg: Config, secret: str, token: str) -> Optional[dict]:
    if not cfg.require_auth:
        return {"role": "admin", "sub": "insecure"}
    try:
        return verify_token(token, secret, cfg.api_token)
    except AuthError:
        return None
