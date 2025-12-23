# Story 8.2: Content Loading and Validation

Status: completed

## Story

As a **system**,
I want **to load and validate location packs at startup**,
So that **the game uses well-formed content and provides clear errors for malformed packs**.

## Acceptance Criteria

1. **Given** the game starts, **When** a location pack is loaded, **Then** the JSON is parsed and validated against schema with errors logged if content is malformed.

2. **Given** a round begins, **When** a location is selected, **Then** a random location is chosen from the pack (per FR58) using the existing CSPRNG pattern.

3. **Given** `game/content.py` module, **When** content is loaded, **Then** functions are available: `load_location_pack()`, `get_random_location()`, `get_roles_for_location()`.

4. **Given** a location pack with missing required fields, **When** loaded, **Then** clear error message is logged identifying the missing field and the pack is rejected.

5. **Given** roles are assigned, **When** a location is selected, **Then** non-spy players receive a random role from the location's role list.

6. **Given** the game state, **When** location tracking is needed, **Then** optionally prevent repeat locations until all used (enhancement).

## Tasks / Subtasks

- [x] Task 1: Create `game/content.py` module (AC: 3)
  - [x] 1.1: Create module file with proper imports and logging setup
  - [x] 1.2: Implement `load_location_pack(pack_id: str) -> LocationPack | None`
  - [x] 1.3: Implement `get_random_location(pack: LocationPack) -> Location`
  - [x] 1.4: Implement `get_roles_for_location(location: Location) -> list[Role]`
  - [x] 1.5: Add type hints using TypedDict for Location, Role, LocationPack

- [x] Task 2: Implement JSON loading with validation (AC: 1, 4)
  - [x] 2.1: Load JSON file from `content/` directory using `hass.async_add_executor_job()` for file I/O
  - [x] 2.2: Validate required pack fields: id, name, locations
  - [x] 2.3: Validate each location has: id, name, roles (array with 6+ items)
  - [x] 2.4: Validate each role has: id, name, hint
  - [x] 2.5: Log clear error messages for validation failures

- [x] Task 3: Implement random location selection (AC: 2)
  - [x] 3.1: Use `secrets.choice()` for CSPRNG-based selection (per Architecture security requirements)
  - [x] 3.2: Return Location object with all metadata

- [x] Task 4: Implement role assignment helper (AC: 5)
  - [x] 4.1: `assign_roles_for_location(pack_id, location, player_count) -> list[Role]`
  - [x] 4.2: Raise ValueError if player_count > role_count (enforce minimum roles)
  - [x] 4.3: Use Fisher-Yates shuffle with secrets.randbelow() for CSPRNG role distribution

- [x] Task 5: Add constants to const.py (AC: 1, 4)
  - [x] 5.1: Content directory path derived from module location
  - [x] 5.2: DEFAULT_PACK already exists in const.py
  - [x] 5.3: ContentValidationError class for validation failures

## Dev Notes

### Architecture Compliance

**File Location:** `custom_components/spyster/game/content.py`

**Required Patterns:**
```python
# game/content.py
import json
import secrets
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Type definitions
class Role:
    id: str
    name: str
    hint: str | None

class Location:
    id: str
    name: str
    flavor: str | None
    roles: list[Role]

class LocationPack:
    id: str
    name: str
    description: str
    version: str
    locations: list[Location]
```

### Critical Implementation Rules

**From project-context.md:**
- **File I/O**: Use `hass.async_add_executor_job()` for blocking file operations
- **CSPRNG**: Use `secrets.choice()` for random selection (security requirement)
- **Logging**: Always `_LOGGER = logging.getLogger(__name__)` with context
- **Constants**: Never hardcode - add to const.py

### Function Signatures

```python
async def load_location_pack(hass: HomeAssistant, pack_id: str) -> LocationPack | None:
    """
    Load and validate a location pack from content directory.

    Args:
        hass: Home Assistant instance for async file I/O
        pack_id: Pack identifier (e.g., "classic")

    Returns:
        LocationPack if valid, None if not found or invalid
    """

def get_random_location(pack: LocationPack) -> Location:
    """
    Select a random location from pack using CSPRNG.

    Args:
        pack: Validated location pack

    Returns:
        Randomly selected Location
    """

def get_roles_for_location(location: Location) -> list[Role]:
    """
    Get all available roles for a location.

    Args:
        location: Location object

    Returns:
        List of Role objects
    """

def assign_roles_for_location(
    location: Location,
    player_count: int,
    exclude_spy: bool = True
) -> list[Role]:
    """
    Randomly assign roles to players.

    Args:
        location: Location object
        player_count: Number of non-spy players needing roles
        exclude_spy: Reserved for future spy role in location

    Returns:
        List of Role objects, one per player
    """
```

### Error Handling Pattern

```python
# Good - detailed logging with context
_LOGGER.error(
    "Location pack validation failed: %s - missing field '%s'",
    pack_id,
    field_name
)

# Good - return pattern for content module
async def load_location_pack(hass, pack_id: str) -> LocationPack | None:
    try:
        # ... load and validate
        return pack
    except FileNotFoundError:
        _LOGGER.error("Location pack not found: %s", pack_id)
        return None
    except json.JSONDecodeError as e:
        _LOGGER.error("Location pack JSON invalid: %s - %s", pack_id, e)
        return None
```

### Testing Notes

- Pure functions in content.py allow easy unit testing
- Mock `hass.async_add_executor_job()` for async tests
- Test validation with intentionally malformed JSON fixtures

### Project Structure Notes

- Path: `custom_components/spyster/game/content.py`
- Depends on: `const.py` for paths and error codes
- Used by: `game/roles.py` for role assignment during game start
- Content files: `content/*.json`

### Integration with Existing Modules

**Integration with `game/roles.py`:**
The existing `roles.py` module handles spy assignment. This story adds role assignment for non-spy players:

```python
# In roles.py, after spy assignment:
from .content import load_location_pack, get_random_location, assign_roles_for_location

# During game start:
pack = await load_location_pack(hass, game_config.location_pack)
location = get_random_location(pack)
non_spy_roles = assign_roles_for_location(location, len(non_spy_players))

# Assign roles to non-spy players
for player, role in zip(non_spy_players, non_spy_roles):
    player.role = role
    player.location = location
```

**Update `game/__init__.py`:**
Export the new content functions for use by other modules.

### References

- [Source: _bmad-output/architecture.md#Content Architecture] - Schema and loading patterns
- [Source: _bmad-output/architecture.md#Security Architecture] - CSPRNG requirements
- [Source: _bmad-output/project-context.md#Python Rules] - File I/O patterns
- [Source: _bmad-output/epics.md#Story 8.2] - Original acceptance criteria

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Implemented comprehensive content.py module with TypedDict type definitions (Role, Location, LocationPack)
- Added validate_location_pack() function that returns list of validation errors
- Implemented get_roles_for_location() to retrieve roles for a specific location by ID
- Implemented assign_roles_for_location() with Fisher-Yates shuffle using secrets.randbelow() for CSPRNG
- Added get_location_by_id() helper function for retrieving specific locations
- Implemented preload_location_packs() for async loading at integration startup
- Added clear_cache() for testing support
- All functions include proper error handling and logging

### File List

- [x] `custom_components/spyster/game/content.py`
- [x] `custom_components/spyster/const.py` (existing constants used)
