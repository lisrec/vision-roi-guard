from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VisionRoiGuardCoordinator


class VisionRoiGuardEntity(CoordinatorEntity[VisionRoiGuardCoordinator]):
    """Base class for integration entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VisionRoiGuardCoordinator, entry_title: str) -> None:
        super().__init__(coordinator)
        self._entry_title = entry_title

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry_id)},
            name=self._entry_title,
            manufacturer="Vision ROI Guard",
            model="ROI Safety Analyzer",
        )
