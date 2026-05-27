"""Make MCP tool schemas pass OpenAI's function-calling validator.

Some MCP servers (e.g. Barndoor's Gmail) expose tool input schemas where an
array's ``items`` (or a nested object) has no ``type``. OpenAI's function-calling
API rejects these with, e.g.::

    Invalid schema for function 'send_draft': In context=(...,'items'),
    schema must have a 'type' key.

CrewAI builds the OpenAI tool payload in
``crewai.utilities.agent_utils.convert_tools_to_openai_schema`` (which
``crew_agent_executor`` imports by name). We wrap it to do two things:

1. Recursively backfill a sensible ``type`` on any schema node that lacks one and
   isn't a composite (``anyOf``/``$ref``/``enum``/...). OpenAI requires every node
   (e.g. an array's ``items``) to declare a ``type``.
2. Turn off ``strict`` mode. CrewAI sets ``strict: True`` on every function, which
   makes OpenAI demand that every property appear in ``required`` (and nothing else).
   MCP tools have optional fields and loose ``required`` lists, so strict mode
   rejects them (e.g. "Extra required key 'title' supplied"). Non-strict mode is the
   normal way to call MCP tools and accepts these schemas as-is.

Call :func:`patch_crewai_tool_schemas` once before running a Crew. It is idempotent.
"""

from __future__ import annotations

from typing import Any

# Keywords whose presence means a node defines its shape without a bare ``type``.
_COMPOSITION_KEYS = ("$ref", "anyOf", "oneOf", "allOf", "enum", "const")
# Sub-schema locations to recurse into.
_SUBSCHEMA_DICT = ("items", "additionalProperties", "not", "contains", "if", "then", "else")
_SUBSCHEMA_LIST = ("anyOf", "oneOf", "allOf", "prefixItems")
_SUBSCHEMA_MAP = ("properties", "patternProperties", "$defs", "definitions")


def _backfill_types(schema: Any) -> None:
    """Recursively ensure every schema node has a ``type`` OpenAI will accept."""
    if not isinstance(schema, dict):
        return

    for key in _SUBSCHEMA_DICT:
        if isinstance(schema.get(key), dict):
            _backfill_types(schema[key])
    if isinstance(schema.get("items"), list):  # tuple-style "items": [ {...}, {...} ]
        for sub in schema["items"]:
            _backfill_types(sub)
    for key in _SUBSCHEMA_LIST:
        if isinstance(schema.get(key), list):
            for sub in schema[key]:
                _backfill_types(sub)
    for key in _SUBSCHEMA_MAP:
        if isinstance(schema.get(key), dict):
            for sub in schema[key].values():
                _backfill_types(sub)

    if "type" not in schema and not any(k in schema for k in _COMPOSITION_KEYS):
        if "properties" in schema:
            schema["type"] = "object"
        elif "items" in schema or "prefixItems" in schema:
            schema["type"] = "array"
        else:
            schema["type"] = "string"


def _sanitize_function_entry(entry: Any) -> None:
    """Backfill types and disable strict mode on one OpenAI tool dict, in place."""
    if not isinstance(entry, dict):
        return
    function = entry.get("function")
    if not isinstance(function, dict):
        return
    params = function.get("parameters")
    if isinstance(params, dict):
        _backfill_types(params)
    function["strict"] = False


def _patch_openai_provider() -> None:
    """Primary hook: the OpenAI provider's tool conversion, the last step before the API.

    ``OpenAICompletion._convert_tools_for_interference`` builds ``params["tools"]`` for
    every chat-completions call (streaming and not), regardless of which agent executor
    is driving — so sanitizing its output covers all paths and all MCP servers.
    """
    try:
        from crewai.llms.providers.openai.completion import OpenAICompletion
    except Exception:
        return

    original = OpenAICompletion._convert_tools_for_interference
    if getattr(original, "_mcp_sanitized", False):
        return

    def sanitized(self, tools):  # type: ignore[no-untyped-def]
        openai_tools = original(self, tools)
        for entry in openai_tools:
            _sanitize_function_entry(entry)
        return openai_tools

    sanitized._mcp_sanitized = True  # type: ignore[attr-defined]
    OpenAICompletion._convert_tools_for_interference = sanitized


def _patch_executor_conversion() -> None:
    """Defense in depth: also sanitize the generic executor conversion (e.g. LiteLLM path)."""
    try:
        from crewai.agents import crew_agent_executor
        from crewai.utilities import agent_utils
    except Exception:
        return

    original = agent_utils.convert_tools_to_openai_schema
    if getattr(original, "_mcp_sanitized", False):
        return

    def sanitized(tools):  # type: ignore[no-untyped-def]
        openai_tools, available_functions, tool_name_mapping = original(tools)
        for entry in openai_tools:
            _sanitize_function_entry(entry)
        return openai_tools, available_functions, tool_name_mapping

    sanitized._mcp_sanitized = True  # type: ignore[attr-defined]
    agent_utils.convert_tools_to_openai_schema = sanitized
    crew_agent_executor.convert_tools_to_openai_schema = sanitized


def patch_crewai_tool_schemas() -> None:
    """Make MCP tool schemas valid for OpenAI, everywhere CrewAI emits them. Idempotent."""
    _patch_openai_provider()
    _patch_executor_conversion()
