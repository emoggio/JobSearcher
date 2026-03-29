"""
Shared Anthropic client factory.
Reads ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, and ANTHROPIC_CUSTOM_HEADERS
from the environment so the company gateway (Portkey / CGW) works correctly.
"""
import os
import json
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


def _parse_custom_headers(raw: str) -> dict[str, str]:
    """
    Parse ANTHROPIC_CUSTOM_HEADERS.
    Supports two formats:
      1. JSON object: {"x-portkey-config": "abc", ...}  (preferred, set by Scout)
      2. Comma-separated key: value pairs (set by Claude Code CLI directly)
    """
    if not raw:
        return {}
    # Try JSON object first (our format)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        pass
    # Fall back: newline or comma-separated "key: value" lines
    headers: dict[str, str] = {}
    for part in raw.replace("\n", ",").split(","):
        part = part.strip()
        if ":" in part:
            k, _, v = part.partition(":")
            headers[k.strip().strip('"')] = v.strip().strip('"')
    return headers


def make_client() -> AsyncAnthropic:
    """Return an AsyncAnthropic client configured for the current environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    custom_headers_raw = os.getenv("ANTHROPIC_CUSTOM_HEADERS", "")

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
        logger.debug("Anthropic client: using custom base URL %s", base_url)
    if custom_headers_raw:
        headers = _parse_custom_headers(custom_headers_raw)
        if headers:
            kwargs["default_headers"] = headers
            logger.debug("Anthropic client: %d custom headers applied", len(headers))

    return AsyncAnthropic(**kwargs)
