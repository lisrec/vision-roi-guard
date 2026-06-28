from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries

from custom_components.vision_roi_guard.const import DOMAIN


@pytest.mark.asyncio
async def test_user_flow_creates_entry(hass, camera_state) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"

    with patch(
        "custom_components.vision_roi_guard.config_flow.ensure_backend_available"
    ) as mock_backend_available:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Garden Guard",
                "camera_entity_id": "camera.test_camera",
                "backend_type": "mock",
            },
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Garden Guard"
    mock_backend_available.assert_called_once_with("mock")


@pytest.mark.asyncio
async def test_user_flow_rejects_missing_camera(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Garden Guard",
            "camera_entity_id": "camera.missing",
            "backend_type": "mock",
        },
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "camera_not_found"}
