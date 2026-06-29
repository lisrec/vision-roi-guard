from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .helpers.redact import redact_mapping


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, object]:
    """Return redacted diagnostics for a config entry."""
    del hass
    runtime_data = entry.runtime_data
    state = runtime_data.coordinator.state
    backend_name = getattr(runtime_data.backend, "backend_name", None)
    return {
        "entry": redact_mapping(
            {
                "data": dict(entry.data),
                "options": dict(entry.options),
            }
        ),
        "state": redact_mapping(
            {
                "last_result": state.last_result,
                "last_reason": _redact_diagnostic_text(state.last_reason),
                "last_error": _redact_diagnostic_text(state.last_error),
                "backend_name": state.backend_name,
                "configured_backend_name": backend_name,
                "camera_available": state.camera_available,
                "analysis_ok": state.analysis_ok,
                "roi_point_count": state.roi_point_count,
                "last_analyzed_image_path": state.last_analyzed_image_path,
                "debug_image_path": state.debug_image_path,
            }
        ),
    }


_TOKEN_OR_LONG_ID = re.compile(r"[A-Za-z0-9_-]{32,}")
_URL = re.compile(r"https?://[^\s]+")
_MAX_DIAGNOSTIC_TEXT_LENGTH = 160


def _redact_diagnostic_text(value: str | None) -> str | None:
    """Redact and cap backend-controlled diagnostic text."""
    if value is None:
        return None
    redacted = _URL.sub("[redacted-url]", str(value))
    redacted = _TOKEN_OR_LONG_ID.sub("[redacted-token]", redacted)
    if len(redacted) > _MAX_DIAGNOSTIC_TEXT_LENGTH:
        return f"{redacted[:_MAX_DIAGNOSTIC_TEXT_LENGTH]}…[truncated]"
    return redacted
