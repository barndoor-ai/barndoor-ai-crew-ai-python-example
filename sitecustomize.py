"""Startup hook imported automatically by Python's site module."""

from encoding_safety import install_ascii_stdio_fallback

install_ascii_stdio_fallback()
