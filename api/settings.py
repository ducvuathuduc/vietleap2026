"""Runtime configuration from environment variables (see README)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    out_dir: Path = field(default_factory=lambda: Path(os.getenv("KIT_OUT_DIR", KIT / "out")))
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("KIT_UPLOAD_DIR", KIT / "data" / "uploads")))
    cors_origins: tuple[str, ...] = tuple(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
    # OpenAI-compatible chat-completions endpoint (OpenAI, Groq, OpenRouter, Anthropic OpenAI-compat, LiteLLM, Ollama...)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or None
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "60"))
    agent_max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "8"))
    reports_on_upload: bool = os.getenv("REPORTS_ON_UPLOAD", "1") == "1"


def get_settings() -> Settings:
    return Settings()
