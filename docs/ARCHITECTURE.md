# Architecture

`vision-roi-guard` is split into four layers:

1. Home Assistant layer
   - config flow, options flow, entities, diagnostics, and services
   - entry point: `custom_components/vision_roi_guard/`
2. Runtime orchestration
   - `VisionRoiGuardCoordinator` manages state and analysis execution
3. Local preprocessing
   - `roi.py` validates polygon JSON and generates a masked/cropped image
4. Backend adapters
   - `mock` for deterministic local behavior
   - `http` for generic analyzer endpoints
   - `codex_cli` for legacy/local CLI-based image analysis

## Processing path

1. A button press, service call, or coordinator refresh starts analysis.
2. The integration captures a fresh camera snapshot to a temporary local file.
3. ROI preprocessing masks the image outside the polygon and optionally crops to the ROI bounding box.
4. The processed image is passed to the selected backend.
5. The backend returns a normalized verdict: `safe`, `blocked`, `uncertain`, or `error`.
6. Entities update from coordinator state.
7. If enabled, the processed image is written to a local debug store with retention pruning.

## Safety model

- Only `safe` produces `binary_sensor.safe_to_start = on`.
- Any exception, timeout, malformed backend response, or missing ROI becomes `error` and therefore not safe.
- Backend output is parsed strictly; free-form text is rejected.
- Backend process stderr is not stored in entity state or diagnostics.
- Diagnostics redact camera identifiers, ROI JSON, prompt text, and debug file paths.

## Notable implementation decisions

- Camera acquisition uses the Home Assistant `camera.snapshot` service instead of storing long-lived proxy URLs.
- ROI processing uses Pillow instead of OpenCV to keep the dependency footprint small.
- The backend interface is intentionally narrow so analyzer runtimes stay outside the Home Assistant integration.
- Options changes reload the config entry so runtime behavior stays aligned with UI configuration.

## Current limitations

- ROI entry is JSON-based and intentionally minimal.
- There is no image entity for serving retained debug images; debug paths are local troubleshooting aids.
- The `codex_cli` adapter is retained for compatibility, but the preferred production boundary is the generic HTTP analyzer.
- The integration does not command mowers or other actuators directly.
