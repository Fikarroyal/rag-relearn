"""Provider pattern untuk LLM. Default: mock extractive (tanpa API key)."""

from __future__ import annotations
import os
import re
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def generate(self, query: str, context: list[dict]) -> str: ...


class MockLLM(LLMProvider):
    """Extractive generator: menjawab dari chunk rank-1 dan menyertakan sitasi [chunk_id]."""
    name = "mock-extractive"

    def generate(self, query, context):
        if not context:
            return "Informasi tidak ditemukan pada konteks yang tersedia."
        top = context[0]
        body = re.sub(r"\s+", " ", top["content"]).strip()
        return f"{body} [{top['chunk_id']}]"


class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, model=None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-6")

    def generate(self, query, context):
        ctx = "\n\n".join(f"[{c['chunk_id']}] {c['content']}" for c in context)
        msg = self.client.messages.create(
            model=self.model, max_tokens=600,
            messages=[{"role": "user", "content": f"Jawab hanya dari konteks, sertakan sitasi [chunk_id].\n\nKonteks:\n{ctx}\n\nPertanyaan: {query}"}])
        return msg.content[0].text


class OpenAILLM(LLMProvider):
    name = "openai"

    def __init__(self, model=None):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    def generate(self, query, context):
        ctx = "\n\n".join(f"[{c['chunk_id']}] {c['content']}" for c in context)
        r = self.client.chat.completions.create(model=self.model, messages=[
            {"role": "user", "content": f"Jawab hanya dari konteks, sertakan sitasi [chunk_id].\n\n{ctx}\n\nPertanyaan: {query}"}])
        return r.choices[0].message.content


def get_llm(name: str | None = None) -> LLMProvider:
    name = name or os.getenv("LLM_PROVIDER", "mock")
    try:
        if name == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicLLM()
        if name == "openai" and os.getenv("OPENAI_API_KEY"):
            return OpenAILLM()
    except Exception:  # fallback aman
        pass
    return MockLLM()
