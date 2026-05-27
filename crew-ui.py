import streamlit as st
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import barndoor.sdk as bd
from barndoor.sdk import BarndoorSDK
from barndoor.sdk.config import get_static_config
import asyncio
from crewai import Agent, Task, Crew
from crewai_tools import MCPServerAdapter
from openai_tool_schema_patch import patch_crewai_tool_schemas
from barndoor_compat import fetch_all_servers

# MCP tool schemas can omit array `items` types; backfill them so OpenAI accepts the tools.
patch_crewai_tool_schemas()

AUTH_MODES = {
    "interactive": "Interactive login (browser)",
    "m2m": "Machine-to-machine (M2M client credentials)",
}


# ─────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────
async def make_sdk(auth_mode: str) -> BarndoorSDK:
    """Create an authenticated SDK using the chosen auth mode.

    - "interactive": browser OAuth (opens the Barndoor login).
    - "m2m": OAuth client-credentials grant from .env creds (no browser).
    """
    load_dotenv(Path(__file__).parent / ".env")

    if auth_mode == "m2m":
        cfg = get_static_config()
        missing = [
            name
            for name, value in (
                ("AGENT_CLIENT_ID", cfg.client_id),
                ("AGENT_CLIENT_SECRET", cfg.client_secret),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"M2M auth needs {' and '.join(missing)} set in .env")
        return await BarndoorSDK.from_client_credentials(
            cfg.base_url,
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            audience=cfg.api_audience,
            issuer=cfg.auth_issuer,
        )

    return await bd.login_interactive()


# ─────────────────────────────────────────────
# Core async function (DO NOT use asyncio.run!)
# ─────────────────────────────────────────────
async def run_crewai_task(server_slug: str, user_query: str, log, auth_mode: str):
    sdk = None

    try:
        log(f"Authenticating ({AUTH_MODES[auth_mode]})...")
        sdk = await make_sdk(auth_mode)
        log("Authenticated!")

        servers = await fetch_all_servers(sdk)
        server = next((s for s in servers if s.slug == server_slug), None)
        if not server:
            raise ValueError(f"Server '{server_slug}' not found.")

        display_name = (
            server.name
            or getattr(server.mcp_server_directory, "name", None)
            or server_slug.replace("-", " ").title()
        )
        log(f"Using: **{display_name}**")

        await bd.ensure_server_connected(sdk, server_slug)
        params, public_url = await bd.make_mcp_connection_params(sdk, server_slug)

        # Fix token → authorization (handles both formats)
        if "token" in params:
            params["authorization"] = f"Bearer {params.pop('token')}"
        elif "authorization" in params and not params["authorization"].startswith("Bearer "):
            params["authorization"] = f"Bearer {params['authorization']}"

        log("Connected! Loading tools...")

        with MCPServerAdapter(params) as tools:
            log(f"Loaded **{len(tools)} tools**")

            agent = Agent(
                role=f"{display_name} Expert",
                goal=f"Complete any task in the user's {display_name} account using real data.",
                backstory=f"You are a master of {display_name} with full access via Barndoor MCP.",
                tools=tools,
                verbose=True,
                allow_delegation=False,
            )

            task = Task(
                description=user_query,
                expected_output="Clear, accurate, well-formatted answer. Use tables/lists when helpful.",
                agent=agent,
            )

            crew = Crew(agents=[agent], tasks=[task], verbose=True)
            log("Running task...")
            result = await crew.kickoff_async()

        log("Done!")
        return str(result), display_name

    except Exception as e:
        error_msg = f"Error: {type(e).__name__}: {e}"
        log(error_msg)
        return error_msg, "Error"
    finally:
        if sdk:
            await sdk.aclose()


# ─────────────────────────────────────────────
# Load servers once per auth mode
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)  # Refresh every 5 minutes
def load_servers(auth_mode: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        sdk = loop.run_until_complete(make_sdk(auth_mode))
        servers = loop.run_until_complete(fetch_all_servers(sdk))
        loop.run_until_complete(sdk.aclose())

        options = {}
        for s in servers:
            # "available"/"pending" are catalog/not-yet-usable apps; only "connected" is ready.
            if s.connection_status == "connected":
                name = (
                    s.name
                    or getattr(s.mcp_server_directory, "name", None)
                    or s.slug.replace("-", " ").title()
                )
                options[f"{name} • {s.slug}"] = s.slug
        return options or {"No servers found": None}
    finally:
        loop.close()


# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Barndoor + CrewAI Assistant", layout="centered", page_icon="Robot")
st.title("Barndoor MCP + CrewAI Universal Assistant")
st.markdown("Connect any app — Notion, Salesforce, Gmail, Slack, GitHub, Box — and get real results.")


# ─────────────────────────────────────────────
# Landing page: choose auth mode before anything runs
# ─────────────────────────────────────────────
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = None

if st.session_state.auth_mode is None:
    st.subheader("How do you want to authenticate?")
    choice = st.radio(
        "Authentication method",
        options=list(AUTH_MODES),
        format_func=lambda m: AUTH_MODES[m],
        captions=[
            "Opens a Barndoor login in your browser via OAuth.",
            "Uses AGENT_CLIENT_ID / AGENT_CLIENT_SECRET from .env — no browser.",
        ],
        label_visibility="collapsed",
    )
    if st.button("Continue", type="primary"):
        st.session_state.auth_mode = choice
        st.rerun()
    st.stop()

auth_mode = st.session_state.auth_mode
top_left, top_right = st.columns([3, 1])
top_left.caption(f"Authenticated via: **{AUTH_MODES[auth_mode]}**")
if top_right.button("Switch auth"):
    st.session_state.auth_mode = None
    load_servers.clear()  # re-authenticate on next load
    st.rerun()


# ─────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────
servers = load_servers(auth_mode)

if not servers or list(servers.values())[0] is None:
    if auth_mode == "m2m":
        st.error(
            "No connected MCP servers for this M2M client. Client-credentials auth uses the "
            "**application** identity (not your user), so it only sees servers connected to that "
            "client in Barndoor. Connect servers to this client, or use **Switch auth → Interactive login**."
        )
    else:
        st.error("No connected MCP servers found. Go to https://app.barndoor.ai and connect an app.")
    st.stop()

server_choice = st.selectbox("Choose your app:", options=list(servers.keys()))
selected_slug = servers[server_choice]

query = st.text_area(
    "What do you want to do?",
    placeholder="Examples:\n• List my recent Salesforce opportunities\n• Summarize Notion pages tagged 'Q4'\n• Show unread Gmail from last 3 days",
    height=140,
)

if st.button("Run Agent", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Please enter a task.")
        st.stop()

    log_placeholder = st.empty()
    log_lines = []

    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        log_lines.append(f"<small>{ts}</small> {msg}")
        log_placeholder.markdown("\n".join(log_lines), unsafe_allow_html=True)

    with st.spinner("Working..."):
        # This is the CORRECT way in Streamlit
        result, app_name = asyncio.run(run_crewai_task(selected_slug, query, log, auth_mode))

    st.markdown("---")
    st.subheader(f"Result from {app_name}")

    if result.startswith("Error:"):
        st.error(result)
    else:
        st.markdown(result)

    st.caption(f"Completed • {datetime.now():%Y-%m-%d %I:%M %p}")
