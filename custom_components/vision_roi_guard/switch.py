from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_ENABLED, DEFAULT_ENABLED, DOMAIN
from .entity import VisionRoiGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EnabledSwitch(hass, runtime_data.coordinator, entry)])


class EnabledSwitch(VisionRoiGuardEntity, SwitchEntity):
    _attr_translation_key = "enabled"

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry.title)
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_enabled"

    @property
    def is_on(self) -> bool:
        return self._entry.options.get(CONF_ENABLED, DEFAULT_ENABLED)

    async def async_turn_on(self, **kwargs) -> None:
        del kwargs
        await self._update_option(True)

    async def async_turn_off(self, **kwargs) -> None:
        del kwargs
        await self._update_option(False)

    async def _update_option(self, value: bool) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_ENABLED] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.update_options({**self._entry.data, **new_options})
        self.async_write_ha_state()
