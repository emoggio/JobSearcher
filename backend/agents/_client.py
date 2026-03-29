"""
Shared Anthropic client factory.

Priority order for credentials:
  1. ANTHROPIC_CUSTOM_HEADERS (process env — set by Claude Code terminal session)
  2. ~/.claude/config.json + live ANTHROPIC_CUSTOM_HEADERS env (Claude Code gateway)
  3. ANTHROPIC_API_KEY in .env (standard personal API key)

Always start the backend from the SAME terminal as Claude Code so that
the live session headers are inherited as process environment variables.
"""
import json
import logging
import os
from pathlib import Path

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


def _parse_custom_headers(raw: str) -> dict[str, str]:
    """
    Parse ANTHROPIC_CUSTOM_HEADERS.
    Claude Code sets this as newline-separated 'Key: Value' lines where
    values may themselves contain colons (e.g. JSON strings).
    Also handles JSON object format as a fallback.
    """
    if not raw:
        return {}
    # Try JSON object first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        pass
    # Parse newline-separated "Key: Value" lines (split only on FIRST ": ")
    headers: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if ": " in line:
            k, _, v = line.partition(": ")
            headers[k.strip()] = v.strip()
        elif ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()
    return headers


def _read_claude_code_config() -> tuple[str, str, str]:
    """
    Read api_key, base_url, custom_headers from Claude Code's config.
    Returns (api_key, base_url, custom_headers_raw).
    Falls back to empty strings if not found.
    """
    try:
        config_path = Path.home() / ".claude" / "config.json"
        config = json.loads(config_path.read_text())
        api_key = config.get("primaryApiKey", "")
        base_url = config.get("apiBaseUrl", "")
        return api_key, base_url, ""
    except Exception:
        return "", "", ""


def make_client() -> AsyncAnthropic:
    """Return an AsyncAnthropic client configured for the current environment."""
    # 1. Try process environment first (inherited from Claude Code terminal)
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    custom_headers_raw = os.getenv("ANTHROPIC_CUSTOM_HEADERS", "")

    # 2. If no custom headers in env, try reading Claude Code config
    if not custom_headers_raw and not api_key:
        cc_key, cc_base, _ = _read_claude_code_config()
        if cc_key:
            api_key = api_key or cc_key
        if cc_base:
            base_url = base_url or cc_base

    kwargs: dict = {"api_key": api_key or "dummy"}

    if base_url:
        kwargs["base_url"] = base_url
        logger.debug("Anthropic client: gateway %s", base_url)

    if custom_headers_raw:
        headers = _parse_custom_headers(custom_headers_raw)
        if headers:
            kwargs["default_headers"] = headers
            logger.debug("Anthropic client: %d custom headers applied", len(headers))

    return AsyncAnthropic(**kwargs)
