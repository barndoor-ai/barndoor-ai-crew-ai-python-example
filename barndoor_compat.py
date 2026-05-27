"""Workaround for a pagination bug in barndoor-sdk's ``BarndoorSDK.list_servers``.

The registry API returns its paging metadata nested under a ``pagination`` key::

    {"data": [...], "pagination": {"page": 1, "total": 25, "next_page": 2, ...}}

but ``list_servers`` reads ``next_page`` from the top level (where it's always
``None``), so it never advances past the first page and silently returns only the
first ~10 servers. That hides any connected app that isn't in the first page.

:func:`fetch_all_servers` paginates correctly by reading the ``pagination`` envelope.
Drop it in place of ``await sdk.list_servers()``. Remove once the SDK is fixed
upstream (HEAD 7d804d6 still has the bug).
"""

from __future__ import annotations

from barndoor.sdk.models import ServerSummary

_PAGE_LIMIT = 100
_MAX_PAGES = 100  # guard against an API that never reports next_page == null


async def fetch_all_servers(sdk) -> list[ServerSummary]:  # type: ignore[no-untyped-def]
    """Return every MCP server for the caller, following real pagination."""
    await sdk.ensure_valid_token()

    servers: list[ServerSummary] = []
    page = 1
    for _ in range(_MAX_PAGES):
        resp = await sdk._req("GET", "/api/servers", params={"page": page, "limit": _PAGE_LIMIT})

        # Legacy shape: a bare list of servers.
        if isinstance(resp, list):
            servers.extend(ServerSummary.model_validate(o) for o in resp)
            break

        servers.extend(ServerSummary.model_validate(o) for o in resp.get("data", []))

        pagination = resp.get("pagination") or resp  # tolerate either envelope shape
        next_page = pagination.get("next_page")
        if not next_page:
            break
        page = int(next_page)

    return servers
