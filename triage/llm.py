"""Thin, provider-agnostic LLM client.

Pick the provider with the LLM_PROVIDER environment variable (or the --provider
CLI flag):

    mock       no API key needed; deterministic output for demos and tests
    anthropic  needs ANTHROPIC_API_KEY  (pip install anthropic)
    openai     needs OPENAI_API_KEY     (pip install openai)

LLM_MODEL overrides the default model for the chosen provider.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4.1-mini",
}


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        mock_fn: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "mock").lower()
        if self.provider not in {"mock", "anthropic", "openai"}:
            raise LLMError(f"Unknown provider '{self.provider}'. Use mock, anthropic or openai.")
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(self.provider, "mock")
        self.mock_fn = mock_fn

    def complete(self, system: str, prompt: str, max_tokens: int = 1500) -> str:
        if self.provider == "mock":
            if self.mock_fn is None:
                raise LLMError("Mock provider selected but no mock function was supplied.")
            return self.mock_fn(system, prompt)
        if self.provider == "anthropic":
            return self._anthropic(system, prompt, max_tokens)
        return self._openai(system, prompt, max_tokens)

    def _anthropic(self, system: str, prompt: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError("Run `pip install anthropic` to use this provider.") from exc
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")

    def _openai(self, system: str, prompt: str, max_tokens: int) -> str:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise LLMError("Run `pip install openai` to use this provider.") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise LLMError("OPENAI_API_KEY is not set.")
        client = openai.OpenAI()
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""
