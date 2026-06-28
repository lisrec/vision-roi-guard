from __future__ import annotations

import asyncio

import pytest

from custom_components.vision_roi_guard.backends.codex_cli import (
    CodexCliBackend,
    parse_codex_response,
)
from custom_components.vision_roi_guard.exceptions import BackendError


def test_parse_codex_response_success() -> None:
    result = parse_codex_response(
        '{"verdict":"safe","reason":"empty_lawn","seen_objects":["grass"]}'
    )
    assert result.verdict == "safe"
    assert result.reason == "empty_lawn"
    assert result.seen_objects == ("grass",)


def test_parse_codex_response_invalid_json() -> None:
    with pytest.raises(BackendError):
        parse_codex_response("not json")


class _FakeProcess:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        return None


@pytest.mark.asyncio
async def test_codex_backend_handles_non_zero_exit_without_leaking_stderr(
    monkeypatch, tmp_path
) -> None:
    async def _fake_exec(*args, **kwargs):
        del args, kwargs
        return _FakeProcess(1, b"", b"private backend details")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"image")
    backend = CodexCliBackend({})
    with pytest.raises(BackendError) as err:
        await backend.analyze(str(image_path), {}, 10)
    assert str(err.value) == "codex_exit_1"


@pytest.mark.asyncio
async def test_codex_backend_rejects_missing_image_before_subprocess(monkeypatch) -> None:
    async def _fake_exec(*args, **kwargs):
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)
    backend = CodexCliBackend({})
    with pytest.raises(BackendError, match="codex_image_missing"):
        await backend.analyze("missing.png", {}, 10)
