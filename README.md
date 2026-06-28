# vision-roi-guard

Home Assistant custom integration for ROI-based vision safety gates.

`vision-roi-guard` analyzes a Home Assistant camera snapshot only inside a configured polygon ROI, then exposes the result as Home Assistant entities and services for downstream automations such as mower safety gates.

## Current status

The repository contains a functional custom integration with:

- UI config flow and options flow
- local ROI JSON parsing, polygon validation, masking, and crop generation via Pillow
- pluggable backends with `mock`, provider-neutral `http`, and `codex_cli`
- coordinator-driven state model and HA entities
- services for `run_analysis` and `clear_state`
- redacted diagnostics
- pytest coverage for core logic and HA integration setup paths

## Installation

1. Install the repository as a custom integration, preferably through HACS as a custom repository of category `Integration`.
2. Restart Home Assistant.
3. Add `Vision ROI Guard` from Settings -> Devices & Services -> Add Integration.
4. Choose a Home Assistant `camera.*` entity and a backend.
5. Open the integration options and paste ROI points JSON such as:

```json
[[10,10],[100,10],[100,100],[10,100]]
```

Only `safe` is treated as safe-to-start. `blocked`, `uncertain`, and `error` all fail closed.

## Entities and services

The integration exposes:

- `binary_sensor.safe_to_start`, `binary_sensor.analysis_ok`, and `binary_sensor.camera_available`
- sensors for last verdict, reason, seen objects, analysis time, duration, and error
- buttons for immediate analysis and saving a debug snapshot
- switch/time/number entities for enabled state, active window, and interval
- services `vision_roi_guard.run_analysis` and `vision_roi_guard.clear_state`

Debug images are opt-in and retained locally under Home Assistant storage with pruning.

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

- ROI points are configured as JSON text; there is no graphical polygon editor yet.
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
