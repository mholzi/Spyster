---
story_id: "3.3"
story_name: "Spy Assignment"
epic: "Epic 3: Game Configuration & Role Assignment"
sprint: "Sprint 1 - Foundation"
priority: "critical"
estimated_effort: "4 hours"
dependencies: ["3.1", "3.2"]
status: "ready-for-dev"
created: "2025-12-23"
---

# Story 3.3: Spy Assignment

## User Story

As a **system**,
I want **to randomly assign exactly one spy per round**,
So that **the game has a fair and unpredictable spy selection**.

## Acceptance Criteria

### AC1: Cryptographically Secure Spy Selection
**Given** the game transitions to ROLES phase
**When** spy assignment occurs
**Then** exactly one player is marked as spy using `secrets.choice()` (CSPRNG)
**And** all other players are marked as non-spy

### AC2: Random Spy Per Round
**Given** a new round starts
**When** spy assignment occurs
**Then** a new random player is selected (may be same player as previous round per FR23)

### AC3: Role Privacy Guaranteed
**Given** the spy assignment is complete
**When** the assignment is stored
**Then** the spy identity is stored only in server-side GameState
**And** no client-visible data reveals who the spy is

## Requirements Traceability

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR19 | System assigns exactly one player as Spy per round | `assign_spy()` function |
| FR23 | System randomly assigns spy each round | `secrets.choice()` CSPRNG |
| NFR6 | Spy assignment cannot be predicted or reverse-engineered | CSPRNG + server-side only |
| NFR7 | Player cannot see another player's role via network inspection | Per-player state filtering |
| ARCH-6 | Spy assignment must use `secrets.choice()` (CSPRNG) | Import secrets module |
| ARCH-7 | Per-player state filtering via `get_state(for_player=player_name)` | GameState.get_state() |

## Technical Design

### Architecture Overview

```
Phase Transition: LOBBY → ROLES
    ↓
start_game() called by host
    ↓
assign_spy() - Select 1 random player
    ↓
Store spy_name in GameState._spy_name (private)
    ↓
broadcast_state() - Per-player filtering
    ↓
Clients receive role data (spy sees location_list, others see location)
```

### Data Model Changes

**GameState class additions:**

```python
class GameState:
    def __init__(self, hass: HomeAssistant):
        # ... existing fields ...
        self._spy_name: str | None = None  # Private - never in broadcast
        self._current_location: dict | None = None  # Selected location data
        self._location_pack_id: str = "classic"  # Configured pack
```

### Implementation Details

#### File: `custom_components/spyster/game/roles.py`

```python
"""Role assignment logic for Spyster game."""
from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .state import GameState

_LOGGER = logging.getLogger(__name__)


def assign_spy(game_state: GameState) -> str:
    """
    Assign exactly one player as the spy using CSPRNG.

    Args:
        game_state: Current game state with active players

    Returns:
        Name of the player selected as spy

    Raises:
        ValueError: If no connected players available
    """
    connected_players = [
        name for name, player in game_state.players.items()
        if player.connected
    ]

    if not connected_players:
        raise ValueError("Cannot assign spy: no connected players")

    if len(connected_players) < 4:
        raise ValueError(f"Cannot assign spy: need 4+ players, have {len(connected_players)}")

    # CRITICAL: Use secrets.choice() for cryptographic randomness (NFR6, ARCH-6)
    spy_name = secrets.choice(connected_players)

    _LOGGER.info(
        "Spy assigned for round %d: player count %d",
        game_state.current_round,
        len(connected_players)
    )
    # SECURITY: Never log spy identity to avoid data leaks

    return spy_name


def get_player_role_data(
    game_state: GameState,
    player_name: str
) -> dict:
    """
    Get role information for a specific player (filtered).

    Args:
        game_state: Current game state
        player_name: Name of player requesting role data

    Returns:
        Role data dict appropriate for this player:
        - Spy: {"is_spy": True, "locations": [...list of all locations...]}
        - Non-spy: {"is_spy": False, "location": "Beach", "role": "Lifeguard"}
    """
    if not game_state.current_location:
        raise ValueError("No location assigned for current round")

    is_spy = (player_name == game_state.spy_name)

    if is_spy:
        # Spy sees ALL possible locations (not the actual one)
        from .content import get_location_list

        location_list = get_location_list(game_state.location_pack_id)

        return {
            "is_spy": True,
            "locations": location_list,  # List of all location names
            "message": "YOU ARE THE SPY"
        }
    else:
        # Non-spy sees actual location and their assigned role
        role = game_state.player_roles.get(player_name)

        if not role:
            _LOGGER.warning("Player %s has no role assigned", player_name)
            role = {"name": "Visitor", "hint": "You're just passing through"}

        return {
            "is_spy": False,
            "location": game_state.current_location["name"],
            "role": role["name"],
            "role_hint": role.get("hint", ""),
            "other_roles": [
                r["name"] for r in game_state.current_location["roles"]
                if r["name"] != role["name"]
            ]
        }


def assign_roles(game_state: GameState) -> None:
    """
    Assign spy and distribute roles to all players.

    Updates game_state with:
    - spy_name (private)
    - current_location (from selected pack)
    - player_roles dict (role assigned to each non-spy)

    Raises:
        ValueError: If prerequisites not met (location not selected, etc.)
    """
    from .content import get_random_location

    # Select location for this round
    game_state.current_location = get_random_location(game_state.location_pack_id)

    if not game_state.current_location:
        raise ValueError(f"Failed to load location from pack: {game_state.location_pack_id}")

    _LOGGER.info(
        "Location selected for round %d: %s (%d roles available)",
        game_state.current_round,
        game_state.current_location["name"],
        len(game_state.current_location["roles"])
    )

    # Assign spy using CSPRNG
    game_state.spy_name = assign_spy(game_state)

    # Assign roles to non-spy players
    connected_players = [
        name for name, player in game_state.players.items()
        if player.connected and name != game_state.spy_name
    ]

    available_roles = list(game_state.current_location["roles"])
    game_state.player_roles = {}

    for player_name in connected_players:
        # Assign random role (with repetition if more players than roles)
        role = secrets.choice(available_roles)
        game_state.player_roles[player_name] = role

    _LOGGER.info(
        "Roles assigned: %d non-spy players",
        len(connected_players)
    )
```

#### File: `custom_components/spyster/game/state.py` (modifications)

```python
# Add imports at top
import secrets
from .roles import assign_roles

class GameState:
    def __init__(self, hass: HomeAssistant):
        # ... existing fields ...

        # Role assignment fields (PRIVATE - never in broadcasts)
        self._spy_name: str | None = None
        self._current_location: dict | None = None
        self._location_pack_id: str = "classic"
        self._player_roles: dict[str, dict] = {}  # {player_name: role_dict}
        self.current_round: int = 0

    @property
    def spy_name(self) -> str | None:
        """Get spy name (read-only access)."""
        return self._spy_name

    @spy_name.setter
    def spy_name(self, value: str) -> None:
        """Set spy name (internal use only)."""
        self._spy_name = value

    @property
    def current_location(self) -> dict | None:
        """Get current location data."""
        return self._current_location

    @current_location.setter
    def current_location(self, value: dict) -> None:
        """Set current location."""
        self._current_location = value

    @property
    def player_roles(self) -> dict[str, dict]:
        """Get player roles dict."""
        return self._player_roles

    @player_roles.setter
    def player_roles(self, value: dict[str, dict]) -> None:
        """Set player roles."""
        self._player_roles = value

    @property
    def location_pack_id(self) -> str:
        """Get configured location pack ID."""
        return self._location_pack_id

    def start_game(self) -> tuple[bool, str | None]:
        """
        Start the game - transition from LOBBY to ROLES phase.

        Returns:
            (success, error_code)
        """
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_NOT_ENOUGH_PLAYERS,
            GamePhase
        )

        # Phase guard
        if self.phase != GamePhase.LOBBY:
            return False, ERR_INVALID_PHASE

        # Player count validation
        connected = [p for p in self.players.values() if p.connected]
        if len(connected) < 4:
            return False, ERR_NOT_ENOUGH_PLAYERS
        if len(connected) > 10:
            return False, "ERR_TOO_MANY_PLAYERS"

        # Initialize first round
        self.current_round = 1

        # Assign spy and roles
        try:
            assign_roles(self)
        except ValueError as err:
            _LOGGER.error("Failed to assign roles: %s", err)
            return False, "ERR_ROLE_ASSIGNMENT_FAILED"

        # Transition to ROLES phase
        self.phase = GamePhase.ROLES

        _LOGGER.info(
            "Game started: %d players, round 1/%d",
            len(connected),
            self.config.get("rounds", 5)
        )

        # Start role display timer (5 seconds)
        self.start_timer(
            "role_display",
            5.0,
            self._on_role_display_complete
        )

        return True, None

    async def _on_role_display_complete(self) -> None:
        """Timer callback: role display timer expired."""
        from ..const import GamePhase

        if self.phase == GamePhase.ROLES:
            self.phase = GamePhase.QUESTIONING

            # Start round timer
            round_duration = self.config.get("round_duration", 420)  # 7 minutes default
            self.start_timer(
                "round",
                round_duration,
                self._on_round_timer_expired
            )

            _LOGGER.info("Questioning phase started: %d seconds", round_duration)

            # Broadcast state change
            if self._ws_handler:
                await self._ws_handler.broadcast_state()

    def get_state(self, for_player: str | None = None) -> dict:
        """
        Get game state, optionally filtered for specific player.

        SECURITY CRITICAL: Never include spy_name in any broadcast.
        Use per-player filtering for role data.

        Args:
            for_player: If provided, include role data for this player only

        Returns:
            State dict appropriate for recipient
        """
        from ..const import GamePhase
        from .roles import get_player_role_data

        state = {
            "phase": self.phase.value,
            "player_count": len([p for p in self.players.values() if p.connected]),
            "players": [
                {
                    "name": name,
                    "connected": player.connected,
                    "is_host": player.is_host
                }
                for name, player in self.players.items()
            ]
        }

        # Add phase-specific data
        if self.phase == GamePhase.ROLES:
            if for_player:
                # Per-player role data (SECURITY: filtered based on spy status)
                try:
                    role_data = get_player_role_data(self, for_player)
                    state["role"] = role_data
                except ValueError as err:
                    _LOGGER.warning("Failed to get role data for %s: %s", for_player, err)

        elif self.phase == GamePhase.QUESTIONING:
            state["round"] = self.current_round
            state["round_total"] = self.config.get("rounds", 5)

            # Timer info (if available)
            if "round" in self._timers:
                # Calculate remaining time
                # Note: This is simplified - real implementation needs timer start time
                state["timer_remaining"] = self.config.get("round_duration", 420)

        # NEVER include these fields in any broadcast:
        # - self._spy_name
        # - self._current_location (except filtered through get_player_role_data)
        # - self._player_roles (except filtered through get_player_role_data)

        return state
```

#### File: `custom_components/spyster/game/content.py` (new file)

```python
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
    """
    Load a location pack from JSON file.

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
    """
    Get a random location from the specified pack.

    Args:
        pack_id: Pack identifier

    Returns:
        Location dict with name, roles, flavor, etc.
    """
    # Note: hass not available in this context - packs should be preloaded
    pack = _LOADED_PACKS.get(pack_id)

    if not pack or not pack.get("locations"):
        _LOGGER.error("Location pack not loaded: %s", pack_id)
        return None

    # Use CSPRNG for location selection
    location = secrets.choice(pack["locations"])

    return location


def get_location_list(pack_id: str) -> list[str]:
    """
    Get list of all location names in a pack (for spy display).

    Args:
        pack_id: Pack identifier

    Returns:
        List of location names
    """
    pack = _LOADED_PACKS.get(pack_id)

    if not pack or not pack.get("locations"):
        _LOGGER.error("Location pack not loaded: %s", pack_id)
        return []

    return [loc["name"] for loc in pack["locations"]]


async def preload_location_packs(hass: HomeAssistant) -> None:
    """
    Preload all location packs at integration startup.

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
```

#### File: `custom_components/spyster/const.py` (additions)

```python
# Add these error codes
ERR_NOT_ENOUGH_PLAYERS = "NOT_ENOUGH_PLAYERS"
ERR_TOO_MANY_PLAYERS = "TOO_MANY_PLAYERS"
ERR_ROLE_ASSIGNMENT_FAILED = "ROLE_ASSIGNMENT_FAILED"

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_NOT_ENOUGH_PLAYERS: "Need at least 4 players to start the game.",
    ERR_TOO_MANY_PLAYERS: "Maximum 10 players allowed.",
    ERR_ROLE_ASSIGNMENT_FAILED: "Failed to assign roles. Please try again.",
}
```

### Security Considerations

#### CSPRNG Usage (NFR6, ARCH-6)
- **Implementation**: `secrets.choice()` for spy selection
- **Rationale**: Uses OS-provided CSPRNG, not predictable PRNG
- **Verification**: Python's `secrets` module is cryptographically secure

#### Role Privacy (NFR7, ARCH-7, ARCH-8)
- **Never broadcast spy_name**: Stored as private `_spy_name` field
- **Per-player state filtering**: `get_state(for_player=name)` returns different data per player
- **Network inspection proof**: Spy sees `locations` list, non-spy sees `location` + `role`

#### State Isolation
- **Spy cannot see actual location**: Only receives full location list
- **Non-spy cannot see spy identity**: Not included in any broadcast
- **No correlation possible**: Spy selection independent of network timing

### Testing Strategy

#### Unit Tests: `tests/test_roles.py`

```python
"""Tests for role assignment logic."""
import pytest
import secrets
from custom_components.spyster.game.roles import assign_spy, get_player_role_data


def test_assign_spy_selects_one_player(mock_game_state):
    """Test that exactly one spy is selected."""
    spy_name = assign_spy(mock_game_state)

    assert spy_name in mock_game_state.players
    assert mock_game_state.players[spy_name].connected


def test_assign_spy_fails_with_no_players(empty_game_state):
    """Test spy assignment fails with no connected players."""
    with pytest.raises(ValueError, match="no connected players"):
        assign_spy(empty_game_state)


def test_assign_spy_fails_with_too_few_players(mock_game_state):
    """Test spy assignment fails with < 4 players."""
    # Disconnect all but 3 players
    connected_count = 0
    for player in mock_game_state.players.values():
        if connected_count >= 3:
            player.connected = False
        else:
            connected_count += 1

    with pytest.raises(ValueError, match="need 4\\+ players"):
        assign_spy(mock_game_state)


def test_assign_spy_uses_csprng(mock_game_state, monkeypatch):
    """Test that secrets.choice() is used (not random.choice)."""
    called = []

    def mock_choice(seq):
        called.append(True)
        return seq[0]

    monkeypatch.setattr(secrets, "choice", mock_choice)

    assign_spy(mock_game_state)

    assert len(called) == 1, "secrets.choice() must be called"


def test_get_player_role_data_spy(mock_game_state):
    """Test spy receives location list (not actual location)."""
    mock_game_state.spy_name = "Player1"
    mock_game_state.current_location = {
        "name": "Beach",
        "roles": [{"name": "Lifeguard", "hint": "You watch swimmers"}]
    }

    role_data = get_player_role_data(mock_game_state, "Player1")

    assert role_data["is_spy"] is True
    assert "locations" in role_data
    assert isinstance(role_data["locations"], list)
    assert "location" not in role_data  # Spy must NOT see actual location


def test_get_player_role_data_non_spy(mock_game_state):
    """Test non-spy receives location and role."""
    mock_game_state.spy_name = "Player1"
    mock_game_state.current_location = {
        "name": "Beach",
        "roles": [
            {"name": "Lifeguard", "hint": "You watch swimmers"},
            {"name": "Tourist", "hint": "You're on vacation"}
        ]
    }
    mock_game_state.player_roles = {
        "Player2": {"name": "Lifeguard", "hint": "You watch swimmers"}
    }

    role_data = get_player_role_data(mock_game_state, "Player2")

    assert role_data["is_spy"] is False
    assert role_data["location"] == "Beach"
    assert role_data["role"] == "Lifeguard"
    assert "locations" not in role_data  # Non-spy must NOT see location list


def test_role_privacy_network_inspection(mock_game_state):
    """Test that network inspection cannot reveal spy identity."""
    mock_game_state.spy_name = "Player1"
    mock_game_state.current_location = {"name": "Beach", "roles": []}

    # Get state for two different players
    spy_state = mock_game_state.get_state(for_player="Player1")
    non_spy_state = mock_game_state.get_state(for_player="Player2")

    # Neither state should contain spy_name
    import json
    spy_json = json.dumps(spy_state)
    non_spy_json = json.dumps(non_spy_state)

    assert "Player1" not in spy_json or "Player1" in [p["name"] for p in spy_state.get("players", [])]
    assert "spy_name" not in spy_json
    assert "spy_name" not in non_spy_json
    assert "_spy_name" not in spy_json
```

#### Integration Tests

```python
"""Integration tests for game start and spy assignment."""
import pytest
from custom_components.spyster.const import GamePhase


async def test_start_game_assigns_spy(hass, mock_websocket_handler):
    """Test that starting game assigns spy and transitions to ROLES."""
    game_state = mock_websocket_handler.game_state

    # Add 5 connected players
    for i in range(1, 6):
        game_state.add_player(f"Player{i}", is_host=(i == 1))

    # Start game
    success, error = game_state.start_game()

    assert success is True
    assert error is None
    assert game_state.phase == GamePhase.ROLES
    assert game_state.spy_name is not None
    assert game_state.spy_name in game_state.players
    assert game_state.current_location is not None
    assert game_state.current_round == 1


async def test_broadcast_state_filters_role_data(hass, mock_websocket_handler):
    """Test that broadcast_state sends different data to each player."""
    game_state = mock_websocket_handler.game_state

    # Setup game with spy assigned
    for i in range(1, 5):
        player = game_state.add_player(f"Player{i}", is_host=(i == 1))
        player.connected = True

    game_state.start_game()

    # Capture broadcast messages
    messages = {}

    async def capture_send(player_name, message):
        messages[player_name] = message

    # Mock send_json for each player WebSocket
    for player_name, player in game_state.players.items():
        player.ws.send_json = lambda msg, pn=player_name: capture_send(pn, msg)

    # Broadcast state
    await mock_websocket_handler.broadcast_state()

    # Verify each player got different role data
    spy_message = messages[game_state.spy_name]

    assert spy_message["role"]["is_spy"] is True
    assert "locations" in spy_message["role"]

    # Check a non-spy player
    non_spy_name = next(name for name in messages if name != game_state.spy_name)
    non_spy_message = messages[non_spy_name]

    assert non_spy_message["role"]["is_spy"] is False
    assert "location" in non_spy_message["role"]
    assert "role" in non_spy_message["role"]
```

### Performance Considerations

- **CSPRNG overhead**: `secrets.choice()` is slightly slower than `random.choice()` but difference is negligible for 4-10 items
- **Content pack caching**: Location packs loaded once at startup, cached in memory
- **State filtering overhead**: Per-player filtering adds ~1ms per player (acceptable for 10 players)

## Implementation Checklist

### Phase 1: Core Role Assignment
- [ ] Create `game/roles.py` with `assign_spy()` function
- [ ] Add `spy_name`, `current_location`, `player_roles` fields to GameState
- [ ] Implement `GameState.start_game()` with role assignment
- [ ] Add error codes to `const.py`

### Phase 2: Content System
- [ ] Create `game/content.py` with pack loading functions
- [ ] Create minimal `content/classic.json` with 3 test locations
- [ ] Add `preload_location_packs()` call in `__init__.py`
- [ ] Implement content pack caching

### Phase 3: State Filtering
- [ ] Implement `get_player_role_data()` function
- [ ] Update `GameState.get_state()` to include role data when `for_player` provided
- [ ] Verify ROLES phase state includes proper filtering

### Phase 4: Timer Integration
- [ ] Add `role_display` timer (5 seconds) after phase → ROLES
- [ ] Implement `_on_role_display_complete()` callback
- [ ] Transition ROLES → QUESTIONING when timer expires

### Phase 5: Testing
- [ ] Unit tests for `assign_spy()` with edge cases
- [ ] Unit tests for `get_player_role_data()` spy vs non-spy
- [ ] Unit tests for CSPRNG usage verification
- [ ] Integration test for full game start flow
- [ ] Security test for role privacy via network inspection

### Phase 6: Content Pack
- [ ] Expand `content/classic.json` to 10 locations
- [ ] Add 6-8 roles per location with hints
- [ ] Add flavor text for each location
- [ ] Validate JSON schema

## Definition of Done

- [ ] All acceptance criteria verified with passing tests
- [ ] Code follows architectural patterns (snake_case, logging with context)
- [ ] Security verified: spy_name never in broadcasts
- [ ] Unit test coverage ≥ 90% for roles.py
- [ ] Integration test covers full game start flow
- [ ] Documentation updated (inline comments + this story file)
- [ ] Code review completed with no critical issues
- [ ] Manual testing: start game with 4-10 players, verify spy assignment
- [ ] Performance verified: role assignment < 100ms for 10 players

## Dependencies

### Depends On
- **Story 3.1**: Game Configuration UI (must set location_pack_id)
- **Story 3.2**: Start Game with Player Validation (provides start_game trigger)

### Enables
- **Story 3.4**: Role Distribution with Per-Player Filtering (uses get_player_role_data)
- **Story 3.5**: Role Display UI with Spy Parity (consumes role data)

## Notes

### Why CSPRNG Matters
Using `secrets.choice()` instead of `random.choice()` ensures:
1. Spy selection cannot be predicted by observing previous selections
2. No seed-based attacks possible
3. Compliance with NFR6 security requirement

### Content Pack Design
The enriched location schema with hints and flavor text:
- **Hints**: Help new players understand their role context
- **Flavor**: Adds atmosphere on host display
- **IDs**: Enable future stats tracking and favorites

### Future Enhancements
- **Anti-repeat spy logic**: Track last N spy selections, bias against recent spies
- **Role balancing**: Ensure varied role distribution across rounds
- **Multi-pack support**: UI to select pack before game start
- **Custom location editor**: In-game pack creation (Vision feature)

---

**Story Status**: Ready for Development
**Estimated Effort**: 4 hours
**Risk Level**: Low (well-defined, proven security patterns)
