---
story_id: "2-5"
epic: "Epic 2: Player Join & Connection"
title: "Player Reconnection"
status: "ready-for-dev"
priority: "high"
estimated_complexity: "medium"
created: "2025-12-23"
project: "Spyster"
assigned_to: "dev"
---

# Story 2.5: Player Reconnection

## User Story

As a **player**,
I want **to automatically reconnect if my connection drops**,
So that **I don't lose my place in the game**.

## Business Context

Players may experience temporary connection drops due to network issues, phone screen locks, or browser backgrounding. Without automatic reconnection, these players would be forced to rejoin as new players, disrupting the game flow. This story implements a 5-minute reconnection window that preserves the player's session, role, and game state, ensuring a smooth experience even with unstable connections.

## Technical Context

### Architecture Alignment

**Phase State Machine:** Reconnection must work in ANY phase, restoring the player to the current game state regardless of whether they're in LOBBY, QUESTIONING, VOTE, or any other phase.

**Timer Architecture:** Uses the named timer pattern with two reconnection-related timers:
- `disconnect_grace:{player_name}` - 30 seconds before marking player as disconnected
- `reconnect_window:{player_name}` - 5 minutes before invalidating session token

**Security:** Session tokens are URL-based (stored in URL parameters), allowing automatic restoration when player reopens browser. Tokens must be cryptographically secure using `secrets.token_urlsafe()`.

**WebSocket Protocol:** Reconnection is transparent to the client - when WebSocket reconnects with valid token, server restores session and broadcasts updated state with player marked as "connected" again.

**Per-Player State Filtering:** Reconnection must preserve role privacy. The `get_state(for_player=player_name)` method ensures:
- Each player sees only THEIR role information
- Spy sees `location_list`, non-spy sees `location` and their specific role
- Network inspection cannot reveal other players' roles
- This applies during ALL phases, including reconnection

### Related Components

- **game/player.py:** `PlayerSession` class tracks `connected` state, `session_token`, and `disconnect_time`
- **game/state.py:** `GameState` manages player collection and reconnection window timers
- **server/websocket.py:** WebSocket handler detects reconnection via session token in handshake
- **const.py:** Constants for timer durations (`DISCONNECT_GRACE_SECONDS=30`, `RECONNECT_WINDOW_SECONDS=300`)

### Dependencies

- **Story 2.1 (WebSocket Connection Handler):** Must support session token in query parameters for reconnection
- **Story 2.3 (Player Session Management):** Must have `session_token` field and `players_by_token` dictionary implemented
- **Story 2.4 (Disconnect Detection):** Must have `connected` flag, `disconnect_time` field, and `disconnect_grace:{player_name}` timer implemented

**Critical Dependency Chain:**
1. Story 2.4 detects disconnect and starts `disconnect_grace:{player_name}` timer (30 seconds)
2. When disconnect_grace timer fires, it calls `mark_disconnected()` which sets `disconnect_time`
3. Story 2.5 (this story) uses `disconnect_time` to start `reconnect_window:{player_name}` timer (5 minutes)
4. Both timers can run simultaneously but have different purposes:
   - `disconnect_grace` determines WHEN to mark player as "disconnected" (visual indicator)
   - `reconnect_window` determines WHEN to permanently remove player from game

## Acceptance Criteria

### AC1: Automatic Reconnection Within Window

**Given** a player is marked "disconnected" (connection dropped but within 5-minute window)
**When** they reopen the browser with their session token (URL includes `?token=xxx`)
**Then** they are automatically restored to their session
**And** their status changes back to "connected"
**And** they see the current game state (correct phase, their role if assigned, timer state)
**And** all other players receive updated state showing player as connected

**Implementation Details:**
- WebSocket handler extracts `token` from query parameters on connection
- Looks up `PlayerSession` by token in `GameState.players_by_token`
- If found and `disconnect_time` is < 5 minutes ago, restore session
- Cancel `reconnect_window:{player_name}` timer
- Set `player.connected = True`, update `player.ws` to new WebSocket
- Call `broadcast_state()` to notify all clients

### AC2: Session Invalidation After 5 Minutes

**Given** a player has been disconnected for over 5 minutes
**When** they try to reconnect with their old session token
**Then** their session is invalid (session token no longer in `players_by_token`)
**And** they receive error `ERR_SESSION_EXPIRED` with message "Your session has expired. Please rejoin the game."
**And** they must rejoin as a new player (if game is still in LOBBY phase)

**Implementation Details:**
- `reconnect_window:{player_name}` timer fires after 5 minutes
- Timer callback removes player from `GameState.players` and `players_by_token`
- Broadcasts state update showing player removed
- If player tries to reconnect after removal, token lookup fails
- Send `{"type": "error", "code": "ERR_SESSION_EXPIRED", "message": "..."}`
- Client should redirect to join screen

### AC3: Reconnection During Active Round

**Given** a player reconnects during an active round (phase = QUESTIONING, VOTE, REVEAL, or SCORING)
**When** the session is restored
**Then** they see their role and current phase immediately
**And** if phase is VOTE, they see the voting UI (can still vote if timer hasn't expired)
**And** if phase is QUESTIONING, they see their role card and round timer
**And** game continues without interruption for other players

**Implementation Details:**
- `get_state(for_player=player_name)` returns personalized state including role
- If `phase == GamePhase.VOTE` and player hasn't voted, voting UI should be active
- If player already voted before disconnect, show "LOCKED" state
- WebSocket sends `{"type": "state", "phase": "VOTE", "role": {...}, "voted": false, ...}`
- Frontend detects reconnection and renders appropriate UI for current phase

### AC4: Multiple Reconnections

**Given** a player reconnects successfully
**When** they disconnect and reconnect again (multiple times within the 5-minute window)
**Then** each reconnection restores their session
**And** the 5-minute window is calculated from the FIRST disconnect time (not the most recent)
**And** connection status updates correctly each time
**And** the reconnection window timer remains active from the first disconnect

**Implementation Details:**
- `disconnect_time` is set ONLY on first disconnect, not updated on subsequent disconnects
- This prevents "session extension" by repeatedly disconnecting/reconnecting
- Reconnection does NOT cancel the `reconnect_window:{player_name}` timer - it keeps running from initial disconnect
- On reconnection, check if session is still valid (within 5 minutes of FIRST disconnect_time)
- Timer continues countdown regardless of reconnection status, fires after 5 minutes from first disconnect

### AC5: 5-Minute Absolute Limit (NFR12 Enforcement)

**Given** a player disconnects at time T
**When** 5 minutes elapses (T + 300 seconds)
**Then** the player is PERMANENTLY removed from the game
**And** their session token is invalidated (removed from `players_by_token`)
**And** this occurs regardless of whether they are currently connected or disconnected
**And** all other players receive updated state showing the player removed

**Implementation Details:**
- This enforces NFR12: "Support reconnection within 5-minute grace period"
- The timer ALWAYS fires at exactly 5 minutes from first disconnect
- Even if player reconnects at 4:59 and is currently playing, they are removed at 5:00
- This is an absolute session lifetime limit, not a "disconnected for 5 minutes" limit
- Frontend should warn players approaching this limit (future enhancement)

## Implementation Tasks

### Task 1: Session Token Validation in WebSocket Handler

**File:** `custom_components/spyster/server/websocket.py`

**Changes:**

```python
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections with session token support."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Extract session token from query parameters
    token = request.query.get("token")

    if token:
        # Attempt session restoration
        player = game_state.get_player_by_token(token)

        if player:
            # Check if session is still valid (within 5-minute window)
            if player.is_session_valid():
                # Restore session
                _LOGGER.info("Player reconnecting: %s (token: %s)", player.name, token[:8])

                # Update player session (timer keeps running from first disconnect)
                player.connected = True
                player.ws = ws

                # Send current game state
                state = game_state.get_state(for_player=player.name)
                await ws.send_json({"type": "state", **state})

                # Notify all clients that player is back
                await game_state.broadcast_state()

                # Continue with message loop
                await _message_loop(ws, player)
                return ws
            else:
                # Session expired
                await ws.send_json({
                    "type": "error",
                    "code": ERR_SESSION_EXPIRED,
                    "message": "Your session has expired. Please rejoin the game."
                })
                await ws.close()
                return ws

    # New connection (no token or invalid token) - continue with join flow
    await _message_loop(ws, None)
    return ws
```

### Task 2: Session Validation Logic in PlayerSession

**File:** `custom_components/spyster/game/player.py`

**Changes:**

```python
from datetime import datetime, timedelta
from const import RECONNECT_WINDOW_SECONDS

class PlayerSession:
    """Represents a player's session in the game."""

    def __init__(self, name: str, session_token: str, ws: web.WebSocketResponse):
        self.name = name
        self.session_token = session_token
        self.ws = ws
        self.connected = True
        self.disconnect_time: datetime | None = None
        self.role: str | None = None
        self.voted: bool = False
        self.vote_target: str | None = None
        self.vote_confidence: int = 1

    def mark_disconnected(self) -> None:
        """Mark player as disconnected and record timestamp."""
        if self.connected:
            self.connected = False
            self.disconnect_time = datetime.now()
            _LOGGER.info("Player marked disconnected: %s at %s", self.name, self.disconnect_time)

    def mark_reconnected(self) -> None:
        """Mark player as reconnected (does NOT reset disconnect_time or timer)."""
        self.connected = True
        # Note: disconnect_time is NOT reset - keeps original for session expiry validation
        # Note: reconnect_window timer is NOT cancelled - continues from first disconnect
        _LOGGER.info("Player reconnected: %s (disconnect_time preserved)", self.name)

    def is_session_valid(self) -> bool:
        """Check if session is still within reconnection window."""
        if self.disconnect_time is None:
            return True  # Never disconnected

        elapsed = datetime.now() - self.disconnect_time
        is_valid = elapsed.total_seconds() < RECONNECT_WINDOW_SECONDS

        _LOGGER.debug(
            "Session validation: %s disconnected for %.1fs (valid: %s)",
            self.name,
            elapsed.total_seconds(),
            is_valid
        )

        return is_valid
```

### Task 3: Token Lookup in GameState

**File:** `custom_components/spyster/game/state.py`

**Changes:**

```python
class GameState:
    """Manages game state and phase transitions."""

    def __init__(self):
        self.phase = GamePhase.LOBBY
        self.players: dict[str, PlayerSession] = {}
        self.players_by_token: dict[str, PlayerSession] = {}  # NEW
        self._timers: dict[str, asyncio.Task] = {}
        # ... other initialization

    def add_player(self, name: str, ws: web.WebSocketResponse) -> tuple[bool, str | None, str | None]:
        """
        Add a new player to the game.

        Returns: (success, error_code, session_token)
        """
        if name in self.players:
            return False, ERR_NAME_TAKEN, None

        if len(self.players) >= 10:
            return False, ERR_GAME_FULL, None

        # Generate session token
        session_token = secrets.token_urlsafe(16)

        # Create player session
        player = PlayerSession(name, session_token, ws)
        self.players[name] = player
        self.players_by_token[session_token] = player  # NEW

        _LOGGER.info("Player added: %s (token: %s, total: %d)", name, session_token[:8], len(self.players))

        return True, None, session_token

    def get_player_by_token(self, token: str) -> PlayerSession | None:
        """Look up player by session token."""
        return self.players_by_token.get(token)

    def remove_player(self, name: str) -> None:
        """Remove player from game (session expired or kicked)."""
        if name in self.players:
            player = self.players[name]

            # Remove from both dictionaries
            del self.players[name]
            if player.session_token in self.players_by_token:
                del self.players_by_token[player.session_token]

            # Cancel any active timers for this player
            self.cancel_timer(f"disconnect_grace:{name}")
            self.cancel_timer(f"reconnect_window:{name}")

            _LOGGER.info("Player removed: %s (total: %d)", name, len(self.players))
```

### Task 4: Reconnection Window Timer

**File:** `custom_components/spyster/game/state.py`

**Changes:**

```python
async def _on_player_disconnect(self, player_name: str) -> None:
    """
    Handle player disconnect after grace period expires.

    Called by disconnect_grace timer (30 seconds after connection drop) - from Story 2.4.
    Extended in Story 2.5 to start reconnection window timer.
    """
    if player_name not in self.players:
        return  # Player already removed

    player = self.players[player_name]

    if not player.connected:
        # Player still disconnected after grace period
        player.mark_disconnected()  # Sets disconnect_time and connected=False

        # Story 2.5 addition: Start 5-minute reconnection window
        self.start_timer(
            name=f"reconnect_window:{player_name}",
            duration=RECONNECT_WINDOW_SECONDS,
            callback=lambda: self._on_reconnect_window_expired(player_name)
        )

        _LOGGER.warning(
            "Player disconnected: %s (reconnection window: %d seconds)",
            player_name,
            RECONNECT_WINDOW_SECONDS
        )

        # Broadcast state update showing player as disconnected
        await self.broadcast_state()

async def _on_reconnect_window_expired(self, player_name: str) -> None:
    """
    Remove player after 5-minute reconnection window expires.

    Called by reconnect_window timer (fires regardless of reconnection status).
    """
    if player_name not in self.players:
        return  # Player already removed

    # Remove player regardless of connected status - 5 minutes elapsed from first disconnect
    _LOGGER.info(
        "Reconnection window expired: %s (removing from game after %d seconds)",
        player_name,
        RECONNECT_WINDOW_SECONDS
    )

    self.remove_player(player_name)

    # Broadcast state update
    await self.broadcast_state()
```

### Task 5: Constants Definition

**File:** `custom_components/spyster/const.py`

**Add:**

```python
# Reconnection timing
DISCONNECT_GRACE_SECONDS = 30  # Time before marking player as disconnected
RECONNECT_WINDOW_SECONDS = 300  # 5 minutes to reconnect

# Error codes
ERR_SESSION_EXPIRED = "SESSION_EXPIRED"

# Error messages
ERROR_MESSAGES = {
    # ... existing errors
    ERR_SESSION_EXPIRED: "Your session has expired. Please rejoin the game.",
}
```

### Task 6: Frontend Reconnection Handling

**File:** `custom_components/spyster/www/js/player.js`

**Changes:**

```javascript
class SpysterClient {
    constructor() {
        this.ws = null;
        this.sessionToken = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2 seconds

        // Extract session token from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.sessionToken = urlParams.get('token');
    }

    connect() {
        // Build WebSocket URL with session token if available
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsUrl = `${protocol}//${window.location.host}/api/spyster/ws`;

        if (this.sessionToken) {
            wsUrl += `?token=${this.sessionToken}`;
        }

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;

            // If we have a session token, wait for state update
            // Otherwise, show join screen
            if (!this.sessionToken) {
                this.showJoinScreen();
            }
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this.handleMessage(msg);
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting (attempt ${this.reconnectAttempts})...`);

            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
            this.showReconnectError();
        }
    }

    handleMessage(msg) {
        switch (msg.type) {
            case 'state':
                // Server restored our session - update UI with current state
                this.updateGameState(msg);
                break;

            case 'error':
                if (msg.code === 'SESSION_EXPIRED') {
                    // Session expired - clear token and show join screen
                    this.sessionToken = null;
                    window.history.replaceState({}, '', window.location.pathname);
                    this.showExpiredSessionMessage(msg.message);
                    this.showJoinScreen();
                } else {
                    this.showError(msg.message);
                }
                break;

            // ... other message handlers
        }
    }

    showExpiredSessionMessage(message) {
        // Show toast notification
        const toast = document.createElement('div');
        toast.className = 'toast toast-warning';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => toast.remove(), 5000);
    }
}

// Initialize on page load
const client = new SpysterClient();
client.connect();
```

### Task 7: URL Token Management on Join

**File:** `custom_components/spyster/www/js/player.js`

**Changes:**

```javascript
async joinGame(playerName) {
    const msg = {
        type: 'join',
        name: playerName
    };

    this.ws.send(JSON.stringify(msg));
}

handleMessage(msg) {
    switch (msg.type) {
        case 'join_success':
            // Server sends session token on successful join
            this.sessionToken = msg.session_token;

            // Update URL with session token (enables reconnection)
            const newUrl = `${window.location.pathname}?token=${this.sessionToken}`;
            window.history.replaceState({}, '', newUrl);

            console.log('Joined game successfully with token:', this.sessionToken.substring(0, 8));
            break;

        // ... other cases
    }
}
```

## Testing Checklist

### Unit Tests

**File:** `tests/test_player.py`

- [ ] `test_session_valid_when_never_disconnected()` - New session returns True
- [ ] `test_session_valid_within_window()` - Session valid at 4min 59sec
- [ ] `test_session_invalid_after_window()` - Session invalid at 5min 01sec
- [ ] `test_mark_disconnected_sets_timestamp()` - Disconnect time recorded
- [ ] `test_mark_connected_preserves_disconnect_time()` - Reconnection doesn't reset timer

**File:** `tests/test_state.py`

- [ ] `test_get_player_by_token_returns_player()` - Token lookup works
- [ ] `test_get_player_by_token_returns_none_for_invalid()` - Invalid token returns None
- [ ] `test_remove_player_clears_token()` - Removal cleans up both dictionaries
- [ ] `test_reconnect_window_timer_removes_player()` - Timer callback fires correctly

### Integration Tests

**File:** `tests/test_websocket.py`

- [ ] `test_reconnect_with_valid_token()` - Successful reconnection flow
- [ ] `test_reconnect_with_expired_token()` - Receives ERR_SESSION_EXPIRED
- [ ] `test_reconnect_preserves_window_timer()` - Timer continues after reconnection
- [ ] `test_reconnect_during_vote_phase()` - Phase-specific state restored
- [ ] `test_multiple_reconnections()` - Session window doesn't extend
- [ ] `test_absolute_5min_limit()` - Player removed at 5min mark even if reconnected

### Manual Testing Scenarios

- [ ] Disconnect phone during LOBBY, reconnect - should see lobby
- [ ] Disconnect during QUESTIONING, reconnect - should see role and timer
- [ ] Disconnect during VOTE (before voting), reconnect - can still vote
- [ ] Disconnect during VOTE (after voting), reconnect - see "LOCKED" state
- [ ] Wait 5 minutes disconnected, try to reconnect - should see "session expired" error
- [ ] Disconnect at 0:00, reconnect at 4:50, stay connected - should be removed at 5:00 (absolute limit)
- [ ] Lock phone screen, unlock - should auto-reconnect
- [ ] Switch apps, return to browser - should auto-reconnect
- [ ] Disconnect/reconnect 3 times rapidly - final disconnect time should be from first disconnect

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing scenarios verified
- [ ] Code follows architecture patterns (naming, phase guards, logging)
- [ ] Constants used from `const.py` (no hardcoded values)
- [ ] Logging includes context (player names, timestamps, token prefixes)
- [ ] Error handling graceful (no crashes on invalid tokens)
- [ ] WebSocket reconnection logic tested with network interruptions
- [ ] Session token properly removed from URL on expiration
- [ ] Documentation updated (if needed)

## Related Stories

- **Depends On:**
  - Story 2.1: WebSocket Connection Handler (connection infrastructure)
  - Story 2.3: Player Session Management (session tokens, PlayerSession class)
  - Story 2.4: Disconnect Detection (disconnect_time, connected flag)

- **Blocks:**
  - Story 3.4: Role Distribution (reconnection must preserve role privacy)
  - Story 5.3: Vote Submission (reconnection must preserve vote state)

## Notes for Developers

### Security Considerations

- Session tokens MUST use `secrets.token_urlsafe()` for cryptographic randomness
- Token length of 16 bytes provides 128 bits of entropy (2^128 possible tokens)
- Tokens should NEVER be logged in full - always use `token[:8]` for log messages
- No cookies - URL-based tokens work better on mobile browsers

### Performance Considerations

- `players_by_token` dictionary provides O(1) lookup by token
- Reconnection window timers are per-player, not global (allows independent timeouts)
- Timer cleanup is critical - cancel in `remove_player()` to prevent memory leaks
- Timers are NOT cancelled on reconnection - they run to completion from first disconnect

### Edge Cases

1. **Player disconnects at exactly 5 minutes:** Timer callback fires, session invalidated (player removed)
2. **Player reconnects at 4:59, disconnects again at 5:01:** Player removed at 5:00 mark from FIRST disconnect (timer keeps running)
3. **Player reconnected but timer expires:** Player removed from game even if currently connected (5-minute absolute limit from first disconnect)
4. **Two players share a name:** Impossible - name collision prevented at join time
5. **Host disconnects:** Different flow (PAUSED phase) - not handled in this story

### Future Enhancements

- Persistent session storage (survive server restart) - requires Redis/database
- Configurable reconnection window per game settings
- "Player is reconnecting..." UI indicator for other players
- Analytics: track reconnection success rate

## Verification Commands

```bash
# Run unit tests
pytest tests/test_player.py::test_session_valid -v
pytest tests/test_state.py::test_reconnect_window -v

# Run integration tests
pytest tests/test_websocket.py::test_reconnect -v

# Manual test with curl (simulate reconnection)
# 1. Join game and capture token from response
curl -X POST http://localhost:8123/api/spyster/join -d '{"name": "TestPlayer"}'

# 2. Reconnect with token
wscat -c "ws://localhost:8123/api/spyster/ws?token=CAPTURED_TOKEN"
```

## Success Metrics

- **Reconnection Success Rate:** >95% of reconnections within 5-minute window succeed
- **Session Cleanup:** 100% of expired sessions removed (no memory leaks)
- **User Experience:** Players report seamless reconnection (no noticeable disruption)
- **Error Handling:** 0 crashes from invalid/expired tokens

---

**Story Status:** ready-for-dev
**Created:** 2025-12-23
**Last Updated:** 2025-12-23
