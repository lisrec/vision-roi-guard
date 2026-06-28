# vision-roi-guard — Full Implementation Plan

> Status: design phase
> 
> Goal: build a production-grade, HACS-installable Home Assistant custom integration that evaluates a camera snapshot only within a configured polygon ROI and exposes the result as Home Assistant entities/services for downstream automations.

---

## 1. Product definition

### 1.1 Problem statement

Many Home Assistant automations need a **vision-based go/no-go decision** about a specific physical zone, not the whole camera frame.

Canonical example:
- camera sees both **lawn** and **terrace**
- a person on the terrace should **not** block the mower
- a child, ball, hose, or animal on the lawn **should** block the mower

Whole-frame person detection is too coarse. Prompt-only instructions like "ignore the terrace" are too brittle. The integration must therefore support:

1. local preprocessing of the image
2. polygon ROI masking
3. optional crop to ROI bounding box
4. pluggable backend classification
5. Home Assistant-native entity model for automation

### 1.2 Product goal

Provide a reusable HA integration that:
- fetches a fresh camera frame
- isolates a configured ROI
- sends the ROI-derived image to a selected analysis backend
- stores the verdict and metadata in HA entities
- never requires private site-specific information to be committed to the repository

### 1.3 Non-goals for v1

v1 should **not**:
- directly start/pause/dock a mower
- own retry scheduling logic like "try again in 1h"
- include a graphical polygon editor inside HA frontend
- ship site-specific prompts, images, tokens, hostnames, or ROI coordinates
- depend on one single AI provider forever

Those concerns belong either to HA automations or later versions.

---

## 2. Core design principles

1. **Privacy-first** — no private cameras, images, hostnames, tokens, or ROI points in git.
2. **Fail-safe by default** — ambiguous/error states must never imply safe-to-start.
3. **HA-native** — config flow, options flow, entities, services, diagnostics, unloading.
4. **Backend-pluggable** — `codex_cli` first, more adapters later.
5. **Local preprocessing first** — mask/crop before backend analysis.
6. **Separation of concerns** — integration analyzes; HA automations decide what to do.
7. **HACS-ready from day one** — manifest, hacs metadata, releases, branding, tests.

---

## 3. User-facing scope

## 3.1 Supported use-cases in v1

### Primary
- manual "analyze now"
- scheduled analysis driven by HA automation
- mower safety gate for lawn-only decision making

### Secondary, supported by architecture
- pool zone monitoring
- driveway occupancy gate
- child-safe zone checks
- robot vacuum room-clear verification

---

## 4. Home Assistant integration model

## 4.1 Domain and naming

Proposed domain:
- `vision_roi_guard`

Display name:
- `Vision ROI Guard`

Per-installation instance title examples:
- `Garden Mower Guard`
- `Backyard ROI Guard`
- `Pool Safety Zone`

## 4.2 Installation target

Custom integration installed through HACS:
- repository type: **Integration**
- code location:
  - `custom_components/vision_roi_guard/`

---

## 5. Repository structure

Target repository layout:

```text
vision-roi-guard/
├── README.md
├── LICENSE
├── hacs.json
├── pyproject.toml
├── requirements_dev.txt
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── custom_components/
│   └── vision_roi_guard/
│       ├── __init__.py
│       ├── manifest.json
│       ├── const.py
│       ├── coordinator.py
│       ├── config_flow.py
│       ├── diagnostics.py
│       ├── services.yaml
│       ├── strings.json
│       ├── translations/
│       │   └── en.json
│       ├── button.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── switch.py
│       ├── number.py
│       ├── time.py
│       ├── image.py                  # optional in v1, preferred if feasible
│       ├── models.py
│       ├── exceptions.py
│       ├── camera_client.py
│       ├── roi.py
│       ├── debug_store.py
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── codex_cli.py
│       │   ├── mock.py
│       │   └── webhook.py           # optional stub for future
│       └── helpers/
│           ├── redact.py
│           ├── schema.py
│           └── validation.py
├── tests/
│   ├── conftest.py
│   ├── test_config_flow.py
│   ├── test_options_flow.py
│   ├── test_coordinator.py
│   ├── test_roi.py
│   ├── test_diagnostics.py
│   ├── test_services.py
│   └── backends/
│       ├── test_codex_cli.py
│       └── test_mock.py
└── docs/
    ├── IMPLEMENTATION_PLAN.md
    ├── ARCHITECTURE.md
    ├── ENTITY_MODEL.md
    ├── SECURITY_AND_PRIVACY.md
    ├── HACS_RELEASES.md
    └── examples/
        ├── automation_mower_gate.yaml
        └── options_example.json
```

Note: only `IMPLEMENTATION_PLAN.md` is required now; the others are recommended follow-up docs once code starts.

---

## 6. Privacy and secret boundaries

## 6.1 Must never be committed

The repository must never contain:
- real camera entity IDs from private deployments, unless generic examples
- HA tokens or camera proxy tokens
- local IPs/hostnames
- raw snapshots from a private garden/driveway/home
- ROI points from a private installation unless intentionally published by user
- provider auth files, Codex auth files, `.env` with real values
- debug output that contains local paths or identifiers

## 6.2 Where private configuration belongs

Private/site-specific data must live in:
- HA `config_entry.data`
- HA `config_entry.options`
- local debug folder managed by HA installation
- local automations/scripts, not in the public repo

## 6.3 Diagnostics policy

Diagnostics output must redact:
- tokens
- auth headers
- proxy URLs containing tokens
- local paths if they reveal user names/host structure
- raw backend responses unless sanitized
- raw image data entirely

Diagnostics may include:
- backend type (`codex_cli`)
- latest state (`safe`, `blocked`, etc.)
- timestamps
- dimensions of ROI image
- whether debug image saving is enabled
- validation errors (sanitized)

---

## 7. Functional architecture

## 7.1 Processing pipeline

Target pipeline:

```text
HA service/button/automation
  -> coordinator run request
  -> camera source resolution
  -> fresh frame download
  -> ROI mask generation
  -> optional crop
  -> backend request
  -> normalized verdict
  -> entity state update
  -> optional debug image persistence
```

## 7.2 Failure behavior

The system must produce one of four normalized results:
- `safe`
- `blocked`
- `uncertain`
- `error`

Mapping rule:
- `safe` => only when backend explicitly indicates safe
- `blocked` => backend explicitly indicates unsafe
- `uncertain` => backend ambiguous / incomplete / low confidence
- `error` => transport, parsing, timeout, camera failure, runner failure

For downstream automation, **`safe_to_start = true` only for `safe`**.
All other states imply **not safe**.

---

## 8. Configuration model

## 8.1 Config flow (initial setup)

Purpose: collect minimum required information to create one config entry.

### Required fields
- `name`
- `camera_entity_id`
- `backend_type`

### Optional at setup (can also live in options)
- `save_debug_images` (default false)
- `analysis_timeout_sec` (default 120)
- `roi_mode` (default `polygon`)

### v1 config flow validation
On submit, integration must:
1. verify camera entity exists
2. verify backend is available for selection
3. validate minimum backend prerequisites
4. create entry only if setup is meaningful

### Backend-specific config flow notes
#### `codex_cli`
Validation should check:
- `codex` binary exists in PATH
- a lightweight auth/health probe succeeds

Important: do **not** store Codex auth secrets in the integration. The integration should rely on existing Codex local auth state.

## 8.2 Options flow

Options flow should hold everything likely to change post-installation.

### General options
- `enabled` (bool)
- `active_start_time`
- `active_stop_time`
- `analysis_interval_min`
- `analysis_timeout_sec`
- `save_debug_images`
- `debug_retention_count`
- `mask_outside_roi_mode` (`black`, `dim`, `transparent_if_png` later)
- `crop_to_bounding_box` (bool)

### ROI options
- `roi_points_json`
- optional future `roi_preset_name`

For v1, use a validated JSON text field or multi-line text field containing:
```json
[[1180,900],[1180,650],[1320,460]]
```

Validation rules:
- minimum 3 points
- integer coordinates
- points within source frame bounds if known
- polygon must be non-self-intersecting if practical to validate

### Backend options
#### `codex_cli`
- `model` (optional override)
- `prompt_template`
- `max_output_tokens` (if supported by chosen CLI path)
- `cli_timeout_sec`

### Classification policy options
- `blocked_labels`
- `safe_labels`
- `uncertain_on_unknown_objects` (bool)
- `minimum_confidence` (reserved for future backends)

For v1, keep policy minimal and prefer backend-prompt + normalized JSON response.

---

## 9. Entity model

The integration should expose a clean, automation-friendly entity set.

## 9.1 Primary state entities

### `binary_sensor.<instance>_safe_to_start`
- `on` only when last result is `safe`
- device class: none
- attributes:
  - `last_result`
  - `last_reason`
  - `last_seen_objects`
  - `last_analyzed_at`

### `sensor.<instance>_last_result`
State values:
- `safe`
- `blocked`
- `uncertain`
- `error`

### `sensor.<instance>_last_reason`
Short text reason, e.g.
- `child_on_lawn`
- `hose_detected`
- `camera_unavailable`
- `backend_timeout`

### `sensor.<instance>_last_seen_objects`
String or serialized compact list, e.g.
- `hose; ball; child`

Prefer attributes for raw structured list if HA entity style allows it cleanly.

### `sensor.<instance>_last_time_analyzed`
Datetime sensor

### `sensor.<instance>_last_duration_sec`
Numeric sensor

## 9.2 Health entities

### `binary_sensor.<instance>_analysis_ok`
`on` when the last run completed without internal failure.

### `binary_sensor.<instance>_camera_available`
Reflects whether the camera source was resolvable/downloadable in the last check.

### `sensor.<instance>_last_error`
Only meaningful when last result is `error`; otherwise blank/unknown.

## 9.3 Control entities

### `switch.<instance>_enabled`
Master enable/disable.

### `number.<instance>_analysis_interval_min`
Editable interval.

### `time.<instance>_analysis_start_time`
### `time.<instance>_analysis_stop_time`
User-settable time window.

### `button.<instance>_run_analyze_now`
Manual trigger.

### `button.<instance>_save_debug_snapshot`
Optional manual debug action if enabled.

## 9.4 Optional debug entity for v1

Prefer to add one of:
- `image.<instance>_last_crop`
- or if image entity complexity is too high in v1, expose only file path in sensor attributes and document how to inspect the local file

Recommendation: implement image entity if feasible; otherwise defer to v1.1.

---

## 10. Service model

## 10.1 Required services

### `vision_roi_guard.run_analysis`
Parameters:
- `entity_id` or `config_entry_id`
- `force` (optional; bypass time window/disabled state if true)
- `save_debug` (optional)

### `vision_roi_guard.clear_state`
Clears transient last result and error fields.

## 10.2 Optional service

### `vision_roi_guard.export_debug_bundle`
Only if easy to implement safely later. Not required for v1.

---

## 11. Camera acquisition strategy

## 11.1 Camera source for v1

Use Home Assistant camera entity as the only supported source in v1.

### Why
- simplest HA-native experience
- less configuration burden
- avoids early abstraction complexity

## 11.2 Acquisition method

Preferred strategy:
1. read current camera state/entity picture or use HA-supported snapshot path
2. fetch a **fresh** image at run time
3. avoid hardcoding long-lived camera proxy URLs or tokens

Important requirement:
- never persist stale proxy tokens into repository or default config

Potential implementations:
- use HA camera proxy endpoint resolved at runtime
- or invoke HA snapshot service to a temporary local file

Recommendation for v1:
- use **snapshot service to temp file** if practical and robust from integration context
- fallback: runtime proxy fetch if snapshot service path is cleaner in integration code

Decision must be based on HA integration ergonomics and testability.

---

## 12. ROI processing design

## 12.1 Input
- source image path or bytes
- polygon point list

## 12.2 Outputs
- masked image
- optional crop image
- metadata:
  - original size
  - crop bounding box
  - output size
  - point count

## 12.3 Processing rules

1. generate polygon mask
2. apply outside-ROI treatment
3. optionally crop to polygon bounding rectangle
4. encode final backend input image

## 12.4 Library choice

Use `Pillow` in v1.

Why:
- simple
- fewer heavy dependencies than OpenCV
- enough for polygon mask + crop
- easy to test

OpenCV should be deferred unless a real need appears.

---

## 13. Backend abstraction

## 13.1 Interface

Create `backends/base.py` with a stable interface like:

- `async validate()`
- `async analyze(image_path, prompt_context) -> AnalysisResult`
- `async healthcheck()`

## 13.2 Normalized result model

`AnalysisResult` should include:
- `verdict`
- `reason`
- `seen_objects`
- `raw_text` (optional, private/internal)
- `backend_name`
- `duration_sec`
- `error_code` (optional)

## 13.3 v1 backend: `codex_cli`

### Execution model
Use subprocess invocation of:
- `codex exec`
- with `-i <image>`
- with deterministic prompt
- preferably with structured output constraints

### Output strategy
Strong recommendation:
- force compact JSON output
- parse strictly
- reject non-JSON or malformed output as `error` or `uncertain`

Expected response shape:
```json
{
  "verdict": "safe",
  "reason": "empty_lawn",
  "seen_objects": ["hose", "mower"]
}
```

### Security constraints
- no secrets passed via repo-stored config
- local Codex auth state only
- no logging of raw auth env

### Failure modes to handle
- binary missing
- timeout
- auth expired
- malformed response
- unsupported image mode
- CLI non-zero exit

## 13.4 `mock` backend

Mandatory for tests and early demos.

Capabilities:
- fixed result mode
- keyword-driven fake mode
- deterministic output without network

This backend is essential for CI.

---

## 14. Coordinator design

Use `DataUpdateCoordinator` or equivalent central runtime object.

Responsibilities:
- hold latest state
- trigger on-demand analysis
- optionally run periodic refresh
- expose synchronized updates to entities

Recommendation:
- keep **automatic scheduling inside coordinator minimal**
- let HA automations call `run_analysis` for real-world workflows

Optional polling behavior can still exist for status freshness, but product logic should not depend solely on internal polling.

---

## 15. HA automation boundary

The integration should **not** own mower logic.

### Integration responsibility
- analyze image
- publish states
- publish services

### Automation responsibility
- when to run analysis
- whether to start mower
- postpone by 1h
- notify user

Example downstream automation pattern:
1. T-1 min before mower start
2. call `vision_roi_guard.run_analysis`
3. if `binary_sensor.safe_to_start == on` => call `lawn_mower.start_mowing`
4. else => postpone + notify

This keeps the integration generic and reusable.

---

## 16. Diagnostics and logging

## 16.1 Logging policy

Use structured, low-noise logging.

Log once for:
- camera unavailable
- backend unavailable
- analysis restored
- malformed result

Avoid:
- logging full prompts every run
- logging raw image contents
- logging raw auth paths or tokens

## 16.2 Diagnostics implementation

Diagnostics should include:
- config entry data/options with redaction
- last result metadata
- backend name
- availability flags
- ROI metadata (e.g. point count), but not necessarily raw coordinates unless user explicitly accepts that tradeoff

Recommendation:
- redact exact ROI coordinates in diagnostics by default, or provide them only if they are not considered sensitive. Default safer stance: redact.

---

## 17. HACS packaging requirements

Based on HACS integration publishing requirements, repository must include:
- correct repository structure
- valid `manifest.json`
- valid `hacs.json`
- brand assets
- GitHub repository suitable for HACS ingestion

## 17.1 Required metadata

### `manifest.json`
At minimum include:
- `domain`
- `name`
- `version`
- `documentation`
- `issue_tracker`
- `codeowners`
- `integration_type`
- `iot_class`

Expected choices:
- `integration_type`: likely `service` or `hub` depending final modeling; evaluate carefully
- `iot_class`: likely `local_polling` or `local_push` not accurate if Codex CLI involved; probably `local_polling` if camera fetch + local subprocess dominate. Must choose based on actual behavior.

### `hacs.json`
Must declare integration metadata expected by HACS.

## 17.2 Branding
Need brand assets under repository brand path or equivalent supported pattern.

---

## 18. Home Assistant quality-scale targets

The design should target at least **Silver/Gold-quality practices**, even if we do not formally claim that immediately.

Priority requirements from HA docs:
- setup via UI
- connection test in config flow
- support unload
- unique IDs
- config flow coverage
- reauthentication path if backend requires it
- diagnostics
- runtime data stored correctly

## 18.1 Practical quality goals for v1

Minimum:
- config flow
- options flow
- unload/reload support
- services
- tests for core logic
- diagnostics
- clear error states

Recommended:
- >95% coverage for integration module set
- mock backend CI coverage
- codex backend integration-style tests with subprocess mocking

---

## 19. Testing strategy

## 19.1 Unit tests

Required unit test areas:
- ROI polygon validation
- masking output behavior
- crop bounding box behavior
- normalized result parsing
- diagnostics redaction
- config flow validation
- options flow validation
- service invocation

## 19.2 Backend tests

### `codex_cli`
Use subprocess mocking for:
- success with valid JSON
- malformed output
- timeout
- missing binary
- non-zero exit

### `mock`
Test deterministic result generation.

## 19.3 HA integration tests

Need tests for:
- config entry setup
- entity registration
- service calls update entity states
- unload/reload

## 19.4 Fixture policy

Do not use private real garden images in repository tests.

Use:
- synthetic generated test images
- public neutral fixture images
- minimal geometric mock images

---

## 20. Security model

## 20.1 Threats

- accidental commit of local secrets
- accidental logging of auth tokens
- stale camera proxy token persistence
- diagnostics leaking private camera details
- backend command injection via unvalidated prompt/template/options

## 20.2 Mitigations

- never store shell command templates freely editable without validation
- sanitize subprocess arguments as arg list, not shell string concatenation
- strict timeout on backend execution
- strict JSON parsing
- redact diagnostics
- no automatic upload/export of debug images

## 20.3 Codex CLI-specific hardening

- call subprocess without shell interpolation where possible
- validate file paths
- keep prompt template under controlled formatting
- cap execution time
- map failures to safe states

---

## 21. Prompt and result contract

## 21.1 Prompt philosophy

Prompt must be narrow and deterministic.

The backend should answer only:
- whether ROI is safe for the intended activity
- short reason
- short object list

Avoid open-ended descriptions.

## 21.2 Proposed result contract

```json
{
  "verdict": "safe|blocked|uncertain",
  "reason": "snake_case_short_reason",
  "seen_objects": ["object_1", "object_2"]
}
```

If backend cannot produce this shape, integration must treat the run as failed or uncertain.

---

## 22. v1 implementation milestones

## Milestone 0 — repository/bootstrap
- repo scaffold
- README
- LICENSE
- docs
- git + GitHub + release strategy

## Milestone 1 — HA skeleton
- manifest
- constants
- setup/unload
- config flow stub
- options flow stub
- basic entities

## Milestone 2 — ROI engine
- polygon validation
- masking
- crop
- debug output management

## Milestone 3 — backend abstraction
- base interface
- mock backend
- codex_cli backend
- normalized parsing

## Milestone 4 — coordinator + services
- run_analysis service
- entity update model
- manual button trigger
- health handling

## Milestone 5 — diagnostics and hardening
- diagnostics
- redaction
- logging cleanup
- failure mapping

## Milestone 6 — HACS polish
- hacs.json
- branding
- releases
- CI
- installation docs

---

## 23. Detailed implementation tasks

## Task group A — bootstrap repository

### A1. Add metadata files
Create:
- `hacs.json`
- `pyproject.toml`
- `requirements_dev.txt`
- GitHub Actions CI workflow

### A2. Add component folder skeleton
Create empty but valid files under `custom_components/vision_roi_guard/`.

### A3. Add manifest
Populate with HACS/HA-safe metadata.

Acceptance criteria:
- repository structure matches HACS expectations
- HA can discover the custom component package

## Task group B — core HA integration shell

### B1. `const.py`
Define:
- domain
- defaults
- result enums
- backend identifiers
- option keys

### B2. `models.py`
Define dataclasses / typed models:
- runtime state
- analysis result
- ROI config
- backend config

### B3. `__init__.py`
Implement:
- `async_setup`
- `async_setup_entry`
- `async_unload_entry`
- service registration

Acceptance criteria:
- entry loads/unloads cleanly

## Task group C — config flow and options flow

### C1. Config flow
Implement:
- setup form
- camera existence validation
- backend validation
- unique-id logic to prevent duplicate entries

### C2. Options flow
Implement:
- timing fields
- debug toggles
- ROI JSON field
- backend-specific options

### C3. Validation helpers
Centralize all validation in helper module.

Acceptance criteria:
- invalid ROI rejected
- missing camera rejected
- unavailable backend rejected with clear error

## Task group D — ROI processing engine

### D1. ROI parser
Parse JSON to validated point list.

### D2. Mask generator
Use Pillow to generate polygon mask.

### D3. Crop generator
Generate bounding-box crop.

### D4. Output manager
Store temp files safely and clean up.

Acceptance criteria:
- same input + ROI produces deterministic output
- test coverage exists for odd polygon cases

## Task group E — camera acquisition

### E1. Camera client abstraction
Implement camera frame acquisition wrapper.

### E2. Runtime freshness
Always fetch fresh frame per run.

### E3. Error mapping
Map unavailable camera or fetch errors to normalized integration state.

Acceptance criteria:
- stale hardcoded tokens not required
- camera failure sets safe-to-start false

## Task group F — backend abstraction

### F1. Base class
Define backend interface.

### F2. Mock backend
Deterministic local backend for tests.

### F3. Codex CLI backend
Implement subprocess runner, timeout, parsing, validation.

### F4. Prompt builder
Create stable prompt template builder from state and options.

Acceptance criteria:
- subprocess args constructed safely
- malformed output handled gracefully

## Task group G — coordinator and state publishing

### G1. Coordinator
Single runtime orchestration object per config entry.

### G2. State store
Persist latest analysis state in memory/runtime_data.

### G3. Entity platforms
Implement:
- `binary_sensor.py`
- `sensor.py`
- `button.py`
- `switch.py`
- `number.py`
- `time.py`

### G4. Optional image/debug platform
If practical, expose last crop image.

Acceptance criteria:
- manual button updates entities immediately after run
- reload preserves config while runtime state repopulates cleanly

## Task group H — services

### H1. `run_analysis`
Support manual triggering with optional force/debug flags.

### H2. `clear_state`
Reset transient state.

Acceptance criteria:
- service callable from HA developer tools
- service errors surfaced with proper exceptions

## Task group I — diagnostics, logging, redaction

### I1. Diagnostics
Implement sanitized diagnostics payload.

### I2. Redaction helpers
Redact tokens, URLs, paths, sensitive option fields.

### I3. Logging
Low-noise structured logs.

Acceptance criteria:
- diagnostics contain no secrets in tests

## Task group J — HACS and documentation

### J1. HACS metadata
Add `hacs.json` and verify structure.

### J2. Branding
Add placeholder brand assets.

### J3. README and docs
Document:
- install
- setup
- backend prerequisites
- automations examples
- troubleshooting
- privacy notes

### J4. Releases
Create semver release process.

Acceptance criteria:
- repo installable as custom HACS integration after first release

---

## 24. Example local automation pattern (not in integration core)

Example user automation:

```yaml
alias: Mower preflight
trigger:
  - platform: time
    at: "12:59:00"
action:
  - action: vision_roi_guard.run_analysis
    target:
      entity_id: binary_sensor.garden_mower_guard_safe_to_start
  - choose:
      - conditions:
          - condition: state
            entity_id: binary_sensor.garden_mower_guard_safe_to_start
            state: "on"
        sequence:
          - action: lawn_mower.start_mowing
            target:
              entity_id: lawn_mower.kosiarka
    default:
      - action: notify.notify
        data:
          message: "Mower blocked by ROI guard"
```

This stays outside the integration so the project remains generic.

---

## 25. Open questions to resolve before coding starts

1. **Exact camera acquisition path:** snapshot service vs camera proxy fetch.
2. **`image` entity in v1:** include now or defer.
3. **ROI editing UX:** JSON text only in v1 or helper import/export service.
4. **Prompt customization:** user-editable in options or fixed template in v1.
5. **Manifest `iot_class` and `integration_type`:** choose final values carefully based on implementation reality.
6. **Whether diagnostics should include exact ROI coordinates:** default likely no.
7. **Whether internal coordinator should support periodic polling or leave timing fully to HA automations.**

Recommendation: keep v1 conservative and choose the simpler answer whenever possible.

---

## 26. Recommended v1 decisions

To avoid scope creep, lock these in for v1:

- single source type: **HA camera entity only**
- single real backend: **`codex_cli`**
- single test backend: **`mock`**
- ROI editing: **validated JSON in options flow**
- output contract: **strict JSON result**
- debug images: **off by default**
- fail-safe: **anything except `safe` means not safe**
- mower control: **outside integration**
- scheduling: **primarily outside integration**

---

## 27. Acceptance criteria for v1 release

A v1.0.0 release is ready when all of the following are true:

1. integration installs via HACS from GitHub release
2. config flow creates an entry successfully
3. options flow validates ROI and timing fields
4. `run_analysis` service works end-to-end
5. camera frame is fetched freshly per run
6. ROI mask/crop is applied locally
7. `codex_cli` backend returns parsed normalized result
8. entity states update correctly after success and failure
9. diagnostics redact sensitive fields
10. CI passes with automated tests
11. README explains install, setup, privacy, and example automation
12. no private deployment data exists in repository history

---

## 28. Suggested branch and release strategy

- `main` for stable trunk
- short feature branches for milestones
- semantic versions:
  - `v0.1.0` — repo scaffold + plan
  - `v0.2.0` — HA skeleton
  - `v0.3.0` — ROI engine
  - `v0.4.0` — codex backend
  - `v0.5.0` — services + entities
  - `v0.6.0` — diagnostics + HACS polish
  - `v1.0.0` — first production-ready release

---

## 29. Immediate next implementation step

After this plan, the next concrete work item should be:

### Step 1
Create the actual HACS/HA component skeleton and metadata files, with tests bootstrapped from day one.

That gives a clean base for coding without mixing design and site-specific experimentation.

---

## 30. Final recommendation

Treat this repository as a **generic open-source engine for ROI-based HA vision gates**, not as a mower-specific one-off.

Keep three layers separate:

1. **Open-source integration core**
2. **Local HA config entry/options**
3. **Local automations implementing private household behavior**

That separation is the key to publishing safely while still making the integration genuinely useful at home.
