from __future__ import annotations

from typing import Any, Iterator, Optional

from argos.ai.client import ChatMessage, ChatResponse, GatewayClient
from argos.config import Config, LlmMode

GATEWAY_FAILOVER_MODELS = [
    "tencent/hy3:free",
    "kilo-auto/free",
    "openrouter/free",
    "cohere/north-mini-code:free",
]


class GatewayFailover:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.client = GatewayClient(cfg.gateway_base_url, api_key=cfg.kilo_api_key, timeout=cfg.request_timeout)
        self.models = GATEWAY_FAILOVER_MODELS

    def chat(self, messages: list[ChatMessage], tools=None, max_tokens: int = 1024,
             model: Optional[str] = None, temperature: float = 0.2) -> ChatResponse:
        last_err: Optional[str] = None
        models = [model] if model else self.models
        for m in models:
            try:
                return self.client.chat(m, messages, tools=tools, max_tokens=max_tokens,
                                        temperature=temperature, anonymous=True)
            except RuntimeError as exc:
                last_err = str(exc)
                continue
        raise RuntimeError(f"Los proveedores del gateway fallaron: {last_err}")

    def stream(self, messages: list[ChatMessage], tools=None, max_tokens: int = 1024,
               model: Optional[str] = None, temperature: float = 0.2) -> Iterator[ChatResponse]:
        chosen = model or self.models[0]
        yield from self.client.stream_chat(chosen, messages, tools=tools, max_tokens=max_tokens,
                                           temperature=temperature, anonymous=True)

    def available(self) -> bool:
        try:
            self.client.list_models(anonymous=True)
            return True
        except Exception:
            return False


class DirectProviderFailover:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.providers = cfg.remote_providers

    def chat(self, messages: list[ChatMessage], tools=None, max_tokens: int = 1024,
             model: Optional[str] = None, temperature: float = 0.2) -> ChatResponse:
        import os

        last_err: Optional[str] = None
        for p in self.providers:
            key = os.environ.get(p.api_key_env) if p.api_key_env else None
            if p.requires_key and not key:
                continue
            if model and p.model != model:
                continue
            client = GatewayClient(p.base_url, api_key=key, timeout=self.cfg.request_timeout)
            try:
                return client.chat(p.model, messages, tools=tools, max_tokens=max_tokens,
                                    temperature=temperature, anonymous=not p.requires_key)
            except RuntimeError as exc:
                last_err = str(exc)
                continue
        raise RuntimeError(f"Los proveedores directos fallaron: {last_err}")

    def available(self) -> bool:
        return any(p.requires_key is False or p.api_key_env for p in self.providers)


class LocalRuntime:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.client = GatewayClient(cfg.local_base_url, api_key=None, timeout=cfg.request_timeout)
        self.model = cfg.local_model

    def available(self) -> bool:
        try:
            self.client.list_models(anonymous=True)
            return True
        except Exception:
            return False

    def chat(self, messages: list[ChatMessage], tools=None, max_tokens: int = 1024,
             model: Optional[str] = None, temperature: float = 0.2) -> ChatResponse:
        return self.client.chat(model or self.model, messages, tools=tools, max_tokens=max_tokens,
                                temperature=temperature, anonymous=True)

    def stream(self, messages: list[ChatMessage], tools=None, max_tokens: int = 1024,
               model: Optional[str] = None, temperature: float = 0.2) -> Iterator[ChatResponse]:
        yield from self.client.stream_chat(model or self.model, messages, tools=tools, max_tokens=max_tokens,
                                           temperature=temperature, anonymous=True)


class HybridRouter:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.mode = cfg.llm_mode
        self.gateway = GatewayFailover(cfg)
        self.direct = DirectProviderFailover(cfg)
        self.local = LocalRuntime(cfg)
        self._last_channel = "none"
        self._last_model = ""

    def _resolve(self, runtime: dict[str, Any]) -> tuple[str, Optional[str], float, int]:
        mode = runtime.get("mode") or self.mode.value
        model = runtime.get("model") or None
        temperature = float(runtime.get("temperature", 0.2))
        max_tokens = int(runtime.get("max_tokens", 1024))
        return mode, model, temperature, max_tokens

    def chat(self, messages: list[ChatMessage], tools=None, runtime: dict[str, Any] | None = None) -> ChatResponse:
        runtime = runtime or {}
        mode, model, temperature, max_tokens = self._resolve(runtime)
        if mode == LlmMode.LOCAL.value:
            resp = self.local.chat(messages, tools=tools, max_tokens=max_tokens, temperature=temperature)
            self._last_channel = "local"
            self._last_model = self.local.model
            return resp
        try:
            resp = self.gateway.chat(messages, tools=tools, max_tokens=max_tokens, model=model, temperature=temperature)
            self._last_channel = "gateway"
            self._last_model = model or "gateway-failover"
            return resp
        except RuntimeError:
            if mode == LlmMode.REMOTE.value:
                raise
            resp = self.local.chat(messages, tools=tools, max_tokens=max_tokens, temperature=temperature)
            self._last_channel = "local-fallback"
            self._last_model = self.local.model
            return resp

    def stream(self, messages: list[ChatMessage], tools=None, runtime: dict[str, Any] | None = None) -> Iterator[ChatResponse]:
        runtime = runtime or {}
        mode, model, temperature, max_tokens = self._resolve(runtime)
        if mode == LlmMode.LOCAL.value:
            self._last_channel = "local"
            self._last_model = self.local.model
            yield from self.local.stream(messages, tools=tools, max_tokens=max_tokens, temperature=temperature)
            return
        try:
            self._last_channel = "gateway"
            self._last_model = model or "gateway-failover"
            yield from self.gateway.stream(messages, tools=tools, max_tokens=max_tokens, model=model, temperature=temperature)
        except RuntimeError:
            if mode == LlmMode.REMOTE.value:
                raise
            self._last_channel = "local-fallback"
            self._last_model = self.local.model
            yield from self.local.stream(messages, tools=tools, max_tokens=max_tokens, temperature=temperature)

    def channel(self) -> str:
        return self._last_channel

    def model(self) -> str:
        return self._last_model

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "last_channel": self._last_channel,
            "last_model": self._last_model,
            "gateway_available": self.gateway.available(),
            "local_available": self.local.available(),
            "direct_available": self.direct.available(),
        }
