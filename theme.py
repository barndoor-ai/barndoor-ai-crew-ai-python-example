"""Per-customer theme for the Streamlit demo.

Edit the ``THEME`` dict to rebrand the app for whoever you're demoing to. Values are
read into ``st.set_page_config`` and injected as CSS at the top of the page, plus they
drive a custom header (title left, logo right). Changes take effect on next ``streamlit run``.

``logo_url`` can be an ``http(s)://`` URL or a relative path to a local file
(e.g. ``"assets/acme-logo.png"``) — local files are embedded as base64 so the browser
can render them.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import streamlit as st

THEME: dict = {
    # ── Header / branding ────────────────────────────────────────
    "company_name": "Barndoor",
    "title": "Knowledge Worker Assistant",
    "subtitle": (
        "Connect any app — Notion, Salesforce, Gmail, Slack, GitHub, Box — "
        "and get real results."
    ),
    # URL (https) or relative file path under the repo. Empty string hides the logo.
    "logo_url": "data:image/png;base64,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",
    "logo_height_px": 44,
    # ── Browser tab ─────────────────────────────────────────────
    "page_title": "Barndoor + CrewAI Assistant",
    "page_icon": "🤖",
    # ── Colors ──────────────────────────────────────────────────
    "primary_color": "#2563EB",
    "primary_color_text": "#FFFFFF",
    "background_color": "#FFFFFF",
    "secondary_background_color": "#F8FAFC",
    "text_color": "#0F172A",
    "muted_text_color": "#64748B",
    "border_color": "#E2E8F0",
    # ── Typography ──────────────────────────────────────────────
    "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
}


def page_config_kwargs() -> dict:
    """Kwargs to pass into ``st.set_page_config`` (must be the first Streamlit call)."""
    return {
        "page_title": THEME["page_title"],
        "page_icon": THEME["page_icon"],
        "layout": "centered",
    }


def _logo_src(logo: str) -> str:
    """Return a usable ``src`` for an <img>: pass HTTPS URLs through, base64-embed local files."""
    if not logo:
        return ""
    if logo.startswith(("http://", "https://", "data:")):
        return logo
    path = Path(logo)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    if not path.exists():
        return ""
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def apply_theme() -> None:
    """Inject the theme CSS and render the custom branded header."""
    t = THEME
    logo_src = _logo_src(t["logo_url"])
    logo_html = (
        f'<img src="{logo_src}" alt="{t["company_name"]} logo" class="demo-logo" />'
        if logo_src
        else ""
    )

    st.markdown(
        f"""
        <style>
          :root {{
            --primary: {t["primary_color"]};
            --primary-text: {t["primary_color_text"]};
            --bg: {t["background_color"]};
            --bg-secondary: {t["secondary_background_color"]};
            --text: {t["text_color"]};
            --text-muted: {t["muted_text_color"]};
            --border: {t["border_color"]};
          }}
          html, body, .stApp {{
            background-color: var(--bg) !important;
            color: var(--text) !important;
            font-family: {t["font_family"]};
          }}
          .stApp [data-testid="stSidebar"] {{
            background-color: var(--bg-secondary) !important;
          }}
          .stApp [data-testid="stMarkdownContainer"] p,
          .stApp [data-testid="stMarkdownContainer"] li,
          .stApp [data-testid="stMarkdownContainer"] strong,
          .stApp [data-testid="stMarkdownContainer"] em,
          .stApp [data-testid="stMarkdownContainer"] code,
          .stApp label, .stApp h1, .stApp h2, .stApp h3 {{
            color: var(--text);
          }}
          .stApp [data-testid="stCaptionContainer"],
          .stApp small {{
            color: var(--text-muted);
          }}

          /* Markdown tables — agent often returns tabular results */
          .stApp [data-testid="stMarkdownContainer"] table,
          .stApp [data-testid="stMarkdownContainer"] thead,
          .stApp [data-testid="stMarkdownContainer"] tbody,
          .stApp [data-testid="stMarkdownContainer"] tr,
          .stApp [data-testid="stMarkdownContainer"] th,
          .stApp [data-testid="stMarkdownContainer"] td {{
            color: var(--text) !important;
            border-color: var(--border) !important;
          }}
          .stApp [data-testid="stMarkdownContainer"] th {{
            background-color: var(--bg-secondary) !important;
            font-weight: 600;
          }}
          .stApp [data-testid="stMarkdownContainer"] tr:nth-child(even) td {{
            background-color: var(--bg-secondary) !important;
          }}
          .stButton > button,
          .stFormSubmitButton > button,
          [data-testid="stFormSubmitButton"] button,
          button[kind="primary"],
          button[kind="primaryFormSubmit"] {{
            background-color: var(--primary) !important;
            color: var(--primary-text) !important;
            border: 1px solid var(--primary) !important;
          }}
          .stButton > button:hover,
          .stFormSubmitButton > button:hover {{ filter: brightness(0.92); }}
          .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
            background-color: var(--bg-secondary) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
          }}

          /* Expander (App & model) — make sure header isn't dark on white pages */
          .stApp [data-testid="stExpander"] details,
          .stApp [data-testid="stExpander"] summary,
          .stApp details, .stApp details summary {{
            background-color: var(--bg-secondary) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
          }}
          .stApp [data-testid="stExpander"] summary *,
          .stApp details summary * {{
            color: var(--text) !important;
            fill: var(--text) !important;
          }}

          /* File uploader (Attach files) dropzone */
          .stApp [data-testid="stFileUploader"] section,
          .stApp [data-testid="stFileUploaderDropzone"],
          .stApp [data-testid="stFileUploaderDropzoneInstructions"] {{
            background-color: var(--bg-secondary) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
          }}
          .stApp [data-testid="stFileUploaderDropzoneInstructions"] * {{
            color: var(--text) !important;
            fill: var(--text) !important;
          }}
          .stApp [data-testid="stFileUploader"] button {{
            background-color: var(--bg) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
          }}
          .demo-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 4px 0 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
          }}
          .demo-header h1 {{ margin: 0; font-size: 1.5rem; color: var(--text); }}
          .demo-header .subtitle {{ margin: 4px 0 0; font-size: .9rem; color: var(--text-muted); }}
          .demo-header img.demo-logo {{ height: {t["logo_height_px"]}px; width: auto; }}
        </style>
        <div class="demo-header">
          <div>
            <h1>{t["title"]}</h1>
            <div class="subtitle">{t["subtitle"]}</div>
          </div>
          {logo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
