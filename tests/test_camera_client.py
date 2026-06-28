from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.vision_roi_guard import camera_client
from custom_components.vision_roi_guard.camera_client import capture_camera_snapshot
from custom_components.vision_roi_guard.const import STORAGE_DIR, WORK_DIR


async def _register_snapshot_service(hass: HomeAssistant) -> None:
    async def _snapshot(call: ServiceCall) -> None:
        await hass.async_add_executor_job(
            Path(call.data["filename"]).write_bytes, b"snapshot"
        )

    hass.services.async_register("camera", "snapshot", _snapshot)


@pytest.mark.asyncio
async def test_capture_camera_snapshot_prefers_media_dir(
    hass: HomeAssistant, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(camera_client, "SNAPSHOT_MEDIA_ROOT", media_root)
    await _register_snapshot_service(hass)

    snapshot_path = await capture_camera_snapshot(hass, "camera.test_camera")

    assert snapshot_path.parent == media_root / STORAGE_DIR / WORK_DIR
    assert snapshot_path.suffix == ".jpg"
    assert snapshot_path.read_bytes() == b"snapshot"


@pytest.mark.asyncio
async def test_capture_camera_snapshot_falls_back_to_www_dir(
    hass: HomeAssistant, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(camera_client, "SNAPSHOT_MEDIA_ROOT", tmp_path / "missing-media")
    await _register_snapshot_service(hass)

    snapshot_path = await capture_camera_snapshot(hass, "camera.test_camera")

    assert snapshot_path.parent == Path(hass.config.path("www", STORAGE_DIR, WORK_DIR))
    assert snapshot_path.suffix == ".jpg"
    assert snapshot_path.read_bytes() == b"snapshot"
