"""Process-wide text encoding safeguards for hosted Streamlit runs."""

from __future__ import annotations

import os
import sys

ASCII_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u00b7": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u2026": "...",
        "\u2192": "->",
        "\u2713": "OK",
        "\u2714": "OK",
    }
)


def ascii_safe(value: object) -> str:
    """Return display text safe for ASCII-only logging sinks."""
    text = str(value).translate(ASCII_TRANSLATION)
    return text.encode("ascii", errors="ignore").decode("ascii")


class AsciiFallbackTextIO:
    """Proxy a text stream and retry writes with ASCII-safe text on encode errors."""

    _codex_ascii_fallback = True

    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        try:
            return self._stream.write(text)
        except UnicodeEncodeError:
            return self._stream.write(ascii_safe(text))

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        return self._stream.flush()

    def isatty(self):
        return self._stream.isatty()

    def reconfigure(self, *args, **kwargs):
        return self._stream.reconfigure(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._stream, name)


def install_ascii_stdio_fallback() -> None:
    """Make stdout/stderr tolerant of Unicode writes in ASCII-hosted runtimes."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8:replace")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        if not getattr(stream, "_codex_ascii_fallback", False):
            setattr(sys, name, AsciiFallbackTextIO(stream))
