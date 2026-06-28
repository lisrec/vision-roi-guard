# vision-roi-guard

Home Assistant custom integration for ROI-based vision safety gates.

## Goal

`vision-roi-guard` analyzes a camera snapshot only inside a configured polygon ROI (region of interest), then exposes Home Assistant entities and services that can be used to automate safety-critical decisions such as whether a robotic mower may start.

## Intended capabilities

- Home Assistant config flow + options flow
- HACS-installable custom integration
- ROI polygon masking and crop generation
- Pluggable analysis backends
  - `codex_cli`
  - future `openai_api`, `ollama`, `webhook`, `mock`
- Safe diagnostics with redaction
- Entities for result, health, timing, and manual execution
- Services for manual analysis and debugging

## Non-goals for v1

- Directly controlling the mower inside the integration
- Embedding any private site-specific camera names, tokens, ROI points, prompts, or images in the repository
- Cloud account secrets committed to the repo

## Repository status

This repository currently contains the product design and implementation plan. Code scaffolding and implementation will follow the plan in `docs/IMPLEMENTATION_PLAN.md`.

## License

MIT
