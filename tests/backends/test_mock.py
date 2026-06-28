from __future__ import annotations

import pytest

from custom_components.vision_roi_guard.backends.mock import MockBackend


@pytest.mark.asyncio
async def test_mock_backend_fixed_mode() -> None:
    backend = MockBackend({"mock_verdict": "blocked", "mock_reason": "person_detected"})
    result = await backend.analyze("anything.png", {}, 10)
    assert result.verdict == "blocked"
    assert result.reason == "person_detected"


@pytest.mark.asyncio
async def test_mock_backend_filename_mode() -> None:
    backend = MockBackend({"mock_mode": "filename_keyword"})
    result = await backend.analyze("snapshot_blocked.png", {}, 10)
    assert result.verdict == "blocked"
    assert result.seen_objects == ("person",)
