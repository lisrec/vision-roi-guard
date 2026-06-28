from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from ..const import (
    BACKEND_TYPES,
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_ANALYSIS_INTERVAL_MIN,
    CONF_ANALYSIS_TIMEOUT_SEC,
    CONF_BACKEND_TYPE,
    CONF_CAMERA_ENTITY_ID,
    CONF_CLI_TIMEOUT_SEC,
    CONF_CROP_TO_BOUNDING_BOX,
    CONF_DEBUG_RETENTION_COUNT,
    CONF_ENABLED,
    CONF_MASK_OUTSIDE_ROI_MODE,
    CONF_MAX_OUTPUT_TOKENS,
    CONF_MOCK_MODE,
    CONF_MOCK_REASON,
    CONF_MOCK_SEEN_OBJECTS,
    CONF_MOCK_VERDICT,
    CONF_MODEL,
    CONF_PROMPT_TEMPLATE,
    CONF_ROI_POINTS_JSON,
    CONF_SAVE_DEBUG_IMAGES,
    CONF_UNCERTAIN_ON_UNKNOWN_OBJECTS,
    DEFAULT_ACTIVE_START_TIME,
    DEFAULT_ACTIVE_STOP_TIME,
    DEFAULT_ANALYSIS_INTERVAL_MIN,
    DEFAULT_ANALYSIS_TIMEOUT_SEC,
    DEFAULT_CLI_TIMEOUT_SEC,
    DEFAULT_CROP_TO_BOUNDING_BOX,
    DEFAULT_DEBUG_RETENTION_COUNT,
    DEFAULT_ENABLED,
    DEFAULT_MASK_OUTSIDE_ROI_MODE,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MOCK_MODE,
    DEFAULT_MOCK_REASON,
    DEFAULT_MOCK_SEEN_OBJECTS,
    DEFAULT_MOCK_VERDICT,
    DEFAULT_PROMPT_TEMPLATE,
    DEFAULT_SAVE_DEBUG_IMAGES,
    DEFAULT_UNCERTAIN_ON_UNKNOWN_OBJECTS,
)

MASK_MODE_OPTIONS = ("black", "dim")
MOCK_MODE_OPTIONS = ("fixed", "filename_keyword")


def build_user_schema(defaults: dict[str, object] | None = None) -> vol.Schema:
    """Build the initial config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", "")): str,
            vol.Required(
                CONF_CAMERA_ENTITY_ID, default=defaults.get(CONF_CAMERA_ENTITY_ID, "")
            ): str,
            vol.Required(
                CONF_BACKEND_TYPE,
                default=defaults.get(CONF_BACKEND_TYPE, BACKEND_TYPES[0]),
            ): SelectSelector(SelectSelectorConfig(options=list(BACKEND_TYPES))),
        }
    )


def build_options_schema(current: dict[str, object]) -> vol.Schema:
    """Build the options flow schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_ENABLED, default=current.get(CONF_ENABLED, DEFAULT_ENABLED)
            ): BooleanSelector(),
            vol.Optional(
                CONF_ACTIVE_START_TIME,
                default=current.get(CONF_ACTIVE_START_TIME, DEFAULT_ACTIVE_START_TIME),
            ): cv.time,
            vol.Optional(
                CONF_ACTIVE_STOP_TIME,
                default=current.get(CONF_ACTIVE_STOP_TIME, DEFAULT_ACTIVE_STOP_TIME),
            ): cv.time,
            vol.Optional(
                CONF_ANALYSIS_INTERVAL_MIN,
                default=current.get(CONF_ANALYSIS_INTERVAL_MIN, DEFAULT_ANALYSIS_INTERVAL_MIN),
            ): NumberSelector(NumberSelectorConfig(min=0, max=1440, mode="box")),
            vol.Optional(
                CONF_ANALYSIS_TIMEOUT_SEC,
                default=current.get(CONF_ANALYSIS_TIMEOUT_SEC, DEFAULT_ANALYSIS_TIMEOUT_SEC),
            ): NumberSelector(NumberSelectorConfig(min=5, max=600, mode="box")),
            vol.Optional(
                CONF_SAVE_DEBUG_IMAGES,
                default=current.get(CONF_SAVE_DEBUG_IMAGES, DEFAULT_SAVE_DEBUG_IMAGES),
            ): BooleanSelector(),
            vol.Optional(
                CONF_DEBUG_RETENTION_COUNT,
                default=current.get(CONF_DEBUG_RETENTION_COUNT, DEFAULT_DEBUG_RETENTION_COUNT),
            ): NumberSelector(NumberSelectorConfig(min=1, max=500, mode="box")),
            vol.Optional(
                CONF_MASK_OUTSIDE_ROI_MODE,
                default=current.get(CONF_MASK_OUTSIDE_ROI_MODE, DEFAULT_MASK_OUTSIDE_ROI_MODE),
            ): SelectSelector(SelectSelectorConfig(options=list(MASK_MODE_OPTIONS))),
            vol.Optional(
                CONF_CROP_TO_BOUNDING_BOX,
                default=current.get(CONF_CROP_TO_BOUNDING_BOX, DEFAULT_CROP_TO_BOUNDING_BOX),
            ): BooleanSelector(),
            vol.Optional(
                CONF_ROI_POINTS_JSON, default=current.get(CONF_ROI_POINTS_JSON, "")
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Optional(CONF_MODEL, default=current.get(CONF_MODEL, "")): TextSelector(),
            vol.Optional(
                CONF_PROMPT_TEMPLATE,
                default=current.get(CONF_PROMPT_TEMPLATE, DEFAULT_PROMPT_TEMPLATE),
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Optional(
                CONF_CLI_TIMEOUT_SEC,
                default=current.get(CONF_CLI_TIMEOUT_SEC, DEFAULT_CLI_TIMEOUT_SEC),
            ): NumberSelector(NumberSelectorConfig(min=5, max=600, mode="box")),
            vol.Optional(
                CONF_MAX_OUTPUT_TOKENS,
                default=current.get(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS),
            ): NumberSelector(NumberSelectorConfig(min=1, max=4096, mode="box")),
            vol.Optional(
                CONF_UNCERTAIN_ON_UNKNOWN_OBJECTS,
                default=current.get(
                    CONF_UNCERTAIN_ON_UNKNOWN_OBJECTS,
                    DEFAULT_UNCERTAIN_ON_UNKNOWN_OBJECTS,
                ),
            ): BooleanSelector(),
            vol.Optional(
                CONF_MOCK_MODE, default=current.get(CONF_MOCK_MODE, DEFAULT_MOCK_MODE)
            ): SelectSelector(SelectSelectorConfig(options=list(MOCK_MODE_OPTIONS))),
            vol.Optional(
                CONF_MOCK_VERDICT,
                default=current.get(CONF_MOCK_VERDICT, DEFAULT_MOCK_VERDICT),
            ): TextSelector(),
            vol.Optional(
                CONF_MOCK_REASON,
                default=current.get(CONF_MOCK_REASON, DEFAULT_MOCK_REASON),
            ): TextSelector(),
            vol.Optional(
                CONF_MOCK_SEEN_OBJECTS,
                default=current.get(CONF_MOCK_SEEN_OBJECTS, DEFAULT_MOCK_SEEN_OBJECTS),
            ): TextSelector(),
        }
    )
