# Story 2.6: Host Lobby Management

Status: ready-for-dev

## Story

As a **host**,
I want **to manage the lobby and remove inactive players**,
So that **I can start the game without waiting for ghosts**.

## Acceptance Criteria

1. **Given** a player has been "disconnected" for 60+ seconds
   **When** the host views the lobby
   **Then** a "Remove" button appears next to that player

2. **Given** the host taps "Remove" on a disconnected player
   **When** the action is confirmed
   **Then** the player is removed from the game
   **And** the lobby updates on all connected clients

3. **Given** the host tries to remove a connected player
   **When** they attempt the action
   **Then** the action is blocked (only disconnected players can be removed)

4. **Given** the host display shows the lobby
   **When** players join/leave/disconnect
   **Then** the player list updates in real-time with status indicators

## Tasks / Subtasks

- [ ] **Task 1: Add player removal admin action to WebSocket protocol** (AC: #2, #3)
  - [ ] Add `remove_player` admin action to WebSocket message handler
  - [ ] Validate that requester is host before processing removal
  - [ ] Check that target player is disconnected (not connected)
  - [ ] Return `ERR_NOT_HOST` if non-host tries to remove
  - [ ] Return `ERR_CANNOT_REMOVE_CONNECTED` if player is still connected

- [ ] **Task 2: Implement remove_player method in GameState** (AC: #2, #3)
  - [ ] Add `remove_player(player_name: str) -> tuple[bool, str | None]` method
  - [ ] Validate phase is LOBBY (can't remove during active game)
  - [ ] Check player exists and is disconnected for 60+ seconds
  - [ ] Cancel all timers associated with player (`disconnect_grace:{name}`, `reconnect_window:{name}`)
  - [ ] Remove player from `self.players` dict
  - [ ] Log removal event with context

- [ ] **Task 3: Add error constants for lobby management** (AC: #3)
  - [ ] Add `ERR_CANNOT_REMOVE_CONNECTED` to const.py
  - [ ] Add `ERR_PLAYER_NOT_FOUND` to const.py
  - [ ] Add user-friendly messages to ERROR_MESSAGES dict
  - [ ] Document error codes in const.py comments

- [ ] **Task 4: Add disconnection duration tracking to PlayerSession** (AC: #1)
  - [ ] Add `disconnected_at: float | None` field to PlayerSession
  - [ ] Set `disconnected_at = time.time()` when player marked disconnected
  - [ ] Add helper method `get_disconnect_duration() -> float | None`
  - [ ] Clear `disconnected_at` on reconnection

- [ ] **Task 5: Update host UI to show Remove button conditionally** (AC: #1, #4)
  - [ ] Modify `renderPlayers()` in host.js to check disconnect duration
  - [ ] Show "Remove" button only if `disconnect_duration >= 60`
  - [ ] Style Remove button with destructive appearance (red accent)
  - [ ] Add confirmation dialog when Remove is clicked
  - [ ] Send `{type: "admin", action: "remove_player", player_name: "..."}` on confirm

- [ ] **Task 6: Add real-time status indicators to host player list** (AC: #4)
  - [ ] Add CSS for connected state indicator (green dot)
  - [ ] Add CSS for disconnected state indicator (yellow/orange dot)
  - [ ] Update player card rendering to include status dot
  - [ ] Ensure status updates in real-time via state broadcast
  - [ ] Add ARIA labels for accessibility ("Player X - Connected/Disconnected")

- [ ] **Task 7: Broadcast state after player removal** (AC: #2, #4)
  - [ ] Call `broadcast_state()` after successful removal
  - [ ] Ensure all connected clients receive updated player list
  - [ ] Update player count in state payload
  - [ ] Handle case where removal drops below minimum players (< 4)

- [ ] **Task 8: Test lobby management edge cases** (AC: All)
  - [ ] Test removing non-existent player
  - [ ] Test removing player who just reconnected (< 60s disconnect)
  - [ ] Test removing player during non-LOBBY phase
  - [ ] Test multiple simultaneous removal requests
  - [ ] Test removal when player count is exactly 4
  - [ ] Test host can't remove themselves

## Dev Notes

### Architecture Patterns to Follow

**Admin Action Pattern:**
Following established admin action routing in WebSocket handler:
- Admin actions require `is_host=True` check
- Action handlers return `(success: bool, error_code: str | None)`
- All actions followed by `broadcast_state()` if successful

**Phase Guard Pattern:**
Player removal only allowed in LOBBY phase:
- Prevents disruption during active game rounds
- Ensures clean state management
- Consistent with other phase-restricted actions

**Timer Cleanup Pattern:**
When removing player, must cancel all associated timers:
- `disconnect_grace:{player_name}` - might still be running
- `reconnect_window:{player_name}` - might still be running
- Prevents orphaned tasks and memory leaks

### WebSocket Admin Action Message Format

**Client → Server (Remove Request):**
```json
{
  "type": "admin",
  "action": "remove_player",
  "player_name": "Alice"
}
```

**Server → Client (Success):**
```json
{
  "type": "state",
  "phase": "LOBBY",
  "players": [
    {"name": "Bob", "connected": true, "is_host": false},
    {"name": "Carol", "connected": true, "is_host": false}
  ],
  "player_count": 2
}
```

**Server → Client (Error - Player Connected):**
```json
{
  "type": "error",
  "code": "ERR_CANNOT_REMOVE_CONNECTED",
  "message": "Cannot remove a connected player. Wait for them to disconnect first."
}
```

**Server → Client (Error - Not Host):**
```json
{
  "type": "error",
  "code": "ERR_NOT_HOST",
  "message": "Only the host can remove players."
}
```

### PlayerSession Disconnect Duration Tracking

**Add to PlayerSession class:**
```python
from time import time

class PlayerSession:
    def __init__(self, name: str, ws: web.WebSocketResponse, is_host: bool = False):
        self.name = name
        self.ws = ws
        self.is_host = is_host
        self.connected = True
        self.disconnected_at: float | None = None  # NEW: Track when disconnected

    def mark_disconnected(self) -> None:
        """Mark player as disconnected and record timestamp."""
        self.connected = False
        self.disconnected_at = time()
        _LOGGER.info("Player marked disconnected: %s (at: %.2f)", self.name, self.disconnected_at)

    def mark_connected(self) -> None:
        """Mark player as connected and clear disconnect timestamp."""
        self.connected = True
        self.disconnected_at = None
        _LOGGER.info("Player marked connected: %s", self.name)

    def get_disconnect_duration(self) -> float | None:
        """Get seconds since disconnection, or None if connected."""
        if self.connected or self.disconnected_at is None:
            return None
        return time() - self.disconnected_at
```

### GameState remove_player Implementation Pattern

```python
def remove_player(self, player_name: str) -> tuple[bool, str | None]:
    """Remove a disconnected player from the lobby.

    Args:
        player_name: Name of player to remove

    Returns:
        (success, error_code) - error_code is None on success

    Validation:
    - Phase must be LOBBY
    - Player must exist
    - Player must be disconnected for 60+ seconds
    """
    from .const import ERR_INVALID_PHASE, ERR_PLAYER_NOT_FOUND, ERR_CANNOT_REMOVE_CONNECTED

    # Phase guard - only in LOBBY
    if self.phase != GamePhase.LOBBY:
        _LOGGER.warning("Cannot remove player: invalid phase %s", self.phase)
        return False, ERR_INVALID_PHASE

    # Check player exists
    if player_name not in self.players:
        _LOGGER.warning("Cannot remove player: not found %s", player_name)
        return False, ERR_PLAYER_NOT_FOUND

    player = self.players[player_name]

    # Check player is disconnected
    if player.connected:
        _LOGGER.warning("Cannot remove player: still connected %s", player_name)
        return False, ERR_CANNOT_REMOVE_CONNECTED

    # Check disconnect duration >= 60 seconds
    disconnect_duration = player.get_disconnect_duration()
    if disconnect_duration is None or disconnect_duration < 60:
        _LOGGER.warning(
            "Cannot remove player: not disconnected long enough %s (duration: %.1fs)",
            player_name,
            disconnect_duration or 0
        )
        return False, ERR_CANNOT_REMOVE_CONNECTED

    # Cancel all timers for this player
    self.cancel_timer(f"disconnect_grace:{player_name}")
    self.cancel_timer(f"reconnect_window:{player_name}")

    # Remove from players dict
    del self.players[player_name]

    _LOGGER.info(
        "Player removed from lobby: %s (was disconnected for %.1fs, remaining: %d)",
        player_name,
        disconnect_duration,
        len(self.players)
    )

    return True, None
```

### WebSocket Admin Handler Extension

**In server/websocket.py:**
```python
async def _handle_admin(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle admin actions from host."""
    player = self._get_player_by_ws(ws)
    if not player:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_IN_GAME,
            "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
        })
        return

    # Only host can perform admin actions
    if not player.is_host:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_HOST,
            "message": ERROR_MESSAGES[ERR_NOT_HOST]
        })
        return

    action = data.get("action")

    if action == "remove_player":
        await self._handle_remove_player(ws, data)
    # ... other admin actions (start_game, pause_game, etc.)

async def _handle_remove_player(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle player removal admin action."""
    from .const import ERROR_MESSAGES

    target_player = data.get("player_name")
    if not target_player:
        await ws.send_json({
            "type": "error",
            "code": "ERR_INVALID_MESSAGE",
            "message": "Missing player_name"
        })
        return

    success, error = self.game_state.remove_player(target_player)
    if not success:
        await ws.send_json({
            "type": "error",
            "code": error,
            "message": ERROR_MESSAGES[error]
        })
        return

    _LOGGER.info("Admin removed player: %s", target_player)
    await self.broadcast_state()
```

### Host UI Player Rendering Pattern

**In www/js/host.js:**
```javascript
function renderPlayers(players) {
  const playerListEl = document.getElementById('player-list');
  if (!players || players.length === 0) {
    playerListEl.innerHTML = '<p class="empty-state">Waiting for players to join...</p>';
    return;
  }

  playerListEl.innerHTML = players.map(player => {
    const statusClass = player.connected ? 'connected' : 'disconnected';
    const statusLabel = player.connected ? 'Connected' : 'Disconnected';
    const hostBadge = player.is_host ? '<span class="host-badge">HOST</span>' : '';

    // Show Remove button only if disconnected >= 60 seconds
    let removeButton = '';
    if (!player.connected && player.disconnect_duration >= 60) {
      removeButton = `
        <button
          class="btn-remove"
          onclick="removePlayer('${player.name}')"
          aria-label="Remove ${player.name}"
        >
          Remove
        </button>
      `;
    }

    return `
      <div class="player-card ${statusClass}">
        <div class="status-indicator" aria-label="${statusLabel}"></div>
        <div class="player-info">
          <span class="player-name">${player.name}</span>
          ${hostBadge}
        </div>
        ${removeButton}
      </div>
    `;
  }).join('');
}

function removePlayer(playerName) {
  const confirmed = confirm(`Remove ${playerName} from the lobby?`);
  if (!confirmed) return;

  sendMessage({
    type: 'admin',
    action: 'remove_player',
    player_name: playerName
  });
}
```

### CSS for Status Indicators and Remove Button

**In www/css/styles.css:**
```css
/* Player card status indicators */
.player-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--surface-color);
  transition: background 0.2s;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.player-card.connected .status-indicator {
  background: var(--success-color); /* green */
  box-shadow: 0 0 8px var(--success-color);
}

.player-card.disconnected .status-indicator {
  background: var(--warning-color); /* yellow/orange */
  box-shadow: 0 0 8px var(--warning-color);
}

/* Host badge */
.host-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--accent-pink);
  color: var(--background-dark);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Remove button - destructive action styling */
.btn-remove {
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 600;
  background: transparent;
  border: 2px solid var(--error-color); /* red */
  color: var(--error-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: auto;
}

.btn-remove:hover {
  background: var(--error-color);
  color: var(--background-dark);
  transform: scale(1.05);
}

.btn-remove:active {
  transform: scale(0.98);
}

/* CSS variable definitions (if not already in styles.css) */
:root {
  --success-color: #00ff88;
  --warning-color: #ffaa00;
  --error-color: #ff2d55;
  --accent-pink: #ff2d6a;
  --background-dark: #0a0a12;
  --surface-color: #1a1a24;
}
```

### Constants to Add to const.py

```python
# Lobby management error codes
ERR_CANNOT_REMOVE_CONNECTED = "CANNOT_REMOVE_CONNECTED"
ERR_PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"

# Disconnect threshold for removal eligibility
MIN_DISCONNECT_DURATION_FOR_REMOVAL = 60  # seconds

# Error messages
ERROR_MESSAGES = {
    # ... existing error messages ...
    ERR_CANNOT_REMOVE_CONNECTED: "Cannot remove a connected player. Wait for them to disconnect first.",
    ERR_PLAYER_NOT_FOUND: "Player not found in the game.",
    # ... other error messages ...
}
```

### State Broadcast Payload Extension

**Updated player object in state payload:**
```json
{
  "type": "state",
  "phase": "LOBBY",
  "players": [
    {
      "name": "Alice",
      "connected": false,
      "is_host": false,
      "disconnect_duration": 75  // NEW: Seconds since disconnect, null if connected
    },
    {
      "name": "Bob",
      "connected": true,
      "is_host": true,
      "disconnect_duration": null
    }
  ],
  "player_count": 2
}
```

**Add to GameState.get_state() serialization:**
```python
def get_state(self, for_player: str | None = None) -> dict:
    """Get game state, optionally filtered for specific player."""
    players_data = []
    for name, player in self.players.items():
        players_data.append({
            "name": name,
            "connected": player.connected,
            "is_host": player.is_host,
            "disconnect_duration": player.get_disconnect_duration()  # NEW
        })

    state = {
        "phase": self.phase.value,
        "players": players_data,
        "player_count": len(self.players)
    }

    # ... rest of state filtering logic
    return state
```

### Testing Requirements

**Unit Tests (tests/test_state.py):**
- Test `remove_player()` succeeds when player disconnected 60+ seconds
- Test `remove_player()` fails with `ERR_CANNOT_REMOVE_CONNECTED` when player connected
- Test `remove_player()` fails with `ERR_CANNOT_REMOVE_CONNECTED` when disconnected < 60s
- Test `remove_player()` fails with `ERR_INVALID_PHASE` when not in LOBBY
- Test `remove_player()` fails with `ERR_PLAYER_NOT_FOUND` when player doesn't exist
- Test `remove_player()` cancels all player timers on success
- Test `PlayerSession.get_disconnect_duration()` returns None when connected
- Test `PlayerSession.get_disconnect_duration()` returns correct duration when disconnected

**Integration Tests (tests/test_websocket.py):**
- Test host can remove disconnected player via WebSocket
- Test non-host receives `ERR_NOT_HOST` when attempting removal
- Test removal broadcasts updated state to all clients
- Test player list updates correctly after removal
- Test removal confirmation flow in UI

**UI Tests (manual or Playwright):**
- Test Remove button appears only when player disconnected >= 60s
- Test Remove button has destructive styling (red border)
- Test confirmation dialog appears when Remove clicked
- Test player card disappears from lobby after removal
- Test status indicators update in real-time (green/yellow dots)

### Edge Cases to Handle

1. **Player reconnects just before removal:**
   - Player disconnected 65 seconds, host clicks Remove
   - Player reconnects 1 second before message processed
   - Should fail with `ERR_CANNOT_REMOVE_CONNECTED` (reconnection cleared disconnect timestamp)

2. **Multiple hosts try to remove same player:**
   - Second request should fail with `ERR_PLAYER_NOT_FOUND` (already removed)

3. **Host tries to remove themselves:**
   - Should fail with `ERR_CANNOT_REMOVE_CONNECTED` (host should always be connected)
   - Alternatively, add explicit check: if player_name == host_name, return error

4. **Removal drops below minimum players (< 4):**
   - Removal succeeds (no minimum during LOBBY)
   - START button remains disabled if < 4 players
   - This is handled by existing game start validation

5. **Timer cleanup on removal:**
   - Must cancel `disconnect_grace:{name}` timer if still running
   - Must cancel `reconnect_window:{name}` timer if still running
   - Prevents orphaned asyncio tasks

### Security Considerations

**Host Privilege Validation:**
- ALWAYS check `player.is_host` before processing admin actions
- Never trust client to self-report host status
- Host status set server-side during join (first player = host)

**No Client-Side Enforcement:**
- Server is authoritative for all removal logic
- Client UI only provides convenience (showing Remove button)
- Malicious client cannot bypass 60-second rule by sending message

**State Integrity:**
- Player removal followed by immediate state broadcast
- All clients see consistent player list
- No race conditions with reconnection (checked atomically in remove_player)

### Performance Considerations

**Minimal Overhead:**
- `get_disconnect_duration()` is simple arithmetic (O(1))
- Timer cancellation is O(1) with named timer dict
- Player removal is O(1) dict delete

**Real-Time Updates:**
- State broadcasts already happening on connect/disconnect
- Adding removal doesn't increase message frequency
- Disconnect duration included in existing state payload (no extra message)

**Timer Cleanup:**
- Prevents memory leaks from orphaned asyncio tasks
- Important for long-running game sessions
- Part of normal game state hygiene

### Anti-Patterns to Avoid

**BAD - Allowing removal of connected players:**
```python
# NO! This creates confusion and poor UX
def remove_player(self, player_name: str):
    if player_name in self.players:
        del self.players[player_name]  # Removed without checking connection
```

**GOOD - Validate disconnection state:**
```python
# YES! Only remove players who are clearly inactive
def remove_player(self, player_name: str) -> tuple[bool, str | None]:
    player = self.players[player_name]
    if player.connected:
        return False, ERR_CANNOT_REMOVE_CONNECTED
    # ... rest of validation
```

**BAD - Client-side timer threshold:**
```javascript
// NO! Client calculates 60-second threshold (can be manipulated)
if (player.disconnectedAt && Date.now() - player.disconnectedAt >= 60000) {
  showRemoveButton();
}
```

**GOOD - Server-side threshold calculation:**
```python
# YES! Server enforces the 60-second rule
disconnect_duration = player.get_disconnect_duration()
if disconnect_duration is None or disconnect_duration < 60:
    return False, ERR_CANNOT_REMOVE_CONNECTED
```

**BAD - Not cancelling player timers:**
```python
# NO! Leaves orphaned tasks running
def remove_player(self, player_name: str):
    del self.players[player_name]
    # Forgot to cancel timers! Memory leak!
```

**GOOD - Clean up all player resources:**
```python
# YES! Cancel all timers before removal
def remove_player(self, player_name: str):
    self.cancel_timer(f"disconnect_grace:{player_name}")
    self.cancel_timer(f"reconnect_window:{player_name}")
    del self.players[player_name]
```

### Accessibility Considerations

**ARIA Labels:**
- Status indicators have `aria-label="Connected"` or `"Disconnected"`
- Remove buttons have `aria-label="Remove [Player Name]"`
- Player cards have semantic structure

**Keyboard Navigation:**
- Remove button is focusable via Tab
- Activatable via Enter/Space
- Confirmation dialog is keyboard-accessible

**Visual Accessibility:**
- Status indicators use color AND icon/dot (not color alone)
- Remove button has sufficient contrast (WCAG AA)
- Confirmation dialog has clear cancel option

**Screen Reader Support:**
- Player list announced as list with count
- Status changes announced via aria-live region (if implemented)
- Removal confirmation clearly states player name

### References

**Source Documents:**
- [Epics: Story 2.6 Acceptance Criteria](/Volumes/My Passport/Spyster/_bmad-output/epics.md#story-26-host-lobby-management)
- [Architecture: WebSocket Message Protocol](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#api--communication-patterns)
- [Architecture: Timer Architecture - Named Timer Dictionary](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#timer-architecture)
- [Architecture: Communication Patterns - State Broadcast](/Volumes/My Passport/Spyster/_bmad-output/architecture.md#communication-patterns)
- [Project Context: WebSocket Rules - Broadcast after changes](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#websocket-rules)
- [Project Context: Phase State Machine Rules](/Volumes/My Passport/Spyster/_bmad-output/project-context.md#phase-state-machine-rules)

**Epic Context:**
- Epic 2: Player Join & Connection
- Story 2.4 (Disconnect Detection) - Foundation for this story
- Story 2.5 (Player Reconnection) - Related reconnection window handling
- Story 2.6 enables clean lobby management before game start

**Related Stories:**
- Story 2.4: Disconnect Detection (provides disconnection tracking)
- Story 2.5: Player Reconnection (related reconnection window)
- Story 3.2: Start Game with Player Validation (enforces minimum 4 players)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

(To be filled during implementation)

### Completion Notes List

(To be filled during implementation)

### File List

**Files to Modify:**
- `custom_components/spyster/const.py` - Add error codes and constants
- `custom_components/spyster/game/player.py` - Add disconnect duration tracking
- `custom_components/spyster/game/state.py` - Add remove_player method
- `custom_components/spyster/server/websocket.py` - Add remove_player admin handler
- `custom_components/spyster/www/js/host.js` - Add Remove button UI
- `custom_components/spyster/www/css/styles.css` - Add status indicator and button styles

**Tests to Create/Update:**
- `tests/test_state.py` - Add remove_player tests
- `tests/test_player.py` - Add disconnect duration tests
- `tests/test_websocket.py` - Add admin removal integration tests

**No New Files Created** - All changes are extensions to existing files from Epic 1 and earlier Epic 2 stories.
