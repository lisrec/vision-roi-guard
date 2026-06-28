from __future__ import annotations

import secrets
from pathlib import Path

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from .const import STORAGE_DIR, WORK_DIR
from .exceptions import CameraSnapshotError

SNAPSHOT_MEDIA_ROOT = Path("/media")
SNAPSHOT_WWW_DIR = "www"


async def capture_camera_snapshot(hass: HomeAssistant, camera_entity_id: str) -> Path:
    """Capture a fresh camera snapshot to a temporary file."""
    work_dir = _snapshot_work_dir(hass)
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


def _snapshot_work_dir(hass: HomeAssistant) -> Path:
    """Return a camera.snapshot-writable temporary work directory."""
    if SNAPSHOT_MEDIA_ROOT.is_dir():
        return SNAPSHOT_MEDIA_ROOT / STORAGE_DIR / WORK_DIR
    return Path(hass.config.path(SNAPSHOT_WWW_DIR, STORAGE_DIR, WORK_DIR))
