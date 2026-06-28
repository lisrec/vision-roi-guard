from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BACKEND_HTTP_ANALYZER,
    BACKEND_MOCK,
    CONF_BACKEND_TYPE,
    CONF_CAMERA_ENTITY_ID,
    DOMAIN,
)
from .exceptions import ValidationError
from .helpers.schema import build_options_schema, build_user_schema
from .helpers.validation import (
    ensure_backend_available,
    sanitize_option_payload,
    validate_camera_entity_id,
    validate_http_backend_config,
)


class VisionRoiGuardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Vision ROI Guard."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validate_camera_entity_id(self.hass, user_input[CONF_CAMERA_ENTITY_ID])
                ensure_backend_available(user_input[CONF_BACKEND_TYPE])
                sanitized_options = sanitize_option_payload(user_input)
                if user_input[CONF_BACKEND_TYPE] == BACKEND_HTTP_ANALYZER:
                    validate_http_backend_config(sanitized_options)
            except ValidationError as err:
                errors["base"] = str(err)
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_CAMERA_ENTITY_ID]}::{user_input[CONF_BACKEND_TYPE]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        "name": user_input["name"],
                        CONF_CAMERA_ENTITY_ID: user_input[CONF_CAMERA_ENTITY_ID],
                        CONF_BACKEND_TYPE: user_input[CONF_BACKEND_TYPE],
                    },
                    options={
                        key: value
                        for key, value in sanitized_options.items()
                        if key
                        not in (
                            "name",
                            CONF_CAMERA_ENTITY_ID,
                            CONF_BACKEND_TYPE,
                        )
                    },
                )

        return self.async_show_form(step_id="user", data_schema=build_user_schema(), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return VisionRoiGuardOptionsFlow(config_entry)


class VisionRoiGuardOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current = {**self._config_entry.data, **self._config_entry.options}
        if user_input is not None:
            try:
                sanitized = sanitize_option_payload(user_input)
                backend_type = self._config_entry.data.get(CONF_BACKEND_TYPE, BACKEND_MOCK)
                if backend_type != BACKEND_MOCK:
                    ensure_backend_available(backend_type)
                if backend_type == BACKEND_HTTP_ANALYZER:
                    validate_http_backend_config({**current, **sanitized})
            except ValidationError as err:
                errors["base"] = str(err)
            else:
                return self.async_create_entry(title="", data=sanitized)

        return self.async_show_form(
            step_id="init",
            data_schema=build_options_schema(current),
            errors=errors,
        )
