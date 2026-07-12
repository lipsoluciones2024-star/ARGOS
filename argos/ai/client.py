from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class ChatMessage:
    role: str
    content: Optional[str] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.role == "tool":
            if self.tool_call_id:
                d["tool_call_id"] = self.tool_call_id
            if self.name:
                d["name"] = self.name
        elif self.name:
            d["name"] = self.name
        return d


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments)},
        }


@dataclass
class ChatResponse:
    content: Optional[str]
    reasoning: Optional[str]
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


class GatewayClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self, anonymous: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if not anonymous and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        anonymous: bool = True,
        stream: bool = False,
    ) -> ChatResponse:
        anonymous = anonymous or ":free" in model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(anonymous),
                    json=payload,
                )
                if r.status_code == 401:
                    raise RuntimeError("401: missing API key for paid model")
                if r.status_code == 429:
                    raise RuntimeError("429: anonymous rate limit (200 req/h/IP) exceeded")
                r.raise_for_status()
                return self._parse(r.json())
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"http error: {exc}") from exc

    @staticmethod
    def _parse(data: dict[str, Any]) -> ChatResponse:
        choice = data["choices"][0]["message"]
        content = choice.get("content")
        reasoning = choice.get("reasoning")
        tool_calls: list[ToolCall] = []
        for tc in choice.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = __import__("json").loads(args)
                except Exception:
                    args = {}
            tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))
        if not content and reasoning:
            content = reasoning
        return ChatResponse(content=content, reasoning=reasoning, tool_calls=tool_calls,
                            model=data.get("model"), raw=data)

    def list_models(self, anonymous: bool = True) -> list[str]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/v1/models", headers=self._headers(anonymous))
            r.raise_for_status()
            return [m["id"] for m in r.json().get("data", [])]

    def stream_chat(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        anonymous: bool = True,
    ):
        """Yield incremental :class:`ChatResponse` chunks for a streaming request.

        Falls back to a single non-streaming response if streaming is unsupported.
        """
        anonymous = anonymous or ":free" in model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(anonymous),
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        line = (line or "").strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            return
                        try:
                            parsed = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        yield self._parse_chunk(parsed)
        except (httpx.TimeoutException, httpx.HTTPError):
            yield self.chat(model, messages, tools=tools, temperature=temperature,
                            max_tokens=max_tokens, anonymous=anonymous, stream=False)

    @staticmethod
    def _parse_chunk(data: dict[str, Any]) -> ChatResponse:
        delta = data["choices"][0].get("delta", {})
        content = delta.get("content")
        reasoning = delta.get("reasoning")
        tool_calls: list[ToolCall] = []
        for tc in delta.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", "")
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=fn.get("name", ""),
                arguments={"_partial": args} if isinstance(args, str) else (args or {}),
            ))
        return ChatResponse(content=content, reasoning=reasoning, tool_calls=tool_calls,
                            model=data.get("model"), raw=data)
