from __future__ import annotations

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import barndoor.sdk as bd
from barndoor.sdk.config import get_config
from crewai import Agent, Task, Crew
from crewai_tools import MCPServerAdapter

SERVER_SLUG = "notion"

async def main() -> None:
    try:
        # Load .env
        load_dotenv(Path(__file__).parent / ".env")

        # Authenticate with Barndoor
        sdk = await bd.login_interactive()
        config = get_config()

        print(f"API Base URL: {config.api_base_url}")
        print(f"MCP Base URL: {config.mcp_base_url}")

        # List available servers
        servers = await sdk.list_servers()
        print("\nAvailable MCP servers:")
        for s in servers:
            print(f"  • {s.slug:<12} status={s.connection_status}")

        # Ensure connection
        await bd.ensure_server_connected(sdk, SERVER_SLUG)

        # Fetch connection params
        params, public_url = await bd.make_mcp_connection_params(sdk, SERVER_SLUG)

        # Explicitly override the URL using known BARNDOOR_URL
        override_base_url = os.getenv("BARNDOOR_URL")
        if not override_base_url:
            raise ValueError("❌ BARNDOOR_URL not found in .env")

        # Reconstruct URL with correct hostname and token
        token = params["url"].split("?token=")[-1]
        fixed_url = f"{override_base_url}/mcp/{SERVER_SLUG}?token={token}"

        params["url"] = fixed_url
        public_url = fixed_url

        print(f"✓ Ready – MCP URL: {params['url']}")

        # Run the CrewAI task
        with MCPServerAdapter(params) as mcp_tools:
            researcher = Agent(
                role="Notion Workspace Assistant",
                goal="Help users query and update their Notion pages & databases",
                backstory="Sample agent using Barndoor MCP integration with Notion.",
                tools=mcp_tools,
                verbose=True
            )

            task = Task(
                description="List ten notion pages and summarize their content.",
                expected_output="A list of notion pages and short description",
                agent=researcher
            )

            crew = Crew(
            agents=[researcher],
            tasks=[task],
            verbose=True  # ✅ VALID
        )


            print("\n🚀 Running CrewAI with MCP tools…")
            result = await crew.kickoff_async()
            print(f"\n✓ Result: {result}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await sdk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
