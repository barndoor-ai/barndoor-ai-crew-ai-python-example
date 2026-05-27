from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import barndoor.sdk as bd
from barndoor.sdk.config import get_config
from crewai import Agent, Task, Crew
from crewai_tools import MCPServerAdapter
from openai_tool_schema_patch import patch_crewai_tool_schemas
from barndoor_compat import fetch_all_servers
from llm_gateway import make_llm, list_gateway_models, DEFAULT_MODEL, DEMO_UNSUPPORTED_MODELS

# MCP tool schemas can omit array `items` types; backfill them so OpenAI accepts the tools.
patch_crewai_tool_schemas()


async def select_server(sdk: bd.BarndoorSDK) -> tuple[str, str]:
    servers = await fetch_all_servers(sdk)

    # Only "connected" servers are usable; "available"/"pending" are catalog apps.
    usable = [s for s in servers if s.connection_status == "connected"]

    if not usable:
        print("No connected MCP servers found.")
        print("Connect an app at https://app.barndoor.ai/servers")
        raise SystemExit(1)

    print("\nUsable MCP Servers")
    print("=" * 90)
    for i, s in enumerate(usable, start=1):
        status = "Connected" if s.connection_status == "connected" else "Available"
        name = s.name or s.mcp_server_directory.name or s.slug.replace("-", " ").title()
        print(f"  {i:<3}) {s.slug:<22} [{status}] → {name}")
    print("=" * 90)

    while True:
        try:
            choice = input(f"\nChoose (1-{len(usable)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(usable):
                selected = usable[idx]
                display_name = (
                    selected.name
                    or selected.mcp_server_directory.name
                    or selected.slug.replace("-", " ").title()
                )
                print(f"\nSelected: {selected.slug} → {display_name} [{selected.connection_status}]")
                return selected.slug, display_name
        except ValueError:
            print("Please enter a number")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            raise SystemExit(0)


async def main() -> None:
    load_dotenv(Path(__file__).parent / ".env")

    print("Logging in to Barndoor...")
    sdk = await bd.login_interactive()

    config = get_config()
    print(f"API URL : {config.api_base_url}")
    print(f"MCP URL : {config.mcp_base_url}\n")

    server_slug, server_name = await select_server(sdk)

    await bd.ensure_server_connected(sdk, server_slug)
    params, public_url = await bd.make_mcp_connection_params(sdk, server_slug)

    # ──────────────────────────────────────────────────────────────
    # CRITICAL FIX – Barndoor now returns either "token" OR "authorization"
    # ──────────────────────────────────────────────────────────────
    if "token" in params and "authorization" not in params:
        # Old style → convert
        params["authorization"] = f"Bearer {params.pop('token')}"
    elif "authorization" in params and not params["authorization"].startswith("Bearer "):
        # Sometimes it's just the raw token
        params["authorization"] = f"Bearer {params['authorization']}"

    # Safe printing
    auth_header = params.get("authorization", "(missing)")
    print(f"\nMCP Server URL : {params['url']}")
    print(f"Transport      : {params.get('transport', 'unknown')}")
    print(f"Public URL     : {public_url}")
    print(f"Authorization  : {auth_header}\n")
    print ("Token: " + sdk.token + "\n")

    print(f"Connected to: {server_name}")
    print("\nWhat do you want the agent to do?")
    user_task = input("\n> ").strip()
    if not user_task:
        print("Task cannot be empty!")
        raise SystemExit(1)

    # Pick the model served by the Barndoor LLM gateway.
    default_model = os.getenv("OPENAI_MODEL_NAME", DEFAULT_MODEL)
    try:
        gateway_models = list_gateway_models()
    except Exception as e:
        print(f"\n(Could not list gateway models: {e})")
        gateway_models = []
    if gateway_models:
        print("\nModels via the Barndoor LLM gateway:")
        for m in gateway_models:
            print(f"  - {m}")
    # Unsupported models the gateway will reject (404) — included to demo that path.
    print("Not served by the gateway (will fail if chosen):")
    for m in DEMO_UNSUPPORTED_MODELS:
        print(f"  - {m}")
    model = input(f"\nModel [{default_model}]: ").strip() or default_model

    # ──────────────────────────────────────────────────────────────
    # Run CrewAI with the MCP tools
    # ──────────────────────────────────────────────────────────────gen
    with MCPServerAdapter(params) as mcp_tools:
        print(f"\nLoaded {len(mcp_tools)} tools from {server_name}\n")

        agent = Agent(
            role=f"{server_name} Assistant",
            goal=f"Help the user with anything in their {server_name} account using real MCP tools.",
            backstory="You are an expert user of this app with full read/write access via Barndoor MCP.",
            tools=mcp_tools,
            llm=make_llm(model),
            verbose=True,
            allow_delegation=False,
        )

        task = Task(
            description=user_task,
            expected_output="Clear, helpful, well-formatted response. Use markdown tables/lists when appropriate.",
            agent=agent,
        )

        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        print("Running task...\n")
        result = await crew.kickoff_async()

        print("\nTask Complete!\n")
        print(result)

        # Save report
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in server_name)
        report_path = reports_dir / f"{safe_name}_{timestamp}.md"

        header = f"# {server_name} Report\n\n"
        header += f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        header += f"Task: {user_task}\n\n---\n\n"

        report_path.write_text(header + str(result), encoding="utf-8")
        print(f"\nReport saved → {report_path.resolve()}")

    await sdk.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        raise