from __future__ import annotations

from datetime import time

import pytest
import voluptuous_serialize
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vision_roi_guard.const import (
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_ANALYSIS_INTERVAL_MIN,
    CONF_MOCK_SEEN_OBJECTS,
    CONF_MOCK_VERDICT,
    CONF_MODEL,
    DOMAIN,
)
from custom_components.vision_roi_guard.helpers.schema import build_options_schema


@pytest.mark.asyncio
async def test_options_flow_validates_roi_json(hass: HomeAssistant, camera_state) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"roi_points_json": "not json"}
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "roi_json_invalid"}


@pytest.mark.asyncio
async def test_options_flow_normalizes_backend_options(hass: HomeAssistant, camera_state) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ACTIVE_START_TIME: "06:30:00",
            CONF_ACTIVE_STOP_TIME: time(22, 15),
            CONF_ANALYSIS_INTERVAL_MIN: 15.0,
            CONF_MODEL: "  gpt-test  ",
            CONF_MOCK_VERDICT: "BLOCKED",
            CONF_MOCK_SEEN_OBJECTS: " person, hose ,, ",
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_ACTIVE_START_TIME] == time(6, 30)
    assert result["data"][CONF_ACTIVE_STOP_TIME] == time(22, 15)
    assert result["data"][CONF_ANALYSIS_INTERVAL_MIN] == 15
    assert result["data"][CONF_MODEL] == "gpt-test"
    assert result["data"][CONF_MOCK_VERDICT] == "blocked"
    assert result["data"][CONF_MOCK_SEEN_OBJECTS] == "person,hose"


def test_options_schema_is_serializable() -> None:
    serialized = voluptuous_serialize.convert(
        build_options_schema({}), custom_serializer=cv.custom_serializer
    )
    names = {item["name"] for item in serialized}
    assert "active_start_time" in names
    assert "active_stop_time" in names
