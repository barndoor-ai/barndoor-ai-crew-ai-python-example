"""Route CrewAI's LLM calls through the Barndoor LLM gateway (OpenAI-compatible).

The gateway (``.../api/llm-gateway/v1``) speaks the OpenAI API, authenticates with the
OpenAI API key, and exposes models by id — e.g. ``OpenAI/gpt-4o`` and ``gpt-4.1-mini``.

CrewAI/litellm treats a leading ``OpenAI/`` as a *provider* prefix and strips it before
calling, so the gateway 404s on the resulting bare name. Work around it by constructing the
LLM with a plain id CrewAI accepts, then setting ``.model`` to the exact gateway id, which
CrewAI forwards verbatim in the request.

Set ``BARNDOOR_LLM_GATEWAY_URL`` to override the endpoint (or to point back at OpenAI).
"""

from __future__ import annotations

import os

import httpx
from crewai import LLM

GATEWAY_URL = os.getenv(
    "BARNDOOR_LLM_GATEWAY_URL", "https://app.barndoor.ai/api/llm-gateway/v1"
)
# A bare model id CrewAI accepts at construction time; the real id is set afterward.
_INIT_MODEL = "gpt-4.1-mini"
DEFAULT_MODEL = "gpt-4.1-mini"

# Models the gateway intentionally does NOT serve. Offered in the menus so a demo can
# show the gateway rejecting an unsupported model (it returns 404 "model not found").
DEMO_UNSUPPORTED_MODELS = ["OpenAI/gpt-5", "OpenAI/gpt-5-mini", "OpenAI/gpt-5-nano"]


def _api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required to use the Barndoor LLM gateway")
    return key


def list_gateway_models() -> list[str]:
    """Return the model ids the gateway currently exposes (for menus/dropdowns)."""
    resp = httpx.get(
        f"{GATEWAY_URL}/models",
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=20,
    )
    resp.raise_for_status()
    return [m["id"] for m in resp.json().get("data", [])]


def make_llm(model: str) -> LLM:
    """Build a CrewAI LLM that routes ``model`` through the Barndoor gateway."""
    llm = LLM(model=_INIT_MODEL, base_url=GATEWAY_URL, api_key=_api_key())
    # Forward the exact gateway id (bypasses CrewAI's provider-prefix stripping).
    llm.model = model
    return llm
