from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def camera_state(hass: HomeAssistant) -> None:
    hass.states.async_set("camera.test_camera", "idle")


@pytest.fixture
def sample_roi_json() -> str:
    return "[[1,1],[8,1],[8,8],[1,8]]"


@pytest.fixture
def tmp_snapshot_path(tmp_path: Path) -> Generator[Path, None, None]:
    yield tmp_path / "snapshot.jpg"
