from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vision_roi_guard.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry(hass, camera_state) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
        options={"roi_points_json": "[[1,1],[8,1],[8,8],[1,8]]"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.garden_guard_safe_to_start")
    assert state is not None
    image_state = hass.states.get("image.garden_guard_last_analyzed_image")
    assert image_state is not None
