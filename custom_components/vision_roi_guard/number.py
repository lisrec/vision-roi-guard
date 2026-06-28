from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_ANALYSIS_INTERVAL_MIN, DEFAULT_ANALYSIS_INTERVAL_MIN, DOMAIN
from .entity import VisionRoiGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AnalysisIntervalNumber(hass, runtime_data.coordinator, entry)])


class AnalysisIntervalNumber(VisionRoiGuardEntity, NumberEntity):
    _attr_translation_key = "analysis_interval_min"
    _attr_native_unit_of_measurement = "min"
    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 1

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry.title)
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_analysis_interval_min"

    @property
    def native_value(self) -> int:
        return int(
            self._entry.options.get(CONF_ANALYSIS_INTERVAL_MIN, DEFAULT_ANALYSIS_INTERVAL_MIN)
        )

    async def async_set_native_value(self, value: float) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_ANALYSIS_INTERVAL_MIN] = int(value)
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.update_options({**self._entry.data, **new_options})
        self.async_write_ha_state()
