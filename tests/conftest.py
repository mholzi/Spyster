"""Shared test fixtures for Spyster tests."""
import pytest
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance for testing."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for testing."""
    entry = MagicMock()
    entry.data = {
        "host": "localhost",
        "port": 8123
    }
    return entry
