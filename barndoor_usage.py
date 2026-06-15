"""Query Barndoor's LLM usage API for an agent API key's recent calls.

Endpoint: ``GET https://app.barndoor.ai/api/llm-usage/query`` (overridable via
``BARNDOOR_USAGE_URL``). The caller supplies the Bearer JWT — typically the
authenticated user's session token (``sdk.token`` from ``BarndoorSDK``).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

USAGE_URL = os.getenv(
    "BARNDOOR_USAGE_URL",
    "https://app.barndoor.ai/api/llm-usage/query",
)


def fetch_usage(
    api_key_id: str,
    from_iso: str,
    to_iso: str,
    *,
    bearer: str,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Return the raw JSON from ``/llm-usage/query`` for one agent API key."""
    if not api_key_id:
        raise ValueError("api_key_id is required (Barndoor agent API key UUID)")
    if not bearer:
        raise ValueError("bearer JWT is required (e.g. the SDK session token)")
    resp = httpx.get(
        USAGE_URL,
        headers={"Authorization": f"Bearer {bearer}"},
        params={
            "api_key_id": api_key_id,
            "from": from_iso,
            "to": to_iso,
            "limit": limit,
            "offset": offset,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
