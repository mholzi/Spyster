---
story_id: "3.1"
epic_id: "epic-3"
title: "Game Configuration UI"
status: "ready-for-dev"
created: "2025-12-23"
priority: "high"
estimated_effort: "5 story points"
dependencies: ["2.6"]
---

# Story 3.1: Game Configuration UI

## Story Statement

As a **host**,
I want **to configure game settings before starting**,
So that **I can customize the game for my group**.

## Business Context

This story enables the host to customize game settings in the lobby before starting, providing flexibility for different group sizes, available time, and location preferences. Configuration must be intuitive and visible to all players in the lobby to set expectations.

## Acceptance Criteria

### AC1: Configuration Options Display
**Given** the host is viewing the lobby
**When** the configuration options are displayed
**Then** the host can set round duration (default 7 minutes)
**And** the host can set number of rounds (default 5)
**And** the host can select a location pack (Classic by default)

### AC2: Configuration Value Updates
**Given** the host changes a configuration value
**When** the value is updated
**Then** the new value is stored in GameState
**And** the configuration is displayed to confirm the setting

### AC3: Configuration Applied to Gameplay
**Given** configuration values are set
**When** the game starts
**Then** the configured values are used for gameplay

## Requirements Coverage

### Functional Requirements
- **FR2**: Host can configure round duration before starting
- **FR3**: Host can select a location pack before starting
- **FR8**: Host can configure number of rounds per game (fixed count only)

### Non-Functional Requirements
- **UX-4**: Minimum touch targets: 44px (48px for primary)
- **UX-11**: WCAG 2.1 AA compliance (4.5:1 contrast minimum)
- **UX-12**: ARIA roles on interactive elements
- **NFR2**: WebSocket Latency - Messages delivered in < 100ms on local network

### Architecture Decisions
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-15**: Constants in `const.py` - never hardcode config values
- **ARCH-16**: Logging format: `_LOGGER.info("Event: %s (context: %d)", name, value)`
- **ARCH-17**: Phase guards on all state-mutating methods

## Technical Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Host Display (UI)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Configuration Panel (host.html)          │   │
│  │  • Round Duration Selector                       │   │
│  │  • Number of Rounds Selector                     │   │
│  │  • Location Pack Selector                        │   │
│  └────────────┬────────────────────────────────────┘   │
│               │ WebSocket                               │
└───────────────┼─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│              WebSocket Handler (server)                  │
│  • handle_configure message                             │
│  • Validate configuration values                        │
│  • Update GameState                                     │
│  • Broadcast state to all clients                       │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                GameState (game/state.py)                 │
│  • config: GameConfig                                   │
│  • update_config(field, value) → (bool, error?)        │
│  • validate_config() → bool                             │
└─────────────────────────────────────────────────────────┘
```

### Data Structures

#### GameConfig Class
```python
# game/config.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class GameConfig:
    """Game configuration settings."""
    round_duration_minutes: int = 7  # Default 7 minutes
    num_rounds: int = 5              # Default 5 rounds
    location_pack: str = "classic"   # Default Classic pack

    def validate(self) -> tuple[bool, str | None]:
        """
        Validate configuration values.

        Returns:
            (valid, error_code)
        """
        if not (1 <= self.round_duration_minutes <= 30):
            return False, ERR_CONFIG_INVALID_DURATION

        if not (1 <= self.num_rounds <= 20):
            return False, ERR_CONFIG_INVALID_ROUNDS

        # Validate location pack exists
        if not self._pack_exists(self.location_pack):
            return False, ERR_CONFIG_INVALID_PACK

        return True, None

    def _pack_exists(self, pack_id: str) -> bool:
        """Check if location pack exists."""
        from pathlib import Path
        pack_file = Path(__file__).parent.parent / "content" / f"{pack_id}.json"
        return pack_file.exists()
```

### WebSocket Protocol

#### Client → Server: Configure Message
```json
{
  "type": "configure",
  "field": "round_duration_minutes" | "num_rounds" | "location_pack",
  "value": <int | string>
}
```

Examples:
```json
{"type": "configure", "field": "round_duration_minutes", "value": 10}
{"type": "configure", "field": "num_rounds", "value": 3}
{"type": "configure", "field": "location_pack", "value": "classic"}
```

#### Server → Client: State Update
```json
{
  "type": "state",
  "phase": "LOBBY",
  "config": {
    "round_duration_minutes": 7,
    "num_rounds": 5,
    "location_pack": "classic"
  },
  ...
}
```

### Constants

```python
# const.py

# Configuration Limits
CONFIG_MIN_ROUND_DURATION = 1      # minutes
CONFIG_MAX_ROUND_DURATION = 30     # minutes
CONFIG_DEFAULT_ROUND_DURATION = 7  # minutes

CONFIG_MIN_ROUNDS = 1
CONFIG_MAX_ROUNDS = 20
CONFIG_DEFAULT_ROUNDS = 5

CONFIG_DEFAULT_LOCATION_PACK = "classic"

# Error Codes
ERR_CONFIG_INVALID_DURATION = "CONFIG_INVALID_DURATION"
ERR_CONFIG_INVALID_ROUNDS = "CONFIG_INVALID_ROUNDS"
ERR_CONFIG_INVALID_PACK = "CONFIG_INVALID_PACK"
ERR_CONFIG_GAME_STARTED = "CONFIG_GAME_STARTED"

# Error Messages
ERROR_MESSAGES = {
    ...existing errors...,
    ERR_CONFIG_INVALID_DURATION: "Round duration must be between 1-30 minutes.",
    ERR_CONFIG_INVALID_ROUNDS: "Number of rounds must be between 1-20.",
    ERR_CONFIG_INVALID_PACK: "Selected location pack not found.",
    ERR_CONFIG_GAME_STARTED: "Cannot change configuration after game has started.",
}
```

## Implementation Tasks

### Task 1: Create GameConfig Class
**File**: `custom_components/spyster/game/config.py`

```python
"""Game configuration management."""
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

from ..const import (
    CONFIG_MIN_ROUND_DURATION,
    CONFIG_MAX_ROUND_DURATION,
    CONFIG_DEFAULT_ROUND_DURATION,
    CONFIG_MIN_ROUNDS,
    CONFIG_MAX_ROUNDS,
    CONFIG_DEFAULT_ROUNDS,
    CONFIG_DEFAULT_LOCATION_PACK,
    ERR_CONFIG_INVALID_DURATION,
    ERR_CONFIG_INVALID_ROUNDS,
    ERR_CONFIG_INVALID_PACK,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Game configuration settings."""

    round_duration_minutes: int = CONFIG_DEFAULT_ROUND_DURATION
    num_rounds: int = CONFIG_DEFAULT_ROUNDS
    location_pack: str = CONFIG_DEFAULT_LOCATION_PACK

    def validate(self) -> tuple[bool, str | None]:
        """
        Validate all configuration values.

        Returns:
            (valid, error_code) - True if valid, otherwise False with error code
        """
        # Validate round duration
        if not (CONFIG_MIN_ROUND_DURATION <= self.round_duration_minutes <= CONFIG_MAX_ROUND_DURATION):
            _LOGGER.warning(
                "Invalid round duration: %d (min: %d, max: %d)",
                self.round_duration_minutes,
                CONFIG_MIN_ROUND_DURATION,
                CONFIG_MAX_ROUND_DURATION
            )
            return False, ERR_CONFIG_INVALID_DURATION

        # Validate number of rounds
        if not (CONFIG_MIN_ROUNDS <= self.num_rounds <= CONFIG_MAX_ROUNDS):
            _LOGGER.warning(
                "Invalid number of rounds: %d (min: %d, max: %d)",
                self.num_rounds,
                CONFIG_MIN_ROUNDS,
                CONFIG_MAX_ROUNDS
            )
            return False, ERR_CONFIG_INVALID_ROUNDS

        # Validate location pack exists
        if not self._pack_exists(self.location_pack):
            _LOGGER.warning("Location pack not found: %s", self.location_pack)
            return False, ERR_CONFIG_INVALID_PACK

        return True, None

    def _pack_exists(self, pack_id: str) -> bool:
        """Check if location pack file exists."""
        pack_file = Path(__file__).parent.parent / "content" / f"{pack_id}.json"
        exists = pack_file.exists()
        _LOGGER.debug("Location pack check: %s - %s", pack_id, "exists" if exists else "not found")
        return exists

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GameConfig":
        """Create from dictionary."""
        return cls(
            round_duration_minutes=data.get("round_duration_minutes", CONFIG_DEFAULT_ROUND_DURATION),
            num_rounds=data.get("num_rounds", CONFIG_DEFAULT_ROUNDS),
            location_pack=data.get("location_pack", CONFIG_DEFAULT_LOCATION_PACK),
        )
```

**Acceptance Test**:
```python
# tests/test_config.py
import pytest
from custom_components.spyster.game.config import GameConfig
from custom_components.spyster.const import (
    ERR_CONFIG_INVALID_DURATION,
    ERR_CONFIG_INVALID_ROUNDS,
    ERR_CONFIG_INVALID_PACK,
)


def test_default_config():
    """Test default configuration values."""
    config = GameConfig()
    assert config.round_duration_minutes == 7
    assert config.num_rounds == 5
    assert config.location_pack == "classic"


def test_valid_config():
    """Test validation of valid config."""
    config = GameConfig(round_duration_minutes=10, num_rounds=3)
    valid, error = config.validate()
    assert valid is True
    assert error is None


def test_invalid_round_duration_too_low():
    """Test validation rejects round duration below minimum."""
    config = GameConfig(round_duration_minutes=0)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_DURATION


def test_invalid_round_duration_too_high():
    """Test validation rejects round duration above maximum."""
    config = GameConfig(round_duration_minutes=31)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_DURATION


def test_invalid_num_rounds():
    """Test validation rejects invalid number of rounds."""
    config = GameConfig(num_rounds=0)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_ROUNDS


def test_invalid_location_pack():
    """Test validation rejects non-existent location pack."""
    config = GameConfig(location_pack="nonexistent_pack")
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_PACK


def test_to_dict():
    """Test serialization to dictionary."""
    config = GameConfig(round_duration_minutes=10, num_rounds=3)
    data = config.to_dict()
    assert data["round_duration_minutes"] == 10
    assert data["num_rounds"] == 3
    assert data["location_pack"] == "classic"


def test_from_dict():
    """Test deserialization from dictionary."""
    data = {"round_duration_minutes": 15, "num_rounds": 7, "location_pack": "classic"}
    config = GameConfig.from_dict(data)
    assert config.round_duration_minutes == 15
    assert config.num_rounds == 7
    assert config.location_pack == "classic"
```

---

### Task 2: Integrate GameConfig into GameState
**File**: `custom_components/spyster/game/state.py`

**Changes**:
```python
# Add import
from .config import GameConfig

class GameState:
    """Central game state management."""

    def __init__(self):
        # ...existing init...
        self.config = GameConfig()  # Add configuration

    def update_config(self, field: str, value: int | str) -> tuple[bool, str | None]:
        """
        Update a configuration field.

        Args:
            field: Configuration field name
            value: New value

        Returns:
            (success, error_code)
        """
        # Phase guard - can only configure in LOBBY
        if self.phase != GamePhase.LOBBY:
            return False, ERR_CONFIG_GAME_STARTED

        # Update field
        if field == "round_duration_minutes":
            self.config.round_duration_minutes = int(value)
        elif field == "num_rounds":
            self.config.num_rounds = int(value)
        elif field == "location_pack":
            self.config.location_pack = str(value)
        else:
            _LOGGER.warning("Unknown config field: %s", field)
            return False, ERR_INVALID_MESSAGE

        # Validate new configuration
        valid, error = self.config.validate()
        if not valid:
            # Revert to defaults if invalid
            self.config = GameConfig()
            _LOGGER.warning("Config validation failed: %s", error)
            return False, error

        _LOGGER.info("Configuration updated: %s = %s", field, value)
        return True, None

    def get_state(self, for_player: str | None = None) -> dict:
        """Get game state, filtered for specific player if provided."""
        state = {
            "phase": self.phase.value,
            "player_count": len(self.players),
            "config": self.config.to_dict(),  # Include config in state
            # ...rest of state...
        }
        # ...existing state logic...
        return state
```

**Acceptance Test**:
```python
# tests/test_state.py (additions)

def test_config_update_in_lobby(game_state):
    """Test configuration can be updated in LOBBY phase."""
    game_state.phase = GamePhase.LOBBY

    success, error = game_state.update_config("round_duration_minutes", 10)
    assert success is True
    assert error is None
    assert game_state.config.round_duration_minutes == 10


def test_config_update_after_game_started(game_state):
    """Test configuration cannot be updated after game starts."""
    game_state.phase = GamePhase.ROLES

    success, error = game_state.update_config("round_duration_minutes", 10)
    assert success is False
    assert error == ERR_CONFIG_GAME_STARTED


def test_config_update_invalid_value(game_state):
    """Test configuration rejects invalid values."""
    game_state.phase = GamePhase.LOBBY

    success, error = game_state.update_config("round_duration_minutes", 999)
    assert success is False
    assert error == ERR_CONFIG_INVALID_DURATION
    # Config should revert to defaults
    assert game_state.config.round_duration_minutes == 7


def test_config_in_state_dict(game_state):
    """Test configuration is included in state dict."""
    state = game_state.get_state()
    assert "config" in state
    assert state["config"]["round_duration_minutes"] == 7
    assert state["config"]["num_rounds"] == 5
    assert state["config"]["location_pack"] == "classic"
```

---

### Task 3: Add WebSocket Configure Handler
**File**: `custom_components/spyster/server/websocket.py`

**Changes**:
```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Route incoming WebSocket messages to appropriate handlers."""
    msg_type = data.get("type")

    # ...existing handlers...

    elif msg_type == "configure":
        await self._handle_configure(ws, data)

    # ...rest of handlers...


async def _handle_configure(self, ws: web.WebSocketResponse, data: dict) -> None:
    """
    Handle configuration update from host.

    Message format:
        {"type": "configure", "field": "round_duration_minutes", "value": 10}
    """
    player = self._get_player_by_ws(ws)
    if not player:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_IN_GAME,
            "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
        })
        return

    # Only host can configure
    if not player.is_host:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_HOST,
            "message": ERROR_MESSAGES[ERR_NOT_HOST]
        })
        return

    field = data.get("field")
    value = data.get("value")

    if not field or value is None:
        await ws.send_json({
            "type": "error",
            "code": ERR_INVALID_MESSAGE,
            "message": "Missing field or value in configure message."
        })
        return

    # Update configuration
    success, error = self.game_state.update_config(field, value)

    if not success:
        await ws.send_json({
            "type": "error",
            "code": error,
            "message": ERROR_MESSAGES.get(error, "Configuration update failed.")
        })
        return

    _LOGGER.info("Configuration updated by host %s: %s = %s", player.name, field, value)

    # Broadcast updated state to all players
    await self.broadcast_state()
```

**Acceptance Test**:
```python
# tests/test_websocket.py (additions)

async def test_handle_configure_valid(websocket_handler, mock_ws, host_player):
    """Test handling valid configuration update."""
    websocket_handler.game_state.phase = GamePhase.LOBBY
    websocket_handler._connections[mock_ws] = host_player

    message = {
        "type": "configure",
        "field": "round_duration_minutes",
        "value": 10
    }

    await websocket_handler._handle_configure(mock_ws, message)

    # Check config was updated
    assert websocket_handler.game_state.config.round_duration_minutes == 10

    # Check state was broadcasted
    assert mock_ws.send_json.called


async def test_handle_configure_not_host(websocket_handler, mock_ws, regular_player):
    """Test non-host cannot configure."""
    websocket_handler.game_state.phase = GamePhase.LOBBY
    websocket_handler._connections[mock_ws] = regular_player

    message = {
        "type": "configure",
        "field": "round_duration_minutes",
        "value": 10
    }

    await websocket_handler._handle_configure(mock_ws, message)

    # Check error was sent
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_NOT_HOST


async def test_handle_configure_invalid_value(websocket_handler, mock_ws, host_player):
    """Test configuration rejects invalid values."""
    websocket_handler.game_state.phase = GamePhase.LOBBY
    websocket_handler._connections[mock_ws] = host_player

    message = {
        "type": "configure",
        "field": "round_duration_minutes",
        "value": 999  # Invalid
    }

    await websocket_handler._handle_configure(mock_ws, message)

    # Check error was sent
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_CONFIG_INVALID_DURATION
```

---

### Task 4: Update Host UI with Configuration Panel
**File**: `custom_components/spyster/www/host.html`

**Changes** (add configuration panel in lobby section):
```html
<!-- Lobby Phase -->
<div id="lobby-phase" class="phase-container" data-phase="LOBBY">
    <h1 class="phase-title">Lobby</h1>

    <!-- Configuration Panel -->
    <div class="config-panel">
        <h2>Game Settings</h2>

        <!-- Round Duration -->
        <div class="config-option">
            <label for="config-round-duration">Round Duration (minutes)</label>
            <div class="config-controls">
                <button
                    id="config-round-duration-dec"
                    class="config-btn"
                    aria-label="Decrease round duration">
                    −
                </button>
                <span id="config-round-duration-value" class="config-value">7</span>
                <button
                    id="config-round-duration-inc"
                    class="config-btn"
                    aria-label="Increase round duration">
                    +
                </button>
            </div>
        </div>

        <!-- Number of Rounds -->
        <div class="config-option">
            <label for="config-num-rounds">Number of Rounds</label>
            <div class="config-controls">
                <button
                    id="config-num-rounds-dec"
                    class="config-btn"
                    aria-label="Decrease number of rounds">
                    −
                </button>
                <span id="config-num-rounds-value" class="config-value">5</span>
                <button
                    id="config-num-rounds-inc"
                    class="config-btn"
                    aria-label="Increase number of rounds">
                    +
                </button>
            </div>
        </div>

        <!-- Location Pack -->
        <div class="config-option">
            <label for="config-location-pack">Location Pack</label>
            <select
                id="config-location-pack"
                class="config-select"
                aria-label="Select location pack">
                <option value="classic" selected>Classic</option>
                <!-- Future packs added here -->
            </select>
        </div>
    </div>

    <!-- QR Code -->
    <div class="qr-container">
        <img id="qr-code" src="" alt="QR Code to join game" />
        <p class="join-url" id="join-url"></p>
    </div>

    <!-- Player List -->
    <div id="player-list" class="player-list"></div>

    <!-- Start Button -->
    <button id="start-game-btn" class="btn-primary" disabled>
        Start Game (Need 4+ Players)
    </button>
</div>
```

---

### Task 5: Add Configuration Logic to Host JS
**File**: `custom_components/spyster/www/js/host.js`

**Changes**:
```javascript
// Configuration state
let currentConfig = {
    round_duration_minutes: 7,
    num_rounds: 5,
    location_pack: "classic"
};

// Initialize configuration controls
function initConfigControls() {
    // Round duration controls
    document.getElementById("config-round-duration-inc").addEventListener("click", () => {
        updateConfig("round_duration_minutes", currentConfig.round_duration_minutes + 1);
    });

    document.getElementById("config-round-duration-dec").addEventListener("click", () => {
        updateConfig("round_duration_minutes", currentConfig.round_duration_minutes - 1);
    });

    // Number of rounds controls
    document.getElementById("config-num-rounds-inc").addEventListener("click", () => {
        updateConfig("num_rounds", currentConfig.num_rounds + 1);
    });

    document.getElementById("config-num-rounds-dec").addEventListener("click", () => {
        updateConfig("num_rounds", currentConfig.num_rounds - 1);
    });

    // Location pack selector
    document.getElementById("config-location-pack").addEventListener("change", (e) => {
        updateConfig("location_pack", e.target.value);
    });
}

/**
 * Send configuration update to server.
 * @param {string} field - Configuration field name
 * @param {number|string} value - New value
 */
function updateConfig(field, value) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error("WebSocket not connected");
        return;
    }

    ws.send(JSON.stringify({
        type: "configure",
        field: field,
        value: value
    }));
}

/**
 * Render configuration display from state.
 * @param {object} config - Configuration object from state
 */
function renderConfig(config) {
    if (!config) return;

    // Update local state
    currentConfig = config;

    // Update display values
    document.getElementById("config-round-duration-value").textContent =
        config.round_duration_minutes;
    document.getElementById("config-num-rounds-value").textContent =
        config.num_rounds;
    document.getElementById("config-location-pack").value =
        config.location_pack;
}

// Handle state updates
function handleStateUpdate(state) {
    // ...existing state handling...

    // Update configuration display
    if (state.config) {
        renderConfig(state.config);
    }

    // ...rest of state handling...
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initConfigControls();
    // ...existing initialization...
});
```

**Acceptance Test** (manual):
1. Load host display in browser
2. Verify configuration panel shows default values (7 min, 5 rounds, Classic)
3. Click "+" on round duration → value increments, server receives update
4. Click "−" on number of rounds → value decrements, server receives update
5. Change location pack dropdown → server receives update
6. Verify other connected clients see updated configuration in real-time

---

### Task 6: Add Configuration Display to Player UI
**File**: `custom_components/spyster/www/player.html`

**Changes** (add config info in lobby):
```html
<!-- Lobby Phase - Player View -->
<div id="lobby-phase" class="phase-container" data-phase="LOBBY">
    <h1 class="phase-title">Waiting for Game to Start</h1>

    <div class="lobby-info">
        <p class="player-name">Welcome, <span id="player-name-display"></span>!</p>
        <p class="player-count"><span id="player-count">0</span> players connected</p>
    </div>

    <!-- Game Settings Display -->
    <div class="config-display">
        <h3>Game Settings</h3>
        <ul>
            <li>Round Duration: <strong><span id="config-round-duration-display">7</span> minutes</strong></li>
            <li>Number of Rounds: <strong><span id="config-num-rounds-display">5</span></strong></li>
            <li>Location Pack: <strong><span id="config-location-pack-display">Classic</span></strong></li>
        </ul>
    </div>

    <p class="waiting-message">The host will start the game when everyone is ready.</p>
</div>
```

---

### Task 7: Update Player JS to Display Configuration
**File**: `custom_components/spyster/www/js/player.js`

**Changes**:
```javascript
/**
 * Render configuration display for players.
 * @param {object} config - Configuration object from state
 */
function renderConfigDisplay(config) {
    if (!config) return;

    document.getElementById("config-round-duration-display").textContent =
        config.round_duration_minutes;
    document.getElementById("config-num-rounds-display").textContent =
        config.num_rounds;
    document.getElementById("config-location-pack-display").textContent =
        formatLocationPackName(config.location_pack);
}

/**
 * Format location pack ID for display.
 * @param {string} packId - Location pack identifier
 * @returns {string} - Formatted pack name
 */
function formatLocationPackName(packId) {
    // Capitalize first letter
    return packId.charAt(0).toUpperCase() + packId.slice(1);
}

// Handle state updates
function handleStateUpdate(state) {
    // ...existing state handling...

    // Update configuration display
    if (state.config) {
        renderConfigDisplay(state.config);
    }

    // ...rest of state handling...
}
```

---

### Task 8: Add Configuration Styles
**File**: `custom_components/spyster/www/css/styles.css`

**Changes**:
```css
/* Configuration Panel - Host Display */
.config-panel {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 24px;
    margin: 24px 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.config-panel h2 {
    color: var(--color-pink);
    font-size: 24px;
    margin-bottom: 20px;
    text-align: center;
}

.config-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding: 12px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
}

.config-option:last-child {
    margin-bottom: 0;
}

.config-option label {
    color: var(--color-text-primary);
    font-size: 18px;
    font-weight: 500;
}

.config-controls {
    display: flex;
    align-items: center;
    gap: 16px;
}

.config-btn {
    min-width: 48px;
    min-height: 48px;
    border: 2px solid var(--color-pink);
    background: rgba(255, 45, 106, 0.1);
    color: var(--color-pink);
    font-size: 24px;
    font-weight: bold;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.config-btn:hover {
    background: rgba(255, 45, 106, 0.2);
    transform: scale(1.05);
}

.config-btn:active {
    transform: scale(0.95);
}

.config-btn:focus {
    outline: 2px solid var(--color-cyan);
    outline-offset: 2px;
}

.config-value {
    color: var(--color-cyan);
    font-size: 28px;
    font-weight: bold;
    min-width: 48px;
    text-align: center;
}

.config-select {
    min-width: 200px;
    min-height: 48px;
    padding: 8px 16px;
    background: rgba(0, 0, 0, 0.3);
    border: 2px solid var(--color-pink);
    border-radius: 8px;
    color: var(--color-text-primary);
    font-size: 18px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.config-select:hover {
    background: rgba(0, 0, 0, 0.4);
    border-color: var(--color-cyan);
}

.config-select:focus {
    outline: 2px solid var(--color-cyan);
    outline-offset: 2px;
}

/* Configuration Display - Player View */
.config-display {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 16px;
    margin: 20px 0;
}

.config-display h3 {
    color: var(--color-pink);
    font-size: 18px;
    margin-bottom: 12px;
}

.config-display ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.config-display li {
    color: var(--color-text-secondary);
    font-size: 16px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.config-display li:last-child {
    border-bottom: none;
}

.config-display strong {
    color: var(--color-cyan);
    font-weight: 600;
}

/* Responsive - Host Display (larger screens) */
@media (min-width: 768px) {
    .config-panel h2 {
        font-size: 36px;
    }

    .config-option label {
        font-size: 28px;
    }

    .config-btn {
        min-width: 64px;
        min-height: 64px;
        font-size: 32px;
    }

    .config-value {
        font-size: 42px;
        min-width: 80px;
    }

    .config-select {
        min-height: 64px;
        font-size: 24px;
    }
}

/* Accessibility: Reduced Motion */
@media (prefers-reduced-motion: reduce) {
    .config-btn {
        transition: none;
    }

    .config-btn:hover {
        transform: none;
    }

    .config-btn:active {
        transform: none;
    }
}
```

---

### Task 9: Update Constants File
**File**: `custom_components/spyster/const.py`

**Additions**:
```python
# Configuration Constants
CONFIG_MIN_ROUND_DURATION = 1      # minutes
CONFIG_MAX_ROUND_DURATION = 30     # minutes
CONFIG_DEFAULT_ROUND_DURATION = 7  # minutes

CONFIG_MIN_ROUNDS = 1
CONFIG_MAX_ROUNDS = 20
CONFIG_DEFAULT_ROUNDS = 5

CONFIG_DEFAULT_LOCATION_PACK = "classic"

# Error Codes (add to existing)
ERR_CONFIG_INVALID_DURATION = "CONFIG_INVALID_DURATION"
ERR_CONFIG_INVALID_ROUNDS = "CONFIG_INVALID_ROUNDS"
ERR_CONFIG_INVALID_PACK = "CONFIG_INVALID_PACK"
ERR_CONFIG_GAME_STARTED = "CONFIG_GAME_STARTED"

# Error Messages (add to existing dict)
ERROR_MESSAGES = {
    # ...existing error messages...
    ERR_CONFIG_INVALID_DURATION: "Round duration must be between 1-30 minutes.",
    ERR_CONFIG_INVALID_ROUNDS: "Number of rounds must be between 1-20.",
    ERR_CONFIG_INVALID_PACK: "Selected location pack not found.",
    ERR_CONFIG_GAME_STARTED: "Cannot change configuration after game has started.",
}
```

## Testing Strategy

### Unit Tests
- **GameConfig validation**: All boundary conditions (min, max, invalid)
- **GameState.update_config()**: Phase guards, field validation, state updates
- **WebSocket handler**: Permission checks, error responses, state broadcast

### Integration Tests
- **End-to-end configuration flow**: Host changes config → server updates → all clients see update
- **Configuration persistence**: Config values used when game starts
- **Error scenarios**: Invalid values rejected, non-host blocked, post-game-start blocked

### Manual Testing Checklist
- [ ] Host sees configuration panel in lobby with default values
- [ ] Increment/decrement buttons work for both numeric fields
- [ ] Location pack dropdown shows available packs
- [ ] Configuration changes broadcast to all connected players in real-time
- [ ] Player view displays current configuration (read-only)
- [ ] Configuration cannot be changed after game starts
- [ ] Invalid values (out of range) are rejected with error message
- [ ] Only host can change configuration (non-host gets error)
- [ ] Touch targets meet 48px minimum (WCAG)
- [ ] Keyboard navigation works for all controls
- [ ] Focus states are clearly visible
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] ARIA labels present on all interactive elements

## Definition of Done

- [ ] All 9 implementation tasks completed
- [ ] All unit tests passing (15+ tests)
- [ ] Integration tests passing
- [ ] Manual testing checklist completed
- [ ] Code follows project patterns (naming, logging, error handling)
- [ ] Configuration values stored in `const.py`
- [ ] Phase guards implemented and tested
- [ ] State broadcast after configuration changes
- [ ] Host UI configuration panel functional
- [ ] Player UI displays current configuration
- [ ] Accessibility requirements met (WCAG AA, ARIA, keyboard nav)
- [ ] Code reviewed by another developer
- [ ] No console errors during normal operation

## Dependencies

### Blocking Dependencies
- **Story 2.6**: Host Lobby Management (must have host display and player list working)

### Technical Dependencies
- GameState class with phase enum
- WebSocket handler with message routing
- Host and player HTML/JS infrastructure
- Constants file with error codes

## Notes

### Architecture Compliance
- **ARCH-14**: State broadcast after every config update ✓
- **ARCH-15**: All config values and limits in `const.py` ✓
- **ARCH-16**: Logging includes field and value context ✓
- **ARCH-17**: Phase guard prevents config changes after game starts ✓

### UX Compliance
- **UX-4**: All buttons meet 48px minimum touch target ✓
- **UX-11**: Color contrast meets WCAG AA ✓
- **UX-12**: ARIA roles on all interactive elements ✓
- **UX-13**: Respects `prefers-reduced-motion` ✓
- **UX-14**: Full keyboard navigation support ✓

### Future Enhancements (Post-MVP)
- Multiple location pack support with pack switching
- Custom round duration presets (Quick: 3min, Standard: 7min, Long: 15min)
- Configuration templates (save/load favorite settings)
- Location pack preview (show sample locations before selection)

---

**Story Status**: Ready for Development
**Estimated Effort**: 5 story points
**Priority**: High (required for Epic 3)
