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
    "logo_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQFp6cY-Rzi3abC1a6Zs7PNQUmgzNxzmf5vyMad7LyNPQ&s=10",
    "logo_height_px": 44,
    # ── Browser tab ─────────────────────────────────────────────
    "page_title": "Barndoor + CrewAI Assistant",
    "page_icon": "🤖",
    # ── Colors ──────────────────────────────────────────────────
    # Primary palette — three shades let buttons have a real hover state and
    # subtle accents (default Material-style dark green).
    "primary_color": "#2E7D32",        # main: buttons, header title, h1/h2/h3
    "primary_color_light": "#66BB6A",  # light: subtle accents / highlights
    "primary_color_dark": "#1B5E20",   # dark:  button hover / pressed
    "primary_color_text": "#FFFFFF",   # text on top of primary fills
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
            --primary-light: {t["primary_color_light"]};
            --primary-dark: {t["primary_color_dark"]};
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
          .stApp label {{
            color: var(--text);
          }}
          /* Inline `code` — used in run log for tool names; Streamlit's default
             is a near-black background that's invisible on light themes. */
          .stApp [data-testid="stMarkdownContainer"] code {{
            background-color: var(--bg-secondary) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            padding: 1px 6px !important;
            border-radius: 4px !important;
            font-size: 0.9em !important;
          }}
          /* Code blocks keep their default monospace block styling, but ensure
             nested <code> doesn't inherit the chip background. */
          .stApp [data-testid="stMarkdownContainer"] pre code {{
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
          }}
          /* Headings adopt the primary color so the brand reads across the page. */
          .stApp h1, .stApp h2, .stApp h3, .demo-header h1 {{
            color: var(--primary) !important;
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
          .stFormSubmitButton > button:hover {{
            background-color: var(--primary-dark) !important;
            border-color: var(--primary-dark) !important;
          }}
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
