---
story_id: "2-3"
story_name: "Player Session Management"
epic: "Epic 2: Player Join & Connection"
status: "ready-for-dev"
created: "2025-12-23"
project: "Spyster"
---

# Story 2.3: Player Session Management

## Story Overview

As a **system**,
I want **to track player sessions with URL tokens**,
So that **players can reconnect without re-entering their name**.

**Epic:** Epic 2: Player Join & Connection
**Priority:** High
**Story Points:** 5

## Acceptance Criteria

### AC1: Session Token Generation on Join
**Given** a player successfully joins
**When** the join is confirmed
**Then** a session token is generated and included in the URL
**And** the PlayerSession object is created with `connected=True`

**Technical Details:**
- Use `secrets.token_urlsafe(16)` for cryptographically secure token generation
- Token should be unique per player session
- URL format: `/api/spyster/player?token={session_token}`
- Token stored in PlayerSession object for validation

### AC2: Automatic Session Restoration
**Given** a player with an existing session token
**When** they reconnect with the same token
**Then** they are restored to their previous session automatically

**Technical Details:**
- WebSocket handler validates token on connection
- Session lookup by token in `game_state.sessions` dictionary
- Restore player to current game phase with their role intact
- Update `connected=True` on PlayerSession
- Broadcast state update to all connected clients

### AC3: Duplicate Session Prevention (FR18)
**Given** a player tries to join with an in-use name
**When** a valid session exists for that name
**Then** the old session is replaced (prevents duplicate sessions per FR18)

**Technical Details:**
- Check for existing player name in `game_state.players`
- If found, invalidate old session token
- Create new session token for the new connection
- Close old WebSocket connection gracefully with code 4001
- Remove old session from `game_state.sessions`
- Broadcast updated player list
- This allows same player to rejoin if they lose their token URL

## Implementation Details

### Components to Create/Modify

#### 1. `game/player.py` - PlayerSession Class Enhancement

```python
from dataclasses import dataclass, field
import secrets
from datetime import datetime
from typing import Optional
from aiohttp import web

@dataclass
class PlayerSession:
    """Represents a player's session in the game."""

    name: str
    token: str
    connected: bool = True
    is_host: bool = False
    ws: Optional[web.WebSocketResponse] = None
    role: Optional[str] = None  # Assigned during ROLES phase
    is_spy: bool = False
    vote_target: Optional[str] = None
    vote_confidence: int = 1
    score: int = 0
    joined_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)

    @classmethod
    def create_new(cls, name: str, is_host: bool = False) -> "PlayerSession":
        """Create a new player session with generated token."""
        token = secrets.token_urlsafe(16)
        return cls(name=name, token=token, is_host=is_host)

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now()

    def disconnect(self) -> None:
        """Mark player as disconnected."""
        self.connected = False
        self.ws = None

    def reconnect(self, ws: web.WebSocketResponse) -> None:
        """Reconnect player with new WebSocket."""
        self.connected = True
        self.ws = ws
        self.update_heartbeat()
```

#### 2. `game/state.py` - GameState Session Management

```python
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from .player import PlayerSession
from ..const import (
    ERR_NAME_TAKEN,
    ERR_INVALID_TOKEN,
    ERR_SESSION_EXPIRED,
    RECONNECT_WINDOW_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class GameState:
    def __init__(self):
        # Existing attributes...
        self.players: Dict[str, PlayerSession] = {}
        self.sessions: Dict[str, PlayerSession] = {}  # token -> PlayerSession
        # ... other initialization

    def add_player(
        self,
        name: str,
        is_host: bool = False,
        ws: Optional[web.WebSocketResponse] = None
    ) -> Tuple[bool, Optional[str], Optional[PlayerSession]]:
        """
        Add a new player or replace existing session.

        Returns: (success, error_code, player_session)
        """
        # Check for duplicate name (FR18)
        if name in self.players:
            # Replace old session
            old_session = self.players[name]
            _LOGGER.info(
                "Replacing session for %s (old token: %s)",
                name,
                old_session.token[:8]
            )
            # Clean up old session
            del self.sessions[old_session.token]
            if old_session.ws and not old_session.ws.closed:
                asyncio.create_task(
                    old_session.ws.close(
                        code=4001,
                        message="Session replaced by new connection"
                    )
                )

        # Create new session
        session = PlayerSession.create_new(name, is_host)
        session.ws = ws

        # Store in both dictionaries
        self.players[name] = session
        self.sessions[session.token] = session

        _LOGGER.info(
            "Player added: %s (token: %s, total: %d)",
            name,
            session.token[:8],
            len(self.players)
        )

        return True, None, session

    def get_session_by_token(self, token: str) -> Optional[PlayerSession]:
        """Retrieve player session by token."""
        return self.sessions.get(token)

    def restore_session(
        self,
        token: str,
        ws: web.WebSocketResponse
    ) -> Tuple[bool, Optional[str], Optional[PlayerSession]]:
        """
        Restore a player session using token.

        Returns: (success, error_code, player_session)
        """
        session = self.get_session_by_token(token)

        if not session:
            return False, ERR_INVALID_TOKEN, None

        # Check if session is still valid (within reconnection window)
        if not self._is_session_valid(session):
            # Clean up expired session
            del self.sessions[token]
            if session.name in self.players:
                del self.players[session.name]
            return False, ERR_SESSION_EXPIRED, None

        # Reconnect session
        session.reconnect(ws)

        _LOGGER.info(
            "Session restored: %s (token: %s)",
            session.name,
            token[:8]
        )

        return True, None, session

    def _is_session_valid(self, session: PlayerSession) -> bool:
        """
        Check if session is still valid based on time elapsed.

        Uses 5-minute reconnection window per NFR12.
        """
        if session.connected:
            return True

        time_since_disconnect = datetime.now() - session.last_heartbeat
        max_window = timedelta(seconds=RECONNECT_WINDOW_SECONDS)

        return time_since_disconnect < max_window
```

#### 3. `server/websocket.py` - WebSocket Handler Updates

```python
from aiohttp import web
import logging
from ..const import (
    ERR_INVALID_TOKEN,
    ERR_SESSION_EXPIRED,
    ERR_NAME_TAKEN,
    ERR_NAME_INVALID,
    ERR_GAME_ALREADY_STARTED,
    ERR_GAME_FULL,
    ERROR_MESSAGES,
)
from ..game.state import GamePhase

_LOGGER = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, game_state):
        self.game_state = game_state

    async def handle_connection(
        self,
        request: web.Request
    ) -> web.WebSocketResponse:
        """Handle new WebSocket connection with session management."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Check for existing session token
        token = request.rel_url.query.get('token')

        if token:
            # Attempt session restoration
            success, error, session = self.game_state.restore_session(token, ws)

            if success:
                # Send restored session state
                await ws.send_json({
                    "type": "session_restored",
                    "name": session.name,
                    "token": session.token,
                    "is_host": session.is_host
                })

                # Send current game state
                state = self.game_state.get_state(for_player=session.name)
                await ws.send_json({"type": "state", **state})

                # Broadcast to others that player reconnected
                await self.broadcast_state()

                _LOGGER.info("Player reconnected: %s", session.name)
            else:
                # Session invalid or expired
                await ws.send_json({
                    "type": "error",
                    "code": error,
                    "message": ERROR_MESSAGES[error]
                })
                await ws.close()
                return ws

        # Continue with normal WebSocket message loop
        await self._message_loop(ws)

        return ws

    async def _handle_join(
        self,
        ws: web.WebSocketResponse,
        data: dict
    ) -> None:
        """Handle player join message."""
        name = data.get("name", "").strip()
        is_host = data.get("is_host", False)

        # Validate name
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

        # Check player count
        if len(self.game_state.players) >= 10:
            await ws.send_json({
                "type": "error",
                "code": ERR_GAME_FULL,
                "message": ERROR_MESSAGES[ERR_GAME_FULL]
            })
            return

        # Add player (handles duplicate name replacement per FR18)
        success, error, session = self.game_state.add_player(name, is_host, ws)

        if success:
            # Send join confirmation with session token
            await ws.send_json({
                "type": "join_confirmed",
                "name": session.name,
                "token": session.token,
                "is_host": session.is_host,
                "redirect_url": f"/api/spyster/player?token={session.token}"
            })

            # Send initial state
            state = self.game_state.get_state(for_player=session.name)
            await ws.send_json({"type": "state", **state})

            # Broadcast to all players
            await self.broadcast_state()

            _LOGGER.info(
                "Player joined: %s (total: %d)",
                name,
                len(self.game_state.players)
            )
        else:
            await ws.send_json({
                "type": "error",
                "code": error,
                "message": ERROR_MESSAGES[error]
            })

    async def broadcast_state(self) -> None:
        """Broadcast personalized state to all connected players."""
        for player_name, session in self.game_state.players.items():
            if session.connected and session.ws:
                try:
                    state = self.game_state.get_state(for_player=player_name)
                    await session.ws.send_json({"type": "state", **state})
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to send state to %s: %s",
                        player_name,
                        err
                    )
```

#### 4. `const.py` - Constants Addition

```python
# Session Management
RECONNECT_WINDOW_SECONDS = 300  # 5 minutes per NFR12

# Error Codes
ERR_INVALID_TOKEN = "INVALID_TOKEN"
ERR_SESSION_EXPIRED = "SESSION_EXPIRED"
ERR_NAME_INVALID = "NAME_INVALID"
ERR_GAME_ALREADY_STARTED = "GAME_ALREADY_STARTED"
ERR_GAME_FULL = "GAME_FULL"

# Error Messages
ERROR_MESSAGES = {
    # ... existing messages
    ERR_INVALID_TOKEN: "Invalid session. Please join again.",
    ERR_SESSION_EXPIRED: "Your session has expired. Please join again.",
    ERR_NAME_INVALID: "Please enter a name between 1-20 characters.",
    ERR_GAME_ALREADY_STARTED: "Game has already started. You cannot join now.",
    ERR_GAME_FULL: "Sorry, this game is full (max 10 players).",
}
```

#### 5. `www/js/player.js` - Client-Side Session Handling

```javascript
class PlayerClient {
    constructor() {
        this.ws = null;
        this.token = null;
        this.playerName = null;
        this.isHost = false;
    }

    init() {
        // Check for existing session token in URL
        const urlParams = new URLSearchParams(window.location.search);
        this.token = urlParams.get('token');

        if (this.token) {
            // Attempt reconnection with token
            this.connectWithToken(this.token);
        } else {
            // Show join screen
            this.showJoinScreen();
        }
    }

    connectWithToken(token) {
        const wsUrl = `ws://${window.location.host}/api/spyster/ws?token=${token}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected with token');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showJoinScreen();
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed, attempting reconnect...');
            setTimeout(() => this.connectWithToken(token), 2000);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'session_restored':
                this.playerName = data.name;
                this.token = data.token;
                this.isHost = data.is_host;
                console.log(`Session restored: ${this.playerName}`);
                this.hideJoinScreen();
                break;

            case 'join_confirmed':
                this.playerName = data.name;
                this.token = data.token;
                this.isHost = data.is_host;
                // Update URL with token
                window.history.replaceState({}, '', data.redirect_url);
                console.log(`Joined as: ${this.playerName}`);
                this.hideJoinScreen();
                break;

            case 'error':
                if (data.code === 'INVALID_TOKEN' || data.code === 'SESSION_EXPIRED') {
                    // Clear token and show join screen
                    this.token = null;
                    window.history.replaceState({}, '', '/api/spyster/player');
                    this.showJoinScreen();
                }
                this.showError(data.message);
                break;

            case 'state':
                this.updateGameState(data);
                break;
        }
    }

    joinGame(name, isHost = false) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            // Connect without token
            const wsUrl = `ws://${window.location.host}/api/spyster/ws`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.ws.send(JSON.stringify({
                    type: 'join',
                    name: name,
                    is_host: isHost
                }));
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
        } else {
            // Already connected, send join
            this.ws.send(JSON.stringify({
                type: 'join',
                name: name,
                is_host: isHost
            }));
        }
    }

    showJoinScreen() {
        document.getElementById('join-screen').style.display = 'block';
        document.getElementById('game-screen').style.display = 'none';
    }

    hideJoinScreen() {
        document.getElementById('join-screen').style.display = 'none';
        document.getElementById('game-screen').style.display = 'block';
    }

    showError(message) {
        const errorEl = document.getElementById('error-message');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }
}

// Initialize on page load
const playerClient = new PlayerClient();
document.addEventListener('DOMContentLoaded', () => playerClient.init());
```

## Technical Notes

### Security Considerations
- Use `secrets.token_urlsafe()` for cryptographically secure token generation
- Never expose internal session IDs or player indices
- Validate all tokens on reconnection
- Clean up expired sessions to prevent memory leaks

### Architecture Alignment
- **ARCH-9, ARCH-10**: Timer system will handle disconnect grace periods (Story 2.4)
- **ARCH-12**: All WebSocket messages follow `{"type": "...", ...payload}` format
- **ARCH-13**: Error responses include both `code` and `message`
- **ARCH-14**: State broadcast after every session change

### NFR Compliance
- **NFR12**: 5-minute reconnection window enforced via `_is_session_valid()`
- **NFR13**: Game state preserved during player disconnect/reconnect
- **NFR8**: Session tokens provide isolation between game sessions

### Testing Strategy

#### Unit Tests (`tests/test_player.py`)
```python
def test_session_creation():
    """Test that new sessions generate unique tokens."""
    session1 = PlayerSession.create_new("Alice")
    session2 = PlayerSession.create_new("Bob")
    assert session1.token != session2.token
    assert len(session1.token) > 16  # Sufficient entropy

def test_duplicate_name_replacement(game_state):
    """Test FR18: Duplicate session prevention."""
    # Add first player
    success1, _, session1 = game_state.add_player("Alice")
    assert success1
    token1 = session1.token

    # Add player with same name
    success2, _, session2 = game_state.add_player("Alice")
    assert success2
    token2 = session2.token

    # Tokens should be different
    assert token1 != token2

    # Only one session should exist
    assert len(game_state.players) == 1
    assert len(game_state.sessions) == 1

    # Old token should be invalid
    assert game_state.get_session_by_token(token1) is None

    # New token should be valid
    assert game_state.get_session_by_token(token2) == session2

def test_session_restoration(game_state):
    """Test successful session restoration."""
    # Create session
    _, _, session = game_state.add_player("Alice")
    token = session.token

    # Simulate disconnect
    session.disconnect()

    # Restore session
    mock_ws = MockWebSocket()
    success, error, restored = game_state.restore_session(token, mock_ws)

    assert success
    assert error is None
    assert restored.name == "Alice"
    assert restored.connected is True
    assert restored.ws == mock_ws

def test_session_expiry():
    """Test session expiry after reconnection window."""
    session = PlayerSession.create_new("Alice")
    session.disconnect()

    # Simulate time passing
    session.last_heartbeat = datetime.now() - timedelta(minutes=6)

    # Session should be invalid
    game_state = GameState()
    game_state.sessions[session.token] = session

    mock_ws = MockWebSocket()
    success, error, _ = game_state.restore_session(session.token, mock_ws)

    assert not success
    assert error == ERR_SESSION_EXPIRED
```

#### Integration Tests
```python
async def test_join_and_reconnect_flow(aiohttp_client):
    """Test complete join → disconnect → reconnect flow."""
    app = create_app()
    client = await aiohttp_client(app)

    # Join game
    ws = await client.ws_connect('/api/spyster/ws')
    await ws.send_json({"type": "join", "name": "Alice"})

    msg = await ws.receive_json()
    assert msg['type'] == 'join_confirmed'
    token = msg['token']

    # Close connection
    await ws.close()

    # Reconnect with token
    ws2 = await client.ws_connect(f'/api/spyster/ws?token={token}')

    msg2 = await ws2.receive_json()
    assert msg2['type'] == 'session_restored'
    assert msg2['name'] == 'Alice'
```

## Definition of Done

- [ ] `PlayerSession.create_new()` generates unique tokens using `secrets.token_urlsafe(16)`
- [ ] `GameState.add_player()` replaces existing session when duplicate name detected (FR18)
- [ ] `GameState.restore_session()` validates tokens and reconnects players
- [ ] Session expiry enforced after 5-minute window (NFR12)
- [ ] WebSocket handler includes token in join confirmation response
- [ ] Client JavaScript stores token in URL for automatic reconnection
- [ ] All unit tests passing
- [ ] Integration test confirms join → disconnect → reconnect flow
- [ ] No memory leaks from abandoned sessions (cleanup verified)
- [ ] Logging includes session token prefix (first 8 chars) for debugging

## Dependencies

**Blocked By:**
- Story 2.1: WebSocket Connection Handler (requires base WebSocket infrastructure)

**Blocks:**
- Story 2.4: Disconnect Detection (requires session tracking)
- Story 2.5: Player Reconnection (extends session restoration)

## Related Requirements

**Functional Requirements:**
- FR18: System prevents duplicate sessions for same player name (removes old session)
- FR14: Player can automatically reconnect if disconnected (within 5 minutes)

**Non-Functional Requirements:**
- NFR12: Reconnection Window - Player can reconnect within 5 minutes of disconnect
- NFR13: State Preservation - Game state survives individual player disconnects
- NFR8: Session Isolation - Players in one game session cannot access another session's data

**Architecture Decisions:**
- Session tokens: URL-based tokens, not cookies (mobile browser compatibility)
- Per-player state filtering via `get_state(for_player=player_name)`
- Named timer dictionary pattern for reconnection windows (Story 2.4)

## Notes for Developers

### Common Pitfalls
1. **Token Length**: Don't reduce token length below 16 bytes - security requirement
2. **URL Updates**: Always update browser URL with token after join confirmation
3. **WebSocket Cleanup**: Properly close old WebSocket when replacing duplicate session
4. **Session Cleanup**: Remove expired sessions from both `players` and `sessions` dicts

### Future Enhancements
- Story 2.5 will add automatic reconnection with exponential backoff
- Story 2.4 will implement heartbeat system for disconnect detection
- Consider adding session activity logging for debugging production issues

### Performance Considerations
- Token validation is O(1) lookup in `sessions` dictionary
- Session expiry check is lazy (only on reconnection attempt)
- Consider periodic cleanup task if sessions accumulate (future enhancement)
