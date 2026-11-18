"""Regress real Pillow compressed PNG metadata rejection, not mocked errors."""

import struct
import zlib
from io import BytesIO

import pytest
from PIL import Image

from custom_components.vision_roi_guard.backends.mock import MockBackend
from custom_components.vision_roi_guard.const import CONF_CAMERA_ENTITY_ID, CONF_ROI_POINTS_JSON
from custom_components.vision_roi_guard.coordinator import VisionRoiGuardCoordinator
from custom_components.vision_roi_guard.exceptions import ValidationError
from custom_components.vision_roi_guard.roi import (
    parse_roi_points_json,
    process_image,
    render_roi_editor_image,
)


def _metadata_limit_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    base = buffer.getvalue()
    # Valid zTXt structure; expansion exceeds Pillow's 1 MiB MAX_TEXT_CHUNK.
    data = b"camera\0\0" + zlib.compress(b"x" * (1024 * 1024 + 1))
    tag = b"zTXt"
    chunk = struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return base[:33] + chunk + base[33:]


@pytest.mark.parametrize("operation", ["analysis", "editor"])
def test_metadata_decoder_error_is_sanitized(operation) -> None:
    points = parse_roi_points_json("[[1,1],[8,1],[8,8],[1,8]]")
    with pytest.raises(ValidationError, match="^image_invalid$"):
        if operation == "analysis":
            process_image(_metadata_limit_png(), points, "black", True)
        else:
            render_roi_editor_image(_metadata_limit_png(), points)


@pytest.mark.asyncio
async def test_metadata_error_revokes_prior_safe(monkeypatch, hass, tmp_path) -> None:
    snapshot = tmp_path / "snapshot.png"
    invalid = False

    async def capture(*args, **kwargs):
        del args, kwargs
        if invalid:
            snapshot.write_bytes(_metadata_limit_png())
        else:
            Image.new("RGB", (10, 10), "white").save(snapshot, format="PNG")
        return snapshot

    monkeypatch.setattr(
        "custom_components.vision_roi_guard.coordinator.capture_camera_snapshot", capture
    )
    coordinator = VisionRoiGuardCoordinator(
        hass,
        "metadata-rejection",
        "Test Guard",
        {CONF_CAMERA_ENTITY_ID: "camera.test_camera"},
        {CONF_ROI_POINTS_JSON: "[[1,1],[8,1],[8,8],[1,8]]"},
        MockBackend({}),
    )
    assert (
        await coordinator.async_run_analysis(force=True, save_debug=False)
    ).safe_to_start is True
    invalid = True

    result = await coordinator.async_run_analysis(force=True, save_debug=False)

    assert result.safe_to_start is False
    assert result.analysis_ok is False
    assert result.last_result == "error"
    assert result.last_error == "image_invalid"
    assert not snapshot.exists()
