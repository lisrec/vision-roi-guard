"""Keep the compatibility lane distinct from the audited current fixture."""

import json
import runpy
from importlib.metadata import distribution, version
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch

import pytest
from ha_test_helpers import MockConfigEntry, serialize_schema


def test_fixture_providers_cannot_overlap() -> None:
    """Overlapping auto-loaded plugins must fail, not silently select a helper."""
    with (
        patch("importlib.util.find_spec", return_value=object()),
        pytest.raises(RuntimeError, match="exactly one Home Assistant fixture"),
    ):
        runpy.run_path(str(Path(__file__).with_name("ha_test_helpers.py")))


def test_installed_fixture_matches_core_and_serializer() -> None:
    """Exercise the actual installed pair instead of accepting resolver success."""
    if find_spec("pytest_homeassistant") is not None:
        assert find_spec("pytest_homeassistant_custom_component") is None
        assert version("pytest-homeassistant") == version("homeassistant") == "2026.11.2"
        assert version("pillow") == "13.0.0"
        assert MockConfigEntry.__module__ == "pytest_homeassistant.common"
        assert serialize_schema.__module__.startswith("probatio")
    elif version("homeassistant") == "2026.9.4":
        assert version("pytest-homeassistant-custom-component") == "0.13.367"
        assert version("pillow") == "12.3.0"
        fixture_source = json.loads(
            distribution("pytest-homeassistant-custom-component").read_text("direct_url.json")
        )
        assert fixture_source["vcs_info"]["commit_id"] == (
            "ecc26f34993d166edac608197b1df172d9da23de"
        )
        assert MockConfigEntry.__module__ == "pytest_homeassistant_custom_component.common"
        assert serialize_schema.__module__ == "voluptuous_serialize"
    else:
        assert version("pytest-homeassistant-custom-component") == "0.13.316"
        assert version("homeassistant") == "2026.2.3"
        assert version("pillow") == "12.0.0"
        assert MockConfigEntry.__module__ == "pytest_homeassistant_custom_component.common"
        assert serialize_schema.__module__ == "voluptuous_serialize"
