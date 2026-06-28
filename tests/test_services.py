from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vision_roi_guard.const import (
    DOMAIN,
    SERVICE_CLEAR_STATE,
    SERVICE_RUN_ANALYSIS,
)


@pytest.mark.asyncio
async def test_services_target_config_entry(hass, camera_state) -> None:
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

    runtime_data = entry.runtime_data
    runtime_data.coordinator.async_run_analysis = AsyncMock()
    runtime_data.coordinator.async_clear_state = AsyncMock()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RUN_ANALYSIS,
        {"config_entry_id": entry.entry_id, "force": True, "save_debug": True},
        blocking=True,
    )
    runtime_data.coordinator.async_run_analysis.assert_awaited_once_with(
        force=True, save_debug=True
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_STATE,
        {"config_entry_id": entry.entry_id},
        blocking=True,
    )
    runtime_data.coordinator.async_clear_state.assert_awaited_once()
