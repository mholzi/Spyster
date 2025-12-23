"""Tests for Spyster integration initialization."""
import pytest

from custom_components.spyster import async_setup_entry, async_unload_entry
from custom_components.spyster.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_initializes_hass_data(mock_hass, mock_config_entry):
    """Test that async_setup_entry initializes hass.data[DOMAIN]."""
    # Execute
    result = await async_setup_entry(mock_hass, mock_config_entry)

    # Verify
    assert result is True
    assert DOMAIN in mock_hass.data
    assert "config" in mock_hass.data[DOMAIN]
    assert mock_hass.data[DOMAIN]["config"] == mock_config_entry.data


@pytest.mark.asyncio
async def test_async_setup_entry_preserves_existing_data(mock_hass, mock_config_entry):
    """Test that async_setup_entry doesn't overwrite existing hass.data."""
    # Setup - pre-populate hass.data
    mock_hass.data[DOMAIN] = {"existing": "data"}

    # Execute
    result = await async_setup_entry(mock_hass, mock_config_entry)

    # Verify
    assert result is True
    assert DOMAIN in mock_hass.data
    assert "existing" in mock_hass.data[DOMAIN]
    assert "config" in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_cleans_up_data(mock_hass, mock_config_entry):
    """Test that async_unload_entry properly cleans up hass.data."""
    # Setup
    mock_hass.data[DOMAIN] = {"config": {}, "game_state": {}}

    # Execute
    result = await async_unload_entry(mock_hass, mock_config_entry)

    # Verify
    assert result is True
    assert DOMAIN not in mock_hass.data


@pytest.mark.asyncio
async def test_async_unload_entry_handles_missing_domain(mock_hass, mock_config_entry):
    """Test that async_unload_entry handles case where DOMAIN is not in hass.data."""
    # Execute (no setup - DOMAIN not in hass.data)
    result = await async_unload_entry(mock_hass, mock_config_entry)

    # Verify
    assert result is True
    assert DOMAIN not in mock_hass.data


@pytest.mark.asyncio
async def test_async_setup_entry_handles_errors_gracefully(mock_hass, mock_config_entry):
    """Test that async_setup_entry handles errors and returns False."""
    # Setup - make setdefault raise an exception
    mock_hass.data.setdefault = lambda *args: (_ for _ in ()).throw(RuntimeError("Test error"))

    # Execute
    result = await async_setup_entry(mock_hass, mock_config_entry)

    # Verify - should return False on error, not raise exception
    assert result is False
