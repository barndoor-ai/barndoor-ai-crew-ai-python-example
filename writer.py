# writer_mcp_demo.py
from __future__ import annotations

import asyncio, json, os
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from writerai import Writer
import barndoor.sdk as bd
from barndoor.sdk.config import get_config

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

SERVER_SLUG = "notion"
MODEL = "palmyra-x5"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mcp_call",
            "description": f"Call a tool on the connected '{SERVER_SLUG}' MCP server via Barndoor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "MCP tool name (e.g., 'query', 'list_pages', 'get_page')"},
                    "args": {"type": "object", "description": "Arguments for the MCP tool"},
                },
                "required": ["tool", "args"],
                "additionalProperties": False,
            },
        },
    }
]

@asynccontextmanager
async def open_mcp_session(sdk: Any, server_slug: str) -> ClientSession:
    # Make sure we’re connected, then ask Barndoor for the *exact* URL+headers to use.
    await sdk.ensure_server_connected(server_slug)
    params, _public_url = await bd.make_mcp_connection_params(sdk, server_slug)

    mcp_url = params["url"]            # e.g. https://.../mcp/notion
    headers = params.get("headers", {})  # includes Authorization + x-barndoor-session-id

    async with sse_client(url=mcp_url, headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            yield session

async def call_writer_with_mcp(
    user_prompt: str,
    *,
    server_slug: str = SERVER_SLUG,
    model: str = MODEL,
    system_prompt: Optional[str] = None,
) -> str:
    load_dotenv(Path(__file__).parent / ".env")

    # Barndoor login
    sdk = await bd.login_interactive()
    try:
        cfg = get_config()
        print(f"API Base URL: {cfg.api_base_url}")
        print(f"MCP Base URL: {cfg.mcp_base_url}")

        # Open MCP session using the Barndoor-provided url+headers
        async with open_mcp_session(sdk, server_slug) as mcp:
            await mcp.initialize()
            tools_list = await mcp.list_tools()
            print("Discovered MCP tools:", [t.name for t in tools_list.tools])

            async def run_mcp_call(tool: str, args: Dict[str, Any]) -> str:
                result = await mcp.call_tool(name=tool, arguments=args)
                parts = [c.text for c in (result.content or []) if getattr(c, "type", None) == "text"]
                return "\n".join(parts) if parts else json.dumps(
                    [c.model_dump() for c in (result.content or [])], indent=2
                )

            # Writer orchestrates tool use
            client = Writer()
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                    or "You are a Notion Workspace Assistant. Prefer using `mcp_call` and then summarize.",
                },
                {"role": "user", "content": user_prompt},
            ]

            first = client.chat.chat(model=model, messages=messages, tools=TOOLS, tool_choice="auto")
            assistant_msg = first.choices[0].message
            messages.append(assistant_msg)

            # Bridge tool calls to MCP
            if getattr(assistant_msg, "tool_calls", None):
                for tc in assistant_msg.tool_calls:
                    fn = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    if fn == "mcp_call":
                        result = await run_mcp_call(args.get("tool"), args.get("args", {}) or {})
                    else:
                        result = f"[error] unknown function '{fn}'"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": fn,
                        "content": result,
                    })

                final = client.chat.chat(model=model, messages=messages)
                return final.choices[0].message.content or ""
            else:
                return assistant_msg.content or ""
    finally:
        await sdk.aclose()

async def _demo() -> None:
    out = await call_writer_with_mcp(
        "List ten Notion pages and summarize each in 1–2 sentences.",
        server_slug=SERVER_SLUG,
        model=MODEL,
    )
    print("\n✓ Result:\n")
    print(out)

if __name__ == "__main__":
    asyncio.run(_demo())
