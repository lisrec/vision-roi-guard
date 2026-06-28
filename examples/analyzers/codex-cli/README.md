# Codex CLI Analyzer Bridge

The Home Assistant integration does not call Codex directly when using the HTTP
backend. Run a separate bridge process that accepts the v1 `/analyze` request,
invokes the provider/runtime of your choice, and returns normalized JSON.

Recommended bridge behavior:

- Bind to `127.0.0.1` by default.
- Require bearer auth before exposing beyond localhost.
- Do not log bearer tokens, prompts, image bytes, camera entity IDs, or ROI points.
- Return only `safe`, `blocked`, `uncertain`, or `error`.
- Treat provider failures as `error`.

Example integration settings:

- Backend: `http`
- Analyzer URL: `http://127.0.0.1:8766/analyze`
- Auth type: `bearer`
- Bearer token: generated locally by the operator
- Profile: `mower_safety`

This directory intentionally does not include provider credentials, prompts, or
site-specific examples.
