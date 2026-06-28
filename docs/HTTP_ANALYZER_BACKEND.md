# HTTP Analyzer Backend

> Status: design target for the open-source integration.
>
> Goal: make `vision-roi-guard` independent from any specific AI runtime. The Home Assistant integration should be able to send a processed ROI image to any compatible analyzer endpoint, whether that analyzer runs inside Home Assistant, in another Docker container, on the HA host, on a LAN GPU machine, or remotely.

## 1. Product direction

`vision-roi-guard` should treat image classification as an external capability behind a stable protocol.

The Home Assistant integration owns:

1. camera snapshot acquisition,
2. ROI validation,
3. ROI masking/cropping,
4. scheduling/manual trigger integration,
5. Home Assistant entities/services/diagnostics,
6. fail-safe result mapping.

The analyzer endpoint owns:

1. provider-specific AI runtime access,
2. prompts/model selection,
3. Codex/OpenAI/Ollama/local-model integration,
4. provider retries/rate limits,
5. provider credentials and secrets,
6. returning a normalized verdict.

The core integration must not assume that Codex, OpenAI, Ollama, a GPU, or any other AI runtime is available inside the Home Assistant process/container.

## 2. Architecture

```text
Home Assistant / vision_roi_guard
  camera snapshot -> ROI mask/crop -> HTTP request
      |
      v
Configurable Analyzer Endpoint
  /analyze API compatible with this document
      |
      v
Any implementation:
  - Codex CLI bridge
  - OpenAI Vision wrapper
  - Ollama/LLaVA wrapper
  - local GPU service
  - custom remote API
  - mock/test analyzer
```

The public feature should be named **HTTP Analyzer** or **Custom Analyzer Endpoint**. Avoid provider-specific naming in the core UI except in examples.

## 3. User-facing configuration

The integration should support at least these analyzer choices:

```text
Analyzer type:
- Mock analyzer
- HTTP analyzer
```

The previous/direct `codex_cli` backend may remain for compatibility, but the preferred open-source architecture is the generic HTTP analyzer.

### 3.1 Config flow fields

Initial setup should ask for stable installation-time values:

| Field | Example | Required | Notes |
|---|---|---:|---|
| Name | `Garden ROI Guard` | yes | HA config entry title |
| Camera entity | `camera.example_camera` | yes | must be a Home Assistant camera entity |
| Analyzer type | `http` | yes | `mock` or `http` |
| Analyzer URL | `http://host.docker.internal:8766/analyze` | if HTTP | absolute `http://` or `https://` URL |
| Auth type | `bearer` | no | `none` or `bearer` for v1 |
| Auth token | hidden | if bearer | stored in config entry data/options, redacted in diagnostics |
| Timeout seconds | `90` | yes | safe bounded timeout |

### 3.2 Options flow fields

Mutable runtime behavior belongs in options:

| Field | Example | Notes |
|---|---|---|
| ROI polygon JSON | `[[10,10],[100,10],[100,100],[10,100]]` | never hardcoded in repo |
| Enabled | `true` | runtime switch also exposed as entity |
| Active window | `00:00`–`23:59` | existing behavior |
| Analysis interval | `60` | existing behavior |
| ROI image mode | `cropped` | `masked`, `cropped`, future `full_with_roi_metadata` |
| Analyzer profile | `mower_safety` | opaque string passed to backend |
| Fail-safe result | `blocked` | default must be effectively blocked/not safe |
| Max image dimension | `1280` | optional privacy/cost control |
| Debug images | `false` | opt-in, local only |

For v1, keep the UI simple: URL, token, timeout, profile, ROI/image settings. More advanced fields can be added later.

## 4. Deployment examples

The URL decides where the analyzer runs. The core integration should not care what is behind it.

| Deployment | Analyzer URL example |
|---|---|
| Same HA host, HA Container | `http://host.docker.internal:8766/analyze` |
| Another Docker container on same compose network | `http://vision-analyzer:8766/analyze` |
| Home Assistant add-on | `http://addon_vision_analyzer:8766/analyze` |
| LAN server / GPU box | `http://analyzer-host.local:8766/analyze` |
| Remote private endpoint | `https://vision.example.com/analyze` |
| Codex bridge | any compatible `/analyze` URL |
| OpenAI wrapper | any compatible `/analyze` URL |
| Ollama wrapper | any compatible `/analyze` URL |

### 4.1 Home Assistant Container host bridge

For Docker Engine deployments where the analyzer runs on the host, document this compose fragment:

```yaml
services:
  homeassistant:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Then configure:

```text
Analyzer URL: http://host.docker.internal:8766/analyze
Auth type: Bearer token
Timeout: 90
```

Do not document private home IPs or real camera names in public examples.

## 5. HTTP API v1

### 5.1 Request

```http
POST /analyze
Authorization: Bearer <optional-token>
Content-Type: multipart/form-data
```

Multipart fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `image` | file | yes | processed ROI image, typically JPEG/PNG/WebP |
| `profile` | string | yes | analysis profile, e.g. `mower_safety` |
| `metadata` | JSON string | yes | schema/version/policy/source metadata |

Recommended metadata shape:

```json
{
  "schema_version": "vision-roi-guard.v1",
  "analysis_type": "mower_safety",
  "roi_mode": "cropped",
  "image_format": "jpeg",
  "source": {
    "type": "home_assistant_camera",
    "camera_entity": "camera.example"
  },
  "policy": {
    "block_on_people": true,
    "block_on_animals": true,
    "block_on_unknown_objects": true
  }
}
```

Privacy note: metadata may include generic camera entity IDs because the backend may need context, but diagnostics must redact them. Examples in the repository must use placeholders only.

### 5.2 Response

```json
{
  "schema_version": "vision-roi-guard.v1",
  "result": "blocked",
  "reason": "Person visible inside the lawn ROI",
  "seen_objects": ["person"],
  "confidence": 0.91,
  "duration_sec": 12.4
}
```

Required fields:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `result` | string | yes | one of `safe`, `blocked`, `uncertain`, `error` |
| `reason` | string | yes | short human-readable reason |
| `seen_objects` | string[] | no | default `[]` |
| `confidence` | number | no | 0.0–1.0 if provided |
| `duration_sec` | number | no | backend runtime |
| `schema_version` | string | no | should be `vision-roi-guard.v1` |

Unknown response fields must be ignored.

### 5.3 Result semantics

Allowed values:

| Result | Meaning | HA `safe_to_start` |
|---|---|---|
| `safe` | ROI appears clear under the configured profile/policy | `on` |
| `blocked` | object/person/animal/condition blocks the action | `off` |
| `uncertain` | backend cannot decide confidently | `off` |
| `error` | backend failed internally but returned a valid response | `off` |

The integration must treat all communication/parsing failures as not safe.

## 6. Fail-safe rules

Only a valid `safe` response may set `binary_sensor.safe_to_start = on`.

These must all result in not safe / error state:

- request timeout,
- DNS/connectivity error,
- TLS error,
- HTTP 4xx/5xx,
- missing required response fields,
- invalid JSON,
- unsupported `result`,
- backend returns `uncertain`,
- backend returns `error`,
- image preprocessing failure,
- camera unavailable.

Recommended entity mapping:

| Situation | `last_result` | `analysis_ok` | `safe_to_start` |
|---|---|---|---|
| valid `safe` | `safe` | `on` | `on` |
| valid `blocked` | `blocked` | `on` | `off` |
| valid `uncertain` | `uncertain` | `on` | `off` |
| valid backend `error` | `error` | `off` | `off` |
| transport/parser error | `error` | `off` | `off` |

## 7. Security requirements

### 7.1 Integration side

- Use `aiohttp`/Home Assistant async HTTP client patterns; do not block the event loop.
- Enforce timeout with a sane upper bound.
- Validate URL scheme: allow `http` and `https`; reject shell-like values and unsupported schemes.
- Do not execute the URL or token through a shell.
- Redact tokens, URLs, camera entity IDs, ROI JSON, debug file paths, request metadata, and backend error details in diagnostics.
- Do not log raw images or full prompts by default.
- Do not include real snapshots in diagnostics.
- Debug image capture must be opt-in and local-only.
- Limit processed image size before upload when configured.
- Avoid storing analyzer response bodies if they may contain scene details; store short normalized fields only.

### 7.2 Analyzer implementation examples

Reference analyzers in `examples/` must:

- require a token by default or clearly warn when auth is disabled,
- bind to `127.0.0.1` by default, not `0.0.0.0`,
- use `subprocess.run([...])`, never shell string interpolation,
- validate uploaded file size/content type,
- clean up temporary files,
- enforce process timeout,
- return strict JSON only,
- never commit or print provider API keys,
- never include private camera names, hostnames, IPs, images, ROI polygons, or tokens.

## 8. Open-source repository structure

Recommended layout:

```text
vision-roi-guard/
  custom_components/
    vision_roi_guard/
      backends/
        mock.py
        codex_cli.py          # optional/legacy/direct CLI adapter
        http_analyzer.py      # generic preferred adapter
  docs/
    HTTP_ANALYZER_BACKEND.md
    ANALYZER_API.md           # optional split-out version of API section
    DEPLOYMENT.md             # optional deployment examples
    SECURITY.md               # security model and redaction rules
  examples/
    analyzers/
      mock-http/
        server.py
        README.md
      codex-cli/
        server.py
        README.md
        systemd-user.service.example
      openai-vision/
        server.py
        README.md
      ollama/
        server.py
        README.md
```

The core integration should include only the generic HTTP client. Provider-specific analyzers should live under `examples/analyzers/` or in separate optional projects.

## 9. Implementation plan

### Phase 1 — core HTTP analyzer adapter

1. Add constants/options for HTTP analyzer:
   - analyzer type/backend value,
   - analyzer URL,
   - auth type,
   - bearer token,
   - timeout,
   - profile,
   - ROI image mode if not already modeled.
2. Extend config flow/options flow with validation:
   - URL required for HTTP analyzer,
   - scheme must be `http` or `https`,
   - token required when auth type is bearer,
   - timeout within bounded range.
3. Add `backends/http_analyzer.py`:
   - async multipart POST,
   - optional bearer auth,
   - metadata JSON field,
   - timeout handling,
   - strict response validation,
   - errors normalized to backend `error` result.
4. Keep backend interface generic so coordinator does not know provider-specific details.
5. Add tests:
   - config flow HTTP happy path,
   - invalid URL/token/timeout cases,
   - successful safe/blocked/uncertain response,
   - timeout/connect error => error/not safe,
   - invalid JSON/unsupported result => error/not safe,
   - diagnostics redaction.

### Phase 2 — reference mock HTTP analyzer

1. Add `examples/analyzers/mock-http/server.py`.
2. It should expose `/analyze`, accept multipart upload, validate token optionally, and return configurable deterministic result.
3. README should show local run and Docker run examples with placeholder values.

### Phase 3 — Codex CLI bridge example

1. Add `examples/analyzers/codex-cli/server.py` as a reference implementation of the API.
2. It should:
   - read config from environment,
   - bind to `127.0.0.1` by default,
   - require bearer token by default,
   - save upload to temp dir,
   - call `codex exec` with argument list and image path,
   - request strict JSON response,
   - parse/validate output,
   - clean up temp files,
   - return normalized API response.
3. Add systemd user service example.
4. Add security warnings for remote exposure.

### Phase 4 — optional provider examples

OpenAI/Ollama examples should be wrappers around the same `/analyze` contract, not new HA integration backends.

### Phase 5 — validation and HA smoke test

1. Run unit tests/lint.
2. Check repository for secrets/private data before commit.
3. Install the integration into local HA using HACS/manual deploy path.
4. Add/configure test entry with mock or HTTP mock analyzer.
5. Run `analyze now` and verify entities update.
6. Verify logs contain no secret/token/private image data.

## 10. Acceptance criteria

The implementation is acceptable when:

- A user can configure an HTTP analyzer entirely through HA UI.
- The analyzer URL can point to same-host, other-container, LAN, or remote services.
- The HA integration does not depend on Codex/OpenAI/Ollama being installed inside HA.
- Provider-specific code is not required in the core HA integration, except optional legacy/direct adapters.
- All failures are fail-safe and never set `safe_to_start` to on.
- Diagnostics redact secrets and private topology.
- Public docs/examples use placeholders only.
- Tests cover success, blocked, uncertain, timeout, invalid JSON, unsupported result, and diagnostics redaction.
- The repository contains no real camera names, tokens, local URLs, snapshots, private ROI polygons, or home-specific prompts.
