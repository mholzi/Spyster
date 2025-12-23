# Story 1.1: Initialize Project Structure and HA Integration

Status: ready-for-dev

## Story

As a **developer**,
I want **the Spyster custom component initialized with proper structure**,
So that **I have a working foundation following Beatify patterns**.

## Acceptance Criteria

1. **Given** a fresh Home Assistant installation
   **When** the Spyster integration is loaded
   **Then** the integration registers successfully without errors
   **And** `hass.data["spyster"]` is initialized for state storage
   **And** the directory structure follows Beatify pattern

2. **Given** the manifest.json is configured
   **When** HACS scans for integrations
   **Then** Spyster appears as installable with correct metadata

## Tasks / Subtasks

- [ ] **Task 1: Create directory structure following Beatify pattern** (AC: #1)
  - [ ] Create `custom_components/spyster/` base directory
  - [ ] Create `game/`, `server/`, `www/`, `content/`, `translations/` subdirectories
  - [ ] Create `www/js/` and `www/css/` subdirectories
  - [ ] Create all `__init__.py` files for Python package structure

- [ ] **Task 2: Create manifest.json with HACS metadata** (AC: #2)
  - [ ] Define integration metadata (domain, name, version)
  - [ ] Specify Home Assistant minimum version (2025.11+)
  - [ ] Set dependencies (aiohttp bundled with HA)
  - [ ] Configure integration type and requirements

- [ ] **Task 3: Implement async_setup_entry in __init__.py** (AC: #1)
  - [ ] Create entry point following HA integration pattern
  - [ ] Initialize `hass.data[DOMAIN]` for state storage
  - [ ] Register integration with Home Assistant
  - [ ] Implement proper error handling and logging

- [ ] **Task 4: Create const.py with essential constants** (AC: #1)
  - [ ] Define DOMAIN constant
  - [ ] Define configuration keys
  - [ ] Set up logging configuration
  - [ ] Establish error code constants foundation

- [ ] **Task 5: Create basic GameState class skeleton** (AC: #1)
  - [ ] Implement GamePhase enum (LOBBY, ROLES, QUESTIONING, VOTE, REVEAL, SCORING, END, PAUSED)
  - [ ] Create GameState class with phase management
  - [ ] Initialize timer dictionary pattern
  - [ ] Set up basic state storage structure

- [ ] **Task 6: Verify integration loads without errors** (AC: #1, #2)
  - [ ] Test integration installation in HA
  - [ ] Verify no errors in HA logs during load
  - [ ] Confirm `hass.data["spyster"]` is accessible
  - [ ] Validate HACS recognition (if applicable)

## Dev Notes

### Architecture Patterns to Follow

**Beatify Blueprint Pattern:**
- Follow proven production patterns from Beatify custom component
- Real-time multiplayer game architecture with WebSocket support
- Server-authoritative state management
- Phase-based game flow

**Home Assistant Integration Standards:**
- Use `async_setup_entry()` as entry point in `__init__.py`
- Store integration state in `hass.data[DOMAIN]`
- Implement proper cleanup with `async_unload_entry()`
- Follow HA logging conventions with `_LOGGER = logging.getLogger(__name__)`

**Phase State Machine Foundation:**
- GamePhase enum: LOBBY, ROLES, QUESTIONING, VOTE, REVEAL, SCORING, END, PAUSED
- All phases must be defined in this story (enum completeness)
- Phase transitions follow documented flow (no skipping phases)
- This story implements phase=LOBBY initialization only
- Future stories will implement phase transitions (LOBBY → ROLES, etc.)
- Any phase can transition to PAUSED on host disconnect
- PAUSED can return to previous phase on host reconnect

**Critical Implementation Rules:**
- **Async everywhere**: All I/O operations use `async/await`
- **Type hints**: Use `TYPE_CHECKING` guards for imports to avoid circular dependencies
- **Constants in const.py**: NEVER hardcode values - all constants go in `const.py`
- **State storage**: Use `hass.data[DOMAIN]` for integration-wide state

### Project Structure to Create

```
custom_components/spyster/
├── __init__.py              # Entry point - async_setup_entry() ONLY
├── manifest.json            # HACS metadata, dependencies
├── const.py                 # ALL constants, error codes, config values
├── game/
│   ├── __init__.py          # Package initialization
│   └── state.py             # GameState class (create skeleton in this story)
├── server/
│   └── __init__.py          # Package initialization
├── www/
│   ├── js/                  # JavaScript files (empty for now)
│   └── css/                 # CSS files (empty for now)
├── content/
│   └── (empty for now)      # Location packs will go here
└── translations/
    └── (empty for now)      # i18n files will go here
```

### Technology Stack

| Technology | Version | Notes |
|------------|---------|-------|
| Python | 3.12+ | HA 2025.11 requirement |
| Home Assistant | 2025.11+ | Target platform |
| aiohttp | HA bundled | WebSocket + HTTP support |

### Python Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `GameState`, `GamePhase`)
- **Functions**: `snake_case()` (e.g., `async_setup_entry()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DOMAIN`, `CONF_*`)
- **Private**: `_leading_underscore` (e.g., `_timers`, `_logger`)

### Manifest.json Requirements

**Required Fields:**
- `domain`: "spyster"
- `name`: "Spyster"
- `version`: "0.1.0" (initial version)
- `documentation`: GitHub repository URL
- `requirements`: [] (no external dependencies)
- `dependencies`: [] (uses HA bundled libraries)
- `codeowners`: ["@markusholzhaeuser"] or appropriate GitHub handle
- `iot_class`: "local_push" (local network, real-time updates)
- `after_dependencies`: []

**Critical Metadata:**
- `homeassistant`: "2025.11.0" (minimum HA version)
- `integration_type`: "service" (provides game service)

### const.py Essential Constants

```python
"""Constants for Spyster integration."""
from enum import Enum

# Integration domain
DOMAIN = "spyster"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"

# Error codes foundation (expand in future stories)
ERR_INVALID_MESSAGE = "INVALID_MESSAGE"
ERR_INTERNAL = "INTERNAL"

# Game configuration defaults
DEFAULT_ROUND_DURATION = 420  # 7 minutes in seconds
DEFAULT_ROUND_COUNT = 5
DEFAULT_VOTE_DURATION = 60  # 60 seconds

# Timer types
TIMER_ROUND = "round"
TIMER_VOTE = "vote"
TIMER_ROLE_DISPLAY = "role_display"
TIMER_REVEAL_DELAY = "reveal_delay"

# Disconnect handling
DISCONNECT_GRACE_PERIOD = 30  # seconds
RECONNECT_WINDOW = 300  # 5 minutes in seconds
```

### __init__.py Entry Point Pattern

```python
"""Spyster integration for Home Assistant."""
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spyster from a config entry."""
    _LOGGER.info("Setting up Spyster integration")

    # Initialize integration data storage
    hass.data.setdefault(DOMAIN, {})

    # Store config entry data
    hass.data[DOMAIN]["config"] = entry.data

    _LOGGER.info("Spyster integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Spyster integration")

    # Clean up integration data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True
```

### GameState Skeleton Pattern

```python
"""Game state management for Spyster."""
import asyncio
import logging
from enum import Enum
from typing import Callable

_LOGGER = logging.getLogger(__name__)


class GamePhase(Enum):
    """Game phase enumeration.

    All phases must be defined here even though this story only uses LOBBY.
    Future stories will implement phase transitions.
    """
    LOBBY = "LOBBY"
    ROLES = "ROLES"
    QUESTIONING = "QUESTIONING"
    VOTE = "VOTE"
    REVEAL = "REVEAL"
    SCORING = "SCORING"
    END = "END"
    PAUSED = "PAUSED"


class GameState:
    """Manages game state and phase transitions.

    Timer Types Used Across Game:
    - 'round': Configurable round timer (default 7min) - triggers QUESTIONING → VOTE
    - 'vote': 60s voting timer - triggers VOTE → REVEAL
    - 'role_display': 5s role reveal - triggers ROLES → QUESTIONING
    - 'reveal_delay': 3s dramatic pause - triggers REVEAL → SCORING
    - 'disconnect_grace:{player}': 30s grace period per player
    - 'reconnect_window:{player}': 5min reconnection window per player
    """

    def __init__(self) -> None:
        """Initialize game state."""
        self.phase: GamePhase = GamePhase.LOBBY
        self._timers: dict[str, asyncio.Task] = {}
        self.players: dict[str, any] = {}  # PlayerSession objects (populated in Story 2.3)

        _LOGGER.info("GameState initialized: phase=%s", self.phase.value)

    def start_timer(self, name: str, duration: float, callback: Callable) -> None:
        """Start a named timer, cancelling any existing timer with same name.

        Args:
            name: Timer identifier (e.g., 'round', 'vote', 'disconnect_grace:Alice')
            duration: Timer duration in seconds
            callback: Async function to call when timer expires
        """
        self.cancel_timer(name)
        self._timers[name] = asyncio.create_task(
            self._timer_task(name, duration, callback)
        )
        _LOGGER.debug("Timer started: %s (duration: %.1fs)", name, duration)

    def cancel_timer(self, name: str) -> None:
        """Cancel a specific timer by name."""
        if name in self._timers and not self._timers[name].done():
            self._timers[name].cancel()
            del self._timers[name]
            _LOGGER.debug("Timer cancelled: %s", name)

    def cancel_all_timers(self) -> None:
        """Cancel all active timers (game end cleanup)."""
        for name, task in list(self._timers.items()):
            if not task.done():
                task.cancel()
        self._timers.clear()
        _LOGGER.debug("All timers cancelled")

    async def _timer_task(self, name: str, duration: float, callback: Callable) -> None:
        """Internal timer task coroutine."""
        try:
            await asyncio.sleep(duration)
            _LOGGER.info("Timer expired: %s", name)
            await callback(name)
        except asyncio.CancelledError:
            _LOGGER.debug("Timer task cancelled: %s", name)
            raise
```

### Anti-Patterns to Avoid

**BAD - Business logic in __init__.py:**
```python
# NEVER do this - __init__.py should only handle setup
# Problem: Makes integration hard to test and couples setup to game logic
async def async_setup_entry(hass, entry):
    game_state = GameState()
    game_state.start_game()  # NO! Game logic doesn't belong in entry point
```

**GOOD - Keep __init__.py minimal:**
```python
# Only setup and registration in __init__.py
# This is testable and follows HA conventions
async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = entry.data
    return True
```

**BAD - Hardcoded values:**
```python
# NEVER hardcode - makes values impossible to configure or test
self.round_duration = 420  # NO! Magic number, unclear what 420 means
```

**GOOD - Use constants:**
```python
# Constants have names that explain their purpose
from .const import DEFAULT_ROUND_DURATION
self.round_duration = DEFAULT_ROUND_DURATION  # YES! Clear and configurable
```

**BAD - Missing type hints:**
```python
# Missing type hints make code harder for LLMs and humans to understand
def __init__(self):  # NO! What does this return? What type is phase?
    self.phase = GamePhase.LOBBY
```

**GOOD - With type hints:**
```python
# Type hints make code self-documenting and enable IDE/LLM assistance
def __init__(self) -> None:  # YES! Clear that it returns nothing
    self.phase: GamePhase = GamePhase.LOBBY  # Clear that phase is GamePhase enum
```

### Testing Requirements

**Unit Tests to Create:**
- Test `async_setup_entry()` initializes `hass.data[DOMAIN]`
- Test `async_unload_entry()` cleans up properly
- Test `GamePhase` enum has all required phases
- Test `GameState` initializes with LOBBY phase
- Test timer dictionary starts empty
- Test basic timer start/cancel functionality

**Integration Test:**
- Load integration in test HA instance
- Verify no errors in logs
- Verify `hass.data["spyster"]` exists and is dict

### Security Considerations

**This Story:**
- No security-sensitive code in this initialization story
- Foundation only - security patterns implemented in role assignment story

**Future Stories Will Implement:**
- Spy assignment using `secrets.choice()` (CSPRNG)
- Per-player state filtering with `get_state(for_player=name)`
- Role privacy in WebSocket payloads

### Performance Considerations

**This Story:**
- Minimal performance impact - initialization only
- No blocking I/O operations
- Timer dictionary pattern enables efficient concurrent timers

**Design Choices for Future Performance:**
- Named timer dict allows O(1) timer lookup and cancellation
- Server-authoritative state prevents client-side manipulation
- Phase guards prevent invalid state transitions

### References

**Source Documents:**
- [Architecture: Starter Template Evaluation - Beatify Blueprint](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#starter-template-evaluation)
- [Architecture: Game State Architecture - Phase State Machine](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#game-state-architecture)
- [Architecture: Timer Architecture - Named Timer Dictionary](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#timer-architecture)
- [Architecture: Project Structure & Boundaries](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#project-structure--boundaries)
- [Project Context: Technology Stack & Versions](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#technology-stack--versions)
- [Project Context: Home Assistant Integration Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#home-assistant-integration-rules)
- [Project Context: Phase State Machine Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#phase-state-machine-rules)
- [Project Context: Timer Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#timer-rules)
- [Epics: Story 1.1 Acceptance Criteria](/Volumes/My Passport/Spyster/_bmad-output/epics.md#story-11-initialize-project-structure-and-ha-integration)

**Epic Context:**
- Epic 1: Project Foundation & Game Session
- Story 1.1 is the foundation for entire integration
- Subsequent stories (1.2-1.4) build upon this structure
- Beatify pattern provides proven multiplayer architecture

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

(To be filled during implementation)

### Completion Notes List

(To be filled during implementation)

### File List

**Files to Create:**
- `custom_components/spyster/__init__.py`
- `custom_components/spyster/manifest.json`
- `custom_components/spyster/const.py`
- `custom_components/spyster/game/__init__.py`
- `custom_components/spyster/game/state.py`
- `custom_components/spyster/server/__init__.py`
- `custom_components/spyster/www/js/` (directory)
- `custom_components/spyster/www/css/` (directory)
- `custom_components/spyster/content/` (directory)
- `custom_components/spyster/translations/` (directory)

**Tests to Create:**
- `tests/test_init.py`
- `tests/test_state.py`
- `tests/conftest.py`
