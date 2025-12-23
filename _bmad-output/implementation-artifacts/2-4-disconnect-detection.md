---
story_id: '2.4'
epic_id: '2'
title: 'Disconnect Detection'
status: 'ready-for-dev'
created_date: '2025-12-23'
ready_date: '2025-12-23'
implementation_order: 4
dependencies: ['2.1', '2.2', '2.3']
priority: 'high'
estimated_effort: 'medium'
---

# Story 2.4: Disconnect Detection

## User Story

As a **host**,
I want **to see when players disconnect**,
So that **I know who is still active in the game**.

## Story Context

### Epic Context
Part of Epic 2: Player Join & Connection - Players can join via QR scan and the system handles connections reliably with reconnection support.

### Business Value
- Enables host to manage lobby effectively by knowing which players are active
- Provides visual feedback for connection issues
- Creates foundation for reconnection flow (Story 2.5)
- Meets NFR11: Player disconnect detected within 30 seconds

### User Flow
1. Player is connected and active in the game
2. Player's device loses connection (network issue, app backgrounded, etc.)
3. WebSocket connection closes OR heartbeat stops
4. System starts 30-second disconnect grace timer
5. If player doesn't reconnect within 30 seconds, status changes to "disconnected"
6. Host display shows yellow indicator next to disconnected player's name
7. All connected clients see updated player status

## Acceptance Criteria

### AC1: Heartbeat-Based Disconnect Detection
**Given** a player is connected
**When** no heartbeat is received for 30 seconds
**Then** the player is marked as "disconnected" (not removed)
**And** the host display shows a yellow indicator next to their name

**Implementation Notes:**
- Use named timer pattern: `disconnect_grace:{player_name}`
- Timer duration defined in `const.py` as `DISCONNECT_GRACE_TIMEOUT = 30`
- Set `PlayerSession.connected = False` when timer fires
- Broadcast state update to all clients showing new player status

### AC2: WebSocket Close Event Detection
**Given** a WebSocket connection closes
**When** the close event is detected
**Then** a disconnect grace timer starts (30 seconds to mark disconnected)

**Implementation Notes:**
- Handle WebSocket `on_close` event in `websocket.py`
- Log disconnect event with player name and reason
- Start named timer `disconnect_grace:{player_name}` with 30s duration
- Player remains in game with `connected = True` during grace period
- If player reconnects during grace period, cancel the timer

### AC3: Disconnect Grace Timer Completion
**Given** the disconnect grace timer fires
**When** the player hasn't reconnected
**Then** their status changes to "disconnected"
**And** all clients receive updated state via broadcast

**Implementation Notes:**
- Timer callback updates `PlayerSession.connected = False`
- Broadcast personalized state to all players (per-player filtering)
- Host display must differentiate connected vs disconnected players
- Log state change: `_LOGGER.info("Player disconnected: %s", player_name)`
- DO NOT remove player from game (removal handled in Story 2.6)

## Technical Implementation Details

### Files to Modify

#### 1. `custom_components/spyster/const.py`
Add disconnect detection constants:

```python
# Disconnect Detection Timers
DISCONNECT_GRACE_TIMEOUT = 30  # seconds - NFR11 requirement
HEARTBEAT_INTERVAL = 10  # seconds - client sends heartbeat every 10s
```

#### 2. `custom_components/spyster/game/player.py`
Update `PlayerSession` class:

```python
from dataclasses import dataclass
from aiohttp import web
import asyncio

@dataclass
class PlayerSession:
    name: str
    ws: web.WebSocketResponse
    session_token: str
    is_host: bool = False
    connected: bool = True  # New field - track connection status
    last_heartbeat: float = 0.0  # New field - timestamp of last heartbeat
    disconnect_timer: asyncio.Task | None = None  # New field - grace timer reference
```

#### 3. `custom_components/spyster/server/websocket.py`
Implement disconnect detection logic:

```python
import time
import asyncio
import aiohttp
from aiohttp import web
from ..const import DISCONNECT_GRACE_TIMEOUT, HEARTBEAT_INTERVAL

class WebSocketHandler:
    def __init__(self, hass, game_state):
        self.hass = hass
        self.game_state = game_state

    async def handle_connection(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        player_session = None

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        await self._handle_message(ws, data, player_session)
                    except Exception as err:
                        _LOGGER.warning("Failed to handle message: %s", err)
                        await ws.send_json({
                            "type": "error",
                            "code": "ERR_INVALID_MESSAGE",
                            "message": "Invalid message format"
                        })
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.warning("WebSocket error: %s", ws.exception())

        except Exception as err:
            _LOGGER.warning("WebSocket connection error: %s", err)
        finally:
            # Connection closed - start disconnect grace timer
            if player_session:
                await self._on_disconnect(player_session)

        return ws

    async def _handle_message(self, ws, data, player_session):
        msg_type = data.get("type")

        if msg_type == "heartbeat":
            await self._handle_heartbeat(player_session)
        # ... other message handlers

    async def _handle_heartbeat(self, player_session):
        """Update player's last heartbeat timestamp and cancel disconnect timer."""
        if not player_session:
            return

        player_session.last_heartbeat = time.time()

        # Cancel existing disconnect timer if reconnecting
        if player_session.disconnect_timer and not player_session.disconnect_timer.done():
            player_session.disconnect_timer.cancel()
            player_session.disconnect_timer = None

        # If player was marked disconnected, restore to connected
        if not player_session.connected:
            player_session.connected = True
            _LOGGER.info("Player reconnected: %s", player_session.name)
            await self.broadcast_state()

    async def _on_disconnect(self, player_session):
        """Handle WebSocket close event - start disconnect grace timer."""
        if not player_session:
            return

        _LOGGER.info("WebSocket closed for player: %s, starting grace timer", player_session.name)

        # Start 30-second grace timer using GameState timer dictionary (ARCH-9)
        timer_name = f"disconnect_grace:{player_session.name}"
        player_session.disconnect_timer = asyncio.create_task(
            self._disconnect_grace_timer(player_session, timer_name)
        )
        self.game_state._timers[timer_name] = player_session.disconnect_timer

    async def _disconnect_grace_timer(self, player_session, timer_name):
        """Wait for grace period, then mark player as disconnected."""
        try:
            await asyncio.sleep(DISCONNECT_GRACE_TIMEOUT)

            # Grace period expired without reconnection
            player_session.connected = False
            _LOGGER.info("Player disconnected: %s (grace period expired)", player_session.name)

            # Clean up timer reference from GameState (ARCH-9)
            if timer_name in self.game_state._timers:
                del self.game_state._timers[timer_name]
            player_session.disconnect_timer = None

            # Broadcast updated state to all clients
            await self.broadcast_state()

        except asyncio.CancelledError:
            # Timer cancelled (player reconnected)
            _LOGGER.debug("Disconnect timer cancelled for %s (reconnected)", player_session.name)
            if timer_name in self.game_state._timers:
                del self.game_state._timers[timer_name]

    async def broadcast_state(self):
        """Broadcast personalized state to all players."""
        for player_name, player in self.game_state.players.items():
            if player.ws and not player.ws.closed:
                try:
                    state = self.game_state.get_state(for_player=player_name)
                    await player.ws.send_json({"type": "state", **state})
                except Exception as err:
                    _LOGGER.warning("Failed to send state to %s: %s", player_name, err)
```

#### 4. `custom_components/spyster/game/state.py`
Add timer dictionary and update `get_state()` to include player connection status:

```python
import asyncio
from typing import Callable

class GameState:
    def __init__(self):
        self.players: dict[str, PlayerSession] = {}
        self.phase = GamePhase.LOBBY
        self._timers: dict[str, asyncio.Task] = {}  # Named timer dictionary (ARCH-9)
        # ... other fields

    def cancel_timer(self, name: str) -> None:
        """Cancel a specific timer by name (ARCH-10)."""
        if name in self._timers and not self._timers[name].done():
            self._timers[name].cancel()
            del self._timers[name]

    def cancel_all_timers(self) -> None:
        """Cancel all active timers (game end cleanup)."""
        for task in self._timers.values():
            if not task.done():
                task.cancel()
        self._timers.clear()
```

Update `get_state()` to include player connection status:

```python
def get_state(self, for_player: str | None = None) -> dict:
    """
    Get game state, filtered for specific player if provided.

    Returns:
        - Public data: phase, player_count, players (with connection status), scores, timer
        - Private data: role, location (only for requesting player)
    """
    state = {
        "phase": self.phase.value,
        "player_count": len(self.players),
        "players": [
            {
                "name": p.name,
                "connected": p.connected,  # Include connection status
                "is_host": p.is_host
            }
            for p in self.players.values()
        ],
        "current_round": self.current_round,
        "total_rounds": self.config.get("rounds", 5)
    }

    # Add phase-specific data
    # ... existing phase-specific logic

    return state
```

#### 5. `custom_components/spyster/www/js/host.js`
Update host display to show connection status:

```javascript
function renderPlayerList(players) {
    const playerListEl = document.getElementById('player-list');
    playerListEl.innerHTML = '';

    players.forEach(player => {
        const playerCard = document.createElement('div');
        playerCard.className = 'player-card';

        // Add connection status indicator
        const statusIndicator = document.createElement('span');
        statusIndicator.className = player.connected ? 'status-connected' : 'status-disconnected';
        statusIndicator.textContent = player.connected ? '●' : '●';
        statusIndicator.setAttribute('aria-label', player.connected ? 'Connected' : 'Disconnected');

        const nameEl = document.createElement('span');
        nameEl.textContent = player.name;

        playerCard.appendChild(statusIndicator);
        playerCard.appendChild(nameEl);
        playerListEl.appendChild(playerCard);
    });
}

// WebSocket message handler
function handleStateMessage(state) {
    if (state.players) {
        renderPlayerList(state.players);
    }
    // ... other state rendering
}
```

#### 6. `custom_components/spyster/www/css/styles.css`
Add connection status indicator styles:

```css
.player-card {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: var(--surface-bg);
    border-radius: 8px;
    margin-bottom: 8px;
}

.status-connected {
    color: #00ff88; /* Green - connected */
    font-size: 16px;
}

.status-disconnected {
    color: #ffd700; /* Yellow - disconnected (not error red) */
    font-size: 16px;
}
```

#### 7. `custom_components/spyster/www/js/player.js`
Implement client-side heartbeat:

```javascript
const HEARTBEAT_INTERVAL = 10000; // 10 seconds (matches const.py)

class SpysterClient {
    constructor() {
        this.ws = null;
        this.heartbeatTimer = null;
    }

    connect(sessionToken) {
        const wsUrl = `ws://${window.location.host}/api/spyster/ws?token=${sessionToken}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.startHeartbeat();
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.stopHeartbeat();
            // Attempt reconnection (handled in Story 2.5)
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    startHeartbeat() {
        // Send heartbeat every 10 seconds
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, HEARTBEAT_INTERVAL);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
}
```

### Testing Requirements

#### Unit Tests (`tests/test_websocket.py`)

```python
import pytest
import asyncio
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.server.websocket import WebSocketHandler
from custom_components.spyster.const import DISCONNECT_GRACE_TIMEOUT

@pytest.mark.asyncio
async def test_disconnect_grace_timer_marks_player_disconnected(mock_game_state):
    """Test that grace timer marks player as disconnected after timeout."""
    handler = WebSocketHandler(None, mock_game_state)
    player = PlayerSession(name="TestPlayer", ws=None, session_token="test123")
    player.connected = True

    # Start disconnect timer
    await handler._on_disconnect(player)

    # Wait for grace period to expire
    await asyncio.sleep(DISCONNECT_GRACE_TIMEOUT + 1)

    # Player should now be marked disconnected
    assert player.connected is False

@pytest.mark.asyncio
async def test_heartbeat_cancels_disconnect_timer(mock_game_state):
    """Test that heartbeat during grace period prevents disconnect."""
    handler = WebSocketHandler(None, mock_game_state)
    player = PlayerSession(name="TestPlayer", ws=None, session_token="test123")

    # Start disconnect timer
    await handler._on_disconnect(player)

    # Send heartbeat before grace period expires
    await asyncio.sleep(5)
    await handler._handle_heartbeat(player)

    # Wait for what would have been grace period
    await asyncio.sleep(DISCONNECT_GRACE_TIMEOUT + 1)

    # Player should still be connected (timer was cancelled)
    assert player.connected is True

@pytest.mark.asyncio
async def test_broadcast_state_includes_connection_status(mock_game_state):
    """Test that state broadcast includes player connection status."""
    state = mock_game_state.get_state()

    assert "players" in state
    assert len(state["players"]) > 0
    assert "connected" in state["players"][0]
```

#### Integration Tests

**Test Scenario 1: Player Disconnect Detection**
1. Player joins game successfully
2. Simulate WebSocket close event
3. Wait 30 seconds
4. Verify player status changes to "disconnected"
5. Verify host display shows yellow indicator
6. Verify all clients receive updated state

**Test Scenario 2: Heartbeat During Grace Period**
1. Player joins game
2. Simulate WebSocket close
3. Send heartbeat after 10 seconds (before timeout)
4. Verify player remains connected
5. Verify disconnect timer is cancelled

**Test Scenario 3: Multiple Concurrent Disconnects**
1. Start game with 5 players
2. Simulate 3 players disconnecting simultaneously
3. Verify 3 independent grace timers start
4. Verify each player marked disconnected after 30s
5. Verify state broadcasts correctly to remaining 2 connected players

### Error Handling

**Error Scenarios:**

1. **WebSocket close during critical phase**
   - Grace timer runs regardless of game phase
   - Player can reconnect during any phase (Story 2.5)

2. **Multiple disconnect events for same player**
   - Cancel existing timer before starting new one
   - Prevent duplicate timers with same name

3. **Broadcast fails to disconnected player**
   - Catch send errors gracefully
   - Log warning, continue broadcasting to other players

4. **Timer cleanup on game end**
   - Cancel all disconnect timers when game ends
   - Prevent dangling async tasks

### Performance Considerations

**Heartbeat Overhead:**
- 10-second interval = 6 messages/minute/player
- 10 players = 60 heartbeat messages/minute
- Minimal JSON payload: `{"type": "heartbeat"}` (~20 bytes)
- Total bandwidth: ~1.2 KB/minute (negligible)

**Timer Management:**
- Named timer pattern prevents memory leaks
- Timers automatically cleaned up on completion or cancellation
- Maximum concurrent timers: 10 (one per player max)

**State Broadcast Efficiency:**
- Only broadcast when connection status changes
- Per-player filtering already implemented (no additional overhead)

## Definition of Done

### Functional Requirements
- [ ] AC1: Heartbeat-based disconnect detection works within 30 seconds
- [ ] AC2: WebSocket close triggers disconnect grace timer
- [ ] AC3: Grace timer completion marks player disconnected and broadcasts state
- [ ] Host display shows yellow indicator for disconnected players
- [ ] Connected players show green indicator
- [ ] Client sends heartbeat every 10 seconds

### Technical Requirements
- [ ] Constants defined in `const.py` (DISCONNECT_GRACE_TIMEOUT, HEARTBEAT_INTERVAL)
- [ ] `PlayerSession` updated with connection status fields
- [ ] WebSocket handler implements heartbeat and disconnect detection
- [ ] Named timer pattern used for disconnect grace timers
- [ ] State broadcast includes player connection status
- [ ] Host UI renders connection status indicators
- [ ] Player client sends periodic heartbeats

### Quality Requirements
- [ ] All unit tests pass
- [ ] Integration tests cover all acceptance criteria
- [ ] Error handling covers all edge cases
- [ ] Logging follows project patterns (context included)
- [ ] Code follows naming conventions (snake_case Python, camelCase JS)
- [ ] Phase guards respected (disconnect detection works in any phase)
- [ ] No memory leaks from timer management

### Documentation Requirements
- [ ] Code comments explain timer lifecycle
- [ ] Logging messages are descriptive with context
- [ ] Error codes documented in `const.py`

## Dependencies & Integration

### Prerequisites
- Story 2.1: WebSocket Connection Handler (provides connection infrastructure)
- Story 2.2: Player Join Flow (provides player sessions)
- Story 2.3: Player Session Management (provides session token handling)

### Enables
- Story 2.5: Player Reconnection (uses disconnect status to trigger reconnection)
- Story 2.6: Host Lobby Management (uses disconnect status to enable "Remove" button)

### Architectural Alignment
- **Timer Architecture**: Uses named timer dictionary pattern from architecture
- **State Broadcast**: Follows per-player filtering pattern
- **Error Handling**: Uses error code constants from `const.py`
- **Logging**: Follows format pattern with context
- **WebSocket Protocol**: Adds `heartbeat` message type to protocol

## Notes for Developers

### Critical Implementation Points

1. **Timer Naming Pattern**
   - Use `f"disconnect_grace:{player_name}"` for unique timer names
   - Prevents conflicts if same player disconnects/reconnects multiple times

2. **Grace Period vs Removal**
   - Disconnect detection marks player as disconnected (Story 2.4)
   - Removal from game is separate action (Story 2.6)
   - Reconnection window is 5 minutes total (Story 2.5)

3. **Heartbeat Implementation**
   - Client-side: setInterval() for simplicity
   - Server-side: timestamp comparison for timeout detection
   - 10s client interval + 30s server timeout = 3 missed heartbeats before disconnect

4. **State Broadcast Efficiency**
   - Only broadcast when connection status actually changes
   - Don't broadcast on every heartbeat (no state change)

5. **Phase Independence**
   - Disconnect detection works the same in all phases
   - No special handling for LOBBY vs QUESTIONING vs VOTE
   - Simplifies implementation and testing

### Common Pitfalls to Avoid

❌ **Don't remove player immediately on disconnect**
   - Use grace period to allow quick reconnections
   - Removal is host action (Story 2.6)

❌ **Don't forget to cancel timers**
   - Always cancel existing timer before starting new one
   - Clean up timers on game end

❌ **Don't broadcast on every heartbeat**
   - Heartbeat is silent - no state change, no broadcast
   - Only broadcast when connection status flips

❌ **Don't use same state for all players**
   - Continue using per-player state filtering
   - Each player sees personalized payload

### Code Review Checklist

- [ ] Named timer pattern used correctly
- [ ] Timer cancellation on reconnect
- [ ] Timer cleanup on game end
- [ ] Heartbeat doesn't trigger broadcast
- [ ] Connection status included in state
- [ ] Host UI differentiates connected/disconnected
- [ ] Error handling for broadcast failures
- [ ] Logging includes player name context
- [ ] Constants used (no hardcoded timeouts)
- [ ] Phase guards not needed (works in all phases)

## Related Stories

- **Story 2.1**: WebSocket Connection Handler - Provides WebSocket infrastructure
- **Story 2.2**: Player Join Flow - Creates player sessions that need disconnect detection
- **Story 2.3**: Player Session Management - Manages sessions that track connection status
- **Story 2.5**: Player Reconnection - Uses disconnect status to enable auto-reconnect
- **Story 2.6**: Host Lobby Management - Uses disconnect status to enable player removal

## Architectural Context

### Phase State Machine Impact
- Disconnect detection works in ALL phases (LOBBY → END)
- No phase transitions triggered by disconnect
- Phase remains unchanged when player disconnects

### Timer Architecture Usage
```python
# Named timer dictionary in GameState (ARCH-9 requirement)
# In game/state.py:
class GameState:
    def __init__(self):
        self._timers: dict[str, asyncio.Task] = {}

# In websocket handler - access via game_state
timer_name = f"disconnect_grace:{player_name}"
self.game_state._timers[timer_name] = asyncio.create_task(...)

# Cancel timer on reconnect
if timer_name in self.game_state._timers:
    self.game_state._timers[timer_name].cancel()
    del self.game_state._timers[timer_name]
```

### Security Considerations
- Heartbeat message has no sensitive data
- Connection status is public information (visible to all)
- Session tokens still required for all other actions

### Performance Impact
- Negligible: ~20 bytes per heartbeat, 10s interval
- Timer overhead: Python asyncio is efficient for this use case
- State broadcast only on status change (not every heartbeat)

---

**Story Status**: Ready for Development
**Estimated Effort**: Medium (2-3 dev sessions)
**Risk Level**: Low (well-defined, proven pattern from Beatify)
