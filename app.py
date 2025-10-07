from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

import barndoor.sdk as bd
from barndoor.sdk.config import get_config
from crewai import Agent, Task, Crew
from crewai_tools import MCPServerAdapter

SERVER_SLUG = "notion"


async def main() -> None:
    # 1️⃣ Load environment
    load_dotenv(Path(__file__).parent / ".env")

    # 2️⃣ Authenticate with Barndoor (public SDK handles PKCE flow + token caching)
    sdk = await bd.login_interactive()

    config = get_config()

    print(f"API Base URL: {config.api_base_url}")
    print(f"MCP Base URL: {config.mcp_base_url}")
    print(f"Authenticated as: {sdk.token}")

    # 3️⃣ List available MCP servers
    servers = await sdk.list_servers()
    print("\nAvailable MCP servers:")
    for s in servers:
        print(f"  • {s.slug:<12} status={s.connection_status}")

    # 4️⃣ Ensure the selected server is connected
    await bd.ensure_server_connected(sdk, SERVER_SLUG)

    # 5️⃣ Build MCP connection parameters
    params, public_url = await bd.make_mcp_connection_params(sdk, SERVER_SLUG)
    print(f"\n✓ Connected MCP URL: {params['url']}")

    # 6️⃣ Use MCP adapter with CrewAI
    with MCPServerAdapter(params) as mcp_tools:
        agent = Agent(
            role="Notion Assistant",
            goal="Query and summarize Notion workspace pages.",
            backstory="Uses the Barndoor SDK public MCP connection.",
            tools=mcp_tools,
            verbose=True,
        )

        task = Task(
            description="List 5 Notion pages and summarize each one.",
            expected_output="A short list of page names and summaries.",
            agent=agent,
        )

        crew = Crew(agents=[agent], tasks=[task], verbose=True)

        print("\n🚀 Running CrewAI task...\n")
        result = await crew.kickoff_async()
        print(f"✅ CrewAI finished:\n\n{result}")

    # 7️⃣ Save a simple Markdown report
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"notion_summary_{ts}.md"
    report_path.write_text(f"# Notion Summary Report\n\n{result}", encoding="utf-8")
    print(f"\n📝 Report saved to {report_path.resolve()}")

    await sdk.aclose()


if __name__ == "__main__":
    asyncio.run(main())
