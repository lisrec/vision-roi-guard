from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import VisionRoiGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SafeToStartBinarySensor(runtime_data.coordinator, entry),
            AnalysisOkBinarySensor(runtime_data.coordinator, entry),
            CameraAvailableBinarySensor(runtime_data.coordinator, entry),
        ]
    )


class SafeToStartBinarySensor(VisionRoiGuardEntity, BinarySensorEntity):
    _attr_translation_key = "safe_to_start"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_safe_to_start"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.safe_to_start

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "last_result": self.coordinator.state.last_result,
            "last_reason": self.coordinator.state.last_reason,
            "last_seen_objects": list(self.coordinator.state.last_seen_objects),
            "last_analyzed_at": self.coordinator.state.last_analyzed_at,
            "roi_points": [
                [point.x, point.y] for point in self.coordinator.current_roi_points
            ],
            "roi_points_json": self.coordinator.current_roi_points_json,
            "source_width": self.coordinator.state.source_width,
            "source_height": self.coordinator.state.source_height,
        }


class AnalysisOkBinarySensor(VisionRoiGuardEntity, BinarySensorEntity):
    _attr_translation_key = "analysis_ok"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_analysis_ok"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.analysis_ok


class CameraAvailableBinarySensor(VisionRoiGuardEntity, BinarySensorEntity):
    _attr_translation_key = "camera_available"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_camera_available"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.camera_available
