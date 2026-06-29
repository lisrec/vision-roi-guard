from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vision_roi_guard.const import (
    CONF_ROI_POINTS_JSON,
    DOMAIN,
    SERVICE_CLEAR_STATE,
    SERVICE_REFRESH_ROI_EDITOR_IMAGE,
    SERVICE_RUN_ANALYSIS,
    SERVICE_UPDATE_ROI,
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


@pytest.mark.asyncio
async def test_refresh_roi_editor_image_service_targets_config_entry(
    hass, camera_state
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
        options={CONF_ROI_POINTS_JSON: ""},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime_data = entry.runtime_data
    runtime_data.coordinator.async_refresh_roi_editor_image = AsyncMock()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_ROI_EDITOR_IMAGE,
        {"config_entry_id": entry.entry_id},
        blocking=True,
    )

    runtime_data.coordinator.async_refresh_roi_editor_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_roi_service_updates_options(hass, camera_state) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
        options={CONF_ROI_POINTS_JSON: "[[1,1],[8,1],[8,8],[1,8]]"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime_data = entry.runtime_data
    runtime_data.coordinator.async_refresh_roi_editor_image = AsyncMock()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_ROI,
        {
            "config_entry_id": entry.entry_id,
            "points": [[2, 2], [7, 2], [7, 7], [2, 7]],
        },
        blocking=True,
    )

    assert entry.options[CONF_ROI_POINTS_JSON] == "[[2,2],[7,2],[7,7],[2,7]]"
    assert (
        runtime_data.coordinator.current_roi_points_json
        == "[[2,2],[7,2],[7,7],[2,7]]"
    )
    runtime_data.coordinator.async_refresh_roi_editor_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_roi_service_rejects_invalid_polygon(hass, camera_state) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
        options={CONF_ROI_POINTS_JSON: "[[1,1],[8,1],[8,8],[1,8]]"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_ROI,
            {
                "config_entry_id": entry.entry_id,
                "points": [[0, 0], [9, 9], [0, 9], [9, 0]],
            },
            blocking=True,
        )
