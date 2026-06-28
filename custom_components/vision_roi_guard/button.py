from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
            RunAnalyzeNowButton(runtime_data.coordinator, entry),
            SaveDebugSnapshotButton(runtime_data.coordinator, entry),
        ]
    )


class RunAnalyzeNowButton(VisionRoiGuardEntity, ButtonEntity):
    _attr_translation_key = "run_analyze_now"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_run_analyze_now"

    async def async_press(self) -> None:
        await self.coordinator.async_run_analysis(force=True, save_debug=False)


class SaveDebugSnapshotButton(VisionRoiGuardEntity, ButtonEntity):
    _attr_translation_key = "save_debug_snapshot"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry.title)
        self._attr_unique_id = f"{entry.entry_id}_save_debug_snapshot"

    async def async_press(self) -> None:
        await self.coordinator.async_run_analysis(force=True, save_debug=True)
