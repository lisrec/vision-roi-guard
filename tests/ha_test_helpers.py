"""Select the real helper provider for the two explicitly pinned CI lanes.

Never install both overlapping pytest plugins into one environment. Import errors
inside a provider must remain errors, not trigger a fallback to the legacy one.
"""

from importlib.util import find_spec

official_fixture = find_spec("pytest_homeassistant") is not None
legacy_fixture = find_spec("pytest_homeassistant_custom_component") is not None
if official_fixture == legacy_fixture:
    raise RuntimeError("Install exactly one Home Assistant fixture provider")

if official_fixture:
    from pytest_homeassistant.common import MockConfigEntry
else:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

# Use the same serializer as each Core's data-entry-flow HTTP layer. Modern HA
# accepts legacy schemas through Probatio, not voluptuous-serialize's sentinel.
if find_spec("probatio") is not None:
    from probatio import to_field_list as serialize_schema
else:
    from voluptuous_serialize import convert as serialize_schema

__all__ = ["MockConfigEntry", "serialize_schema"]
