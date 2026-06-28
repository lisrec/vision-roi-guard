from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
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
            LastResultSensor(runtime_data.coordinator, entry),
            LastReasonSensor(runtime_data.coordinator, entry),
            LastSeenObjectsSensor(runtime_data.coordinator, entry),
            LastTimeAnalyzedSensor(runtime_data.coordinator, entry),
            LastDurationSensor(runtime_data.coordinator, entry),
            LastErrorSensor(runtime_data.coordinator, entry),
        ]
    )


class BaseStateSensor(VisionRoiGuardEntity, SensorEntity):
    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        debug_path = self.coordinator.state.debug_image_path
        if debug_path is None:
            return None
        return {"debug_image_path": debug_path}


class LastResultSensor(BaseStateSensor):
    _attr_translation_key = "last_result"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_result"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.state.last_result


class LastReasonSensor(BaseStateSensor):
    _attr_translation_key = "last_reason"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_reason"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.state.last_reason


class LastSeenObjectsSensor(BaseStateSensor):
    _attr_translation_key = "last_seen_objects"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_seen_objects"

    @property
    def native_value(self) -> str:
        return "; ".join(self.coordinator.state.last_seen_objects)


class LastTimeAnalyzedSensor(BaseStateSensor):
    _attr_translation_key = "last_time_analyzed"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_time_analyzed"

    @property
    def native_value(self):
        return self.coordinator.state.last_analyzed_at


class LastDurationSensor(BaseStateSensor):
    _attr_translation_key = "last_duration_sec"
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_duration_sec"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.state.last_duration_sec


class LastErrorSensor(BaseStateSensor):
    _attr_translation_key = "last_error"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_last_error"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.state.last_error
