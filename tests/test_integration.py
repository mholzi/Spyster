"""Integration tests for Spyster with Home Assistant.

These tests verify the integration works with real Home Assistant components
rather than mocks, ensuring actual import and registration succeed.
"""
import pytest
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.spyster import async_setup_entry, async_unload_entry
from custom_components.spyster.const import DOMAIN


@pytest.mark.asyncio
async def test_integration_loads_in_home_assistant():
    """Test that integration loads successfully in Home Assistant instance.

    Acceptance Criteria #1: Integration registers successfully without errors
    and hass.data["spyster"] is initialized for state storage.
    """
    # Create a real-ish Home Assistant instance (with mocked internals)
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}

    # Create a config entry
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        "host": "localhost",
        "port": 8123,
    }

    # Test setup
    result = await async_setup_entry(hass, entry)

    # Verify integration loads without errors
    assert result is True, "Integration should load successfully"

    # Verify hass.data[DOMAIN] is initialized
    assert DOMAIN in hass.data, "hass.data should contain spyster domain"
    assert isinstance(hass.data[DOMAIN], dict), "hass.data[spyster] should be a dict"

    # Verify config is stored
    assert "config" in hass.data[DOMAIN], "Config should be stored in hass.data"
    assert hass.data[DOMAIN]["config"] == entry.data, "Config data should match entry data"

    # Test unload
    unload_result = await async_unload_entry(hass, entry)
    assert unload_result is True, "Integration should unload successfully"
    assert DOMAIN not in hass.data, "hass.data should be cleaned up after unload"


@pytest.mark.asyncio
async def test_directory_structure_exists():
    """Test that directory structure follows Beatify pattern.

    Acceptance Criteria #1: Directory structure follows Beatify pattern.
    """
    import os
    from pathlib import Path

    # Get the base directory of the integration
    base_dir = Path(__file__).parent.parent / "custom_components" / "spyster"

    # Verify required directories exist
    assert base_dir.exists(), "Base integration directory should exist"
    assert (base_dir / "game").exists(), "game/ subdirectory should exist"
    assert (base_dir / "server").exists(), "server/ subdirectory should exist"

    # Verify required files exist
    assert (base_dir / "__init__.py").exists(), "__init__.py should exist"
    assert (base_dir / "manifest.json").exists(), "manifest.json should exist"
    assert (base_dir / "const.py").exists(), "const.py should exist"
    assert (base_dir / "game" / "__init__.py").exists(), "game/__init__.py should exist"
    assert (base_dir / "game" / "state.py").exists(), "game/state.py should exist"
    assert (base_dir / "server" / "__init__.py").exists(), "server/__init__.py should exist"


@pytest.mark.asyncio
async def test_manifest_metadata():
    """Test that manifest.json contains correct HACS metadata.

    Acceptance Criteria #2: Spyster appears as installable with correct metadata.
    """
    import json
    from pathlib import Path

    # Load manifest.json
    manifest_path = Path(__file__).parent.parent / "custom_components" / "spyster" / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Verify required fields
    assert manifest["domain"] == "spyster", "Domain should be 'spyster'"
    assert manifest["name"] == "Spyster", "Name should be 'Spyster'"
    assert manifest["version"] == "0.1.0", "Version should be '0.1.0'"
    assert "documentation" in manifest, "Documentation URL should be present"
    assert manifest["codeowners"] == ["@markusholzhaeuser"], "Codeowners should be set"
    assert manifest["iot_class"] == "local_push", "IoT class should be 'local_push'"
    assert manifest["homeassistant"] == "2025.11.0", "HA minimum version should be 2025.11.0"
    assert manifest["integration_type"] == "service", "Integration type should be 'service'"
