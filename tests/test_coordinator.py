from __future__ import annotations

from datetime import time

import pytest

from custom_components.vision_roi_guard.backends.mock import MockBackend
from custom_components.vision_roi_guard.const import (
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_CAMERA_ENTITY_ID,
    CONF_ROI_POINTS_JSON,
)
from custom_components.vision_roi_guard.coordinator import VisionRoiGuardCoordinator


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
