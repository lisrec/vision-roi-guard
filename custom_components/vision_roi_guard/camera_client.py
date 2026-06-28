from __future__ import annotations

import secrets
from pathlib import Path

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from .const import STORAGE_DIR, WORK_DIR
from .exceptions import CameraSnapshotError


async def capture_camera_snapshot(hass: HomeAssistant, camera_entity_id: str) -> Path:
    """Capture a fresh camera snapshot to a temporary file."""
    work_dir = Path(hass.config.path(STORAGE_DIR, WORK_DIR))
    await hass.async_add_executor_job(lambda: work_dir.mkdir(parents=True, exist_ok=True))
    snapshot_path = work_dir / f"{secrets.token_hex(8)}.jpg"

    try:
        await hass.services.async_call(
            "camera",
            "snapshot",
            {ATTR_ENTITY_ID: camera_entity_id, "filename": str(snapshot_path)},
            blocking=True,
        )
    except Exception as err:  # pragma: no cover - HA service exceptions are integration-defined
        raise CameraSnapshotError("camera_snapshot_failed") from err

    exists = await hass.async_add_executor_job(snapshot_path.exists)
    if not exists:
        raise CameraSnapshotError("camera_snapshot_missing")
    return snapshot_path
