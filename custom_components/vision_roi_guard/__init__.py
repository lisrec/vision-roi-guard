from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .backends import create_backend
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_FORCE,
    ATTR_SAVE_DEBUG,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_STATE,
    SERVICE_RUN_ANALYSIS,
)
from .coordinator import VisionRoiGuardCoordinator
from .models import RuntimeData

LOGGER = logging.getLogger(__name__)


VisionRoiGuardConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})

    async def async_run_analysis(call: ServiceCall) -> None:
        coordinators = await _resolve_target_coordinators(hass, call)
        for coordinator in coordinators:
            await coordinator.async_run_analysis(
                force=call.data.get(ATTR_FORCE, False),
                save_debug=call.data.get(ATTR_SAVE_DEBUG, False),
            )

    async def async_clear_state(call: ServiceCall) -> None:
        coordinators = await _resolve_target_coordinators(hass, call)
        for coordinator in coordinators:
            await coordinator.async_clear_state()

    if not hass.services.has_service(DOMAIN, SERVICE_RUN_ANALYSIS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RUN_ANALYSIS,
            async_run_analysis,
            schema=vol.Schema(
                {
                    vol.Optional("entity_id"): vol.Any(str, [str]),
                    vol.Optional(ATTR_CONFIG_ENTRY_ID): str,
                    vol.Optional(ATTR_FORCE, default=False): bool,
                    vol.Optional(ATTR_SAVE_DEBUG, default=False): bool,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_STATE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_STATE,
            async_clear_state,
            schema=vol.Schema(
                {
                    vol.Optional("entity_id"): vol.Any(str, [str]),
                    vol.Optional(ATTR_CONFIG_ENTRY_ID): str,
                }
            ),
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> bool:
    """Set up a config entry."""
    merged_options = {**entry.data, **entry.options}
    backend = create_backend(entry.data["backend_type"], merged_options)
    await backend.validate()

    coordinator = VisionRoiGuardCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        title=entry.title,
        data=dict(entry.data),
        options=merged_options,
        backend=backend,
    )
    entry.runtime_data = RuntimeData(coordinator=coordinator, backend=backend)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    hass.data[DOMAIN][entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _resolve_target_coordinators(
    hass: HomeAssistant, call: ServiceCall
) -> list[VisionRoiGuardCoordinator]:
    if config_entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        runtime_data = hass.data[DOMAIN].get(config_entry_id)
        return [runtime_data.coordinator] if runtime_data else []

    entity_ids = call.data.get("entity_id")
    if entity_ids:
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        entity_registry = er.async_get(hass)
        coordinators: list[VisionRoiGuardCoordinator] = []
        for entity_id in entity_ids:
            registry_entry = entity_registry.async_get(entity_id)
            if registry_entry is None:
                continue
            runtime_data = hass.data[DOMAIN].get(registry_entry.config_entry_id)
            if runtime_data is not None:
                coordinators.append(runtime_data.coordinator)
        return coordinators

    return [runtime_data.coordinator for runtime_data in hass.data[DOMAIN].values()]
