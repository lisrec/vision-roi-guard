from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vision_roi_guard.const import DOMAIN
from custom_components.vision_roi_guard.diagnostics import async_get_config_entry_diagnostics
from custom_components.vision_roi_guard.models import GuardState, RuntimeData


class _Coordinator:
    def __init__(self) -> None:
        self.state = GuardState(
            last_result="safe",
            last_reason="empty_lawn",
            debug_image_path="/private/path/image.png",
            backend_name="mock",
            roi_point_count=4,
        )


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_values(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garden Guard",
        data={
            "camera_entity_id": "camera.test_camera",
            "backend_type": "mock",
            "api_key": "secret-value",
        },
        options={
            "roi_points_json": "[[1,2],[3,4],[5,6]]",
            "nested": {"access_token": "token-value"},
        },
    )
    entry.runtime_data = RuntimeData(coordinator=_Coordinator(), backend=None)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["entry"]["data"]["camera_entity_id"] == "[redacted]"
    assert diagnostics["entry"]["data"]["api_key"] == "[redacted]"
    assert diagnostics["entry"]["options"]["roi_points_json"] == "[redacted]"
    assert diagnostics["entry"]["options"]["nested"]["access_token"] == "[redacted]"
    assert diagnostics["state"]["debug_image_path"] == "[redacted]"
