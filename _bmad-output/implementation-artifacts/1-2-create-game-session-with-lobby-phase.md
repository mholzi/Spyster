# Story 1.2: Create Game Session with Lobby Phase

Status: ready-for-dev

## Story

As a **host**,
I want **to create a new game session**,
So that **I can start hosting a Spyster game**.

## Acceptance Criteria

1. **Given** Spyster integration is loaded
   **When** the host accesses `/api/spyster/host` endpoint
   **Then** a new game session is created automatically
   **And** the session has `session_id`, `created_at`, and `host_id` populated
   **And** the phase is set to LOBBY

2. **Given** a game session exists in LOBBY phase
   **When** the host views the game page
   **Then** the lobby is displayed showing "Waiting for players..."
   **And** the game phase is clearly indicated

3. **Given** GameState class is initialized
   **When** phase transitions are attempted
   **Then** only valid transitions per the phase state machine are allowed

## Tasks / Subtasks

- [ ] **Task 1: Enhance GameState with session initialization** (AC: #1)
  - [ ] Add session metadata fields as instance variables (initialize to None in __init__)
  - [ ] Implement `create_session()` method to initialize new game
  - [ ] Use `secrets.token_urlsafe()` for session ID generation
  - [ ] Add session metadata tracking (created_at, host_id)
  - [ ] Initialize game configuration with defaults from const.py

- [ ] **Task 2: Implement phase transition validation** (AC: #3)
  - [ ] Add VALID_TRANSITIONS dict to const.py with complete phase map
  - [ ] Create `can_transition()` method to validate phase changes
  - [ ] Implement `transition_to()` method with validation and logging
  - [ ] Handle PAUSED special case (store previous_phase)
  - [ ] Add previous_phase field to GameState.__init__

- [ ] **Task 3: Add state retrieval methods** (AC: #2)
  - [ ] Implement `get_state()` method with optional for_player parameter
  - [ ] Return public game state (phase, player_count, config)
  - [ ] Prepare structure for future per-player filtering (Story 3.4)
  - [ ] Add lobby-specific state fields (waiting_for_players flag)

- [ ] **Task 4: Create basic Host view HTTP endpoint** (AC: #1, #2)
  - [ ] Create `server/views.py` with HostView class
  - [ ] Subclass HomeAssistantView with requires_auth=False
  - [ ] Implement GET handler to serve host.html
  - [ ] Register view in __init__.py during async_setup_entry
  - [ ] Initialize GameState instance in async_setup_entry and store in hass.data
  - [ ] Call create_session() when host view is first accessed

- [ ] **Task 5: Create minimal host.html page** (AC: #2)
  - [ ] Create `www/host.html` with basic structure
  - [ ] Add phase indicator showing "LOBBY"
  - [ ] Display "Waiting for players..." message
  - [ ] Include viewport meta for responsive display
  - [ ] Add placeholder for future QR code display (Story 1.3)

- [ ] **Task 6: Add error code constants** (AC: #3)
  - [ ] Add ERR_INVALID_PHASE to const.py
  - [ ] Add ERR_SESSION_EXISTS for duplicate session prevention
  - [ ] Create ERROR_MESSAGES dict in const.py for user-friendly messages
  - [ ] Add VALID_TRANSITIONS dict to const.py (complete phase transition map)
  - [ ] Add MIN_PLAYERS and MAX_PLAYERS constants
  - [ ] Document phase transition error scenarios in comments

- [ ] **Task 7: Unit tests for phase transitions** (AC: #3)
  - [ ] Test valid transitions (LOBBY→ROLES)
  - [ ] Test invalid transitions (LOBBY→VOTE blocked)
  - [ ] Test PAUSED can be entered from any phase
  - [ ] Test PAUSED returns to previous phase on resume

- [ ] **Task 8: Integration test for lobby display** (AC: #1, #2)
  - [ ] Test session creation initializes with LOBBY phase
  - [ ] Test host view endpoint returns HTML
  - [ ] Verify "Waiting for players..." appears in rendered HTML
  - [ ] Confirm phase indicator shows "LOBBY"

## Dev Notes

### Architecture Patterns to Follow

**Phase State Machine Implementation:**
- This story implements the phase transition validation system
- All future state mutations MUST use phase guards
- Phase transitions follow documented flow (no skipping)
- PAUSED can be entered from any phase (host disconnect)
- PAUSED returns to previous phase on resume

**Server-Authoritative State:**
- All game state lives in GameState class on server
- Client views are read-only displays of server state
- No client-side state mutations allowed
- State changes broadcast to all connected clients (Story 2.1)

**Critical Implementation Rules:**
- **Phase guards**: ALWAYS validate current phase before state-mutating actions
- **Return pattern**: `(success: bool, error_code: str | None)` for all actions
- **Logging**: Include context (phase, player_count) in all log messages
- **Constants**: All error codes and defaults in const.py

### Phase Transition Map (Lives in const.py)

**Valid Transitions:**
See const.py additions section below for VALID_TRANSITIONS dict definition.

**Implementation in GameState:**
```python
def can_transition(self, to_phase: GamePhase) -> tuple[bool, str | None]:
    """Validate if phase transition is allowed.

    Returns:
        (True, None) if valid
        (False, ERR_INVALID_PHASE) if blocked
    """
    from .const import VALID_TRANSITIONS, ERR_INVALID_PHASE

    # VALID_TRANSITIONS uses string keys to avoid circular import
    valid_next_strs = VALID_TRANSITIONS.get(self.phase.value, [])
    if to_phase.value not in valid_next_strs:
        _LOGGER.warning(
            "Invalid phase transition blocked: %s → %s",
            self.phase.value,
            to_phase.value
        )
        return False, ERR_INVALID_PHASE
    return True, None
```

### GameState Enhancements

**Session Initialization:**
```python
class GameState:
    """Manages game state and phase transitions.

    NOTE: Story 1.1 already implements __init__ with phase, _timers, and players.
    This story ADDS session metadata fields and game configuration fields to __init__.
    """

    def __init__(self) -> None:
        """Initialize game state.

        Story 1.1 provides: phase, _timers, players
        Story 1.2 adds: session metadata and game configuration
        """
        # Story 1.1 fields (already implemented)
        self.phase: GamePhase = GamePhase.LOBBY
        self._timers: dict[str, asyncio.Task] = {}
        self.players: dict[str, any] = {}

        # Story 1.2 additions
        self.previous_phase: GamePhase | None = None  # For PAUSED resume

        # Session metadata (populated by create_session())
        self.session_id: str | None = None
        self.created_at: float | None = None
        self.host_id: str | None = None

        # Game configuration (defaults from const.py)
        self.round_duration: int = DEFAULT_ROUND_DURATION
        self.round_count: int = DEFAULT_ROUND_COUNT
        self.vote_duration: int = DEFAULT_VOTE_DURATION
        self.location_pack: str = "classic"

        # Game state
        self.current_round: int = 0
        self.player_count: int = 0

        _LOGGER.info("GameState initialized: phase=%s", self.phase.value)

    def create_session(self, host_id: str) -> str:
        """Create a new game session.

        Args:
            host_id: Identifier for the host player

        Returns:
            session_id: Unique session identifier
        """
        import secrets
        import time

        self.session_id = secrets.token_urlsafe(16)
        self.created_at = time.time()
        self.host_id = host_id
        self.phase = GamePhase.LOBBY

        _LOGGER.info(
            "Game session created: session_id=%s, host=%s",
            self.session_id,
            host_id
        )

        return self.session_id
```

**State Retrieval with Future Player Filtering:**
```python
def get_state(self, for_player: str | None = None) -> dict:
    """Get game state, optionally filtered for specific player.

    Args:
        for_player: Player name to filter sensitive data (used in Story 3.4)

    Returns:
        dict: Game state with public fields, personalized if for_player provided

    Note:
        This story implements public state only.
        Story 3.4 will add per-player role filtering.
    """
    state = {
        "session_id": self.session_id,
        "phase": self.phase.value,
        "player_count": self.player_count,
        "current_round": self.current_round,
        "round_count": self.round_count,
        "created_at": self.created_at,
    }

    # Lobby-specific state
    if self.phase == GamePhase.LOBBY:
        state["waiting_for_players"] = True
        state["min_players"] = 4
        state["max_players"] = 10

    # Future stories will add per-player filtering here
    # if for_player:
    #     state["role"] = self._get_player_role(for_player)
    #     state["is_spy"] = self._is_spy(for_player)

    return state
```

**Phase Transition with Validation:**
```python
def transition_to(self, new_phase: GamePhase) -> tuple[bool, str | None]:
    """Transition to a new phase with validation.

    Args:
        new_phase: Target phase

    Returns:
        (success, error_code): True if successful, False with error code if blocked
    """
    # Validate transition
    can_transition, error = self.can_transition(new_phase)
    if not can_transition:
        return False, error

    # Handle PAUSED special case
    if new_phase == GamePhase.PAUSED:
        self.previous_phase = self.phase
        _LOGGER.info("Game paused: previous_phase=%s", self.previous_phase.value)
    elif self.phase == GamePhase.PAUSED and self.previous_phase:
        # Resuming from pause - validate against stored previous phase
        _LOGGER.info("Resuming from pause: %s → %s", self.phase.value, new_phase.value)

    old_phase = self.phase
    self.phase = new_phase

    _LOGGER.info(
        "Phase transition: %s → %s (players: %d)",
        old_phase.value,
        new_phase.value,
        self.player_count
    )

    return True, None
```

### Host View Implementation

**server/views.py Creation:**
```python
"""HTTP views for Spyster integration."""
import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class HostView(HomeAssistantView):
    """Serve the host display page."""

    url = "/api/spyster/host"
    name = "api:spyster:host"
    requires_auth = False  # Frictionless access for local network

    async def get(self, request: web.Request) -> web.Response:
        """Serve host.html."""
        _LOGGER.debug("Host view requested")

        # Get integration directory
        integration_dir = Path(__file__).parent.parent
        host_html_path = integration_dir / "www" / "host.html"

        if not host_html_path.exists():
            _LOGGER.error("host.html not found at %s", host_html_path)
            return web.Response(
                text="Host page not found",
                status=404
            )

        with open(host_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return web.Response(
            text=html_content,
            content_type="text/html"
        )
```

**Registration in __init__.py (additions to Story 1.1):**
```python
"""Spyster integration for Home Assistant."""
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass

from .const import DOMAIN
from .server.views import HostView  # NEW in Story 1.2
from .game.state import GameState   # NEW in Story 1.2

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spyster from a config entry."""
    _LOGGER.info("Setting up Spyster integration")

    # Initialize integration data storage (Story 1.1)
    hass.data.setdefault(DOMAIN, {})

    # Store config entry data (Story 1.1)
    hass.data[DOMAIN]["config"] = entry.data

    # NEW in Story 1.2: Initialize game state
    game_state = GameState()
    hass.data[DOMAIN]["game_state"] = game_state

    # NEW in Story 1.2: Register HTTP views
    hass.http.register_view(HostView())
    _LOGGER.debug("Registered HostView at /api/spyster/host")

    _LOGGER.info("Spyster integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Spyster integration")

    # Cancel all timers
    if DOMAIN in hass.data and "game_state" in hass.data[DOMAIN]:
        game_state = hass.data[DOMAIN]["game_state"]
        game_state.cancel_all_timers()

    # Clean up integration data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True
```

### Host HTML Template

**www/host.html:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <title>Spyster - Host Display</title>
    <style>
        /* Mobile-first responsive design */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #0a0a12;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }

        .phase-indicator {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #ff2d6a;
            margin-bottom: 2rem;
            text-transform: uppercase;
        }

        .lobby-message {
            font-size: 1.25rem;
            color: #a0a0b0;
            margin-bottom: 3rem;
        }

        .qr-placeholder {
            width: 200px;
            height: 200px;
            background-color: #1a1a24;
            border: 2px dashed #ff2d6a;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 0.875rem;
        }

        /* Tablet/TV optimized (768px+) */
        @media (min-width: 768px) {
            .phase-indicator {
                font-size: 3rem;
            }

            .lobby-message {
                font-size: 2rem;
            }

            .qr-placeholder {
                width: 300px;
                height: 300px;
                font-size: 1rem;
            }
        }

        /* Large display (1200px+) */
        @media (min-width: 1200px) {
            .phase-indicator {
                font-size: 4rem;
            }

            .lobby-message {
                font-size: 2.5rem;
            }

            .qr-placeholder {
                width: 400px;
                height: 400px;
                font-size: 1.25rem;
            }
        }
    </style>
</head>
<body>
    <div class="phase-indicator" id="phase-indicator">LOBBY</div>
    <div class="lobby-message" id="lobby-message">Waiting for players...</div>
    <div class="qr-placeholder" id="qr-code">
        QR Code (Story 1.3)
    </div>

    <script>
        // Story 1.2: Static display only
        // WebSocket connection will be added in Story 2.1
        // QR code generation will be added in Story 1.3
        console.log('Spyster Host Display - Story 1.2');
    </script>
</body>
</html>
```

### Constants to Add

**const.py additions:**
```python
# NOTE: GamePhase enum is defined in game/state.py (Story 1.1)
# VALID_TRANSITIONS must be imported by state.py, not defined with GamePhase literals
# Solution: Define transition map as string literals to avoid circular import

# Phase transition error codes
ERR_INVALID_PHASE = "INVALID_PHASE"
ERR_SESSION_EXISTS = "SESSION_EXISTS"

# Error messages for user display (builds on ERR_INVALID_MESSAGE, ERR_INTERNAL from Story 1.1)
ERROR_MESSAGES = {
    ERR_INVALID_MESSAGE: "Invalid message format.",
    ERR_INTERNAL: "Something went wrong. Please try again.",
    ERR_INVALID_PHASE: "You can't do that right now.",
    ERR_SESSION_EXISTS: "A game session already exists.",
}

# Player constraints
MIN_PLAYERS = 4
MAX_PLAYERS = 10

# Phase transition validation map (using string literals to avoid circular import)
# GameState.can_transition() will convert these to GamePhase enum values
VALID_TRANSITIONS = {
    "LOBBY": ["ROLES", "PAUSED"],
    "ROLES": ["QUESTIONING", "PAUSED"],
    "QUESTIONING": ["VOTE", "PAUSED"],
    "VOTE": ["REVEAL", "PAUSED"],
    "REVEAL": ["SCORING", "PAUSED"],
    "SCORING": ["ROLES", "END", "PAUSED"],
    "END": ["LOBBY", "PAUSED"],
    "PAUSED": ["LOBBY", "ROLES", "QUESTIONING", "VOTE", "REVEAL", "SCORING"],
}
```

### Anti-Patterns to Avoid

**BAD - Missing phase validation:**
```python
# NEVER allow state changes without phase checks
# Problem: Can create invalid game states
def start_game(self):
    self.phase = GamePhase.ROLES  # NO! No validation, could be in END phase
```

**GOOD - Always validate phase:**
```python
# Phase validation prevents invalid transitions
# Returns error code for proper error handling
def start_game(self) -> tuple[bool, str | None]:
    if self.phase != GamePhase.LOBBY:
        return False, ERR_INVALID_PHASE

    success, error = self.transition_to(GamePhase.ROLES)
    return success, error
```

**BAD - Hardcoded phase strings:**
```python
# NEVER use string literals for phases
# Problem: Typos cause silent failures
if state["phase"] == "LOBY":  # NO! Typo, will never match
```

**GOOD - Use enum:**
```python
# Enum provides type safety and autocomplete
# Typos caught at development time
if self.phase == GamePhase.LOBBY:  # YES! Type-safe
```

**BAD - Same state broadcast to all players:**
```python
# NEVER send same state to everyone
# Problem: Will leak role data in future stories
for player in players:
    await send(game_state.get_state())  # NO! Everyone gets same data
```

**GOOD - Per-player state filtering:**
```python
# Each player gets personalized state
# Prevents role leakage (critical for Story 3.4)
for player_name in players:
    state = game_state.get_state(for_player=player_name)
    await send(state)  # YES! Personalized per player
```

**BAD - No logging context:**
```python
# Missing context makes debugging impossible
_LOGGER.info("Phase changed")  # NO! Changed from what to what?
```

**GOOD - Include context:**
```python
# Context helps trace game flow
_LOGGER.info(
    "Phase transition: %s → %s (players: %d)",
    old_phase.value,
    new_phase.value,
    self.player_count
)  # YES! Clear what happened
```

### Testing Requirements

**Unit Tests for Phase Transitions:**
```python
# tests/test_state.py additions

def test_lobby_to_roles_transition(game_state):
    """Test valid transition from LOBBY to ROLES."""
    game_state.phase = GamePhase.LOBBY
    success, error = game_state.transition_to(GamePhase.ROLES)
    assert success is True
    assert error is None
    assert game_state.phase == GamePhase.ROLES

def test_lobby_to_vote_blocked(game_state):
    """Test invalid transition from LOBBY to VOTE is blocked."""
    game_state.phase = GamePhase.LOBBY
    success, error = game_state.transition_to(GamePhase.VOTE)
    assert success is False
    assert error == ERR_INVALID_PHASE
    assert game_state.phase == GamePhase.LOBBY  # Phase unchanged

def test_pause_from_any_phase(game_state):
    """Test PAUSED can be entered from any phase."""
    for phase in [GamePhase.LOBBY, GamePhase.ROLES, GamePhase.QUESTIONING]:
        game_state.phase = phase
        success, error = game_state.transition_to(GamePhase.PAUSED)
        assert success is True
        assert game_state.previous_phase == phase

def test_resume_from_pause(game_state):
    """Test resume from PAUSED returns to previous phase."""
    game_state.phase = GamePhase.QUESTIONING
    game_state.transition_to(GamePhase.PAUSED)

    success, error = game_state.transition_to(GamePhase.QUESTIONING)
    assert success is True
    assert game_state.phase == GamePhase.QUESTIONING

def test_session_creation(game_state):
    """Test session initialization."""
    session_id = game_state.create_session("host_player")

    assert game_state.session_id is not None
    assert len(game_state.session_id) > 0
    assert game_state.host_id == "host_player"
    assert game_state.phase == GamePhase.LOBBY
    assert game_state.created_at is not None

def test_get_state_lobby(game_state):
    """Test get_state returns lobby-specific fields."""
    game_state.create_session("host")
    state = game_state.get_state()

    assert state["phase"] == "LOBBY"
    assert state["waiting_for_players"] is True
    assert state["min_players"] == 4
    assert state["max_players"] == 10
```

**Integration Test:**
```python
# tests/test_views.py

async def test_host_view_returns_html(hass, hass_client):
    """Test HostView serves host.html."""
    client = await hass_client()
    resp = await client.get("/api/spyster/host")

    assert resp.status == 200
    assert resp.content_type == "text/html"

    text = await resp.text()
    assert "LOBBY" in text
    assert "Waiting for players..." in text
```

### Security Considerations

**This Story:**
- No security-sensitive code in this story
- Phase validation prevents invalid state manipulation
- Foundation for future role privacy (Story 3.4)

**Future Security Implementation:**
- Story 3.4 will add per-player state filtering
- Role data never sent to wrong players
- Spy assignment uses secrets.choice() (Story 3.3)

### Performance Considerations

**This Story:**
- Minimal performance impact - state retrieval is O(1)
- Phase validation is simple enum comparison
- HTML file served from disk (cached by browser)

**Design Choices:**
- Named timer dict enables O(1) timer management
- State dictionary construction is lightweight
- No database queries or external API calls

### References

**Source Documents:**
- [Architecture: Game State Architecture - Phase State Machine](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#game-state-architecture)
- [Architecture: API & Communication Patterns - WebSocket Protocol](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#api--communication-patterns)
- [Architecture: Implementation Patterns - Process Patterns - Phase Guards](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#process-patterns)
- [Project Context: Phase State Machine Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#phase-state-machine-rules)
- [Project Context: Home Assistant Integration Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#home-assistant-integration-rules)
- [Epics: Story 1.2 Acceptance Criteria](/Volumes/My Passport/Spyster/_bmad-output/epics.md#story-12-create-game-session-with-lobby-phase)
- [Story 1.1: GameState Foundation](/Volumes/My Passport/Spyster/_bmad-output/implementation-artifacts/1-1-initialize-project-structure-and-ha-integration.md#gamestate-skeleton-pattern)

**Epic Context:**
- Epic 1: Project Foundation & Game Session
- Story 1.2 builds on 1.1's GameState skeleton
- Story 1.3 will add QR code generation to lobby
- Story 1.4 will add player view alongside host view
- Phase transition system used by all future stories

**Related Stories:**
- Story 2.1: WebSocket handler will use get_state() for broadcasts
- Story 3.2: Start game will use transition_to(ROLES)
- Story 3.4: Per-player filtering will extend get_state()
- Story 4.1: ROLES→QUESTIONING transition
- Story 6.7: Host can force transition to END phase

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

(To be filled during implementation)

### Completion Notes List

(To be filled during implementation)

### File List

**Files to Modify:**
- `custom_components/spyster/const.py` (add phase transition constants)
- `custom_components/spyster/__init__.py` (register HostView, initialize GameState)
- `custom_components/spyster/game/state.py` (add session creation, phase transitions)

**Files to Create:**
- `custom_components/spyster/server/views.py`
- `custom_components/spyster/www/host.html`

**Tests to Create:**
- `tests/test_state.py` (expand with phase transition tests)
- `tests/test_views.py` (new file for HTTP view tests)

**Tests to Modify:**
- Update existing `tests/test_init.py` if needed for GameState initialization
