from __future__ import annotations

from pathlib import Path

from homeassistant.components.image import ImageEntity
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
    async_add_entities([LastAnalyzedImageEntity(hass, runtime_data.coordinator, entry)])


class LastAnalyzedImageEntity(VisionRoiGuardEntity, ImageEntity):
    _attr_translation_key = "last_analyzed_image"
    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        VisionRoiGuardEntity.__init__(self, coordinator, entry.title)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"{entry.entry_id}_last_analyzed_image"

    @property
    def image_last_updated(self):
        return self.coordinator.state.last_analyzed_at

    def image(self) -> bytes | None:
        image_path = self.coordinator.state.last_analyzed_image_path
        if image_path is None:
            return None
        path = Path(image_path)
        if not path.is_file():
            return None
        return path.read_bytes()
