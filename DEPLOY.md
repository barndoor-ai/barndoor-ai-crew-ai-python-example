# Deploying to Streamlit Community Cloud

This app's default `bd.login_interactive()` opens a browser OAuth flow that listens for
the callback on a **loopback URL** (`http://127.0.0.1:52765/cb`). That works on a
developer's laptop but doesn't on a hosted machine — the browser can't reach the
server's loopback. So a hosted deploy needs a **server-side OAuth callback** where
Keycloak redirects back to the deployed app's public URL.

The app already supports this. Setting `STREAMLIT_PUBLIC_URL` flips it on; on the
landing page you'll see a "Sign in with Barndoor" button instead of the loopback flow.

---

## 1. Pick the public URL for the app

Streamlit Cloud gives apps a URL like `https://<slug>.streamlit.app/`. You can claim
a custom slug from **App settings → URL**. Decide on the URL *before* deploying —
you'll need to register it with Keycloak as a redirect URI.

For the rest of this guide, use the placeholder:

```
https://barndoor-knowledge-worker.streamlit.app/
```

(Trailing slash matters — Keycloak does exact string matching.)

## 2. Register the callback URL in Barndoor's Keycloak

In your Barndoor Keycloak admin (`auth.barndoor.ai` → realm `barndoor` → client
`a739eaa0-6ef3-47f2-a283-dfdb89786014`), open **Valid Redirect URIs** and add:

```
https://barndoor-knowledge-worker.streamlit.app/
```

Click **Save**. Also confirm:

- **Standard Flow** is enabled (it's the authorization code flow with PKCE).
- **Require SSL** is not set to *all requests* with a non-HTTPS URI registered.

## 3. Push the repo and connect to Streamlit Cloud

- Push this repo to GitHub (`jay-updates` branch is fine; pick any).
- Go to <https://share.streamlit.io> → **New app** → pick the repo, branch, and
  entrypoint **`crew-ui.py`**.
- Streamlit Cloud will install dependencies from `requirements.txt`
  (which pins the barndoor SDK to the same git commit as local).

## 4. Set secrets in Streamlit Cloud

In the app's **Settings → Secrets** tab, paste:

```toml
LLM_API_KEY = "bd-…"                                 # gateway key for chat
AGENT_CLIENT_ID = "a739eaa0-…"
AGENT_CLIENT_SECRET = "…"
BARNDOOR_URL = "https://<your-org>.platform.barndoor.ai"
BARNDOOR_ENV = "production"

# Prevent hosted stdout/stderr from using ASCII and crashing on Unicode logs.
PYTHONIOENCODING = "utf-8:replace"

# This is what makes the app use server-side OAuth (not loopback):
STREAMLIT_PUBLIC_URL = "https://barndoor-knowledge-worker.streamlit.app/"

# Optional — only if you use the "API key usage" panel:
BARNDOOR_API_KEY = "<api-key-uuid-to-query-usage-for>"
```

Streamlit Cloud exposes these as both env vars *and* `st.secrets` automatically.

## 5. Test it

Open the app URL. On the landing page pick **Interactive login (browser)** → click
**Continue** → click **Sign in with Barndoor**. You'll go to Keycloak, log in, and be
bounced back to the app — now authenticated. Behind the scenes:

1. Click **Continue** → the app generates an authorize URL + PKCE state, stores them
   in `st.session_state.oauth_pending`, and shows the **Sign in** link button.
2. Clicking it sends you to Keycloak's authorize endpoint.
3. After login, Keycloak redirects to `STREAMLIT_PUBLIC_URL?code=…&state=…`.
4. The app sees `?code` on rerun, validates `state`, exchanges the code for tokens via
   `cloud_oauth.exchange_code`, and caches them to `~/.barndoor/token.json`.
5. `bd.login_interactive()` is called as usual — it finds the cached tokens and
   returns a working `BarndoorSDK` *without* trying the loopback callback.

---

## What changes vs. local dev

| Concern | Local dev | Streamlit Cloud |
|---|---|---|
| Redirect URI | `http://127.0.0.1:52765/cb` (SDK loopback) | `STREAMLIT_PUBLIC_URL` (server-side) |
| Browser ↔ callback | Direct loopback bind | Real HTTP redirect to your hosted URL |
| Triggered by | `STREAMLIT_PUBLIC_URL` unset | `STREAMLIT_PUBLIC_URL` set |
| OAuth code exchange | Inside the SDK's `start_local_callback_server` | [`cloud_oauth.exchange_code`](cloud_oauth.py) |
| Token cache | `~/.barndoor/token.json` | Same — but ephemeral with the container |

## Caveats

- **Containers are ephemeral.** Streamlit Cloud restarts apps periodically; the cached
  token at `~/.barndoor/token.json` doesn't survive. Users will re-sign-in after a
  restart. (For demos this is usually fine; for a 24/7 service consider Render/Fly.)
- **Public vs. private apps.** Streamlit Community Cloud is free for public apps. For
  private apps, use Streamlit Connect (paid) or a different platform (Render, Fly,
  Cloud Run — all support the same `STREAMLIT_PUBLIC_URL` flag).
- **M2M still works the same.** Picking *Machine-to-machine* on the landing page does a
  client-credentials grant — no browser flow involved, so deployment changes nothing.
