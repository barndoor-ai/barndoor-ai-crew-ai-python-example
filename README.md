# Barndoor + CrewAI Example

Two small demos that connect [Barndoor](https://app.barndoor.ai) MCP servers to a
[CrewAI](https://crewai.com) agent:

- **`crew-cli.py`** — an interactive terminal app: pick a connected server, type a task, watch the agent run.
- **`crew-ui.py`** — the same flow as a [Streamlit](https://streamlit.io) web UI.

## Clone

```bash
git clone https://github.com/barndoor-ai/barndoor-ai-crew-ai-python-example.git
```

## Prerequisites

- **Python 3.13** (the project pins `>=3.13,<3.14`)
- [uv](https://docs.astral.sh/uv/)
- A Barndoor account with at least one connected MCP server
- An AI agent registered with Barndoor (for `AGENT_CLIENT_ID` / `AGENT_CLIENT_SECRET`)
- A Barndoor LLM gateway key (`LLM_API_KEY`, a `bd-…` key from app.barndoor.ai)

## What this app does

After authenticating (see [Authentication](#authentication) below), you're presented with the list
of MCP servers you're **connected** to in your Barndoor instance.

Select a connected server, then describe — in natural language — what you'd like the agent to do.
That kicks off the Crew execution: you'll see each step as the agent works, through to its final
output. CLI runs are also saved as Markdown under `reports/`.

## Authentication

The Streamlit UI opens on a landing page where you choose how to authenticate before anything runs:

| Mode | How it works | Identity |
|---|---|---|
| **Interactive login** | Opens the Barndoor login in your browser (OAuth). Tokens are cached in `~/.barndoor/token.json`. | Your **user** — sees the servers *you* connected. |
| **Machine-to-machine (M2M)** | OAuth client-credentials grant from your `.env` creds (`BarndoorSDK.from_client_credentials`). No browser. | The **application** client — sees only servers connected to *that client*. |

Use **Switch auth** (top-right) to change modes; it re-authenticates on the next load.

> **Note:** M2M authenticates as the application identity, not your user. If the M2M client has no
> servers connected to it in Barndoor, the list will be empty even though your user has connections —
> use Interactive login in that case. (The CLI, `crew-cli.py`, always uses interactive login.)

## LLM routing & model selection

All LLM traffic is routed through the **Barndoor LLM gateway** — an OpenAI-compatible endpoint —
instead of calling OpenAI directly. The gateway authenticates with your `LLM_API_KEY`, and the
endpoint is configurable:

```bash
# .env (optional — this is the default)
BARNDOOR_LLM_GATEWAY_URL=https://app.barndoor.ai/api/llm-gateway/v1
```

The model is selectable at runtime, and the choices come **from the gateway** (so they're always valid):

- **Streamlit UI** — a model dropdown populated from the gateway's `/models` (default `OpenAI/gpt-4o-mini`);
  you can also type any id the gateway accepts.
- **CLI** — lists the gateway's models and prompts for one (default `$OPENAI_MODEL_NAME`, else `OpenAI/gpt-4o-mini`).

A few user-curated Anthropic ids (`EXTRA_MODELS` in [`llm_gateway.py`](llm_gateway.py)) are also surfaced
in the menus alongside what `/models` returns; whether they actually route depends on the gateway's
provider config.

> Gateway model ids may be namespaced (e.g. `OpenAI/gpt-4o`). The app forwards the exact id to the
> gateway, working around CrewAI stripping litellm-style provider prefixes. Routing lives in
> [`llm_gateway.py`](llm_gateway.py).

## Theming (per-customer demos)

The Streamlit UI is themed via a single editable file: [`theme.py`](theme.py). Edit the `THEME`
dict and restart the app to rebrand for whoever you're demoing to. Tokens:

| Group | Keys |
|---|---|
| Branding | `company_name`, `title`, `subtitle`, `logo_url`, `logo_height_px` |
| Browser tab | `page_title`, `page_icon` |
| Colors | `primary_color`, `primary_color_text`, `background_color`, `secondary_background_color`, `text_color`, `muted_text_color`, `border_color` |
| Typography | `font_family` |

The logo renders top-right in the page header. `logo_url` accepts an `http(s)://` URL **or** a relative
path to a local file (e.g. `assets/acme.png`) — local files are base64-embedded so the browser can
display them. Leave it empty to hide the logo. Colors and font are applied via a CSS block injected
on every rerun; restart Streamlit after editing `theme.py` to see changes.

### Unsupported-model demo

The menus also include a few models the gateway **doesn't** serve (`OpenAI/gpt-5.4`, `OpenAI/gpt-5.4-mini`,
`OpenAI/gpt-5.4-nano`, defined as `DEMO_UNSUPPORTED_MODELS` in [`llm_gateway.py`](llm_gateway.py)). They're
there on purpose: selecting one and running a task shows the gateway rejecting it (HTTP 404, "model not
found"). The UI catches this and shows a clean message —
*"The Barndoor LLM gateway doesn't support model '…'. Pick a gateway-served model."* — rather than a raw
error. The rejection happens during the agent run, when the LLM call actually reaches the gateway.

## Setup

This is a [uv](https://docs.astral.sh/uv/) project — `pyproject.toml` and `uv.lock` define
everything (including `barndoor`, which is pinned to a git commit).

If you don't have uv: `brew install uv` (macOS), or see the
[install docs](https://docs.astral.sh/uv/getting-started/installation/).

Install the exact locked dependencies into `.venv`:

```bash
uv sync
```

Then create a `.env` file next to the scripts:

```bash
# Barndoor agent credentials (from https://app.barndoor.ai/agents)
AGENT_CLIENT_ID=XXX
AGENT_CLIENT_SECRET=XXX

# API key for the Barndoor LLM gateway (a `bd-…` key from app.barndoor.ai).
LLM_API_KEY=XXX

# Environment selector. "production" (default) = trial/Keycloak; the SDK bakes in
# the issuer (https://auth.barndoor.ai/realms/barndoor) and discovers endpoints via OIDC.
BARNDOOR_ENV=production

# Your tenant API base URL (the {org_slug} is otherwise derived from your login token).
BARNDOOR_URL=https://<your-org-slug>.platform.barndoor.ai
```

> The SDK (barndoor ≥ 1.x) auto-configures auth per environment — you do **not** set
> `AUTH_DOMAIN`/realm URLs by hand. Older SDK pins used Auth0 endpoints and 404 against
> the current Keycloak IdP, which is why this project pins a post-migration commit.

## Run

Interactive CLI:

```bash
uv run python crew-cli.py
```

Streamlit web UI:

```bash
uv run streamlit run crew-ui.py
```

## Tips

- To restart the Barndoor login flow (or switch accounts), delete `~/.barndoor/token.json`.

## Key dependencies

| Package | Version |
|---|---|
| crewai | 1.14.5 |
| crewai-tools | 1.14.5 |
| streamlit | 1.57.0 |
| barndoor | git-pinned |
