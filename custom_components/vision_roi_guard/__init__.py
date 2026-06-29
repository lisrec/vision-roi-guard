from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .backends import create_backend
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_FORCE,
    ATTR_POINTS,
    ATTR_ROI_POINTS_JSON,
    ATTR_SAVE_DEBUG,
    CONF_ROI_POINTS_JSON,
    DOMAIN,
    NAME,
    PLATFORMS,
    SERVICE_CLEAR_STATE,
    SERVICE_REFRESH_ROI_EDITOR_IMAGE,
    SERVICE_RUN_ANALYSIS,
    SERVICE_UPDATE_ROI,
)
from .coordinator import VisionRoiGuardCoordinator
from .exceptions import CameraSnapshotError, ValidationError
from .models import RuntimeData
from .roi import parse_roi_points_json, validate_polygon

LOGGER = logging.getLogger(__name__)


VisionRoiGuardConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    if hass.http is not None:
        static_dir = Path(__file__).parent / "www"
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/vision_roi_guard_static/roi-editor-card.js",
                    str(static_dir / "roi-editor-card.js"),
                    cache_headers=False,
                ),
                StaticPathConfig(
                    "/vision_roi_guard_static/roi-editor-panel.js",
                    str(static_dir / "roi-editor-panel.js"),
                    cache_headers=False,
                ),
            ]
        )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="vision-roi-guard",
        webcomponent_name="vision-roi-guard-panel",
        sidebar_title=NAME,
        sidebar_icon="mdi:vector-polygon",
        module_url="/vision_roi_guard_static/roi-editor-panel.js",
        config={"domain": DOMAIN},
        config_panel_domain=DOMAIN,
    )
    websocket_api.async_register_command(hass, websocket_list_entries)

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

    async def async_update_roi(call: ServiceCall) -> None:
        coordinators = await _resolve_target_coordinators(hass, call)
        roi_points_json = _roi_points_json_from_service_call(call.data)
        for coordinator in coordinators:
            try:
                points = parse_roi_points_json(roi_points_json)
                validate_polygon(points, coordinator.known_frame_size)
            except ValidationError as err:
                raise ServiceValidationError(
                    f"Invalid ROI polygon: {err}"
                ) from err

            runtime_data = hass.data[DOMAIN].get(coordinator.entry_id)
            entry = _entry_for_coordinator(hass, coordinator)
            if runtime_data is None or entry is None:
                continue

            new_options = dict(entry.options)
            new_options[CONF_ROI_POINTS_JSON] = roi_points_json
            hass.config_entries.async_update_entry(entry, options=new_options)
            coordinator.update_options({**entry.data, **new_options})

            try:
                await coordinator.async_refresh_roi_editor_image()
            except (CameraSnapshotError, ValidationError) as err:
                LOGGER.debug("Could not refresh ROI editor image after save: %s", err)

    async def async_refresh_roi_editor_image(call: ServiceCall) -> None:
        coordinators = await _resolve_target_coordinators(hass, call)
        for coordinator in coordinators:
            try:
                await coordinator.async_refresh_roi_editor_image()
            except (CameraSnapshotError, ValidationError) as err:
                raise ServiceValidationError(
                    f"Could not refresh ROI editor image: {err}"
                ) from err

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
    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_ROI):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_ROI,
            async_update_roi,
            schema=vol.Schema(
                {
                    vol.Optional("entity_id"): vol.Any(str, [str]),
                    vol.Optional(ATTR_CONFIG_ENTRY_ID): str,
                    vol.Optional(ATTR_ROI_POINTS_JSON): str,
                    vol.Optional(ATTR_POINTS): list,
                }
            ),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_ROI_EDITOR_IMAGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_ROI_EDITOR_IMAGE,
            async_refresh_roi_editor_image,
            schema=vol.Schema(
                {
                    vol.Optional("entity_id"): vol.Any(str, [str]),
                    vol.Optional(ATTR_CONFIG_ENTRY_ID): str,
                }
            ),
        )
    return True


@callback
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_entries"})
def websocket_list_entries(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List Vision ROI Guard entries for the integration panel."""
    entity_registry = er.async_get(hass)
    entries: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        runtime_data = hass.data[DOMAIN].get(entry.entry_id)
        coordinator = runtime_data.coordinator if runtime_data is not None else None
        entities = _entity_ids_for_entry(entity_registry, entry.entry_id)
        state = coordinator.state if coordinator is not None else None
        points = (
            [[point.x, point.y] for point in coordinator.current_roi_points]
            if coordinator is not None
            else []
        )
        entries.append(
            {
                "config_entry_id": entry.entry_id,
                "title": entry.title,
                "entities": entities,
                "roi_points": points,
                "roi_points_json": (
                    coordinator.current_roi_points_json if coordinator is not None else ""
                ),
                "source_width": state.source_width if state is not None else None,
                "source_height": state.source_height if state is not None else None,
            }
        )
    connection.send_result(msg["id"], {"entries": entries})


def _entity_ids_for_entry(
    entity_registry: er.EntityRegistry, config_entry_id: str
) -> dict[str, str | None]:
    entities: dict[str, str | None] = {
        "safe_to_start": None,
        "roi_editor_image": None,
        "last_analyzed_image": None,
    }
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, config_entry_id
    ):
        unique_id = registry_entry.unique_id
        if unique_id.endswith("_safe_to_start"):
            entities["safe_to_start"] = registry_entry.entity_id
        elif unique_id.endswith("_roi_editor_image"):
            entities["roi_editor_image"] = registry_entry.entity_id
        elif unique_id.endswith("_last_analyzed_image"):
            entities["last_analyzed_image"] = registry_entry.entity_id
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> bool:
    """Set up a config entry."""
    merged_options = {**entry.data, **entry.options}
    backend = create_backend(entry.data["backend_type"], merged_options, hass)
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
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    hass.data[DOMAIN][entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: VisionRoiGuardConfigEntry) -> None:
    """Apply option changes without unloading/recreating all entities."""
    runtime_data = hass.data[DOMAIN].get(entry.entry_id)
    if runtime_data is None:
        return
    merged_options = {**entry.data, **entry.options}
    backend = create_backend(entry.data["backend_type"], merged_options, hass)
    await backend.validate()
    runtime_data.backend = backend
    runtime_data.coordinator.update_backend(backend)
    runtime_data.coordinator.update_options(merged_options)


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


def _roi_points_json_from_service_call(data: dict[str, Any]) -> str:
    roi_points_json = data.get(ATTR_ROI_POINTS_JSON)
    points = data.get(ATTR_POINTS)
    if roi_points_json and points is not None:
        raise ServiceValidationError("Use either roi_points_json or points, not both")
    if roi_points_json:
        return roi_points_json
    if points is None:
        raise ServiceValidationError("Either roi_points_json or points is required")
    if not isinstance(points, list):
        raise ServiceValidationError("points must be a list of [x, y] pairs")

    normalized_points: list[list[int]] = []
    for item in points:
        if (
            not isinstance(item, list | tuple)
            or len(item) != 2
            or not all(isinstance(coord, int) for coord in item)
        ):
            raise ServiceValidationError("points must be a list of integer [x, y] pairs")
        normalized_points.append([item[0], item[1]])
    return json.dumps(normalized_points, separators=(",", ":"))


def _entry_for_coordinator(
    hass: HomeAssistant, coordinator: VisionRoiGuardCoordinator
) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == coordinator.entry_id:
            return entry
    return None
