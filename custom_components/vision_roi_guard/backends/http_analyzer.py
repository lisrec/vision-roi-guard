from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout, FormData
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import (
    CONF_ANALYZER_PROFILE,
    CONF_HTTP_ANALYZER_URL,
    CONF_HTTP_AUTH_TYPE,
    CONF_HTTP_BEARER_TOKEN,
    DEFAULT_ANALYZER_PROFILE,
    HTTP_AUTH_BEARER,
    HTTP_AUTH_NONE,
    VALID_VERDICTS,
    VERDICT_ERROR,
)
from ..exceptions import BackendError, ValidationError
from ..helpers.validation import validate_http_backend_config
from ..models import AnalysisResult
from .base import VisionBackend

SCHEMA_VERSION = "vision-roi-guard.v1"
MAX_HTTP_RESPONSE_BYTES = 16 * 1024
MAX_REASON_LENGTH = 256
MAX_SEEN_OBJECTS = 32
MAX_SEEN_OBJECT_LENGTH = 64
MIN_TIMEOUT_SEC = 5
MAX_TIMEOUT_SEC = 600


def parse_http_analyzer_response(payload: str) -> AnalysisResult:
    """Parse the HTTP analyzer v1 response body."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as err:
        raise BackendError("http_analyzer_invalid_json") from err

    if not isinstance(data, dict):
        raise BackendError("http_analyzer_invalid_json")

    result = data.get("result")
    reason = data.get("reason")
    seen_objects = data.get("seen_objects", [])
    confidence = data.get("confidence")
    duration_sec = data.get("duration_sec", 0.0)

    if result not in VALID_VERDICTS:
        raise BackendError("http_analyzer_invalid_result")
    if not isinstance(reason, str) or not reason.strip():
        raise BackendError("http_analyzer_invalid_reason")
    normalized_reason = reason.strip()
    if len(normalized_reason) > MAX_REASON_LENGTH:
        raise BackendError("http_analyzer_reason_too_long")
    if not isinstance(seen_objects, list) or len(seen_objects) > MAX_SEEN_OBJECTS:
        raise BackendError("http_analyzer_invalid_seen_objects")
    normalized_seen_objects = []
    for item in seen_objects:
        if not isinstance(item, str) or not item.strip():
            raise BackendError("http_analyzer_invalid_seen_objects")
        normalized_item = item.strip()
        if len(normalized_item) > MAX_SEEN_OBJECT_LENGTH:
            raise BackendError("http_analyzer_seen_object_too_long")
        normalized_seen_objects.append(normalized_item)
    if confidence is not None and (
        isinstance(confidence, bool)
        or not isinstance(confidence, int | float)
        or not math.isfinite(float(confidence))
        or confidence < 0
        or confidence > 1
    ):
        raise BackendError("http_analyzer_invalid_confidence")
    if duration_sec is not None and (
        isinstance(duration_sec, bool)
        or not isinstance(duration_sec, int | float)
        or not math.isfinite(float(duration_sec))
        or duration_sec < 0
    ):
        raise BackendError("http_analyzer_invalid_duration")

    return AnalysisResult(
        verdict=result,
        reason=normalized_reason,
        seen_objects=tuple(normalized_seen_objects),
        backend_name="http",
        duration_sec=float(duration_sec or 0.0),
    )


class HttpAnalyzerBackend(VisionBackend):
    """Generic HTTP analyzer backend."""

    backend_name = "http"

    def __init__(self, options: dict[str, Any], hass: HomeAssistant | None = None) -> None:
        self._options = options
        self._hass = hass
        self._url = str(options.get(CONF_HTTP_ANALYZER_URL, "")).strip()
        self._auth_type = str(options.get(CONF_HTTP_AUTH_TYPE, HTTP_AUTH_NONE)).strip().lower()
        self._bearer_token = str(options.get(CONF_HTTP_BEARER_TOKEN, "")).strip()
        self._profile = (
            str(options.get(CONF_ANALYZER_PROFILE, DEFAULT_ANALYZER_PROFILE)).strip()
            or DEFAULT_ANALYZER_PROFILE
        )

    async def validate(self) -> None:
        """Validate static HTTP analyzer configuration without contacting the endpoint."""
        try:
            validate_http_backend_config(self._options)
        except ValidationError as err:
            raise BackendError(str(err)) from err

    async def healthcheck(self) -> None:
        """HTTP analyzers are validated lazily by POST /analyze."""
        await self.validate()

    async def analyze(
        self, image_path: str, prompt_context: dict[str, Any], timeout_sec: int
    ) -> AnalysisResult:
        """Send the processed ROI image to the configured analyzer endpoint."""
        started = perf_counter()
        path = Path(image_path)
        if not await asyncio.to_thread(path.is_file):
            raise BackendError("http_analyzer_image_missing")

        image_bytes = await asyncio.to_thread(path.read_bytes)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "analysis_type": self._profile,
            "profile": self._profile,
            "roi_mode": prompt_context.get("roi_mode"),
            "image_format": prompt_context.get("image_format", "png"),
            "source": {
                "type": "home_assistant_camera",
                "camera_entity": prompt_context.get("camera_entity_id"),
            },
        }
        metadata = _drop_none(metadata)

        form = FormData()
        form.add_field("profile", self._profile)
        form.add_field("metadata", json.dumps(metadata, separators=(",", ":")))
        form.add_field(
            "image",
            image_bytes,
            filename=path.name,
            content_type=f"image/{metadata.get('image_format', 'png')}",
        )

        headers = {}
        if self._auth_type == HTTP_AUTH_BEARER:
            headers["Authorization"] = f"Bearer {self._bearer_token}"

        try:
            session = self._session
            async with session.post(
                self._url,
                data=form,
                headers=headers,
                timeout=ClientTimeout(total=_bounded_timeout(timeout_sec)),
            ) as response:
                if response.status < 200 or response.status >= 300:
                    raise BackendError(f"http_analyzer_http_{response.status}")
                body = await response.content.read(MAX_HTTP_RESPONSE_BYTES + 1)
                if len(body) > MAX_HTTP_RESPONSE_BYTES:
                    raise BackendError("http_analyzer_response_too_large")
                try:
                    text = body.decode(response.charset or "utf-8")
                except UnicodeDecodeError as err:
                    raise BackendError("http_analyzer_invalid_text") from err
        except TimeoutError as err:
            raise BackendError("http_analyzer_timeout") from err
        except ClientError as err:
            raise BackendError("http_analyzer_transport_error") from err

        result = parse_http_analyzer_response(text)
        duration = result.duration_sec or (perf_counter() - started)
        analysis_ok = result.verdict != VERDICT_ERROR
        return AnalysisResult(
            verdict=result.verdict,
            reason=result.reason,
            seen_objects=result.seen_objects,
            backend_name=self.backend_name,
            duration_sec=duration,
            error_code=None if analysis_ok else result.reason,
        )

    @property
    def _session(self) -> ClientSession:
        if self._hass is None:
            raise BackendError("http_analyzer_hass_missing")
        return async_get_clientsession(self._hass)


def _bounded_timeout(timeout_sec: int) -> int:
    """Clamp analyzer call timeouts to safe server-side bounds."""
    if isinstance(timeout_sec, bool):
        return MIN_TIMEOUT_SEC
    try:
        timeout = int(timeout_sec)
    except (TypeError, ValueError):
        return MIN_TIMEOUT_SEC
    return min(max(timeout, MIN_TIMEOUT_SEC), MAX_TIMEOUT_SEC)


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value if item is not None]
    return value
