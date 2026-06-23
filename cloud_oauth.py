"""Server-side OAuth flow for hosted Streamlit deployments.

The SDK's ``bd.login_interactive()`` defaults to a loopback callback
(``http://127.0.0.1:52765/cb``), which only works on a developer's local machine.
When the app is hosted (e.g. Streamlit Community Cloud), the browser can't reach the
*server's* loopback — so the OAuth callback must instead land back on the app itself
as a normal HTTP redirect to a public URL.

This module wraps the SDK's OAuth helpers for that "web app" flow:

1. :func:`build_authorize_request` — generates the Keycloak authorize URL and the
   PKCE ``code_verifier`` + ``state`` to keep in session for callback validation.
2. :func:`exchange_code` — trades the returned ``code`` for an OAuth token dict.
3. :func:`cache_tokens` — writes those tokens to ``~/.barndoor/token.json``. The next
   call to ``bd.login_interactive()`` then finds them, skips the loopback flow, and
   returns a working ``BarndoorSDK``.

The public callback URL is read from ``STREAMLIT_PUBLIC_URL`` (e.g.
``https://your-app.streamlit.app/``). If unset, callers should fall back to the
SDK's normal loopback flow for local development.
"""

from __future__ import annotations

import os

from barndoor.sdk.auth import AuthorizationRequest, create_authorization_request, exchange_code_for_token
from barndoor.sdk.auth_store import save_user_token
from barndoor.sdk.config import get_static_config


def public_callback_url() -> str | None:
    """Return the public redirect URI for this deployment, or ``None`` for local mode.

    Set ``STREAMLIT_PUBLIC_URL`` to the *exact* URL registered as a Valid Redirect URI
    on the Keycloak client (e.g. ``https://your-app.streamlit.app/``). Trailing slash
    matters — Keycloak does exact string matching.
    """
    return os.getenv("STREAMLIT_PUBLIC_URL") or None


def build_authorize_request(redirect_uri: str) -> AuthorizationRequest:
    """Build the Keycloak authorize URL for a web-app PKCE flow.

    Store the returned ``state`` and ``code_verifier`` in session before redirecting
    the user to ``request.url``; pass them back to :func:`exchange_code` on callback.
    """
    cfg = get_static_config()
    return create_authorization_request(
        client_id=cfg.client_id,
        redirect_uri=redirect_uri,
        audience=cfg.api_audience,
        issuer=cfg.auth_issuer,
    )


def exchange_code(redirect_uri: str, code: str, code_verifier: str) -> dict:
    """Exchange an authorization ``code`` for the OAuth token dict."""
    cfg = get_static_config()
    return exchange_code_for_token(
        domain="",  # ignored when ``issuer`` is provided (OIDC discovery is used)
        client_id=cfg.client_id,
        code=code,
        redirect_uri=redirect_uri,
        client_secret=cfg.client_secret or None,
        issuer=cfg.auth_issuer,
        code_verifier=code_verifier,
    )


def cache_tokens(tokens: dict) -> None:
    """Persist tokens to ``~/.barndoor/token.json`` so login_interactive uses them next."""
    save_user_token(tokens)
