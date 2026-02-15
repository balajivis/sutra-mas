"""Unified LLM client supporting Anthropic and OpenAI models."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import anthropic
import openai


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    tokens_in: int
    tokens_out: int
    model: str
    latency_ms: float
    raw_response: dict | None = None


@dataclass
class LLMClient:
    """Multi-provider LLM client for the experiment harness.

    Supports Anthropic (Claude) and OpenAI (GPT) models.
    Tracks token usage across all calls for experiment accounting.
    """

    model: str = "claude-opus-4-6"
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_calls: int = 0
    total_latency_ms: float = 0.0
    call_log: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self._anthropic = None
        self._openai = None

    @property
    def _is_anthropic(self) -> bool:
        return self.model.startswith("claude")

    @property
    def _is_openai(self) -> bool:
        return self.model.startswith("gpt") or self.model.startswith("o1") or self.model.startswith("o3")

    def _get_anthropic_client(self) -> anthropic.Anthropic:
        if self._anthropic is None:
            # Support Azure-hosted Anthropic (AZURE_ANTHROPIC_ENDPOINT + AZURE_API_KEY)
            # or direct Anthropic (ANTHROPIC_API_KEY)
            azure_endpoint = os.environ.get("AZURE_ANTHROPIC_ENDPOINT")
            azure_key = os.environ.get("AZURE_API_KEY")

            if azure_endpoint and azure_key:
                self._anthropic = anthropic.Anthropic(
                    api_key=azure_key,
                    base_url=azure_endpoint,
                )
            else:
                self._anthropic = anthropic.Anthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                )
        return self._anthropic

    def _get_openai_client(self) -> openai.OpenAI:
        if self._openai is None:
            self._openai = openai.OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            )
        return self._openai

    async def chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a chat completion request and return standardized response."""
        start = time.time()

        if self._is_anthropic:
            response = await self._chat_anthropic(system, messages, max_tokens, temperature)
        elif self._is_openai:
            response = await self._chat_openai(system, messages, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown model provider for: {self.model}")

        elapsed = (time.time() - start) * 1000
        response.latency_ms = elapsed

        # Track totals
        self.total_tokens_in += response.tokens_in
        self.total_tokens_out += response.tokens_out
        self.total_calls += 1
        self.total_latency_ms += elapsed

        # Log the call
        self.call_log.append({
            "model": self.model,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "latency_ms": elapsed,
            "system_preview": system[:100],
            "message_count": len(messages),
        })

        return response

    async def _chat_anthropic(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        client = self._get_anthropic_client()

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Use sync client in async context (anthropic SDK handles this)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=anthropic_messages,
        )

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            model=self.model,
            latency_ms=0,  # Set by caller
        )

    async def _chat_openai(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call OpenAI GPT API."""
        client = self._get_openai_client()

        # Build OpenAI messages with system prompt
        openai_messages = [{"role": "system", "content": system}]
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=openai_messages,
        )

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice else ""
        usage = response.usage

        return LLMResponse(
            content=content or "",
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            model=self.model,
            latency_ms=0,
        )

    def get_stats(self) -> dict:
        """Return usage statistics."""
        return {
            "model": self.model,
            "total_calls": self.total_calls,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.total_latency_ms / max(self.total_calls, 1),
        }

    def reset_stats(self) -> None:
        """Reset all usage tracking."""
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_calls = 0
        self.total_latency_ms = 0.0
        self.call_log = []
