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
- An OpenAI API key (CrewAI's default LLM)

## What this app does

The first time you run the app, a browser window opens to the Barndoor login screen. Once
authenticated, it stores OAuth access and refresh tokens in `~/.barndoor/token.json`. You're then
presented with the list of MCP servers you're **connected** to in your Barndoor instance.

Select a connected server, then describe — in natural language — what you'd like the agent to do.
That kicks off the Crew execution: you'll see each step as the agent works, through to its final
output. CLI runs are also saved as Markdown under `reports/`.

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

# OpenAI key for CrewAI's LLM (https://platform.openai.com/api-keys)
OPENAI_API_KEY=XXX

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
