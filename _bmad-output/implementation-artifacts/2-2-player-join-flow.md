---
story_id: '2-2'
story_name: 'Player Join Flow'
epic: 'Epic 2: Player Join & Connection'
status: 'ready-for-dev'
created: '2025-12-23'
project: 'Spyster'
dependencies:
  - '2-1-websocket-connection-handler'
technical_context:
  - 'architecture.md - WebSocket Protocol, Security Architecture'
  - 'project-context.md - Python Rules, WebSocket Rules, Anti-Patterns'
  - 'epics.md - FR10, FR11, FR12, FR13, FR18'
---

# Story 2.2: Player Join Flow

**Epic:** Epic 2: Player Join & Connection

**Status:** ready-for-dev

**Dependencies:**
- Story 2.1: WebSocket Connection Handler (must be implemented first)

---

## User Story

**As a** player
**I want** to enter my name and join the game
**So that** I appear in the lobby and can participate

---

## Acceptance Criteria

### AC1: Name Entry UI Display
**Given** a player opens the join page at `/api/spyster/player`
**When** the page loads
**Then** a name entry field is displayed with a "Join" button
**And** the WebSocket connection is established automatically
**And** the UI shows ready state (no loading spinner after connection)

**Implementation Notes:**
- Input field with `id="player-name-input"`
- Max length: 20 characters (HTML attribute + client validation)
- Pattern validation: 1-20 characters
- Submit button with `id="join-button"`
- Mobile-optimized (44px minimum touch target per UX-4)
- Dark neon theme (per UX-1, UX-2)
- WebSocket initialized on DOMContentLoaded (depends on Story 2.1)

---

### AC2: Successful Join Flow
**Given** a player enters a valid name (1-20 characters)
**When** they tap "Join"
**Then** a `join` message is sent via WebSocket
**And** the server validates the request and creates a player session
**And** the player receives a `join_success` response with session token
**And** their name appears in the lobby on both player and host displays

**Implementation Notes:**
- WebSocket message format: `{"type": "join", "name": "<player_name>"}`
- Server validates: name length, game phase, player count, duplicate names (FR18)
- Server creates PlayerSession with CSPRNG session token (per ARCH-6)
- Player receives `join_success` with session token and player name
- Server broadcasts updated state to all connected clients (per ARCH-14)
- Host display updates player list in real-time

**Server Logic:**
```python
# In server/websocket.py
async def _handle_join(self, ws: web.WebSocketResponse, data: dict) -> None:
    name = data.get("name", "").strip()

    # Validate name length
    if not name or len(name) > 20:
        await ws.send_json({
            "type": "error",
            "code": ERR_NAME_INVALID,
            "message": ERROR_MESSAGES[ERR_NAME_INVALID]
        })
        return

    # Check game phase
    if self.game_state.phase != GamePhase.LOBBY:
        await ws.send_json({
            "type": "error",
            "code": ERR_GAME_ALREADY_STARTED,
            "message": ERROR_MESSAGES[ERR_GAME_ALREADY_STARTED]
        })
        return

    # Check for duplicate name (FR18: remove old session)
    if name in self.game_state.players:
        old_player = self.game_state.players[name]
        if old_player.connected:
            # Close old WebSocket connection
            await old_player.ws.close()
        # Remove old session
        del self.game_state.players[name]
        _LOGGER.info("Removed old session for player: %s", name)

    # Check game capacity
    if len(self.game_state.players) >= 10:
        await ws.send_json({
            "type": "error",
            "code": ERR_GAME_FULL,
            "message": ERROR_MESSAGES[ERR_GAME_FULL]
        })
        return

    # Create player session
    session_token = secrets.token_urlsafe(16)
    player = PlayerSession(
        name=name,
        ws=ws,
        session_token=session_token,
        connected=True
    )

    self.game_state.players[name] = player
    self._ws_to_player[ws] = player

    # Send success response with session token
    await ws.send_json({
        "type": "join_success",
        "session_token": session_token,
        "player_name": name
    })

    _LOGGER.info("Player joined: %s (total: %d)", name, len(self.game_state.players))

    # Broadcast updated state to all clients
    await self.broadcast_state()
```

**Client Logic (www/js/player.js):**
```javascript
// Join button handler
document.getElementById('join-button').addEventListener('click', () => {
    const nameInput = document.getElementById('player-name-input');
    const playerName = nameInput.value.trim();

    if (!playerName || playerName.length > 20) {
        showError('Please enter a name between 1-20 characters');
        return;
    }

    // Send join message
    ws.send(JSON.stringify({
        type: 'join',
        name: playerName
    }));

    // Disable input while waiting
    nameInput.disabled = true;
    document.getElementById('join-button').disabled = true;
});

// Handle join success
function handleJoinSuccess(data) {
    // Store session token in URL
    const url = new URL(window.location);
    url.searchParams.set('token', data.session_token);
    window.history.replaceState({}, '', url);

    // Update UI to show lobby
    showLobby(data.player_name);
}
```

---

### AC3: Duplicate Name Handling (FR18)
**Given** a player enters a name already in use by an active session
**When** they tap "Join"
**Then** the old session is disconnected and removed
**And** the new player successfully joins with that name
**And** the old player's WebSocket receives a close event

**Implementation Notes:**
- **FR18 Requirement**: System removes old session when duplicate name joins
- This allows players to rejoin if browser crashes or tab accidentally closed
- Old WebSocket is closed gracefully before removal
- Server logs the session replacement event
- This replaces the traditional "name already taken" error approach

**Architecture Compliance:**
- Per FR18: "Prevent duplicate sessions - if same name joins, remove old session"
- Per ARCH-4: Phase guard ensures only in LOBBY phase
- Per ARCH-16: Logging includes player name and context

**Note:** If strict name uniqueness is ever needed (future requirement), the alternative implementation would check `connected` status and return `ERR_NAME_TAKEN` instead of removing the old session.

---

### AC4: Game Full Error
**Given** the lobby already has 10 players
**When** a new player tries to join
**Then** they receive error `ERR_GAME_FULL` with message "Sorry, this game is full (max 10 players)."
**And** the join form remains enabled for retry (in case someone leaves)

**Implementation Notes:**
- Maximum players: 10 (per FR11, stored in `MAX_PLAYERS` constant)
- Check count before adding player
- Error code: `ERR_GAME_FULL` (defined in const.py per ARCH-15)
- Error message: User-friendly, from `ERROR_MESSAGES` dict
- Client re-enables input fields after receiving error

**Server Logic:**
```python
# In _handle_join() before creating player session
if len(self.game_state.players) >= 10:
    await ws.send_json({
        "type": "error",
        "code": ERR_GAME_FULL,
        "message": ERROR_MESSAGES[ERR_GAME_FULL]
    })
    return
```

---

### AC5: Game Already Started Error
**Given** the game is no longer in LOBBY phase (host has started the game)
**When** a new player tries to join
**Then** they receive error `ERR_GAME_ALREADY_STARTED` with message "This game has already started."
**And** the join form is disabled (no retry possible)

**Implementation Notes:**
- Phase guard validation (per ARCH-4)
- Check phase at the start of `_handle_join()` before any other validation
- Error code: `ERR_GAME_ALREADY_STARTED` (defined in const.py per ARCH-15)
- Prevents late joins that would disrupt active game
- This check comes BEFORE duplicate name handling (no session created)

**Server Logic:**
```python
# In _handle_join() - first validation
if self.game_state.phase != GamePhase.LOBBY:
    await ws.send_json({
        "type": "error",
        "code": ERR_GAME_ALREADY_STARTED,
        "message": ERROR_MESSAGES[ERR_GAME_ALREADY_STARTED]
    })
    return
```

**Client Error Display:**
```javascript
function handleError(data) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = data.message;
    errorDiv.style.display = 'block';

    // For "game already started", don't re-enable (no retry possible)
    if (data.code === 'ERR_GAME_ALREADY_STARTED') {
        document.getElementById('join-button').textContent = 'Game In Progress';
        document.getElementById('join-button').disabled = true;
        return;
    }

    // For other errors, re-enable input for retry
    document.getElementById('player-name-input').disabled = false;
    document.getElementById('join-button').disabled = false;

    // Auto-hide error after 5 seconds (except for game started)
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}
```

---

## Technical Implementation Details

### Files to Modify

#### 1. `custom_components/spyster/const.py`
Add error codes and messages:
```python
# Error codes for player join
ERR_NAME_INVALID = "NAME_INVALID"
ERR_NAME_TAKEN = "NAME_TAKEN"
ERR_GAME_FULL = "GAME_FULL"
ERR_GAME_ALREADY_STARTED = "GAME_ALREADY_STARTED"

# Error messages
ERROR_MESSAGES = {
    ERR_NAME_INVALID: "Please enter a name between 1-20 characters.",
    ERR_NAME_TAKEN: "That name is already taken. Please choose another.",
    ERR_GAME_FULL: "Sorry, this game is full (max 10 players).",
    ERR_GAME_ALREADY_STARTED: "This game has already started.",
}

# Game configuration
MAX_PLAYERS = 10
MIN_PLAYERS = 4
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 20
```

#### 2. `custom_components/spyster/game/player.py`
Create or update PlayerSession class:
```python
from dataclasses import dataclass
from typing import Optional
from aiohttp import web

@dataclass
class PlayerSession:
    """Represents a player's session in the game."""

    name: str
    session_token: str
    connected: bool = True
    ws: Optional[web.WebSocketResponse] = None

    # Player state
    is_host: bool = False
    is_spy: bool = False
    role: Optional[str] = None

    # Voting state
    voted: bool = False
    vote_target: Optional[str] = None
    vote_confidence: int = 1

    # Scoring
    score: int = 0

    def to_dict(self) -> dict:
        """Return public player info (no sensitive data)."""
        return {
            "name": self.name,
            "connected": self.connected,
            "is_host": self.is_host,
            "score": self.score,
        }
```

#### 3. `custom_components/spyster/server/websocket.py`
Add join message handler:
```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Route WebSocket messages to appropriate handlers."""
    msg_type = data.get("type")

    if msg_type == "join":
        await self._handle_join(ws, data)
    elif msg_type == "admin":
        await self._handle_admin(ws, data)
    elif msg_type == "vote":
        await self._handle_vote(ws, data)
    elif msg_type == "spy_guess":
        await self._handle_spy_guess(ws, data)
    else:
        await ws.send_json({
            "type": "error",
            "code": "ERR_INVALID_MESSAGE",
            "message": "Unknown message type"
        })

async def _handle_join(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle player join request."""
    # Implementation from AC2 above
    # ... (see AC2 Server Logic)
```

#### 4. `custom_components/spyster/www/player.html`
Add join UI:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spyster - Join Game</title>
    <link rel="stylesheet" href="/api/spyster/static/css/styles.css">
</head>
<body class="player-view">
    <div id="join-screen" class="screen">
        <div class="join-container">
            <h1 class="game-logo">SPYSTER</h1>
            <div class="join-form">
                <input
                    type="text"
                    id="player-name-input"
                    placeholder="Enter your name"
                    maxlength="20"
                    autocomplete="off"
                    autocapitalize="words"
                    class="name-input"
                />
                <button id="join-button" class="btn-primary">Join Game</button>
            </div>
            <div id="error-message" class="error-message" style="display: none;"></div>
        </div>
    </div>

    <div id="lobby-screen" class="screen" style="display: none;">
        <h2>Waiting in Lobby</h2>
        <p>You're in! Waiting for host to start...</p>
        <div id="player-list"></div>
    </div>

    <script src="/api/spyster/static/js/player.js"></script>
</body>
</html>
```

#### 5. `custom_components/spyster/www/js/player.js`
Implement WebSocket client with join logic:
```javascript
// WebSocket connection
let ws = null;
let playerName = null;
let sessionToken = null;

// Initialize WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/spyster/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');

        // Check for existing session token
        const urlParams = new URLSearchParams(window.location.search);
        sessionToken = urlParams.get('token');

        if (sessionToken) {
            // Reconnect with existing session
            ws.send(JSON.stringify({
                type: 'reconnect',
                session_token: sessionToken
            }));
        }
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('Connection error. Please check your network.');
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Auto-reconnect logic will be in Story 2.5
    };
}

// Handle incoming messages
function handleMessage(data) {
    switch (data.type) {
        case 'join_success':
            handleJoinSuccess(data);
            break;
        case 'state':
            handleStateUpdate(data);
            break;
        case 'error':
            handleError(data);
            break;
        default:
            console.warn('Unknown message type:', data.type);
    }
}

// Join button click handler
document.getElementById('join-button').addEventListener('click', () => {
    const nameInput = document.getElementById('player-name-input');
    playerName = nameInput.value.trim();

    if (!playerName || playerName.length > 20) {
        showError('Please enter a name between 1-20 characters');
        return;
    }

    // Send join message
    ws.send(JSON.stringify({
        type: 'join',
        name: playerName
    }));

    // Disable input while waiting
    nameInput.disabled = true;
    document.getElementById('join-button').disabled = true;
});

// Handle successful join
function handleJoinSuccess(data) {
    sessionToken = data.session_token;
    playerName = data.player_name;

    // Store session token in URL
    const url = new URL(window.location);
    url.searchParams.set('token', sessionToken);
    window.history.replaceState({}, '', url);

    // Show lobby screen
    document.getElementById('join-screen').style.display = 'none';
    document.getElementById('lobby-screen').style.display = 'block';
}

// Handle state updates
function handleStateUpdate(data) {
    if (data.phase === 'LOBBY') {
        updatePlayerList(data.players);
    }
}

// Update player list in lobby
function updatePlayerList(players) {
    const playerList = document.getElementById('player-list');
    playerList.innerHTML = '<h3>Players:</h3>';

    const ul = document.createElement('ul');
    ul.className = 'player-list';

    players.forEach(player => {
        const li = document.createElement('li');
        li.className = 'player-list-item';
        li.textContent = player.name;
        if (player.name === playerName) {
            li.classList.add('you');
        }
        ul.appendChild(li);
    });

    playerList.appendChild(ul);
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    // Re-enable input for retry
    document.getElementById('player-name-input').disabled = false;
    document.getElementById('join-button').disabled = false;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
});
```

#### 6. `custom_components/spyster/www/css/styles.css`
Add join screen styles:
```css
/* Player Join Screen */
.player-view {
    background: var(--bg-primary, #0a0a12);
    color: var(--text-primary, #ffffff);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.join-container {
    max-width: 400px;
    width: 100%;
    text-align: center;
}

.game-logo {
    font-size: 48px;
    font-weight: 700;
    color: var(--accent-primary, #ff2d6a);
    margin-bottom: 40px;
    text-transform: uppercase;
    letter-spacing: 4px;
}

.join-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.name-input {
    width: 100%;
    height: 56px;
    padding: 0 20px;
    font-size: 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #ffffff;
    transition: all 0.2s;
}

.name-input:focus {
    outline: none;
    border-color: var(--accent-primary, #ff2d6a);
    background: rgba(255, 255, 255, 0.08);
}

.btn-primary {
    width: 100%;
    height: 56px;
    font-size: 18px;
    font-weight: 600;
    background: var(--accent-primary, #ff2d6a);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.btn-primary:hover:not(:disabled) {
    background: #ff4580;
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(255, 45, 106, 0.4);
}

.btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.error-message {
    margin-top: 16px;
    padding: 12px 20px;
    background: rgba(255, 0, 0, 0.1);
    border: 1px solid rgba(255, 0, 0, 0.3);
    border-radius: 8px;
    color: #ff6b6b;
    font-size: 14px;
}

/* Lobby Screen */
.player-list {
    list-style: none;
    padding: 0;
    margin: 20px 0;
}

.player-list-item {
    padding: 12px 20px;
    margin: 8px 0;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    font-size: 16px;
}

.player-list-item.you {
    background: rgba(255, 45, 106, 0.2);
    border: 1px solid var(--accent-primary, #ff2d6a);
}
```

---

## Testing Requirements

### Unit Tests

**File:** `tests/test_join_flow.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.spyster.game.state import GameState, GamePhase
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.const import (
    ERR_NAME_INVALID,
    ERR_GAME_FULL,
    ERR_GAME_ALREADY_STARTED,
    MAX_PLAYERS,
)

@pytest.fixture
async def game_state():
    """Create a fresh game state in LOBBY phase."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    return state

@pytest.mark.asyncio
async def test_valid_join(game_state):
    """Test successful player join."""
    ws = AsyncMock()

    # Simulate join
    player_name = "Alice"
    # ... test implementation

    assert player_name in game_state.players
    assert game_state.players[player_name].connected
    assert len(game_state.players) == 1

@pytest.mark.asyncio
async def test_invalid_name_too_short(game_state):
    """Test join with empty name."""
    ws = AsyncMock()
    # ... test implementation

    ws.send_json.assert_called_once()
    error_data = ws.send_json.call_args[0][0]
    assert error_data["code"] == ERR_NAME_INVALID

@pytest.mark.asyncio
async def test_invalid_name_too_long(game_state):
    """Test join with name > 20 characters."""
    ws = AsyncMock()
    long_name = "A" * 21
    # ... test implementation

    ws.send_json.assert_called_once()
    error_data = ws.send_json.call_args[0][0]
    assert error_data["code"] == ERR_NAME_INVALID

@pytest.mark.asyncio
async def test_duplicate_name_replaces_old_session(game_state):
    """Test FR18: duplicate name removes old session."""
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    # First join - Alice with ws1
    player1 = PlayerSession(
        name="Alice",
        session_token="token1",
        ws=ws1,
        connected=True
    )
    game_state.players["Alice"] = player1

    assert len(game_state.players) == 1
    assert game_state.players["Alice"].session_token == "token1"

    # Second join with same name - Alice with ws2
    # Handler should:
    # 1. Close old WebSocket
    # 2. Remove old session
    # 3. Create new session
    # (Implementation in _handle_join simulates this)

    # After duplicate join handling:
    # Old WebSocket should be closed
    ws1.close.assert_called_once()

    # New player should be in game with new token
    player2 = PlayerSession(
        name="Alice",
        session_token="token2",
        ws=ws2,
        connected=True
    )
    game_state.players["Alice"] = player2

    assert len(game_state.players) == 1
    assert game_state.players["Alice"].ws == ws2
    assert game_state.players["Alice"].session_token == "token2"

@pytest.mark.asyncio
async def test_game_full(game_state):
    """Test join when game has 10 players."""
    # Add 10 players
    for i in range(MAX_PLAYERS):
        ws = AsyncMock()
        player = PlayerSession(
            name=f"Player{i}",
            session_token=f"token{i}",
            ws=ws,
            connected=True
        )
        game_state.players[player.name] = player

    # Try to add 11th player
    ws_new = AsyncMock()
    # ... test implementation

    ws_new.send_json.assert_called_once()
    error_data = ws_new.send_json.call_args[0][0]
    assert error_data["code"] == ERR_GAME_FULL

@pytest.mark.asyncio
async def test_join_after_game_started(game_state):
    """Test join when game is no longer in LOBBY."""
    game_state.phase = GamePhase.ROLES
    ws = AsyncMock()

    # ... test implementation

    ws.send_json.assert_called_once()
    error_data = ws.send_json.call_args[0][0]
    assert error_data["code"] == ERR_GAME_ALREADY_STARTED
```

### Integration Tests

**Manual Test Scenarios:**

1. **Happy Path: First Player Join**
   - Open player URL
   - Enter name "Alice"
   - Click Join
   - Verify: Join screen disappears, lobby screen appears
   - Verify: Player list shows "Alice" with "you" indicator

2. **Multiple Players Join**
   - Repeat join flow with different names on different devices
   - Verify: All players see updated player list in real-time
   - Verify: Host display shows all players

3. **Name Validation**
   - Try empty name → error shown
   - Try 21-character name → error shown
   - Try valid name → success

4. **Duplicate Name Handling (FR18)**
   - Join with name "Bob" on Device 1
   - Join with name "Bob" on Device 2
   - Verify: Device 1 disconnected
   - Verify: Device 2 successfully joined as "Bob"

5. **Game Full**
   - Have 10 players join
   - Try to join as 11th player
   - Verify: Error "Sorry, this game is full"

6. **Join After Game Started (AC5)**
   - Host starts game (transition from LOBBY to ROLES phase)
   - New player opens join page and tries to join
   - Verify: Error message "This game has already started" appears
   - Verify: Join button shows "Game In Progress" and is disabled
   - Verify: No retry is possible (correct behavior - game active)

---

## Definition of Done

- [ ] All acceptance criteria implemented and tested
- [ ] Unit tests written and passing (minimum 90% coverage)
- [ ] Integration tests pass (manual or automated)
- [ ] Code follows architectural patterns from project-context.md
- [ ] WebSocket messages follow protocol from architecture.md
- [ ] Error handling uses constants from const.py
- [ ] Logging includes context (player names, counts)
- [ ] UI follows UX design specification (dark neon theme, 44px touch targets)
- [ ] Mobile-first responsive design verified on actual devices
- [ ] State broadcast after join verified (real-time updates)
- [ ] FR18 duplicate session handling verified
- [ ] Code reviewed (if using code-review workflow)
- [ ] Documentation updated (if needed)

---

## Related Stories

**Depends On:**
- Story 2.1: WebSocket Connection Handler (REQUIRED - WebSocket infrastructure must exist)

**Leads To:**
- Story 2.3: Player Session Management (session tokens, reconnection using tokens from this story)
- Story 2.4: Disconnect Detection (monitors sessions created by this story)
- Story 2.5: Reconnection Flow (uses session tokens generated in AC2)
- Story 2.6: Host Lobby Management (remove players, start game with players from this story)

**Related Stories:**
- Epic 3: Host Display will show players added by this story
- Epic 4: Game Start will validate player count from join flow

---

## Notes

### Architectural Compliance
- **ARCH-4 (Phase Guards):** Join only allowed in LOBBY phase - `_handle_join()` validates `self.game_state.phase != GamePhase.LOBBY` first
- **ARCH-6 (Security):** Session token uses `secrets.token_urlsafe(16)` for CSPRNG generation
- **ARCH-12, ARCH-13 (WebSocket Protocol):** All messages use snake_case fields (`player_name`, `session_token`, not camelCase)
- **ARCH-14 (State Broadcast):** After player joins, `broadcast_state()` sends personalized state to all connected clients
- **ARCH-15 (Error Codes):** All errors use constants from `const.py` (`ERR_NAME_INVALID`, `ERR_GAME_FULL`, etc.)
- **ARCH-16 (Logging):** Includes context - `_LOGGER.info("Player joined: %s (total: %d)", name, len(self.game_state.players))`
- **FR18 (Duplicate Handling):** Old session removed and WebSocket closed when duplicate name joins

### Security Considerations
- Session token generated with `secrets.token_urlsafe()` (CSPRNG per ARCH-6)
- No sensitive data in join flow (role assignment comes later)
- Session token stored in URL for mobile browser compatibility

### UX Considerations
- Mobile-first design (320-428px viewport per UX-15)
- 44px minimum touch targets (per UX-4)
- Dark neon theme (#0a0a12 background, #ff2d6a accent per UX-1, UX-2)
- Clear error messages with retry capability
- Real-time feedback (player list updates immediately)

### FR18 Implementation Note
The original requirement "prevent duplicate sessions" is implemented by **removing the old session** when a duplicate name joins. This allows players to rejoin if their browser crashes or they accidentally close the tab. The old WebSocket is closed gracefully.

---

## Implementation Checklist

### Backend
- [ ] Add error codes to const.py
- [ ] Create/update PlayerSession in game/player.py
- [ ] Implement _handle_join() in server/websocket.py
- [ ] Implement broadcast_state() for real-time updates
- [ ] Add validation: name length, game phase, player count
- [ ] Add FR18 duplicate session removal logic
- [ ] Add logging with context

### Frontend
- [ ] Create player.html with join UI
- [ ] Implement WebSocket client in player.js
- [ ] Add join button click handler
- [ ] Add error display UI and logic
- [ ] Add lobby screen with player list
- [ ] Implement session token storage in URL
- [ ] Add CSS styles for join screen (dark neon theme)
- [ ] Mobile-responsive testing (320-428px)

### Testing
- [ ] Write unit tests for join validation
- [ ] Write unit tests for duplicate name handling
- [ ] Write unit tests for game full scenario
- [ ] Write unit tests for wrong phase scenario
- [ ] Manual testing on mobile devices
- [ ] Cross-browser testing (Chrome, Safari, Firefox)
- [ ] Real-time update verification (multiple devices)

---

**Story Ready for Implementation** ✅
