class VisionRoiGuardError(Exception):
    """Base integration exception."""


class ValidationError(VisionRoiGuardError):
    """Raised when user-provided configuration is invalid."""


class CameraSnapshotError(VisionRoiGuardError):
    """Raised when a camera snapshot cannot be captured."""


class BackendError(VisionRoiGuardError):
    """Raised when a backend fails to analyze an image."""
