from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .backends.base import VisionBackend
from .camera_client import capture_camera_snapshot
from .const import (
    CONF_ACTIVE_START_TIME,
    CONF_ACTIVE_STOP_TIME,
    CONF_ANALYSIS_INTERVAL_MIN,
    CONF_ANALYSIS_TIMEOUT_SEC,
    CONF_CAMERA_ENTITY_ID,
    CONF_CROP_TO_BOUNDING_BOX,
    CONF_DEBUG_RETENTION_COUNT,
    CONF_ENABLED,
    CONF_MASK_OUTSIDE_ROI_MODE,
    CONF_PROMPT_TEMPLATE,
    CONF_ROI_POINTS_JSON,
    CONF_SAVE_DEBUG_IMAGES,
    DEFAULT_ACTIVE_START_TIME,
    DEFAULT_ACTIVE_STOP_TIME,
    DEFAULT_ANALYSIS_INTERVAL_MIN,
    DEFAULT_ANALYSIS_TIMEOUT_SEC,
    DEFAULT_CROP_TO_BOUNDING_BOX,
    DEFAULT_DEBUG_RETENTION_COUNT,
    DEFAULT_ENABLED,
    DEFAULT_MASK_OUTSIDE_ROI_MODE,
    VERDICT_ERROR,
    VERDICT_SAFE,
)
from .debug_store import write_debug_image
from .exceptions import BackendError, CameraSnapshotError, ValidationError
from .models import AnalysisResult, GuardState
from .roi import parse_roi_points_json, process_image

LOGGER = logging.getLogger(__name__)


class VisionRoiGuardCoordinator(DataUpdateCoordinator[GuardState]):
    """Coordinator for a single config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        title: str,
        data: dict[str, Any],
        options: dict[str, Any],
        backend: VisionBackend,
    ) -> None:
        self.entry_id = entry_id
        self._data = data
        self._options = options
        self._backend = backend
        self._state = GuardState(backend_name=backend.backend_name)
        interval_minutes = int(
            options.get(CONF_ANALYSIS_INTERVAL_MIN, DEFAULT_ANALYSIS_INTERVAL_MIN)
        )
        super().__init__(
            hass,
            LOGGER,
            name=f"{title} coordinator",
            update_interval=(timedelta(minutes=interval_minutes) if interval_minutes > 0 else None),
        )
        self.data = self._state

    @property
    def state(self) -> GuardState:
        return self._state

    def update_options(self, options: dict[str, Any]) -> None:
        """Update runtime options without recreating the coordinator."""
        self._options = options
        interval_minutes = int(
            options.get(CONF_ANALYSIS_INTERVAL_MIN, DEFAULT_ANALYSIS_INTERVAL_MIN)
        )
        self.update_interval = timedelta(minutes=interval_minutes) if interval_minutes > 0 else None

    async def _async_update_data(self) -> GuardState:
        """Periodic refresh path."""
        if not self._options.get(CONF_ENABLED, DEFAULT_ENABLED):
            return self._state
        if not _is_within_active_window(
            dt_util.now().time(),
            self._options.get(CONF_ACTIVE_START_TIME, DEFAULT_ACTIVE_START_TIME),
            self._options.get(CONF_ACTIVE_STOP_TIME, DEFAULT_ACTIVE_STOP_TIME),
        ):
            return self._state
        await self.async_run_analysis(force=False, save_debug=False)
        return self._state

    async def async_run_analysis(self, force: bool, save_debug: bool) -> GuardState:
        """Run one analysis cycle."""
        if not force:
            if not self._options.get(CONF_ENABLED, DEFAULT_ENABLED):
                return self._state
            if not _is_within_active_window(
                dt_util.now().time(),
                self._options.get(CONF_ACTIVE_START_TIME, DEFAULT_ACTIVE_START_TIME),
                self._options.get(CONF_ACTIVE_STOP_TIME, DEFAULT_ACTIVE_STOP_TIME),
            ):
                return self._state

        snapshot_path: Path | None = None
        processed_path: Path | None = None
        analyzed_at = dt_util.utcnow()
        timeout_sec = int(
            self._options.get(CONF_ANALYSIS_TIMEOUT_SEC, DEFAULT_ANALYSIS_TIMEOUT_SEC)
        )
        try:
            snapshot_path = await capture_camera_snapshot(
                self.hass, self._data[CONF_CAMERA_ENTITY_ID]
            )
            self._state.camera_available = True
            image_bytes = await self.hass.async_add_executor_job(snapshot_path.read_bytes)

            points = ()
            if roi_json := self._options.get(CONF_ROI_POINTS_JSON, ""):
                points = parse_roi_points_json(roi_json)
            if not points:
                raise ValidationError("roi_missing")

            processed = await self.hass.async_add_executor_job(
                process_image,
                image_bytes,
                points,
                self._options.get(CONF_MASK_OUTSIDE_ROI_MODE, DEFAULT_MASK_OUTSIDE_ROI_MODE),
                self._options.get(CONF_CROP_TO_BOUNDING_BOX, DEFAULT_CROP_TO_BOUNDING_BOX),
            )
            processed_path = snapshot_path.with_suffix(".roi.png")
            await self.hass.async_add_executor_job(
                processed_path.write_bytes, processed.image_bytes
            )

            result = await self._backend.analyze(
                str(processed_path),
                {CONF_PROMPT_TEMPLATE: self._options.get(CONF_PROMPT_TEMPLATE)},
                timeout_sec,
            )
            await self._apply_result(result, analyzed_at, processed.point_count)

            if save_debug or self._options.get(CONF_SAVE_DEBUG_IMAGES, False):
                debug_path = await write_debug_image(
                    self.hass,
                    self.entry_id,
                    processed.image_bytes,
                    int(
                        self._options.get(CONF_DEBUG_RETENTION_COUNT, DEFAULT_DEBUG_RETENTION_COUNT)
                    ),
                )
                self._state.debug_image_path = str(debug_path)
        except (CameraSnapshotError, ValidationError, BackendError) as err:
            self._apply_error(str(err), analyzed_at)
            if isinstance(err, CameraSnapshotError):
                self._state.camera_available = False
        finally:
            if snapshot_path is not None:
                await self.hass.async_add_executor_job(
                    lambda: snapshot_path.unlink(missing_ok=True)
                )
            if processed_path is not None:
                await self.hass.async_add_executor_job(
                    lambda: processed_path.unlink(missing_ok=True)
                )

        self.async_set_updated_data(self._state)
        return self._state

    async def _apply_result(
        self, result: AnalysisResult, analyzed_at: datetime, roi_point_count: int
    ) -> None:
        self._state.last_result = result.verdict
        self._state.last_reason = result.reason
        self._state.last_seen_objects = result.seen_objects
        self._state.last_analyzed_at = analyzed_at
        self._state.last_duration_sec = result.duration_sec
        self._state.last_error = result.error_code
        self._state.analysis_ok = result.verdict != VERDICT_ERROR
        self._state.safe_to_start = result.verdict == VERDICT_SAFE
        self._state.backend_name = result.backend_name
        self._state.roi_point_count = roi_point_count
        self._state.attributes = {
            "last_seen_objects": list(result.seen_objects),
            "backend_name": result.backend_name,
            "roi_point_count": roi_point_count,
        }

    def _apply_error(self, error_code: str, analyzed_at: datetime) -> None:
        """Map any analysis failure to a fail-closed state."""
        self._state.last_result = VERDICT_ERROR
        self._state.last_reason = error_code
        self._state.last_error = error_code
        self._state.analysis_ok = False
        self._state.safe_to_start = False
        self._state.last_analyzed_at = analyzed_at
        self._state.last_duration_sec = None
        self._state.backend_name = self._backend.backend_name
        self._state.attributes = {
            "backend_name": self._backend.backend_name,
            "roi_point_count": self._state.roi_point_count,
        }

    async def async_clear_state(self) -> None:
        """Clear transient state fields."""
        self._state = GuardState(backend_name=self._backend.backend_name)
        self.async_set_updated_data(self._state)


def _is_within_active_window(current, start, stop) -> bool:
    if start <= stop:
        return start <= current <= stop
    return current >= start or current <= stop
