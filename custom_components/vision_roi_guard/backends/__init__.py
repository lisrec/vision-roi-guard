from __future__ import annotations

from typing import Any

from ..const import BACKEND_CODEX_CLI, BACKEND_MOCK
from .base import VisionBackend
from .codex_cli import CodexCliBackend
from .mock import MockBackend


def create_backend(backend_type: str, options: dict[str, Any]) -> VisionBackend:
    """Create a backend instance from config."""
    if backend_type == BACKEND_CODEX_CLI:
        return CodexCliBackend(options)
    if backend_type == BACKEND_MOCK:
        return MockBackend(options)
    raise ValueError(f"Unsupported backend type: {backend_type}")
