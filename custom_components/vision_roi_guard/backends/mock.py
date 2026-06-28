from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from ..const import (
    DEFAULT_MOCK_MODE,
    DEFAULT_MOCK_REASON,
    DEFAULT_MOCK_SEEN_OBJECTS,
    DEFAULT_MOCK_VERDICT,
)
from ..helpers.validation import csv_to_tuple, validate_verdict
from ..models import AnalysisResult
from .base import VisionBackend


class MockBackend(VisionBackend):
    """Deterministic backend for tests and offline demos."""

    backend_name = "mock"

    def __init__(self, options: dict[str, Any]) -> None:
        self._mode = options.get("mock_mode", DEFAULT_MOCK_MODE)
        self._verdict = validate_verdict(options.get("mock_verdict", DEFAULT_MOCK_VERDICT))
        self._reason = options.get("mock_reason", DEFAULT_MOCK_REASON)
        self._seen_objects = csv_to_tuple(
            options.get("mock_seen_objects", DEFAULT_MOCK_SEEN_OBJECTS)
        )

    async def validate(self) -> None:
        """Validate mock backend configuration."""

    async def healthcheck(self) -> None:
        """Mock backend is always healthy."""

    async def analyze(
        self, image_path: str, prompt_context: dict[str, Any], timeout_sec: int
    ) -> AnalysisResult:
        """Return a deterministic analysis result."""
        del prompt_context, timeout_sec
        started = perf_counter()
        verdict = self._verdict
        reason = self._reason
        seen_objects = self._seen_objects

        if self._mode == "filename_keyword":
            name = Path(image_path).name.lower()
            if "blocked" in name:
                verdict = "blocked"
                reason = "mock_filename_blocked"
                seen_objects = ("person",)
            elif "uncertain" in name:
                verdict = "uncertain"
                reason = "mock_filename_uncertain"
                seen_objects = ("unknown_object",)
            else:
                verdict = "safe"
                reason = "mock_filename_safe"
                seen_objects = ()

        return AnalysisResult(
            verdict=verdict,
            reason=reason,
            seen_objects=seen_objects,
            backend_name=self.backend_name,
            duration_sec=perf_counter() - started,
        )
