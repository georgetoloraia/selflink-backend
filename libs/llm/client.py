from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import requests

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover - fallback when library missing
    OpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class LLMClient:
    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        raise NotImplementedError


class MentorLLMClient(LLMClient):
    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self.model = model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url)

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        response = self.client.responses.create(  # type: ignore[attr-defined]
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        content = response.output[0].content[0].text  # type: ignore[index]
        return content.strip()


def get_llm_client(overrides: Optional[Dict[str, Any]] = None) -> LLMClient:
    provider = os.getenv("MENTOR_LLM_PROVIDER", "openai").lower()
    if provider == "mock":
        return MockLLMClient()
    if provider == "openai":
        model = (overrides or {}).get("model") or os.getenv("MENTOR_LLM_MODEL", "gpt-4o-mini")
        api_key = (overrides or {}).get("api_key")
        base_url = (overrides or {}).get("base_url")
        return MentorLLMClient(model=model, api_key=api_key, base_url=base_url)
    if provider == "ollama":
        model = (overrides or {}).get("model") or os.getenv("MENTOR_LLM_MODEL", "llama3")
        host = (overrides or {}).get("host") or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        timeout = float((overrides or {}).get("timeout") or os.getenv("MENTOR_LLM_TIMEOUT", "60"))
        return OllamaLLMClient(model=model, host=host, timeout=timeout)
    raise ValueError(f"Unsupported LLM provider: {provider}")


class MockLLMClient(LLMClient):
    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:  # pragma: no cover
        logger.info("MockLLMClient returning canned response")
        return "I hear you. Let's take a mindful breath together and note one feeling right now."


class OllamaLLMClient(LLMClient):
    def __init__(self, model: str, host: str, timeout: float = 60.0) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "options": {
                "temperature": temperature,
            },
            "stream": False,
        }
        response = requests.post(
            f"{self.host}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "").strip()
        if not text:
            raise RuntimeError("Ollama returned empty response")
        return text
