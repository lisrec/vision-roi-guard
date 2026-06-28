from __future__ import annotations

import shutil
from collections.abc import Iterable
from datetime import time
from typing import Any

from homeassistant.helpers import config_validation as cv

from ..const import (
    BACKEND_CODEX_CLI,
    BACKEND_MOCK,
    BACKEND_TYPES,
    CONF_ANALYSIS_INTERVAL_MIN,
    CONF_ANALYSIS_TIMEOUT_SEC,
    CONF_CLI_TIMEOUT_SEC,
    CONF_DEBUG_RETENTION_COUNT,
    CONF_MAX_OUTPUT_TOKENS,
    CONF_MOCK_MODE,
    CONF_MOCK_REASON,
    CONF_MOCK_SEEN_OBJECTS,
    CONF_MOCK_VERDICT,
    CONF_MODEL,
    CONF_PROMPT_TEMPLATE,
    CONF_ROI_POINTS_JSON,
    DEFAULT_PROMPT_TEMPLATE,
    VALID_VERDICTS,
)
from ..exceptions import ValidationError
from ..models import RoiPoint
from ..roi import parse_roi_points_json, validate_polygon


def ensure_backend_available(backend_type: str) -> None:
    """Validate that a backend can be selected."""
    if backend_type not in BACKEND_TYPES:
        raise ValidationError("unsupported_backend")
    if backend_type == BACKEND_CODEX_CLI and shutil.which("codex") is None:
        raise ValidationError("codex_cli_missing")
    if backend_type == BACKEND_MOCK:
        return


def validate_camera_entity_id(hass: Any, entity_id: str) -> None:
    """Validate that the configured camera entity exists."""
    state = hass.states.get(entity_id)
    if state is None:
        raise ValidationError("camera_not_found")
    if not entity_id.startswith("camera."):
        raise ValidationError("camera_invalid_domain")


def validate_roi_points_option(value: str) -> tuple[RoiPoint, ...]:
    """Validate ROI JSON text and return parsed points."""
    if not value.strip():
        return ()
    points = parse_roi_points_json(value)
    validate_polygon(points)
    return points


def csv_to_tuple(value: str | Iterable[str]) -> tuple[str, ...]:
    """Normalize CSV-like options."""
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value
    return tuple(item.strip() for item in items if item and item.strip())


def validate_verdict(value: str) -> str:
    """Validate a verdict string."""
    normalized = value.strip().lower()
    if normalized not in VALID_VERDICTS[:-1]:
        raise ValidationError("invalid_verdict")
    return normalized


def parse_time(value: str | time) -> time:
    """Normalize a time value from HA forms."""
    if isinstance(value, time):
        return value
    return cv.time(value)


def sanitize_option_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize option data."""
    options = dict(payload)
    if CONF_ROI_POINTS_JSON in options:
        validate_roi_points_option(options[CONF_ROI_POINTS_JSON])
    for key in (
        CONF_ANALYSIS_INTERVAL_MIN,
        CONF_ANALYSIS_TIMEOUT_SEC,
        CONF_CLI_TIMEOUT_SEC,
        CONF_DEBUG_RETENTION_COUNT,
        CONF_MAX_OUTPUT_TOKENS,
    ):
        if key in options:
            options[key] = int(options[key])
    if CONF_MODEL in options:
        options[CONF_MODEL] = str(options[CONF_MODEL]).strip()
    if CONF_PROMPT_TEMPLATE in options:
        options[CONF_PROMPT_TEMPLATE] = (
            str(options[CONF_PROMPT_TEMPLATE]).strip() or DEFAULT_PROMPT_TEMPLATE
        )
    if CONF_MOCK_VERDICT in options:
        options[CONF_MOCK_VERDICT] = validate_verdict(str(options[CONF_MOCK_VERDICT]))
    if CONF_MOCK_REASON in options:
        options[CONF_MOCK_REASON] = str(options[CONF_MOCK_REASON]).strip() or "mock_result"
    if CONF_MOCK_SEEN_OBJECTS in options:
        options[CONF_MOCK_SEEN_OBJECTS] = ",".join(csv_to_tuple(options[CONF_MOCK_SEEN_OBJECTS]))
    if CONF_MOCK_MODE in options and options[CONF_MOCK_MODE] not in ("fixed", "filename_keyword"):
        raise ValidationError("invalid_mock_mode")
    return options
