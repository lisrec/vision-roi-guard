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
- invalid, truncated and Pillow-rejected decompression-bomb camera images map to a
  stable `image_invalid` analysis error and revoke the previous safe verdict

### Dependency and decoder limitations

The modern development lane uses a matched Core/official-fixture pair and is audited.
The separate Core 2026.9.4 production-compatibility lane and older Core 2026.2.3 lane
are compatibility tests, not security-clean runtime environments. Runtime Pillow
floors remain synchronized at `Pillow>=10.0.0`; they have not been raised to 13 because
older supported Core versions own incompatible Pillow pins. Keep issue #4 open until
that support transition is separately reviewed and tested.

Decoder error handling is not a Pillow vulnerability fix, an image resource sandbox,
or proof that production libraries are patched. Existing format support is unchanged.
In particular, absence of JPEG `draft()`/`thumbnail()` does not exclude unrelated
decoder findings. Keep camera sources trusted and update the hosting Core separately.

CI pins the existing setup-uv v7 implementation immutably and verifies the explicit
uv archive digest. Migrating the action to current v10 is a separate major review;
the version check does not treat the old action as current merely because it installs
a patched uv binary.

## Operational guidance

- keep ROI JSON, prompts, and backend selections inside Home Assistant config entries or options
- review retained debug images locally before sharing them outside your environment
- treat diagnostics as potentially sensitive even after redaction if they reveal workflow timing or object labels
- do not rely on this integration as the only safety mechanism for moving equipment; use it as one conservative gate in a broader Home Assistant automation
