from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import AnalysisResult


class VisionBackend(ABC):
    """Backend interface for vision analysis providers."""

    backend_name: str

    @abstractmethod
    async def validate(self) -> None:
        """Validate that the backend can be used."""

    @abstractmethod
    async def healthcheck(self) -> None:
        """Perform a lightweight health check."""

    @abstractmethod
    async def analyze(
        self, image_path: str, prompt_context: dict[str, Any], timeout_sec: int
    ) -> AnalysisResult:
        """Analyze an ROI-processed image."""
