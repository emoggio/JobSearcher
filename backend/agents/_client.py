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
    Parse ANTHROPIC_CUSTOM_HEADERS which Claude Code sets as a
    comma-separated list of 'key: value' pairs, possibly JSON-encoded.
    Example:
      x-portkey-config: abc123, "cgw_session_id": "xyz", ...
    """
    if not raw:
        return {}
    headers: dict[str, str] = {}
    # Try JSON object first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        pass
    # Fall back to splitting on commas, then on first colon
    for part in raw.split(","):
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
