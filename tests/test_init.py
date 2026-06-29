from __future__ import annotations

import pytest
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.setup import async_setup_component
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
    assert state.attributes["roi_points"] == [[1, 1], [8, 1], [8, 8], [1, 8]]
    assert state.attributes["roi_points_json"] == "[[1,1],[8,1],[8,8],[1,8]]"
    image_state = hass.states.get("image.garden_guard_last_analyzed_image")
    assert image_state is not None
    editor_image_state = hass.states.get("image.garden_guard_roi_editor_image")
    assert editor_image_state is not None


@pytest.mark.asyncio
async def test_setup_registers_roi_editor_panel(hass) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    panel = hass.data[DATA_PANELS]["vision-roi-guard"]
    assert panel.component_name == "custom"
    assert panel.sidebar_title == "Vision ROI Guard"
    assert panel.config["_panel_custom"]["module_url"] == (
        "/vision_roi_guard_static/roi-editor-panel.js"
    )


@pytest.mark.asyncio
async def test_websocket_lists_roi_editor_entries(
    hass, camera_state, hass_ws_client
) -> None:
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

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "vision_roi_guard/list_entries"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["entries"] == [
        {
            "config_entry_id": entry.entry_id,
            "title": "Garden Guard",
            "entities": {
                "safe_to_start": "binary_sensor.garden_guard_safe_to_start",
                "roi_editor_image": "image.garden_guard_roi_editor_image",
                "last_analyzed_image": "image.garden_guard_last_analyzed_image",
            },
            "roi_points": [[1, 1], [8, 1], [8, 8], [1, 8]],
            "roi_points_json": "[[1,1],[8,1],[8,8],[1,8]]",
            "source_width": None,
            "source_height": None,
        }
    ]
