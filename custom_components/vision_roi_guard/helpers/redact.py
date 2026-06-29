from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "camera_entity_id",
    "prompt_template",
    "roi_points_json",
    "last_analyzed_image_path",
    "debug_image_path",
    "raw_text",
    "http_analyzer_url",
    "metadata",
}
SENSITIVE_KEY_FRAGMENTS = ("token", "secret", "password", "api_key", "key", "url")


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Redact known sensitive fields from a mapping."""
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        normalized_key = key.lower()
        if key in SENSITIVE_KEYS or any(
            fragment in normalized_key for fragment in SENSITIVE_KEY_FRAGMENTS
        ):
            redacted[key] = "[redacted]"
            continue
        if isinstance(value, dict):
            redacted[key] = redact_mapping(value)
            continue
        redacted[key] = value
    return redacted
