from __future__ import annotations

import struct
import zlib
from io import BytesIO

import pytest
from PIL import Image

from custom_components.vision_roi_guard.exceptions import ValidationError
from custom_components.vision_roi_guard.roi import (
    parse_roi_points_json,
    process_image,
    render_roi_editor_image,
    validate_polygon,
)


def _make_image_bytes() -> bytes:
    image = Image.new("RGB", (10, 10), (255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_parse_roi_points_json() -> None:
    points = parse_roi_points_json("[[1,2],[3,4],[5,6]]")
    assert len(points) == 3
    assert points[0].x == 1


def test_validate_polygon_rejects_self_intersection() -> None:
    points = parse_roi_points_json("[[0,0],[9,9],[0,9],[9,0]]")
    with pytest.raises(ValidationError):
        validate_polygon(points)


def test_process_image_crops_to_bounding_box() -> None:
    points = parse_roi_points_json("[[1,1],[8,1],[8,8],[1,8]]")
    result = process_image(_make_image_bytes(), points, "black", True)
    assert result.original_size == (10, 10)
    assert result.output_size == (8, 8)
    assert result.bounding_box == (1, 1, 9, 9)


@pytest.mark.parametrize("operation", ["analysis", "editor"])
@pytest.mark.parametrize("invalid_kind", ["unidentified", "truncated", "bomb"])
def test_image_decode_failures_are_sanitized(operation, invalid_kind) -> None:
    if invalid_kind == "unidentified":
        payload = b"private camera error response"
    elif invalid_kind == "truncated":
        buffer = BytesIO()
        Image.effect_noise((64, 64), 100).convert("RGB").save(buffer, format="PNG")
        payload = buffer.getvalue()[: len(buffer.getvalue()) // 2]
        # The header is valid; loading pixels, rather than identification, fails.
        with Image.open(BytesIO(payload)) as source:
            assert source.size == (64, 64)
    else:
        payload = bytearray(_make_image_bytes())
        # A real oversized PNG header triggers Pillow's guard without allocating pixels.
        payload[16:24] = struct.pack(">II", 100_000, 100_000)
        payload[29:33] = struct.pack(">I", zlib.crc32(payload[12:29]))
        payload = bytes(payload)

    points = parse_roi_points_json("[[1,1],[8,1],[8,8],[1,8]]")
    with pytest.raises(ValidationError, match="^image_invalid$"):
        if operation == "analysis":
            process_image(payload, points, "black", True)
        else:
            render_roi_editor_image(payload, points)
