"""Assistant LLM configuration (Azure AI Services gpt-4o).

Reads the user's Azure config from the environment. The secret
(``AZURE_API_KEY``) lives in the repo-root ``.env`` (gitignored); we load that
file once here so the API works whether or not it was started with
``uvicorn --env-file .env``. The key is never logged.

``is_llm_configured()`` gates the whole LLM path: when it returns ``False`` the
service uses the deterministic brief and never imports/constructs LangChain.
"""

from __future__ import annotations

import os
from pathlib import Path

# Defaults are the user's proven config; any can be overridden via the environment.
DEFAULT_ENDPOINT = "https://enova-ai-3080-resource.services.ai.azure.com"
DEFAULT_DEPLOYMENT = "gpt-4o"
DEFAULT_API_VERSION = "2024-02-15-preview"

_dotenv_loaded = False


def _load_dotenv_once() -> None:
    """Load repo-root ``.env`` into the environment without overriding set vars."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    # api/assistant/config.py -> repo root is parents[2]
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


def azure_api_key() -> str | None:
    _load_dotenv_once()
    key = os.environ.get("AZURE_API_KEY")
    return key or None


def azure_endpoint() -> str:
    _load_dotenv_once()
    return os.environ.get("AZURE_OPENAI_ENDPOINT", DEFAULT_ENDPOINT)


def azure_deployment() -> str:
    _load_dotenv_once()
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT", DEFAULT_DEPLOYMENT)


def azure_api_version() -> str:
    _load_dotenv_once()
    return os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)


def is_llm_configured() -> bool:
    """True only when an API key is present — the single gate for the LLM path."""
    return bool(azure_api_key())
