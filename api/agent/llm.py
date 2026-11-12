"""Minimal provider-agnostic client for OpenAI-compatible /chat/completions with function calling and streaming.

Works with any endpoint that speaks the OpenAI Chat Completions wire format: OpenAI, Groq, OpenRouter,
Together, DeepSeek, Mistral, Ollama/LM Studio, LiteLLM proxies, and Anthropic's OpenAI-compatibility endpoint."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterator

import httpx


class LLMError(RuntimeError):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str = ""

    def args(self) -> dict:
        try:
            return json.loads(self.arguments or "{}")
        except json.JSONDecodeError as e:
            raise LLMError(f"model produced invalid JSON arguments for {self.name}: {e}")


@dataclass
class Turn:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class ChatClient:
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 60.0, transport: httpx.BaseTransport | None = None):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.http = httpx.Client(timeout=timeout, transport=transport,
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def stream(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.2) -> Iterator[tuple[str, object]]:
        """Yields ("token", str) while streaming text, then ("turn", Turn) once the response is complete."""
        body = {"model": self.model, "messages": messages, "temperature": temperature, "stream": True}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        turn = Turn()
        calls: dict[int, ToolCall] = {}
        try:
            with self.http.stream("POST", self.url, json=body) as resp:
                if resp.status_code >= 400:
                    raise LLMError(f"LLM HTTP {resp.status_code}: {resp.read().decode(errors='replace')[:400]}")
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if not chunk.get("choices"):
                        continue
                    delta = chunk["choices"][0].get("delta") or {}
                    if delta.get("content"):
                        turn.content += delta["content"]
                        yield "token", delta["content"]
                    for tc in delta.get("tool_calls") or []:
                        i = tc.get("index", 0)
                        c = calls.setdefault(i, ToolCall(id=tc.get("id") or f"call_{i}", name=""))
                        if tc.get("id"):
                            c.id = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            c.name = fn["name"]
                        if fn.get("arguments"):
                            c.arguments += fn["arguments"]
        except httpx.HTTPError as e:
            raise LLMError(f"LLM request failed: {type(e).__name__}: {e}") from e
        turn.tool_calls = [calls[i] for i in sorted(calls)]
        yield "turn", turn
