## Clone Repo

```bash
git clone https://github.com/barndoor-ai/crew-ai-python-example.git
```

## Prerequisites
- Python 3.10+
- A Barndoor account
- At least one connected MCP server
- .env file placed next to this script (if needed for extra config)

        ```bash
        AUTH_DOMAIN=auth.barndoor.ai
        AGENT_CLIENT_ID=XXX
        AGENT_CLIENT_SECRET=XX
        OPENAI_API_KEY=XXX
        audience=https://barndoor.AI
        BARNDOOR_API=https://{{tenant}}.mcp.barndoor.ai

        BARNDOOR_URL=https://{{tenant}}.mcp.barndoor.ai 
        API_AUDIENCE=https://barndoor.ai/
        MODE=production
        ```

### Setup Using UV (Recommended)
- uv pip install -r requirements.txt 
- uv pip install barndoor-sdk crewai crewai-tools[mcp] python-dotenv streamlit


## Running Crew CLI.py

- uv streamlit run crew-cli.py

## Simple Crew UI demo app

- uv streamlit run crew-ui.py

