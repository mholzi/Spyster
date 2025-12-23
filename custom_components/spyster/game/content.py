"""Content pack loading and management."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import secrets
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Cache loaded packs
_LOADED_PACKS: dict[str, "LocationPack"] = {}


# Type definitions for location pack structure (Story 8-2: AC1)
class Role(TypedDict):
    """Role definition within a location."""
    id: str
    name: str
    hint: str


class Location(TypedDict):
    """Location definition with roles."""
    id: str
    name: str
    flavor: str
    roles: list[Role]


class LocationPack(TypedDict):
    """Location pack structure."""
    id: str
    name: str
    description: str
    version: str
    locations: list[Location]


class ContentValidationError(Exception):
    """Raised when content pack validation fails."""
    pass


def validate_location_pack(pack_data: dict, pack_id: str) -> list[str]:
    """Validate a location pack structure (Story 8-2: AC2).

    Args:
        pack_data: The pack data dictionary to validate
        pack_id: Pack identifier for error messages

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    # Required top-level fields (version is optional but recommended)
    required_fields = ["id", "name", "locations"]
    for field in required_fields:
        if field not in pack_data:
            errors.append(f"Pack '{pack_id}' missing required field: {field}")

    # Validate version field format if present
    if "version" in pack_data:
        version = pack_data["version"]
        if not isinstance(version, str) or not version.strip():
            errors.append(f"Pack '{pack_id}' version must be a non-empty string")

    # Validate locations array
    locations = pack_data.get("locations", [])
    if not isinstance(locations, list):
        errors.append(f"Pack '{pack_id}' locations must be an array")
        return errors

    if len(locations) < 1:
        errors.append(f"Pack '{pack_id}' must have at least 1 location")

    # Validate each location
    location_ids = set()
    for i, location in enumerate(locations):
        loc_prefix = f"Pack '{pack_id}' location[{i}]"

        # Required location fields
        if "id" not in location:
            errors.append(f"{loc_prefix} missing 'id' field")
        elif location["id"] in location_ids:
            errors.append(f"{loc_prefix} duplicate id: {location['id']}")
        else:
            location_ids.add(location["id"])

        if "name" not in location:
            errors.append(f"{loc_prefix} missing 'name' field")

        if "roles" not in location:
            errors.append(f"{loc_prefix} missing 'roles' field")
            continue

        roles = location.get("roles", [])
        if not isinstance(roles, list):
            errors.append(f"{loc_prefix} roles must be an array")
            continue

        # Minimum 6 roles per location (Story 8-1: AC2)
        if len(roles) < 6:
            errors.append(f"{loc_prefix} must have at least 6 roles, has {len(roles)}")

        # Validate each role
        role_ids = set()
        for j, role in enumerate(roles):
            role_prefix = f"{loc_prefix} role[{j}]"

            if "id" not in role:
                errors.append(f"{role_prefix} missing 'id' field")
            elif role["id"] in role_ids:
                errors.append(f"{role_prefix} duplicate id: {role['id']}")
            else:
                role_ids.add(role["id"])

            if "name" not in role:
                errors.append(f"{role_prefix} missing 'name' field")

            if "hint" not in role:
                errors.append(f"{role_prefix} missing 'hint' field")

    return errors


def load_location_pack(hass: HomeAssistant, pack_id: str) -> LocationPack | None:
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

        # Validate pack structure (Story 8-2: AC2)
        validation_errors = validate_location_pack(pack_data, pack_id)
        if validation_errors:
            for error in validation_errors:
                _LOGGER.error(error)
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


def get_random_location(pack_id: str) -> Location | None:
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


def get_location_list(pack_id: str) -> list[dict[str, str]]:
    """Get list of all locations in a pack with id and name (for spy display).

    Args:
        pack_id: Pack identifier

    Returns:
        List of location dicts with 'id' and 'name' keys

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

    return [{"id": loc["id"], "name": loc["name"]} for loc in pack["locations"]]


def get_roles_for_location(pack_id: str, location_id: str) -> list[Role]:
    """Get all roles for a specific location (Story 8-2: AC3).

    Args:
        pack_id: Pack identifier
        location_id: Location identifier

    Returns:
        List of Role dicts for the location, or empty list if not found
    """
    if not _LOADED_PACKS:
        raise RuntimeError(
            "No location packs loaded - call preload_location_packs() during integration setup"
        )

    pack = _LOADED_PACKS.get(pack_id)
    if not pack:
        _LOGGER.error("Location pack not found: %s", pack_id)
        return []

    for location in pack.get("locations", []):
        if location.get("id") == location_id:
            return location.get("roles", [])

    _LOGGER.error("Location not found: %s in pack %s", location_id, pack_id)
    return []


def assign_roles_for_location(
    pack_id: str,
    location: Location,
    player_count: int
) -> list[Role]:
    """Assign roles to players for a given location (Story 8-2: AC4).

    Uses CSPRNG to randomly select and shuffle roles for the given number
    of non-spy players (player_count - 1, since one player is the spy).

    Args:
        pack_id: Pack identifier (for logging)
        location: The selected location
        player_count: Total number of players (including the spy)

    Returns:
        List of Role dicts, one for each non-spy player

    Raises:
        ValueError: If not enough roles available for player count
    """
    roles = location.get("roles", [])
    non_spy_count = player_count - 1  # One player is the spy

    if len(roles) < non_spy_count:
        raise ValueError(
            f"Location '{location.get('name')}' has {len(roles)} roles "
            f"but needs {non_spy_count} for {player_count} players"
        )

    # Use CSPRNG to shuffle and select roles
    shuffled_roles = list(roles)  # Create a copy

    # Fisher-Yates shuffle using secrets for cryptographic randomness
    for i in range(len(shuffled_roles) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        shuffled_roles[i], shuffled_roles[j] = shuffled_roles[j], shuffled_roles[i]

    # Return the first non_spy_count roles
    assigned_roles = shuffled_roles[:non_spy_count]

    _LOGGER.debug(
        "Assigned %d roles for location '%s': %s",
        len(assigned_roles),
        location.get("name"),
        [r.get("name") for r in assigned_roles]
    )

    return assigned_roles


def get_location_by_id(pack_id: str, location_id: str) -> Location | None:
    """Get a specific location by ID (Story 8-2: AC5).

    Args:
        pack_id: Pack identifier
        location_id: Location identifier

    Returns:
        Location dict or None if not found
    """
    if not _LOADED_PACKS:
        raise RuntimeError(
            "No location packs loaded - call preload_location_packs() during integration setup"
        )

    pack = _LOADED_PACKS.get(pack_id)
    if not pack:
        return None

    for location in pack.get("locations", []):
        if location.get("id") == location_id:
            return location

    return None


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


def clear_cache() -> None:
    """Clear the loaded packs cache (for testing)."""
    _LOADED_PACKS.clear()
