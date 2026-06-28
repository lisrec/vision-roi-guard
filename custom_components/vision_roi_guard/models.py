from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class RoiPoint:
    x: int
    y: int


@dataclass(slots=True, frozen=True)
class ProcessedImage:
    image_bytes: bytes
    image_format: str
    original_size: tuple[int, int]
    output_size: tuple[int, int]
    bounding_box: tuple[int, int, int, int]
    point_count: int


@dataclass(slots=True, frozen=True)
class AnalysisResult:
    verdict: str
    reason: str
    seen_objects: tuple[str, ...] = ()
    backend_name: str = ""
    duration_sec: float = 0.0
    error_code: str | None = None
    raw_text: str | None = None


@dataclass(slots=True)
class GuardState:
    last_result: str | None = None
    last_reason: str | None = None
    last_seen_objects: tuple[str, ...] = ()
    last_analyzed_at: datetime | None = None
    last_duration_sec: float | None = None
    last_error: str | None = None
    safe_to_start: bool = False
    analysis_ok: bool = False
    camera_available: bool = False
    debug_image_path: str | None = None
    backend_name: str | None = None
    roi_point_count: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeData:
    coordinator: Any
    backend: Any
    last_processed_image: Path | None = None
