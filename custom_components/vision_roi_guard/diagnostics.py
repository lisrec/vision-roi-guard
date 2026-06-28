from __future__ import annotations

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
                "last_reason": state.last_reason,
                "last_error": state.last_error,
                "backend_name": state.backend_name,
                "configured_backend_name": backend_name,
                "camera_available": state.camera_available,
                "analysis_ok": state.analysis_ok,
                "roi_point_count": state.roi_point_count,
                "debug_image_path": state.debug_image_path,
            }
        ),
    }
