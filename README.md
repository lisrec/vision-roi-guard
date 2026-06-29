# vision-roi-guard

Home Assistant custom integration for ROI-based vision safety gates.

`vision-roi-guard` analyzes a Home Assistant camera snapshot only inside a configured polygon ROI, then exposes the result as Home Assistant entities and services for downstream automations such as mower safety gates.

## Current status

The repository contains a functional custom integration with:

- UI config flow and options flow
- local ROI JSON parsing, polygon validation, masking, and crop generation via Pillow
- pluggable backends with `mock`, provider-neutral `http`, and `codex_cli`
- coordinator-driven state model and HA entities
- services for `run_analysis`, `update_roi`, `refresh_roi_editor_image`, and `clear_state`
- an integration-owned ROI editor panel for drawing and saving ROI polygons
- redacted diagnostics
- pytest coverage for core logic and HA integration setup paths

## Installation

1. Install the repository as a custom integration, preferably through HACS as a custom repository of category `Integration`.
2. Restart Home Assistant.
3. Add `Vision ROI Guard` from Settings -> Devices & Services -> Add Integration.
4. Choose a Home Assistant `camera.*` entity and a backend.
5. Open the Vision ROI Guard panel from the Home Assistant sidebar and draw the ROI. The options-flow JSON field remains available as an advanced fallback:

```json
[[10,10],[100,10],[100,100],[10,100]]
```

Only `safe` is treated as safe-to-start. `blocked`, `uncertain`, and `error` all fail closed.

## Entities and services

The integration exposes:

- `binary_sensor.safe_to_start`, `binary_sensor.analysis_ok`, and `binary_sensor.camera_available`
- sensors for last verdict, reason, seen objects, analysis time, duration, and error
- `image.last_analyzed_image` for the latest ROI-processed image sent to the analyzer
- `image.roi_editor_image` for a full-frame camera snapshot with the current ROI overlay
- buttons for immediate analysis and saving a debug snapshot
- switch/time/number entities for enabled state, active window, and interval
- services `vision_roi_guard.run_analysis`, `vision_roi_guard.update_roi`, `vision_roi_guard.refresh_roi_editor_image`, and `vision_roi_guard.clear_state`

The last analyzed image is overwritten on each analysis and can be used directly in
Home Assistant image cards. Debug snapshot files remain opt-in and are retained locally
under Home Assistant storage with pruning.

The safe-to-start binary sensor exposes `roi_points`, `roi_points_json`,
`source_width`, and `source_height` attributes for diagnostics and advanced UI use.

## Graphical ROI editor

The primary editor is a Home Assistant panel registered automatically by the
integration at `/vision-roi-guard` and shown as `Vision ROI Guard` in the sidebar.
There is no dashboard resource setup, no manual Lovelace card YAML, and no
entity ID wiring.

The panel lists configured Vision ROI Guard entries by integration title. Select
an entry, press `Refresh frame` to capture the editor image, then draw or adjust
the polygon. Drag vertices to move them, click the image to add a vertex, select
a vertex and press `Delete vertex` to remove it, then press `Save ROI`.

Save calls `vision_roi_guard.update_roi` with the selected `config_entry_id` and
stores the polygon in the config entry options as `roi_points_json`. `Run test
analysis` calls `vision_roi_guard.run_analysis` for the selected entry, and
`Reload saved ROI` discards unsaved panel edits.

The original options-flow JSON field remains available as a fallback and for
advanced edits. `image.*_last_analyzed_image` is unchanged and continues to show
the ROI-processed analyzer input.

### Advanced Lovelace fallback

The integration still serves the previous no-build Lovelace custom card from
`/vision_roi_guard_static/roi-editor-card.js` for power users who want to embed
the editor in a dashboard. This is not the primary setup path; it requires
manually adding the dashboard resource and manually providing entity IDs.

## Backends

### `mock`

Deterministic backend for CI, tests, and local dry runs.

### `http`

Provider-neutral HTTP Analyzer backend. The integration sends the processed ROI image to a configured `http://` or `https://` analyzer URL and accepts the normalized `safe` / `blocked` / `uncertain` / `error` response. The analyzer can run beside Home Assistant, in another Docker container, on the host, on a LAN GPU server, or remotely. Use HTTPS for non-local analyzers and avoid sending private camera/entity metadata to untrusted endpoints.

Reference analyzers live under `examples/analyzers/` and can wrap Codex CLI, Ollama, OpenAI, or any other AI runtime as long as they expose the documented HTTP contract.

### `codex_cli`

Runs the local `codex` executable without shell interpolation and expects strict JSON:

```json
{
  "verdict": "safe",
  "reason": "empty_lawn",
  "seen_objects": ["grass"]
}
```

The current implementation assumes a `codex exec -i <image> ...` command shape. If the CLI surface changes, update the backend adapter rather than weakening parsing or safety defaults.

## Known limitations

- `codex_cli` depends on a locally installed and authenticated `codex` executable in the Home Assistant process `PATH`; for Home Assistant containers, prefer the `http` backend with a host-side Codex bridge instead.
- The integration makes a point-in-time decision from a single camera snapshot. Use Home Assistant automations for retries, mower commands, and multi-sensor policy.
- Debug images may contain private camera content inside the ROI. Keep debug persistence disabled unless actively troubleshooting.

## Development

Create a local environment and run tests:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements_dev.txt
PYTHONPATH=. ./.venv/bin/pytest
./.venv/bin/ruff check custom_components tests
```

## Documentation

- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [HTTP Analyzer Backend](docs/HTTP_ANALYZER_BACKEND.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Example automation](docs/examples/automation_mower_gate.yaml)

## License

MIT
