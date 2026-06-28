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


@pytest.mark.asyncio
async def test_user_flow_creates_http_entry_with_options(hass, camera_state) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "http",
            "http_analyzer_url": "http://127.0.0.1:8766/analyze",
            "http_auth_type": "bearer",
            "http_bearer_token": "test-token",
            "analysis_timeout_sec": 90,
            "analyzer_profile": "mower_safety",
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"]["backend_type"] == "http"
    assert result["options"]["http_analyzer_url"] == "http://127.0.0.1:8766/analyze"
    assert result["options"]["http_bearer_token"] == "test-token"


@pytest.mark.asyncio
async def test_user_flow_rejects_http_without_url(hass, camera_state) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Garden Guard",
            "camera_entity_id": "camera.test_camera",
            "backend_type": "http",
        },
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "missing_http_analyzer_url"}
