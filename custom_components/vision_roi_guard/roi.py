from __future__ import annotations

import json
from io import BytesIO

from PIL import Image, ImageDraw

from .exceptions import ValidationError
from .models import ProcessedImage, RoiPoint


def parse_roi_points_json(value: str) -> tuple[RoiPoint, ...]:
    """Parse ROI point JSON into typed points."""
    try:
        raw_points = json.loads(value)
    except json.JSONDecodeError as err:
        raise ValidationError("roi_json_invalid") from err

    if not isinstance(raw_points, list):
        raise ValidationError("roi_json_invalid")

    points: list[RoiPoint] = []
    for item in raw_points:
        if (
            not isinstance(item, list | tuple)
            or len(item) != 2
            or not all(isinstance(coord, int) for coord in item)
        ):
            raise ValidationError("roi_points_invalid")
        points.append(RoiPoint(item[0], item[1]))

    return tuple(points)


def _orientation(a: RoiPoint, b: RoiPoint, c: RoiPoint) -> int:
    value = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
    if value == 0:
        return 0
    return 1 if value > 0 else 2


def _on_segment(a: RoiPoint, b: RoiPoint, c: RoiPoint) -> bool:
    return min(a.x, c.x) <= b.x <= max(a.x, c.x) and min(a.y, c.y) <= b.y <= max(a.y, c.y)


def _segments_intersect(p1: RoiPoint, q1: RoiPoint, p2: RoiPoint, q2: RoiPoint) -> bool:
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, q1):
        return True
    if o2 == 0 and _on_segment(p1, q2, q1):
        return True
    if o3 == 0 and _on_segment(p2, p1, q2):
        return True
    if o4 == 0 and _on_segment(p2, q1, q2):
        return True
    return False


def validate_polygon(
    points: tuple[RoiPoint, ...], frame_size: tuple[int, int] | None = None
) -> None:
    """Validate a polygon ROI."""
    if len(points) < 3:
        raise ValidationError("roi_too_few_points")

    if frame_size is not None:
        width, height = frame_size
        for point in points:
            if point.x < 0 or point.y < 0 or point.x >= width or point.y >= height:
                raise ValidationError("roi_point_out_of_bounds")

    edges = list(zip(points, points[1:] + points[:1], strict=False))
    for index, (a1, a2) in enumerate(edges):
        for other_index, (b1, b2) in enumerate(edges[index + 1 :], start=index + 1):
            if abs(index - other_index) <= 1 or (index == 0 and other_index == len(edges) - 1):
                continue
            if _segments_intersect(a1, a2, b1, b2):
                raise ValidationError("roi_self_intersection")


def process_image(
    image_bytes: bytes,
    points: tuple[RoiPoint, ...],
    mask_mode: str,
    crop_to_bounding_box: bool,
) -> ProcessedImage:
    """Apply ROI masking and optional cropping to an image."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
        validate_polygon(points, image.size)
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon([(point.x, point.y) for point in points], fill=255)

        if mask_mode == "dim":
            background = image.point(lambda pixel: int(pixel * 0.2))
        else:
            background = Image.new("RGB", image.size, (0, 0, 0))

        composited = Image.composite(image, background, mask)
        bbox = mask.getbbox()
        if bbox is None:
            raise ValidationError("roi_empty_mask")
        output = composited.crop(bbox) if crop_to_bounding_box else composited

        buffer = BytesIO()
        output.save(buffer, format="PNG")
        return ProcessedImage(
            image_bytes=buffer.getvalue(),
            image_format="PNG",
            original_size=image.size,
            output_size=output.size,
            bounding_box=bbox,
            point_count=len(points),
        )


def render_roi_editor_image(
    image_bytes: bytes,
    points: tuple[RoiPoint, ...],
) -> tuple[bytes, tuple[int, int]]:
    """Draw the ROI polygon over a full-frame image for editor use."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGBA")

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if points:
            validate_polygon(points, image.size)
            xy = [(point.x, point.y) for point in points]
            draw.polygon(xy, fill=(0, 172, 193, 64))
            draw.line(xy + [xy[0]], fill=(0, 172, 193, 230), width=3)

            radius = 9
            for index, point in enumerate(points, start=1):
                x = point.x
                y = point.y
                draw.ellipse(
                    (x - radius, y - radius, x + radius, y + radius),
                    fill=(255, 193, 7, 240),
                    outline=(38, 50, 56, 255),
                    width=2,
                )
                draw.text(
                    (x + radius + 3, y - radius - 2),
                    str(index),
                    fill=(255, 255, 255, 255),
                )

        output = Image.alpha_composite(image, overlay).convert("RGB")
        buffer = BytesIO()
        output.save(buffer, format="PNG")
        return buffer.getvalue(), image.size
