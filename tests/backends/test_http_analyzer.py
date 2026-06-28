from __future__ import annotations

import math

import pytest
from aiohttp import ClientError, FormData

from custom_components.vision_roi_guard.backends.http_analyzer import (
    HttpAnalyzerBackend,
    parse_http_analyzer_response,
)
from custom_components.vision_roi_guard.exceptions import BackendError


def test_parse_http_analyzer_response_success() -> None:
    result = parse_http_analyzer_response(
        '{"schema_version":"vision-roi-guard.v1","result":"safe",'
        '"reason":"ROI appears clear","seen_objects":["grass"],"confidence":0.88}'
    )
    assert result.verdict == "safe"
    assert result.reason == "ROI appears clear"
    assert result.seen_objects == ("grass",)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "{}",
        '{"result":"maybe","reason":"bad"}',
        '{"result":"safe","reason":""}',
        '{"result":"safe","reason":"ok","seen_objects":["person", 1]}',
    ],
)
def test_parse_http_analyzer_response_rejects_invalid_payload(payload: str) -> None:
    with pytest.raises(BackendError):
        parse_http_analyzer_response(payload)


class _FakeContent:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def read(self, size: int = -1) -> bytes:
        del size
        return self._payload


class _FakeResponse:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self.charset = "utf-8"
        self.content = _FakeContent(text.encode())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSession:
    def __init__(self, response: _FakeResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, *, data, headers, timeout):
        self.calls.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


@pytest.mark.asyncio
async def test_http_backend_posts_multipart_with_bearer_header(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "roi.png"
    image_path.write_bytes(b"image")
    session = _FakeSession(
        _FakeResponse(200, '{"result":"blocked","reason":"person","seen_objects":["person"]}')
    )
    monkeypatch.setattr(HttpAnalyzerBackend, "_session", property(lambda self: session))

    backend = HttpAnalyzerBackend(
        {
            "http_analyzer_url": "http://127.0.0.1:8766/analyze",
            "http_auth_type": "bearer",
            "http_bearer_token": "test-token",
            "analyzer_profile": "mower_safety",
        }
    )
    result = await backend.analyze(
        str(image_path),
        {"camera_entity_id": "camera.test_camera", "roi_mode": "cropped", "image_format": "png"},
        42,
    )

    assert result.verdict == "blocked"
    assert result.seen_objects == ("person",)
    assert session.calls[0]["url"] == "http://127.0.0.1:8766/analyze"
    assert session.calls[0]["headers"] == {"Authorization": "Bearer test-token"}
    assert session.calls[0]["timeout"].total == 42
    assert isinstance(session.calls[0]["data"], FormData)


@pytest.mark.asyncio
async def test_http_backend_rejects_non_2xx(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "roi.png"
    image_path.write_bytes(b"image")
    session = _FakeSession(_FakeResponse(500, '{"result":"safe","reason":"ignored"}'))
    monkeypatch.setattr(HttpAnalyzerBackend, "_session", property(lambda self: session))

    backend = HttpAnalyzerBackend({"http_analyzer_url": "http://127.0.0.1:8766/analyze"})
    with pytest.raises(BackendError, match="http_analyzer_http_500"):
        await backend.analyze(str(image_path), {}, 10)


@pytest.mark.asyncio
async def test_http_backend_maps_transport_error(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "roi.png"
    image_path.write_bytes(b"image")
    session = _FakeSession(error=ClientError("private transport details"))
    monkeypatch.setattr(HttpAnalyzerBackend, "_session", property(lambda self: session))

    backend = HttpAnalyzerBackend({"http_analyzer_url": "http://127.0.0.1:8766/analyze"})
    with pytest.raises(BackendError) as err:
        await backend.analyze(str(image_path), {}, 10)
    assert str(err.value) == "http_analyzer_transport_error"


def test_parse_http_analyzer_response_rejects_numeric_edge_cases() -> None:
    for payload in (
        '{"result":"safe","reason":"ok","confidence":true}',
        '{"result":"safe","reason":"ok","confidence":NaN}',
        '{"result":"safe","reason":"ok","duration_sec":true}',
        '{"result":"safe","reason":"ok","duration_sec":-1}',
    ):
        with pytest.raises(BackendError):
            parse_http_analyzer_response(payload)


def test_parse_http_analyzer_response_rejects_oversized_fields() -> None:
    with pytest.raises(BackendError, match="reason_too_long"):
        parse_http_analyzer_response(
            '{"result":"safe","reason":"' + ('x' * 300) + '"}'
        )
    with pytest.raises(BackendError, match="invalid_seen_objects"):
        parse_http_analyzer_response(
            '{"result":"safe","reason":"ok","seen_objects":['
            + ','.join('"x"' for _ in range(33))
            + ']} ' 
        )
    with pytest.raises(BackendError, match="seen_object_too_long"):
        parse_http_analyzer_response(
            '{"result":"safe","reason":"ok","seen_objects":["' + ('x' * 80) + '"]}'
        )


@pytest.mark.asyncio
async def test_http_backend_rejects_oversized_response(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "roi.png"
    image_path.write_bytes(b"image")
    session = _FakeSession(_FakeResponse(200, "{" + " " * (16 * 1024 + 1)))
    monkeypatch.setattr(HttpAnalyzerBackend, "_session", property(lambda self: session))

    backend = HttpAnalyzerBackend({"http_analyzer_url": "http://127.0.0.1:8766/analyze"})
    with pytest.raises(BackendError, match="response_too_large"):
        await backend.analyze(str(image_path), {}, 10)


@pytest.mark.asyncio
async def test_http_backend_clamps_timeout(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "roi.png"
    image_path.write_bytes(b"image")
    session = _FakeSession(_FakeResponse(200, '{"result":"safe","reason":"ok"}'))
    monkeypatch.setattr(HttpAnalyzerBackend, "_session", property(lambda self: session))

    backend = HttpAnalyzerBackend({"http_analyzer_url": "http://127.0.0.1:8766/analyze"})
    await backend.analyze(str(image_path), {}, 999999)

    assert math.isclose(session.calls[0]["timeout"].total, 600)
