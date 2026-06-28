from __future__ import annotations

import math
import shutil
from collections.abc import Iterable
from datetime import time
from typing import Any
from urllib.parse import urlparse

from homeassistant.helpers import config_validation as cv

from ..const import (
    BACKEND_CODEX_CLI,
    BACKEND_HTTP_ANALYZER,
    BACKEND_MOCK,
    BACKEND_TYPES,
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_ANALYSIS_INTERVAL_MIN,
    CONF_ANALYSIS_TIMEOUT_SEC,
    CONF_ANALYZER_PROFILE,
    CONF_CLI_TIMEOUT_SEC,
    CONF_DEBUG_RETENTION_COUNT,
    CONF_HTTP_ANALYZER_URL,
    CONF_HTTP_AUTH_TYPE,
    CONF_HTTP_BEARER_TOKEN,
    CONF_MAX_OUTPUT_TOKENS,
    CONF_MOCK_MODE,
    CONF_MOCK_REASON,
    CONF_MOCK_SEEN_OBJECTS,
    CONF_MOCK_VERDICT,
    CONF_MODEL,
    CONF_PROMPT_TEMPLATE,
    CONF_ROI_POINTS_JSON,
    DEFAULT_PROMPT_TEMPLATE,
    HTTP_AUTH_BEARER,
    HTTP_AUTH_TYPES,
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
    if backend_type == BACKEND_HTTP_ANALYZER:
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


def validate_http_analyzer_url(value: str) -> str:
    """Validate and normalize an HTTP analyzer endpoint URL."""
    normalized = str(value).strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationError("invalid_http_analyzer_url")
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
    integer_bounds = {
        CONF_ANALYSIS_INTERVAL_MIN: (0, 1440),
        CONF_ANALYSIS_TIMEOUT_SEC: (5, 600),
        CONF_CLI_TIMEOUT_SEC: (5, 600),
        CONF_DEBUG_RETENTION_COUNT: (1, 500),
        CONF_MAX_OUTPUT_TOKENS: (1, 4096),
    }
    for key, (minimum, maximum) in integer_bounds.items():
        if key in options:
            options[key] = _bounded_int(options[key], key, minimum, maximum)
    for key in (CONF_ACTIVE_START_TIME, CONF_ACTIVE_STOP_TIME):
        if key in options:
            options[key] = parse_time(options[key])
    if CONF_MODEL in options:
        options[CONF_MODEL] = str(options[CONF_MODEL]).strip()
    if CONF_PROMPT_TEMPLATE in options:
        options[CONF_PROMPT_TEMPLATE] = (
            str(options[CONF_PROMPT_TEMPLATE]).strip() or DEFAULT_PROMPT_TEMPLATE
        )
    if CONF_HTTP_ANALYZER_URL in options:
        url = str(options[CONF_HTTP_ANALYZER_URL]).strip()
        options[CONF_HTTP_ANALYZER_URL] = validate_http_analyzer_url(url) if url else ""
    if CONF_HTTP_AUTH_TYPE in options:
        auth_type = str(options[CONF_HTTP_AUTH_TYPE]).strip().lower()
        if auth_type not in HTTP_AUTH_TYPES:
            raise ValidationError("invalid_http_auth_type")
        options[CONF_HTTP_AUTH_TYPE] = auth_type
    if CONF_HTTP_BEARER_TOKEN in options:
        options[CONF_HTTP_BEARER_TOKEN] = str(options[CONF_HTTP_BEARER_TOKEN]).strip()
    if CONF_ANALYZER_PROFILE in options:
        options[CONF_ANALYZER_PROFILE] = (
            str(options[CONF_ANALYZER_PROFILE]).strip() or "mower_safety"
        )
    if (
        options.get(CONF_HTTP_AUTH_TYPE) == HTTP_AUTH_BEARER
        and not str(options.get(CONF_HTTP_BEARER_TOKEN, "")).strip()
    ):
        raise ValidationError("missing_http_bearer_token")
    if CONF_MOCK_VERDICT in options:
        options[CONF_MOCK_VERDICT] = validate_verdict(str(options[CONF_MOCK_VERDICT]))
    if CONF_MOCK_REASON in options:
        options[CONF_MOCK_REASON] = str(options[CONF_MOCK_REASON]).strip() or "mock_result"
    if CONF_MOCK_SEEN_OBJECTS in options:
        options[CONF_MOCK_SEEN_OBJECTS] = ",".join(csv_to_tuple(options[CONF_MOCK_SEEN_OBJECTS]))
    if CONF_MOCK_MODE in options and options[CONF_MOCK_MODE] not in ("fixed", "filename_keyword"):
        raise ValidationError("invalid_mock_mode")
    return options


def validate_http_backend_config(options: dict[str, Any]) -> None:
    """Validate required settings for the HTTP analyzer backend."""
    if not str(options.get(CONF_HTTP_ANALYZER_URL, "")).strip():
        raise ValidationError("missing_http_analyzer_url")
    validate_http_analyzer_url(str(options[CONF_HTTP_ANALYZER_URL]))
    auth_type = str(options.get(CONF_HTTP_AUTH_TYPE, "none")).strip().lower()
    if auth_type not in HTTP_AUTH_TYPES:
        raise ValidationError("invalid_http_auth_type")
    if auth_type == HTTP_AUTH_BEARER and not str(options.get(CONF_HTTP_BEARER_TOKEN, "")).strip():
        raise ValidationError("missing_http_bearer_token")
    if CONF_ANALYSIS_TIMEOUT_SEC in options:
        _bounded_int(options[CONF_ANALYSIS_TIMEOUT_SEC], CONF_ANALYSIS_TIMEOUT_SEC, 5, 600)


def _bounded_int(value: Any, key: str, minimum: int, maximum: int) -> int:
    """Return a bounded integer and reject bool/NaN/inf/out-of-range values."""
    if isinstance(value, bool):
        raise ValidationError(f"invalid_{key}")
    try:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError
        normalized = int(value)
    except (TypeError, ValueError, OverflowError) as err:
        raise ValidationError(f"invalid_{key}") from err
    if normalized < minimum or normalized > maximum:
        raise ValidationError(f"invalid_{key}")
    return normalized
