import os
import re
import streamlit as st
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from barndoor_usage import fetch_usage
import barndoor.sdk as bd
from barndoor.sdk import BarndoorSDK
from barndoor.sdk.config import get_static_config
import asyncio
from crewai import Agent, Task, Crew
from crewai_tools import MCPServerAdapter
from openai_tool_schema_patch import patch_crewai_tool_schemas
from barndoor_compat import fetch_all_servers
from llm_gateway import (
    make_llm,
    list_gateway_models,
    DEFAULT_MODEL,
    DEMO_UNSUPPORTED_MODELS,
    EXTRA_MODELS,
)
from theme import apply_theme, page_config_kwargs

# MCP tool schemas can omit array `items` types; backfill them so OpenAI accepts the tools.
patch_crewai_tool_schemas()

AUTH_MODES = {
    "interactive": "Interactive login (browser)",
    "m2m": "Machine-to-machine (M2M client credentials)",
}


@st.cache_data(ttl=300)
def model_options() -> list[str]:
    """Gateway models + curated extras + unsupported demo ids, deduped & order-preserving."""
    try:
        models = list_gateway_models()
    except Exception:
        models = []
    models = models or [DEFAULT_MODEL]
    seen = set(models)
    out = list(models)
    for m in (*EXTRA_MODELS, *DEMO_UNSUPPORTED_MODELS):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


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


async def get_session_jwt(auth_mode: str) -> str:
    """Authenticate and return the SDK session JWT (used as Bearer for Barndoor APIs)."""
    sdk = await make_sdk(auth_mode)
    try:
        return sdk.token
    finally:
        await sdk.aclose()


# Strip embedded images from agent output: both markdown ![alt](url) and any <img> HTML.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img[^>]*/?>", re.IGNORECASE)


def _strip_images(text: str) -> str:
    return _IMAGE_RE.sub("", text)


# ─────────────────────────────────────────────
# Core async function (DO NOT use asyncio.run!)
# ─────────────────────────────────────────────
async def run_crewai_task(server_slug: str, user_query: str, log, auth_mode: str, model: str):
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

            log(f"Model: **{model}** (via Barndoor LLM gateway)")
            agent = Agent(
                role=f"{display_name} Expert",
                goal=f"Complete any task in the user's {display_name} account using real data.",
                backstory=f"You are a master of {display_name} with full access via Barndoor MCP.",
                tools=tools,
                llm=make_llm(model),
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
        return _strip_images(str(result)), display_name

    except Exception as e:
        detail = str(e).lower()
        if "not found" in detail or "not available" in detail:
            error_msg = (
                f"Error: The Barndoor LLM gateway doesn't support model '{model}'. "
                f"Pick a gateway-served model. (gateway: {type(e).__name__}: {e})"
            )
        else:
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
# Page Config + theme
# ─────────────────────────────────────────────
st.set_page_config(**page_config_kwargs())
apply_theme()


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

# Attachment helpers --------------------------------------------------------
_TEXT_EXT = {
    ".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml", ".toml", ".ini",
    ".html", ".xml", ".sql", ".py", ".js", ".ts", ".sh",
}
_TEXT_CHAR_CAP = 50_000


def _is_text_attachment(name: str, mime: str | None) -> bool:
    if (mime or "").startswith("text/"):
        return True
    return any(name.lower().endswith(ext) for ext in _TEXT_EXT)


def _augment_query_with_files(text: str, files: list) -> str:
    """Inline text-file content and reference binaries by name so the agent sees them."""
    if not files:
        return text
    parts = [text, "\n\n## Attached files"]
    for f in files:
        parts.append(f"\n### {f.name}  ({f.type or 'unknown'}, {f.size:,} bytes)")
        try:
            data = f.read()
        except Exception as e:
            parts.append(f"\n(could not read: {e})")
            continue
        if _is_text_attachment(f.name, f.type):
            body = data.decode("utf-8", errors="replace")
            if len(body) > _TEXT_CHAR_CAP:
                body = body[:_TEXT_CHAR_CAP] + f"\n…[truncated; original {len(body):,} chars]"
            parts.append(f"\n```\n{body}\n```")
        else:
            parts.append("\n_(binary file — referenced by name; not inlined in this demo)_")
    return "".join(parts)


# Chat history (persists across submissions in this session) ---------------
if "messages" not in st.session_state:
    st.session_state.messages = []


def _render_user_msg(msg: dict) -> None:
    with st.chat_message("user"):
        if msg.get("text"):
            st.markdown(msg["text"])
        if msg.get("files"):
            st.caption("📎 " + " · ".join(msg["files"]))


def _render_assistant_msg(msg: dict) -> None:
    with st.chat_message("assistant"):
        if msg.get("is_error"):
            st.error(msg["text"])
        else:
            st.markdown(msg["text"])
        st.caption(
            f"App: **{msg['app']}** · Model: **{msg['model']}** · {msg['ts']}"
        )
        if msg.get("log_html"):
            with st.expander("Run log"):
                st.markdown(msg["log_html"], unsafe_allow_html=True)


# Replay prior turns
for prior in st.session_state.messages:
    if prior["role"] == "user":
        _render_user_msg(prior)
    else:
        _render_assistant_msg(prior)

# "New chat" reset, only visible when there's something to clear
if st.session_state.messages:
    _, reset_col = st.columns([5, 1])
    if reset_col.button("New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Compact connection settings: expanded on first load, collapsed once a thread starts
with st.expander("App & model", expanded=not st.session_state.messages):
    server_choice = st.selectbox("Choose your app:", options=list(servers.keys()))
    selected_slug = servers[server_choice]

    _models = model_options()
    model = st.selectbox(
        "Model (via Barndoor LLM gateway):",
        options=_models,
        index=_models.index(DEFAULT_MODEL) if DEFAULT_MODEL in _models else 0,
        accept_new_options=True,
        help="Models served by the Barndoor LLM gateway. You can also type any other id it accepts.",
    )

st.caption(f"Asking **{server_choice}** with **{model}**")


# API key usage (calls https://app.barndoor.ai/api/llm-usage/query) ---------
with st.expander("API key usage", expanded=False):
    usage_key_id = os.getenv("BARNDOOR_API_KEY", "")
    if usage_key_id:
        st.caption(f"Querying API key: `{usage_key_id}`")
    else:
        st.warning("Set `BARNDOOR_API_KEY` in `.env` to enable usage queries.")

    today = datetime.now(timezone.utc).date()
    date_cols = st.columns(2)
    usage_from = date_cols[0].date_input("From", value=today - timedelta(days=30))
    usage_to = date_cols[1].date_input("To", value=today)
    usage_limit = st.number_input(
        "Limit", min_value=1, max_value=1000, value=100, step=10
    )

    if st.button("Fetch usage", disabled=not usage_key_id):
        if not usage_key_id:
            st.warning("Missing BARNDOOR_API_KEY.")
        else:
            from_iso = (
                datetime.combine(usage_from, datetime.min.time(), tzinfo=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            to_iso = (
                datetime.combine(usage_to, datetime.min.time(), tzinfo=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            try:
                with st.spinner("Querying usage…"):
                    jwt = asyncio.run(get_session_jwt(auth_mode))
                    usage = fetch_usage(
                        usage_key_id,
                        from_iso,
                        to_iso,
                        limit=int(usage_limit),
                        bearer=jwt,
                    )
                records = usage.get("data") if isinstance(usage, dict) else usage
                if isinstance(records, list):
                    st.caption(f"{len(records)} record(s)")
                    if records:
                        st.dataframe(records, use_container_width=True)
                    else:
                        st.info("No usage records in that range.")
                else:
                    st.write(usage)
                with st.expander("Raw response"):
                    st.json(usage)
            except Exception as e:
                st.error(f"Usage fetch failed: {type(e).__name__}: {e}")


# Inline prompt form (text + multi-file uploader + Run button) -------------
with st.form("prompt_form", clear_on_submit=True):
    prompt_text = st.text_area(
        "What do you want to do?",
        placeholder=(
            "Examples:\n"
            "• List my recent Salesforce opportunities\n"
            "• Summarize Notion pages tagged 'Q4'\n"
            "• Show unread Gmail from last 3 days"
        ),
        height=140,
    )
    uploaded = st.file_uploader(
        "Attach files (optional)",
        accept_multiple_files=True,
    )
    submitted = st.form_submit_button(
        "Run Agent", type="primary", use_container_width=True
    )

if submitted:
    prompt_text = (prompt_text or "").strip()
    uploaded = uploaded or []
    if not prompt_text and not uploaded:
        st.warning("Please enter a task or attach a file.")
        st.stop()

    file_names = [f.name for f in uploaded]
    full_query = _augment_query_with_files(prompt_text, uploaded)

    log_lines = []

    def log(m):
        ts = datetime.now().strftime("%H:%M:%S")
        log_lines.append(f"<small>{ts}</small> {m}")

    if uploaded:
        log(f"Attached: {', '.join(file_names)}")

    with st.spinner("Working..."):
        result, app_name = asyncio.run(
            run_crewai_task(selected_slug, full_query, log, auth_mode, model)
        )

    is_error = result.startswith("Error:")
    ts_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    log_html = "\n".join(log_lines)

    st.session_state.messages.append(
        {"role": "user", "text": prompt_text, "files": file_names}
    )
    st.session_state.messages.append({
        "role": "assistant",
        "text": result,
        "app": app_name,
        "model": model,
        "ts": ts_str,
        "log_html": log_html,
        "is_error": is_error,
    })
    st.rerun()
