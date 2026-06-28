from __future__ import annotations

from datetime import time
from typing import Final

DOMAIN: Final = "vision_roi_guard"
NAME: Final = "Vision ROI Guard"

PLATFORMS: Final = (
    "binary_sensor",
    "sensor",
    "button",
    "switch",
    "number",
    "time",
)

CONF_CAMERA_ENTITY_ID: Final = "camera_entity_id"
CONF_BACKEND_TYPE: Final = "backend_type"
CONF_ENABLED: Final = "enabled"
CONF_ACTIVE_START_TIME: Final = "active_start_time"
CONF_ACTIVE_STOP_TIME: Final = "active_stop_time"
CONF_ANALYSIS_INTERVAL_MIN: Final = "analysis_interval_min"
CONF_ANALYSIS_TIMEOUT_SEC: Final = "analysis_timeout_sec"
CONF_SAVE_DEBUG_IMAGES: Final = "save_debug_images"
CONF_DEBUG_RETENTION_COUNT: Final = "debug_retention_count"
CONF_MASK_OUTSIDE_ROI_MODE: Final = "mask_outside_roi_mode"
CONF_CROP_TO_BOUNDING_BOX: Final = "crop_to_bounding_box"
CONF_ROI_POINTS_JSON: Final = "roi_points_json"
CONF_PROMPT_TEMPLATE: Final = "prompt_template"
CONF_CLI_TIMEOUT_SEC: Final = "cli_timeout_sec"
CONF_MODEL: Final = "model"
CONF_MAX_OUTPUT_TOKENS: Final = "max_output_tokens"
CONF_BLOCKED_LABELS: Final = "blocked_labels"
CONF_SAFE_LABELS: Final = "safe_labels"
CONF_UNCERTAIN_ON_UNKNOWN_OBJECTS: Final = "uncertain_on_unknown_objects"
CONF_MOCK_MODE: Final = "mock_mode"
CONF_MOCK_VERDICT: Final = "mock_verdict"
CONF_MOCK_REASON: Final = "mock_reason"
CONF_MOCK_SEEN_OBJECTS: Final = "mock_seen_objects"
CONF_HTTP_ANALYZER_URL: Final = "http_analyzer_url"
CONF_HTTP_AUTH_TYPE: Final = "http_auth_type"
CONF_HTTP_BEARER_TOKEN: Final = "http_bearer_token"
CONF_ANALYZER_PROFILE: Final = "analyzer_profile"

BACKEND_CODEX_CLI: Final = "codex_cli"
BACKEND_MOCK: Final = "mock"
BACKEND_HTTP_ANALYZER: Final = "http"
BACKEND_TYPES: Final = (BACKEND_MOCK, BACKEND_HTTP_ANALYZER, BACKEND_CODEX_CLI)

HTTP_AUTH_NONE: Final = "none"
HTTP_AUTH_BEARER: Final = "bearer"
HTTP_AUTH_TYPES: Final = (HTTP_AUTH_NONE, HTTP_AUTH_BEARER)

VERDICT_SAFE: Final = "safe"
VERDICT_BLOCKED: Final = "blocked"
VERDICT_UNCERTAIN: Final = "uncertain"
VERDICT_ERROR: Final = "error"
VALID_VERDICTS: Final = (
    VERDICT_SAFE,
    VERDICT_BLOCKED,
    VERDICT_UNCERTAIN,
    VERDICT_ERROR,
)

DEFAULT_ENABLED: Final = True
DEFAULT_ACTIVE_START_TIME: Final = time(0, 0)
DEFAULT_ACTIVE_STOP_TIME: Final = time(23, 59)
DEFAULT_ANALYSIS_INTERVAL_MIN: Final = 60
DEFAULT_ANALYSIS_TIMEOUT_SEC: Final = 120
DEFAULT_SAVE_DEBUG_IMAGES: Final = False
DEFAULT_DEBUG_RETENTION_COUNT: Final = 20
DEFAULT_MASK_OUTSIDE_ROI_MODE: Final = "black"
DEFAULT_CROP_TO_BOUNDING_BOX: Final = True
DEFAULT_PROMPT_TEMPLATE: Final = (
    "Analyze only the visible contents of this ROI image for mower safety. "
    "Return strict compact JSON with keys verdict, reason, and seen_objects. "
    "verdict must be one of safe, blocked, uncertain. "
    "reason must be a short snake_case string. "
    "seen_objects must be a short list of snake_case strings."
)
DEFAULT_CLI_TIMEOUT_SEC: Final = 120
DEFAULT_MAX_OUTPUT_TOKENS: Final = 200
DEFAULT_BLOCKED_LABELS: Final = "person,child,animal,ball,hose,toy"
DEFAULT_SAFE_LABELS: Final = "empty_lawn,grass_only"
DEFAULT_UNCERTAIN_ON_UNKNOWN_OBJECTS: Final = True
DEFAULT_MOCK_MODE: Final = "fixed"
DEFAULT_MOCK_VERDICT: Final = VERDICT_SAFE
DEFAULT_MOCK_REASON: Final = "mock_safe"
DEFAULT_MOCK_SEEN_OBJECTS: Final = ""
DEFAULT_HTTP_AUTH_TYPE: Final = HTTP_AUTH_NONE
DEFAULT_ANALYZER_PROFILE: Final = "mower_safety"

SERVICE_RUN_ANALYSIS: Final = "run_analysis"
SERVICE_CLEAR_STATE: Final = "clear_state"

ATTR_FORCE: Final = "force"
ATTR_SAVE_DEBUG: Final = "save_debug"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"

STORAGE_DIR: Final = "vision_roi_guard"
DEBUG_DIR: Final = "debug"
WORK_DIR: Final = "work"
