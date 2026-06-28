from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    DEFAULT_ACTIVE_START_TIME,
    DEFAULT_ACTIVE_STOP_TIME,
    DOMAIN,
)
from .entity import VisionRoiGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ActiveStartTimeEntity(hass, runtime_data.coordinator, entry),
            ActiveStopTimeEntity(hass, runtime_data.coordinator, entry),
        ]
    )


class BaseOptionTimeEntity(VisionRoiGuardEntity, TimeEntity):
    option_key: str
    default_value: time

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry.title)
        self.hass = hass
        self._entry = entry

    @property
    def native_value(self) -> time:
        return self._entry.options.get(self.option_key, self.default_value)

    async def async_set_value(self, value: time) -> None:
        new_options = dict(self._entry.options)
        new_options[self.option_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.update_options({**self._entry.data, **new_options})
        self.async_write_ha_state()


class ActiveStartTimeEntity(BaseOptionTimeEntity):
    _attr_translation_key = "analysis_start_time"
    option_key = CONF_ACTIVE_START_TIME
    default_value = DEFAULT_ACTIVE_START_TIME

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        super().__init__(hass, coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_analysis_start_time"


class ActiveStopTimeEntity(BaseOptionTimeEntity):
    _attr_translation_key = "analysis_stop_time"
    option_key = CONF_ACTIVE_STOP_TIME
    default_value = DEFAULT_ACTIVE_STOP_TIME

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        super().__init__(hass, coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_analysis_stop_time"
