# Security and Privacy

## Repository boundaries

Do not commit:

- real camera entity IDs from a private deployment
- access tokens or auth material
- local IP addresses or hostnames
- private ROI coordinate sets
- private camera snapshots
- generated debug images

## Runtime safeguards

- subprocess execution uses argument lists, never shell interpolation
- the `codex_cli` backend enforces timeouts and strict JSON parsing
- subprocess stderr is reduced to stable error codes before it reaches Home Assistant state
- ambiguous or malformed backend output does not become `safe`
- diagnostics redact sensitive fields by default
- debug image persistence is opt-in

## Operational guidance

- keep ROI JSON, prompts, and backend selections inside Home Assistant config entries or options
- review retained debug images locally before sharing them outside your environment
- treat diagnostics as potentially sensitive even after redaction if they reveal workflow timing or object labels
- do not rely on this integration as the only safety mechanism for moving equipment; use it as one conservative gate in a broader Home Assistant automation
