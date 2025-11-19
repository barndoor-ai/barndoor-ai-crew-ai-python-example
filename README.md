## Clone Repo

```bash
git clone https://github.com/barndoor-ai/crew-ai-python-example.git
```

## Prerequisites
- Python 3.10+
- A Barndoor account
- An MCP server registered with Barndoor (connected/authenticated)
- AI agent registered with Barndoor

## What this app does
The first time you run the app, a browser window will open to the Barndoor login screen. Once authenticated, it will store OAuth access and refresh tokens into a file `~/.barndoor/token.json`. Once logged in, you'll be presented with a list of usable MCP servers registered in your Barndoor instance.

Select one of the MCP servers that you're `[Connected]` to. You'll then be prompted with what 
you'd like the agent to do. Provide a natural language query of what task you'd like the agent to 
perform. 

This will initate the Crew execution. You'll see each step of the Crew job being performed, all
the way through the end where the agent presents it's final output to the task. Additionally, the
Crew task output is saved in the `./reports/` folder.

## Setting up the app

For the fastest setup and install, we recommend using [uv](https://github.com/astral-sh/uv) instead of pip. We also recommend creating a virtual environment to isolate installed packages from your computer's Python environment.

### 1. Install uv (one time)

- On MacOS using brew: `brew install uv`
- For other methods and operating systems, see uv [installation methods](https://docs.astral.sh/uv/getting-started/installation/)


### 2. Create an isolated virtual environment in the repo
```bash
uv venv .venv
source .venv/bin/activate
```

### 3. Install required packages
Packages include the Barndoor SDK, CrewAI SDK, and other tools.
```bash
uv pip install -r requirements.txt 
```

### 4. Create an `.env` configuration file

```bash
# Replace with your agent's client ID and secret from Barndoor
# See: https://app.barndoor.ai/agents
AGENT_CLIENT_ID={{barndoor-agent-client-id}}
AGENT_CLIENT_SECRET={{barndoor-agent-client-secret}}

# Replace with your tenant hostname
BARNDOOR_API=https://{{your-tenant}}.mcp.barndoor.ai
BARNDOOR_URL=https://{{your-tenant}}.mcp.barndoor.ai

# Valid OpenAI API Key
# see: https://platform.openai.com/api-keys
OPENAI_API_KEY={{your-openapi-key}}}

# Default values, no changes required
AUTH_DOMAIN=auth.barndoor.ai
API_AUDIENCE=https://barndoor.ai/
MODE=production
```

## Running the app
There are actually two apps. One that runs in the terminal, and another
that can be run in the browser.

The CLI version: `uv run crew-cli.py`

The browser-based UI version: `uv run streamlit run crew-ui.py`

## Tips

- To reinitiate the Barndoor login flow, or login to a different account remove the `~/.barndoor/token.json` file.

