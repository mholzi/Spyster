---
story_id: "3.2"
epic_id: "3"
epic_name: "Game Configuration & Role Assignment"
story_name: "Start Game with Player Validation"
priority: "high"
estimated_effort: "4 hours"
dependencies: ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "3.1"]
status: "ready-for-dev"
created: "2025-12-23"
---

# Story 3.2: Start Game with Player Validation

As a **host**,
I want **to start the game when enough players have joined**,
So that **we can begin playing**.

## Acceptance Criteria

### AC1: Player Count Validation (< 4 players)

**Given** fewer than 4 players are in the lobby
**When** the host tries to start
**Then** the START button is disabled
**And** a message shows "Need at least 4 players"

### AC2: Valid Player Count (4-10 players)

**Given** 4-10 players are in the lobby
**When** the host taps START
**Then** an `admin` message with `action: start_game` is sent
**And** the game transitions from LOBBY to ROLES phase

### AC3: Maximum Player Limit

**Given** more than 10 players are in the lobby
**When** this state is reached
**Then** it should not be possible (blocked at join per FR)

### AC4: Player Disconnect During Start

**Given** a player disconnects while START is pressed
**When** the player count drops below 4
**Then** the start is aborted with an error message

## Requirements Coverage

### Functional Requirements

- **FR6**: Host can start the game when 4-10 players have joined
- **FR19**: System assigns exactly one player as Spy per round
- **FR22**: All players see a loading state during role assignment (no data leak)

### Non-Functional Requirements

- **NFR2**: WebSocket Latency - Messages delivered in < 100ms on local network
- **NFR4**: State Sync - All players see same game state within 500ms of change
- **NFR6**: Role Unpredictability - Spy assignment cannot be predicted or reverse-engineered from client data

### Architectural Requirements

- **ARCH-3**: Implement GamePhase enum: LOBBY, ROLES, QUESTIONING, VOTE, REVEAL, SCORING, END, PAUSED
- **ARCH-4**: Phase transitions must follow defined flow (no skipping phases)
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on all state-mutating methods
- **ARCH-19**: Return pattern for actions: `(success: bool, error_code: str | None)`

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Add error codes for game start validation:

```python
# Add to existing error codes
ERR_NOT_ENOUGH_PLAYERS = "NOT_ENOUGH_PLAYERS"
ERR_START_ABORTED = "START_ABORTED"
ERR_GAME_ALREADY_STARTED = "GAME_ALREADY_STARTED"

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_NOT_ENOUGH_PLAYERS: "Need at least 4 players to start the game.",
    ERR_START_ABORTED: "Game start aborted - not enough players.",
    ERR_GAME_ALREADY_STARTED: "Game has already started.",
}

# Game configuration constants
MIN_PLAYERS = 4
MAX_PLAYERS = 10
```

#### 2. GameState (`game/state.py`)

Add `start_game()` method with validation:

```python
class GameState:
    def start_game(self) -> tuple[bool, str | None]:
        """
        Start the game if conditions are met.

        Returns:
            (success: bool, error_code: str | None)
        """
        # Phase guard
        if self.phase != GamePhase.LOBBY:
            _LOGGER.warning("Cannot start game - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        # Check if game already started
        if self._game_started:
            _LOGGER.warning("Game already started")
            return False, ERR_GAME_ALREADY_STARTED

        # Count connected players only
        connected_count = self.get_connected_player_count()

        # Validate minimum players
        if connected_count < MIN_PLAYERS:
            _LOGGER.info(
                "Cannot start game - not enough players: %d (need %d)",
                connected_count,
                MIN_PLAYERS
            )
            return False, ERR_NOT_ENOUGH_PLAYERS

        # Validate maximum players (should be prevented at join, but double-check)
        if connected_count > MAX_PLAYERS:
            _LOGGER.warning(
                "Too many players: %d (max %d) - this should not happen",
                connected_count,
                MAX_PLAYERS
            )
            return False, ERR_GAME_FULL

        # All validations passed - start game
        _LOGGER.info("Starting game with %d players", connected_count)
        self._game_started = True
        self.phase = GamePhase.ROLES
        self.current_round = 1

        return True, None

    def get_connected_player_count(self) -> int:
        """Get count of currently connected players."""
        return sum(1 for p in self.players.values() if p.connected)

    def can_start_game(self) -> bool:
        """Check if game can be started (for UI state)."""
        if self.phase != GamePhase.LOBBY:
            return False
        if self._game_started:
            return False

        connected_count = self.get_connected_player_count()
        return MIN_PLAYERS <= connected_count <= MAX_PLAYERS
```

Add fields to `__init__`:

```python
def __init__(self, ...):
    # ... existing fields ...
    self._game_started: bool = False
    self.current_round: int = 0
```

#### 3. WebSocket Handler (`server/websocket.py`)

Add `start_game` admin action handler:

```python
async def _handle_admin(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle admin actions from host."""
    player = self._get_player_by_ws(ws)

    # Verify player is host
    if not player or not player.is_host:
        _LOGGER.warning("Non-host attempted admin action: %s", data.get("action"))
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_HOST,
            "message": ERROR_MESSAGES[ERR_NOT_HOST]
        })
        return

    action = data.get("action")

    if action == "start_game":
        await self._handle_start_game(ws)
    # ... other admin actions ...
    else:
        _LOGGER.warning("Unknown admin action: %s", action)
        await ws.send_json({
            "type": "error",
            "code": "ERR_UNKNOWN_ACTION",
            "message": "Unknown admin action."
        })

async def _handle_start_game(self, ws: web.WebSocketResponse) -> None:
    """Handle game start request from host."""
    success, error_code = self.game_state.start_game()

    if not success:
        _LOGGER.info("Game start failed: %s", error_code)
        await ws.send_json({
            "type": "error",
            "code": error_code,
            "message": ERROR_MESSAGES[error_code]
        })
        return

    # Game started successfully - broadcast to all players
    _LOGGER.info("Game started - transitioning to ROLES phase")
    await self.broadcast_state()
```

Add admin message type handler in `_handle_message`:

```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Route WebSocket messages to appropriate handlers."""
    msg_type = data.get("type")

    if msg_type == "join":
        await self._handle_join(ws, data)
    elif msg_type == "admin":
        await self._handle_admin(ws, data)
    # ... other message types ...
    else:
        _LOGGER.warning("Unknown message type: %s", msg_type)
        await ws.send_json({
            "type": "error",
            "code": "ERR_INVALID_MESSAGE",
            "message": "Invalid message type."
        })
```

#### 4. Host Display UI (`www/host.html`)

Add START button to lobby view:

```html
<!-- In lobby phase section -->
<div id="lobby-view" class="phase-view">
    <div class="lobby-header">
        <h1>Waiting for Players</h1>
        <div id="player-count-display" class="player-count">
            <span id="player-count">0</span> players
        </div>
    </div>

    <!-- Player list -->
    <div id="player-list" class="player-list">
        <!-- Populated by JavaScript -->
    </div>

    <!-- Start game controls -->
    <div class="game-controls">
        <button
            id="start-game-btn"
            class="btn-primary btn-large"
            disabled
        >
            START GAME
        </button>
        <div id="start-message" class="help-text"></div>
    </div>
</div>
```

#### 5. Host Display Logic (`www/js/host.js`)

Add UI update logic:

```javascript
class HostDisplay {
    constructor() {
        this.state = null;
        this.ws = null;
        this.setupEventListeners();
    }

    setupEventListeners() {
        const startBtn = document.getElementById('start-game-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startGame());
        }
    }

    startGame() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        // Send start_game admin action
        this.ws.send(JSON.stringify({
            type: 'admin',
            action: 'start_game'
        }));
    }

    updateLobbyView(state) {
        const playerCount = state.player_count || 0;
        const connectedCount = state.connected_count || 0;
        const canStart = state.can_start || false;

        // Update player count display
        const countDisplay = document.getElementById('player-count');
        if (countDisplay) {
            countDisplay.textContent = connectedCount;
        }

        // Update START button state
        const startBtn = document.getElementById('start-game-btn');
        const startMessage = document.getElementById('start-message');

        if (startBtn) {
            startBtn.disabled = !canStart;

            if (connectedCount < MIN_PLAYERS) {
                startBtn.classList.add('disabled');
                if (startMessage) {
                    startMessage.textContent = `Need at least ${MIN_PLAYERS} players`;
                    startMessage.classList.add('warning');
                }
            } else if (connectedCount >= MIN_PLAYERS && connectedCount <= MAX_PLAYERS) {
                startBtn.classList.remove('disabled');
                if (startMessage) {
                    startMessage.textContent = 'Ready to start!';
                    startMessage.classList.remove('warning');
                    startMessage.classList.add('success');
                }
            }
        }

        // Update player list
        this.renderPlayerList(state.players || []);
    }

    renderPlayerList(players) {
        const listElement = document.getElementById('player-list');
        if (!listElement) return;

        listElement.innerHTML = players.map(player => `
            <div class="player-card ${player.connected ? 'connected' : 'disconnected'}">
                <span class="player-name">${this.escapeHtml(player.name)}</span>
                <span class="connection-indicator">
                    ${player.connected ? '●' : '○'}
                </span>
            </div>
        `).join('');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    onStateUpdate(state) {
        this.state = state;

        if (state.phase === 'LOBBY') {
            this.updateLobbyView(state);
        }
        // ... other phase handlers ...
    }
}

// Constants
const MIN_PLAYERS = 4;
const MAX_PLAYERS = 10;

// Initialize
const hostDisplay = new HostDisplay();
```

#### 6. Player Display UI (`www/player.html`)

Add loading state for role assignment:

```html
<!-- Loading state shown during ROLES phase -->
<div id="roles-loading-view" class="phase-view" style="display: none;">
    <div class="loading-container">
        <div class="spinner"></div>
        <h2>Assigning roles...</h2>
        <p class="help-text">Please wait</p>
    </div>
</div>
```

#### 7. Player Display Logic (`www/js/player.js`)

Add phase transition handling:

```javascript
class PlayerDisplay {
    constructor() {
        this.state = null;
        this.ws = null;
    }

    onStateUpdate(state) {
        this.state = state;

        // Hide all phase views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        // Show appropriate view based on phase
        switch (state.phase) {
            case 'LOBBY':
                this.showLobbyView(state);
                break;
            case 'ROLES':
                this.showRolesLoadingView(state);
                break;
            // ... other phases ...
        }
    }

    showLobbyView(state) {
        const lobbyView = document.getElementById('lobby-view');
        if (lobbyView) {
            lobbyView.style.display = 'block';
            // Update lobby UI
            this.updateLobbyInfo(state);
        }
    }

    showRolesLoadingView(state) {
        const rolesView = document.getElementById('roles-loading-view');
        if (rolesView) {
            rolesView.style.display = 'block';
        }
    }

    updateLobbyInfo(state) {
        const playerCount = state.connected_count || 0;
        const statusText = document.getElementById('lobby-status-text');

        if (statusText) {
            if (playerCount < MIN_PLAYERS) {
                statusText.textContent = `Waiting for more players (${playerCount}/${MIN_PLAYERS})`;
            } else {
                statusText.textContent = `${playerCount} players ready - waiting for host to start`;
            }
        }
    }
}

// Constants
const MIN_PLAYERS = 4;
const MAX_PLAYERS = 10;

// Initialize
const playerDisplay = new PlayerDisplay();
```

### State Flow Diagram

```
LOBBY Phase:
  └─> Host clicks START button
       └─> Send {"type": "admin", "action": "start_game"}
            └─> GameState.start_game() validates:
                 ├─> Phase == LOBBY? ✓
                 ├─> Not already started? ✓
                 ├─> Connected players >= 4? ✓
                 └─> Connected players <= 10? ✓
                      └─> SUCCESS:
                           ├─> Set phase = ROLES
                           ├─> Set current_round = 1
                           ├─> Set _game_started = True
                           └─> Broadcast state to all players
                                ├─> Host sees phase transition
                                └─> Players see "Assigning roles..." loading
```

### Error Handling

| Condition | Error Code | UI Response |
|-----------|------------|-------------|
| < 4 players | `ERR_NOT_ENOUGH_PLAYERS` | START button disabled, show "Need at least 4 players" |
| > 10 players | `ERR_GAME_FULL` | Blocked at join (should not occur) |
| Phase != LOBBY | `ERR_INVALID_PHASE` | START button hidden/disabled |
| Already started | `ERR_GAME_ALREADY_STARTED` | START button disabled |
| Not host | `ERR_NOT_HOST` | START button not visible to players |
| Player disconnects during start | `ERR_START_ABORTED` | Show error message, remain in LOBBY |

## Implementation Tasks

### Task 1: Update Constants

**File:** `custom_components/spyster/const.py`

1. Add `MIN_PLAYERS = 4` constant
2. Add `MAX_PLAYERS = 10` constant
3. Add `ERR_NOT_ENOUGH_PLAYERS` error code
4. Add `ERR_START_ABORTED` error code
5. Add `ERR_GAME_ALREADY_STARTED` error code
6. Add error messages to `ERROR_MESSAGES` dict

**Validation:**
- Constants are used throughout codebase (no hardcoded values)
- Error codes follow existing naming pattern

### Task 2: Update GameState Class

**File:** `custom_components/spyster/game/state.py`

1. Add `_game_started: bool = False` field to `__init__`
2. Add `current_round: int = 0` field to `__init__`
3. Implement `start_game()` method with all validations
4. Implement `get_connected_player_count()` helper
5. Implement `can_start_game()` UI state helper
6. Add logging for all state transitions

**Validation:**
- Phase guard prevents starting from non-LOBBY phase
- Player count validated (4-10)
- Return pattern follows `(bool, str | None)`
- Logging includes context (player count, phase)

### Task 3: Add WebSocket Admin Handler

**File:** `custom_components/spyster/server/websocket.py`

1. Add `_handle_admin()` method with host verification
2. Implement `_handle_start_game()` method
3. Add `"admin"` message type to `_handle_message()` router
4. Broadcast state after successful start
5. Send error responses for failed validations

**Validation:**
- Only host can trigger admin actions
- Error responses include code + message
- State broadcast after phase transition
- Logging includes player name and action

### Task 4: Update Host Display HTML

**File:** `custom_components/spyster/www/host.html`

1. Add START button to lobby view
2. Add player count display
3. Add status message area below button
4. Apply proper CSS classes for styling

**Validation:**
- Button is clearly visible and accessible
- Button has proper touch target size (48px+)
- Status message area for feedback

### Task 5: Update Host Display Logic

**File:** `custom_components/spyster/www/js/host.js`

1. Add `setupEventListeners()` for START button
2. Implement `startGame()` to send admin message
3. Implement `updateLobbyView()` to update button state
4. Update player count in real-time
5. Show/hide status messages based on state

**Validation:**
- Button disabled when < 4 players
- Button enabled when 4-10 players
- Status message updates in real-time
- Proper XSS escaping for player names

### Task 6: Update Player Display HTML

**File:** `custom_components/spyster/www/player.html`

1. Add loading view for ROLES phase
2. Add spinner/animation element
3. Add "Assigning roles..." text
4. Style loading state to match theme

**Validation:**
- Loading state prevents data leaks (FR22)
- No flicker or partial data visible
- Accessible to screen readers

### Task 7: Update Player Display Logic

**File:** `custom_components/spyster/www/js/player.js`

1. Add phase routing in `onStateUpdate()`
2. Implement `showRolesLoadingView()`
3. Update `updateLobbyInfo()` with player count
4. Handle phase transitions smoothly

**Validation:**
- Phase views show/hide correctly
- No console errors during transitions
- Smooth visual transitions

### Task 8: Add CSS Styles

**File:** `custom_components/spyster/www/css/styles.css`

1. Style `.btn-large` for START button
2. Style `.help-text` for status messages
3. Style `.warning` and `.success` message states
4. Style `.spinner` loading animation
5. Style `.loading-container` centered layout

**Validation:**
- Button meets minimum touch target (48px+)
- Warning messages clearly visible (color + icon)
- Loading spinner animates smoothly
- Respects `prefers-reduced-motion`

## Testing Strategy

### Unit Tests

**File:** `tests/test_state.py`

```python
def test_start_game_success(game_state_with_players):
    """Test successful game start with 4-10 players."""
    # Setup: 4 connected players
    success, error = game_state_with_players.start_game()
    assert success is True
    assert error is None
    assert game_state_with_players.phase == GamePhase.ROLES
    assert game_state_with_players.current_round == 1

def test_start_game_not_enough_players(game_state):
    """Test game start fails with < 4 players."""
    # Setup: 3 connected players
    success, error = game_state.start_game()
    assert success is False
    assert error == ERR_NOT_ENOUGH_PLAYERS
    assert game_state.phase == GamePhase.LOBBY

def test_start_game_invalid_phase(game_state_in_roles):
    """Test game start fails from non-LOBBY phase."""
    success, error = game_state_in_roles.start_game()
    assert success is False
    assert error == ERR_INVALID_PHASE

def test_start_game_already_started(game_state_started):
    """Test game start fails if already started."""
    success, error = game_state_started.start_game()
    assert success is False
    assert error == ERR_GAME_ALREADY_STARTED

def test_can_start_game_conditions(game_state):
    """Test can_start_game() helper various conditions."""
    # < 4 players
    assert game_state.can_start_game() is False

    # 4 players
    add_players(game_state, 4)
    assert game_state.can_start_game() is True

    # 10 players
    add_players(game_state, 6)
    assert game_state.can_start_game() is True

    # Already started
    game_state._game_started = True
    assert game_state.can_start_game() is False

def test_get_connected_player_count(game_state):
    """Test connected player counting."""
    add_players(game_state, 5, connected=True)
    add_players(game_state, 2, connected=False)

    assert game_state.get_connected_player_count() == 5
```

### Integration Tests

**File:** `tests/test_websocket.py`

```python
async def test_start_game_admin_action(websocket_handler, mock_host_ws):
    """Test start_game admin action via WebSocket."""
    # Setup: Host connected, 4 players
    await websocket_handler._handle_message(mock_host_ws, {
        "type": "admin",
        "action": "start_game"
    })

    # Verify: Phase transitioned, state broadcasted
    assert websocket_handler.game_state.phase == GamePhase.ROLES
    mock_host_ws.send_json.assert_called()  # State broadcasted

async def test_start_game_non_host(websocket_handler, mock_player_ws):
    """Test non-host cannot start game."""
    await websocket_handler._handle_message(mock_player_ws, {
        "type": "admin",
        "action": "start_game"
    })

    # Verify: Error response sent
    mock_player_ws.send_json.assert_called_with({
        "type": "error",
        "code": ERR_NOT_HOST,
        "message": ERROR_MESSAGES[ERR_NOT_HOST]
    })

async def test_start_game_not_enough_players(websocket_handler, mock_host_ws):
    """Test start fails with < 4 players."""
    # Setup: Only 2 players
    await websocket_handler._handle_message(mock_host_ws, {
        "type": "admin",
        "action": "start_game"
    })

    # Verify: Error response
    mock_host_ws.send_json.assert_called_with({
        "type": "error",
        "code": ERR_NOT_ENOUGH_PLAYERS,
        "message": ERROR_MESSAGES[ERR_NOT_ENOUGH_PLAYERS]
    })
```

### Manual Testing Checklist

**Scenario 1: Successful Game Start**
- [ ] Host creates game, 4 players join
- [ ] START button is enabled with "Ready to start!" message
- [ ] Host clicks START
- [ ] All players see "Assigning roles..." loading state
- [ ] Phase transitions to ROLES
- [ ] No console errors

**Scenario 2: Not Enough Players**
- [ ] Host creates game, 3 players join
- [ ] START button is disabled
- [ ] "Need at least 4 players" message displayed
- [ ] Host cannot click START
- [ ] 4th player joins
- [ ] Button becomes enabled automatically

**Scenario 3: Player Disconnects During Start**
- [ ] Host creates game, 4 players join
- [ ] START button enabled
- [ ] 1 player disconnects (count drops to 3)
- [ ] START button becomes disabled
- [ ] Host sees updated player count
- [ ] "Need at least 4 players" message shown

**Scenario 4: Non-Host Cannot Start**
- [ ] Regular player views their phone
- [ ] No START button visible
- [ ] Cannot send start_game message
- [ ] Only host has controls

**Scenario 5: Maximum Player Count**
- [ ] 10 players join
- [ ] START button still enabled
- [ ] Host can start game
- [ ] 11th player tries to join → blocked (existing FR)

## Definition of Done

- [ ] All code implemented following architecture patterns
- [ ] All constants in `const.py` (no hardcoded values)
- [ ] Phase guards implemented on `start_game()`
- [ ] Error responses include code + message
- [ ] State broadcast after phase transition
- [ ] Logging includes context (player count, phase)
- [ ] All unit tests pass (100% coverage of new code)
- [ ] All integration tests pass
- [ ] Manual testing scenarios completed
- [ ] Code follows naming conventions (snake_case, camelCase)
- [ ] No XSS vulnerabilities (HTML escaping)
- [ ] No console errors or warnings
- [ ] Meets NFR2: WebSocket latency < 100ms
- [ ] Meets NFR4: State sync within 500ms
- [ ] Host display responsive (768px+ viewports)
- [ ] Player display responsive (320-428px)
- [ ] Accessibility: ARIA roles, keyboard navigation
- [ ] Documentation updated (if needed)

## Notes

### Security Considerations

1. **Host Verification**: Only authenticated host can trigger `start_game`
2. **Phase Guards**: Prevent starting from invalid phases
3. **XSS Protection**: All player names escaped in HTML
4. **State Isolation**: Each player receives personalized state (prep for role assignment)

### Performance Considerations

1. **Connected Player Count**: Cached/calculated efficiently
2. **State Broadcast**: Single broadcast to all connected players
3. **UI Updates**: Debounced to prevent flicker during rapid changes

### Future Enhancements

1. **Countdown Timer**: 5-second countdown before role assignment
2. **Player Ready State**: Players confirm ready before start
3. **Minimum Connected Time**: Prevent joining and immediately starting
4. **Custom Player Limits**: Host configures min/max players

## Related Stories

- **Depends On**:
  - Story 2.1: WebSocket Connection Handler (message routing)
  - Story 2.2: Player Join Flow (player sessions)
  - Story 2.3: Player Session Management (session tokens)
  - Story 2.4: Disconnect Detection (connected player count)
  - Story 2.5: Player Reconnection (graceful handling)
  - Story 2.6: Host Lobby Management (host controls)
  - Story 3.1: Game Configuration UI (settings before start)

- **Blocks**:
  - Story 3.3: Spy Assignment (triggered after ROLES transition)
  - Story 3.4: Role Distribution (follows spy assignment)
  - Story 3.5: Role Display UI (players see their roles)

- **Related**:
  - Story 4.1: Transition to Questioning Phase (next phase after ROLES)

## Implementation Priority

**Priority**: HIGH
**Sprint**: Sprint 2
**Estimated Effort**: 4 hours

This story is critical path for gameplay - without it, no game can start. Should be implemented immediately after lobby management (2.6) is complete.
