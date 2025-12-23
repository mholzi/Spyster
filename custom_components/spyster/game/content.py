"""Content pack loading and management."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Cache loaded packs
_LOADED_PACKS: dict[str, dict] = {}


def load_location_pack(hass: HomeAssistant, pack_id: str) -> dict | None:
    """Load a location pack from JSON file.

    Args:
        hass: Home Assistant instance
        pack_id: Pack identifier (e.g., "classic")

    Returns:
        Pack data dict or None if not found/invalid
    """
    if pack_id in _LOADED_PACKS:
        return _LOADED_PACKS[pack_id]

    # Construct path to content file
    integration_dir = Path(__file__).parent.parent
    content_file = integration_dir / "content" / f"{pack_id}.json"

    if not content_file.exists():
        _LOGGER.error("Location pack not found: %s", content_file)
        return None

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            pack_data = json.load(f)

        # Validate pack structure
        if not pack_data.get("locations"):
            _LOGGER.error("Location pack %s has no locations", pack_id)
            return None

        # Cache the pack
        _LOADED_PACKS[pack_id] = pack_data

        _LOGGER.info(
            "Loaded location pack: %s (%d locations)",
            pack_data.get("name", pack_id),
            len(pack_data["locations"])
        )

        return pack_data

    except (json.JSONDecodeError, OSError) as err:
        _LOGGER.error("Failed to load location pack %s: %s", pack_id, err)
        return None


def get_random_location(pack_id: str) -> dict | None:
    """Get a random location from the specified pack.

    Args:
        pack_id: Pack identifier

    Returns:
        Location dict with name, roles, flavor, etc.

    Raises:
        RuntimeError: If pack is not preloaded (critical setup error)
    """
    # DEFENSIVE: Fail fast if packs not preloaded - this indicates setup error
    if not _LOADED_PACKS:
        raise RuntimeError(
            "No location packs loaded - call preload_location_packs() during integration setup"
        )

    pack = _LOADED_PACKS.get(pack_id)

    if not pack:
        _LOGGER.error("Location pack not found: %s (available: %s)", pack_id, list(_LOADED_PACKS.keys()))
        return None

    if not pack.get("locations"):
        _LOGGER.error("Location pack %s has no locations", pack_id)
        return None

    # Use CSPRNG for location selection
    location = secrets.choice(pack["locations"])

    return location


def get_location_list(pack_id: str) -> list[str]:
    """Get list of all location names in a pack (for spy display).

    Args:
        pack_id: Pack identifier

    Returns:
        List of location names

    Raises:
        RuntimeError: If pack is not preloaded (critical setup error)
    """
    # DEFENSIVE: Fail fast if packs not preloaded
    if not _LOADED_PACKS:
        raise RuntimeError(
            "No location packs loaded - call preload_location_packs() during integration setup"
        )

    pack = _LOADED_PACKS.get(pack_id)

    if not pack or not pack.get("locations"):
        _LOGGER.error("Location pack not loaded: %s", pack_id)
        return []

    return [loc["name"] for loc in pack["locations"]]


async def preload_location_packs(hass: HomeAssistant) -> None:
    """Preload all location packs at integration startup.

    Should be called from async_setup_entry.
    """
    integration_dir = Path(__file__).parent.parent
    content_dir = integration_dir / "content"

    if not content_dir.exists():
        _LOGGER.warning("Content directory not found: %s", content_dir)
        return

    # Load all .json files in content directory
    for json_file in content_dir.glob("*.json"):
        if json_file.name == "schema.json":
            continue  # Skip schema file

        pack_id = json_file.stem
        await hass.async_add_executor_job(load_location_pack, hass, pack_id)
