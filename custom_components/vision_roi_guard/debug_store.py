from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DEBUG_DIR, STORAGE_DIR


async def ensure_storage_dir(hass: HomeAssistant) -> Path:
    """Ensure the integration storage directory exists."""
    directory = Path(hass.config.path(STORAGE_DIR, DEBUG_DIR))
    await hass.async_add_executor_job(lambda: directory.mkdir(parents=True, exist_ok=True))
    return directory


async def write_debug_image(
    hass: HomeAssistant,
    entry_id: str,
    image_bytes: bytes,
    retention_count: int,
) -> Path:
    """Persist a debug image and prune old files."""
    directory = await ensure_storage_dir(hass)
    filename = f"{entry_id}-{hass.loop.time():.0f}.png"
    path = directory / filename
    await hass.async_add_executor_job(path.write_bytes, image_bytes)

    def _prune() -> None:
        files = sorted(directory.glob(f"{entry_id}-*.png"), key=lambda item: item.stat().st_mtime)
        for old_path in files[:-retention_count]:
            old_path.unlink(missing_ok=True)

    await hass.async_add_executor_job(_prune)
    return path
