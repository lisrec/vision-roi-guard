from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from custom_components.vision_roi_guard.backends.mock import MockBackend
from custom_components.vision_roi_guard.const import (
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_CAMERA_ENTITY_ID,
    CONF_ROI_POINTS_JSON,
)
from custom_components.vision_roi_guard.coordinator import VisionRoiGuardCoordinator
from custom_components.vision_roi_guard.exceptions import BackendError
from custom_components.vision_roi_guard.image import (
    LastAnalyzedImageEntity,
    RoiEditorImageEntity,
)


class _FailingBackend:
    backend_name = "failing"

    async def analyze(self, image_path, prompt_context, timeout_sec):
        del image_path, prompt_context, timeout_sec
        raise BackendError("backend_failed")


@pytest.mark.asyncio
async def test_coordinator_runs_analysis(monkeypatch, hass, tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.jpg"

    async def _fake_capture(*args, **kwargs):
        del args, kwargs
        from PIL import Image

        image = Image.new("RGB", (10, 10), (255, 255, 255))
        image.save(snapshot_path, format="JPEG")
        return snapshot_path

    monkeypatch.setattr(
        "custom_components.vision_roi_guard.coordinator.capture_camera_snapshot", _fake_capture
    )

    backend = MockBackend({})
    coordinator = VisionRoiGuardCoordinator(
        hass=hass,
        entry_id="entry-id",
        title="Garden Guard",
        data={CONF_CAMERA_ENTITY_ID: "camera.test_camera"},
        options={
            CONF_ROI_POINTS_JSON: "[[1,1],[8,1],[8,8],[1,8]]",
            CONF_ACTIVE_START_TIME: time(0, 0),
            CONF_ACTIVE_STOP_TIME: time(23, 59),
        },
        backend=backend,
    )

    result = await coordinator.async_run_analysis(force=True, save_debug=False)
    assert result.last_result == "safe"
    assert result.safe_to_start is True
    assert result.debug_image_path is None
    assert result.last_analyzed_image_path is not None
    assert result.roi_editor_image_path is not None
    assert result.source_width == 10
    assert result.source_height == 10

    last_image_path = Path(
        hass.config.path("vision_roi_guard", "debug", "entry-id-last-analyzed.png")
    )
    assert result.last_analyzed_image_path == str(last_image_path)
    assert await hass.async_add_executor_job(last_image_path.is_file)

    entity = LastAnalyzedImageEntity(
        hass,
        coordinator,
        type("Entry", (), {"entry_id": "entry-id", "title": "Garden Guard"})(),
    )
    assert entity.content_type == "image/png"
    assert entity.image() == await hass.async_add_executor_job(last_image_path.read_bytes)

    editor_image_path = Path(
        hass.config.path("vision_roi_guard", "debug", "entry-id-roi-editor.png")
    )
    assert result.roi_editor_image_path == str(editor_image_path)
    assert await hass.async_add_executor_job(editor_image_path.is_file)

    editor_entity = RoiEditorImageEntity(
        hass,
        coordinator,
        type("Entry", (), {"entry_id": "entry-id", "title": "Garden Guard"})(),
    )
    assert editor_entity.content_type == "image/png"
    assert editor_entity.image() == await hass.async_add_executor_job(
        editor_image_path.read_bytes
    )


@pytest.mark.asyncio
async def test_coordinator_keeps_last_image_when_backend_fails_after_roi(
    monkeypatch, hass, tmp_path
) -> None:
    snapshot_path = tmp_path / "snapshot.jpg"

    async def _fake_capture(*args, **kwargs):
        del args, kwargs
        from PIL import Image

        image = Image.new("RGB", (10, 10), (255, 255, 255))
        image.save(snapshot_path, format="JPEG")
        return snapshot_path

    monkeypatch.setattr(
        "custom_components.vision_roi_guard.coordinator.capture_camera_snapshot", _fake_capture
    )

    coordinator = VisionRoiGuardCoordinator(
        hass=hass,
        entry_id="entry-id",
        title="Garden Guard",
        data={CONF_CAMERA_ENTITY_ID: "camera.test_camera"},
        options={
            CONF_ROI_POINTS_JSON: "[[1,1],[8,1],[8,8],[1,8]]",
            CONF_ACTIVE_START_TIME: time(0, 0),
            CONF_ACTIVE_STOP_TIME: time(23, 59),
        },
        backend=_FailingBackend(),
    )

    result = await coordinator.async_run_analysis(force=True, save_debug=False)

    assert result.last_result == "error"
    assert result.safe_to_start is False
    assert result.last_error == "backend_failed"
    assert result.last_analyzed_image_path is not None
    assert await hass.async_add_executor_job(Path(result.last_analyzed_image_path).is_file)


@pytest.mark.asyncio
async def test_coordinator_writes_editor_image_without_roi(
    monkeypatch, hass, tmp_path
) -> None:
    snapshot_path = tmp_path / "snapshot.jpg"

    async def _fake_capture(*args, **kwargs):
        del args, kwargs
        from PIL import Image

        image = Image.new("RGB", (10, 10), (255, 255, 255))
        image.save(snapshot_path, format="JPEG")
        return snapshot_path

    monkeypatch.setattr(
        "custom_components.vision_roi_guard.coordinator.capture_camera_snapshot", _fake_capture
    )

    coordinator = VisionRoiGuardCoordinator(
        hass=hass,
        entry_id="entry-id",
        title="Garden Guard",
        data={CONF_CAMERA_ENTITY_ID: "camera.test_camera"},
        options={
            CONF_ROI_POINTS_JSON: "",
            CONF_ACTIVE_START_TIME: time(0, 0),
            CONF_ACTIVE_STOP_TIME: time(23, 59),
        },
        backend=MockBackend({}),
    )

    result = await coordinator.async_run_analysis(force=True, save_debug=False)

    assert result.last_result == "error"
    assert result.safe_to_start is False
    assert result.last_error == "roi_missing"
    assert result.roi_editor_image_path is not None
    assert result.source_width == 10
    assert result.source_height == 10
    assert await hass.async_add_executor_job(Path(result.roi_editor_image_path).is_file)
