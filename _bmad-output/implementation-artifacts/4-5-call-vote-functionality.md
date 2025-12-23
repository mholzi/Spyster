---
story_id: '4-5'
story_name: 'Call Vote Functionality'
epic: 'Epic 4: Questioning Phase Mechanics'
status: 'done'
created: '2025-12-23'
completed: '2025-12-23'
project: 'Spyster'
dependencies:
  - '4-1-questioning-phase-transition'
  - '4-2-round-timer-implementation'
technical_context:
  - 'architecture.md - Timer Architecture, Phase Guards, WebSocket Protocol'
  - 'project-context.md - Python Rules, WebSocket Rules, Anti-Patterns'
  - 'epics.md - FR29, FR30, FR31, ARCH-10, ARCH-11, ARCH-17'
---

# Story 4.5: Call Vote Functionality

**Epic:** Epic 4: Questioning Phase Mechanics

**Status:** ready-for-dev

**Priority:** Critical (Core Game Mechanic)

**Estimated Effort:** 5 story points

**Dependencies:**
- Story 4.1: Questioning Phase Transition (must be complete)
- Story 4.2: Round Timer Implementation (must be complete)

---

## User Story

**As a** player
**I want** to call for a vote at any time during questioning
**So that** I can accuse someone when I'm suspicious

---

## Business Context

This story implements **FR29: Any player can call for a vote during the questioning phase**, which is a core game mechanic. The ability to call a vote at any time creates tension and strategic gameplay - players must decide when they have enough information to make an accusation.

Key gameplay considerations:
- **Democratic trigger**: ANY player can call a vote (not just host)
- **Immediate transition**: All players simultaneously enter voting phase
- **Timer swap**: Round timer cancelled, 60-second vote timer starts (ARCH-11)
- **Race condition handling**: Multiple players might tap "Call Vote" simultaneously

This transitions the game from the social deduction phase (questioning) to the accusation phase (voting), which is a pivotal moment in each round.

---

## Acceptance Criteria

### AC1: Call Vote Button Display
**Given** the game is in QUESTIONING phase
**When** a player views their screen
**Then** a prominent "Call Vote" button is displayed
**And** the button is enabled and tappable (48px+ touch target per UX-4)
**And** the button is visually distinct from other UI elements (high contrast)

**Implementation Notes:**
- Button should be always visible during questioning (not buried in menu)
- Position: Fixed at bottom of screen for easy reach
- Styling: Bright accent color (pink/cyan theme) with clear label
- No confirmation dialog needed - tapping immediately calls vote

---

### AC2: Successful Vote Call Flow
**Given** the game is in QUESTIONING phase
**When** a player taps "Call Vote"
**Then** a `call_vote` message is sent to the server
**And** the server validates the phase and player connection
**And** the game transitions from QUESTIONING to VOTE phase
**And** ALL connected players receive the phase transition simultaneously

**Implementation Notes:**
- Client sends: `{"type": "call_vote"}`
- Server validates: game phase, player is connected, player is in game
- Server actions:
  1. Cancel round timer (ARCH-11)
  2. Transition phase to VOTE
  3. Start vote timer (60 seconds per ARCH-10)
  4. Broadcast state to all clients (ARCH-14)
- All players see vote phase UI simultaneously

**WebSocket Message Flow:**
```
Player → Server: {"type": "call_vote"}
Server → All:    {"type": "state", "phase": "VOTE", "timer": 60, ...}
```

---

### AC3: Timer Cancellation and Swap
**Given** a vote is called during questioning
**When** the phase transition occurs
**Then** the round timer is cancelled immediately (ARCH-11)
**And** the vote timer (60 seconds) begins
**And** all clients see the new countdown timer

**Implementation Notes:**
- Use `cancel_timer("round")` before starting vote timer
- Start vote timer: `start_timer("vote", 60, self._on_vote_timeout)`
- Timer state must be included in broadcast: `{"timer": 60, "timer_type": "vote"}`
- Frontend updates timer display from round countdown to vote countdown

**Architecture Compliance:**
- **ARCH-11**: Cancel existing timer before starting new one with same name
- **ARCH-10**: Vote timer duration is 60 seconds (constant)

---

### AC4: Phase Guard Enforcement (ARCH-17)
**Given** the game is NOT in QUESTIONING phase
**When** a player sends a `call_vote` message
**Then** the server returns an error
**And** the message is: `ERR_INVALID_PHASE`
**And** the game state does not change

**Implementation Notes:**
- Phase guard in `call_vote()` method: `if self.phase != GamePhase.QUESTIONING: return error`
- Error response: `{"type": "error", "code": "ERR_INVALID_PHASE", "message": "Can only call vote during questioning phase"}`
- No state mutation occurs (ARCH-17 enforcement)

---

### AC5: Race Condition Handling
**Given** multiple players tap "Call Vote" simultaneously
**When** the server receives multiple `call_vote` requests
**Then** only the first request is processed
**And** subsequent requests return `ERR_INVALID_PHASE` (already in VOTE phase)
**And** all players end up in the same VOTE phase state

**Implementation Notes:**
- Phase guard naturally handles race condition
- First request: `phase == QUESTIONING` → transition to VOTE → success
- Second request (milliseconds later): `phase == VOTE` → return error
- No special race condition handling needed - phase guard is sufficient
- This is safe because phase transitions are atomic operations

**Architecture Compliance:**
- **ARCH-17**: Phase guards prevent invalid state transitions
- Phase transition is synchronous within event loop (no race between checks)

---

### AC6: Vote Broadcast to All Players
**Given** any connected player calls a vote
**When** the phase transition succeeds
**Then** ALL players (including host) receive the updated state
**And** all players see the VOTE phase UI simultaneously
**And** the player who called the vote sees the same UI as others

**Implementation Notes:**
- Use `broadcast_state()` to send to all connections (per ARCH-14)
- Host display shows "VOTING" phase indicator
- Player displays show voting UI (player selection cards)
- No special treatment for the player who called vote

---

## Technical Implementation

### Files to Create
None - all modifications to existing files

---

### Files to Modify

#### 1. `custom_components/spyster/game/state.py`

**Add `call_vote()` method:**

```python
def call_vote(self) -> tuple[bool, str | None]:
    """
    Transition from QUESTIONING to VOTE phase.

    Any player can call this during questioning (FR29).

    Returns:
        (success: bool, error_code: str | None)

    Phase Guard:
        - Only valid in QUESTIONING phase (ARCH-17)

    Side Effects:
        - Cancels round timer (ARCH-11)
        - Starts vote timer (60s per ARCH-10)
        - Transitions to VOTE phase
    """
    # Phase guard (ARCH-17)
    if self.phase != GamePhase.QUESTIONING:
        return (False, "ERR_INVALID_PHASE")

    _LOGGER.info("Vote called - transitioning from QUESTIONING to VOTE")

    # Cancel round timer (ARCH-11)
    self.cancel_timer("round")

    # Transition to VOTE phase
    self.phase = GamePhase.VOTE

    # Start vote timer (60 seconds per ARCH-10)
    self.start_timer("vote", VOTE_TIMER_DURATION, self._on_vote_timeout)

    return (True, None)


async def _on_vote_timeout(self) -> None:
    """
    Handle vote timer expiration.

    Non-voters are counted as abstain (FR30).
    Transition to REVEAL phase.
    """
    _LOGGER.info(
        "Vote timer expired - %d/%d players voted",
        len(self.votes),
        len(self.players)
    )

    # Transition to REVEAL (Story 5.6 will implement reveal logic)
    self.phase = GamePhase.REVEAL

    # Cancel vote timer
    self.cancel_timer("vote")

    # Start reveal timer (Story 5.6)
    # For now, just transition to REVEAL
    _LOGGER.info("Transitioning to REVEAL phase")
```

**Add to `const.py`:**

```python
# Timer durations (seconds)
VOTE_TIMER_DURATION = 60  # FR30, ARCH-10
```

---

#### 2. `custom_components/spyster/server/websocket.py`

**Add `call_vote` handler:**

```python
async def _handle_call_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
    """
    Handle call_vote message from player.

    FR29: Any player can call for a vote during questioning.

    Args:
        ws: Player's WebSocket connection
        data: Message payload (empty for call_vote)
    """
    # Verify player is connected
    if ws not in self._ws_to_player:
        await ws.send_json({
            "type": "error",
            "code": "ERR_NOT_CONNECTED",
            "message": ERROR_MESSAGES["ERR_NOT_CONNECTED"]
        })
        return

    player = self._ws_to_player[ws]

    _LOGGER.info("Player %s called vote", player.name)

    # Call vote on game state
    game_state = self.hass.data[DOMAIN]["game_state"]
    success, error_code = game_state.call_vote()

    if not success:
        await ws.send_json({
            "type": "error",
            "code": error_code,
            "message": ERROR_MESSAGES.get(error_code, "Unknown error")
        })
        return

    # Broadcast updated state to all clients (ARCH-14)
    await self.broadcast_state()
```

**Update message dispatcher in `_handle_message()`:**

```python
async def _handle_message(self, ws: web.WebSocketResponse, msg: aiohttp.WSMessage) -> None:
    """Dispatch WebSocket messages to appropriate handlers."""
    try:
        data = json.loads(msg.data)
        msg_type = data.get("type")

        # ... existing handlers ...

        if msg_type == "call_vote":
            await self._handle_call_vote(ws, data)

        # ... other handlers ...

    except Exception as err:
        _LOGGER.error("Error handling message: %s", err)
        await ws.send_json({
            "type": "error",
            "code": "ERR_INTERNAL",
            "message": "Internal server error"
        })
```

---

#### 3. `custom_components/spyster/const.py`

**Add error messages:**

```python
# Error codes
ERR_INVALID_PHASE = "ERR_INVALID_PHASE"
ERR_NOT_CONNECTED = "ERR_NOT_CONNECTED"

# Error messages
ERROR_MESSAGES = {
    # ... existing messages ...
    "ERR_INVALID_PHASE": "Action not valid in current game phase",
    "ERR_NOT_CONNECTED": "You are not connected to the game",
}
```

---

#### 4. `custom_components/spyster/www/js/player.js`

**Add call vote button handler:**

```javascript
// Call vote button (shown during QUESTIONING phase)
function renderQuestioningPhase(state) {
    const container = document.getElementById('game-container');

    container.innerHTML = `
        <div class="phase-container questioning">
            <div class="phase-header">
                <div class="phase-title">Questioning</div>
                <div class="round-info">Round ${state.round_number} of ${state.total_rounds}</div>
            </div>

            <!-- Timer display -->
            <div class="timer-display">
                <div class="timer-value" id="timer-value">${formatTime(state.timer)}</div>
                <div class="timer-label">Time Remaining</div>
            </div>

            <!-- Role reminder (shows location or spy status) -->
            <div class="role-reminder">
                ${renderRoleReminder(state)}
            </div>

            <!-- Current Q&A pair (if available) -->
            ${state.questioner && state.answerer ? `
                <div class="qa-pair">
                    <div class="questioner">
                        <span class="label">Asking:</span>
                        <span class="name">${escapeHtml(state.questioner)}</span>
                    </div>
                    <div class="answerer">
                        <span class="label">Answering:</span>
                        <span class="name">${escapeHtml(state.answerer)}</span>
                    </div>
                </div>
            ` : ''}

            <!-- Call Vote Button (PROMINENT) -->
            <button class="call-vote-button" id="call-vote-btn">
                Call Vote
            </button>
        </div>
    `;

    // Attach event listener
    document.getElementById('call-vote-btn').addEventListener('click', handleCallVote);

    // Start timer countdown if needed
    if (state.timer) {
        startTimerCountdown(state.timer);
    }
}

function handleCallVote() {
    // Disable button to prevent double-tap
    const button = document.getElementById('call-vote-btn');
    button.disabled = true;
    button.textContent = 'Calling Vote...';

    // Send call_vote message
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'call_vote'
        }));
    } else {
        showError('Not connected to server');
        button.disabled = false;
        button.textContent = 'Call Vote';
    }
}

function renderRoleReminder(state) {
    // Show spy or non-spy role info
    if (state.is_spy) {
        return `
            <div class="role-spy">
                <div class="spy-indicator">YOU ARE THE SPY</div>
                <div class="spy-hint">Figure out the location!</div>
            </div>
        `;
    } else {
        return `
            <div class="role-non-spy">
                <div class="location-name">${escapeHtml(state.location)}</div>
                <div class="role-name">${escapeHtml(state.role)}</div>
            </div>
        `;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function startTimerCountdown(initialSeconds) {
    let remaining = initialSeconds;

    const interval = setInterval(() => {
        remaining--;
        const timerEl = document.getElementById('timer-value');
        if (timerEl) {
            timerEl.textContent = formatTime(remaining);
        }

        if (remaining <= 0) {
            clearInterval(interval);
        }
    }, 1000);

    // Store interval for cleanup
    window.currentTimerInterval = interval;
}
```

---

#### 5. `custom_components/spyster/www/css/styles.css`

**Add call vote button styling:**

```css
/* Call Vote Button - Prominent and accessible */
.call-vote-button {
    position: fixed;
    bottom: var(--spacing-xl);
    left: 50%;
    transform: translateX(-50%);

    /* Size and spacing */
    min-width: 200px;
    min-height: 48px; /* UX-4: 48px minimum touch target */
    padding: var(--spacing-md) var(--spacing-xl);

    /* Typography */
    font-size: 20px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;

    /* Colors (high contrast) */
    background: var(--accent-primary); /* Pink */
    color: var(--text-primary);
    border: 2px solid var(--accent-primary);
    border-radius: var(--radius-md);

    /* Effects */
    box-shadow: 0 4px 8px rgba(255, 20, 147, 0.3);
    transition: all 0.2s ease;
    cursor: pointer;

    /* Accessibility */
    z-index: 100; /* Always on top */
}

.call-vote-button:hover {
    background: var(--accent-primary-hover);
    box-shadow: 0 6px 12px rgba(255, 20, 147, 0.5);
    transform: translateX(-50%) translateY(-2px);
}

.call-vote-button:active {
    transform: translateX(-50%) translateY(0);
    box-shadow: 0 2px 4px rgba(255, 20, 147, 0.3);
}

.call-vote-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: var(--bg-tertiary);
    border-color: var(--text-tertiary);
}

/* Questioning Phase Container */
.phase-container.questioning {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
    padding: var(--spacing-xl);
    padding-bottom: 120px; /* Space for fixed button */
}

/* Timer Display */
.timer-display {
    text-align: center;
    padding: var(--spacing-lg);
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
}

.timer-value {
    font-size: 72px;
    font-weight: 700;
    color: var(--accent-secondary); /* Cyan */
    font-family: 'Courier New', monospace;
}

.timer-label {
    font-size: 16px;
    color: var(--text-secondary);
    margin-top: var(--spacing-sm);
}

/* Role Reminder */
.role-reminder {
    padding: var(--spacing-md);
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    text-align: center;
}

.role-spy .spy-indicator {
    font-size: 24px;
    font-weight: 700;
    color: var(--accent-primary);
}

.role-non-spy .location-name {
    font-size: 32px;
    font-weight: 700;
    color: var(--accent-secondary);
}

.role-non-spy .role-name {
    font-size: 18px;
    color: var(--text-secondary);
    margin-top: var(--spacing-sm);
}

/* Q&A Pair Display */
.qa-pair {
    display: flex;
    justify-content: space-around;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
}

.questioner, .answerer {
    flex: 1;
    text-align: center;
}

.qa-pair .label {
    display: block;
    font-size: 14px;
    color: var(--text-tertiary);
    margin-bottom: var(--spacing-xs);
}

.qa-pair .name {
    display: block;
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}
```

---

## Testing Requirements

### Unit Tests (`tests/test_state.py`)

```python
def test_call_vote_success():
    """Call vote transitions from QUESTIONING to VOTE."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # Mock timer system
    game_state._timers = {"round": asyncio.create_task(asyncio.sleep(300))}

    success, error = game_state.call_vote()

    assert success is True
    assert error is None
    assert game_state.phase == GamePhase.VOTE
    assert "round" not in game_state._timers  # Round timer cancelled
    assert "vote" in game_state._timers  # Vote timer started


def test_call_vote_invalid_phase():
    """Call vote fails in non-QUESTIONING phase."""
    game_state = GameState()

    # Test in LOBBY
    game_state.phase = GamePhase.LOBBY
    success, error = game_state.call_vote()
    assert success is False
    assert error == "ERR_INVALID_PHASE"

    # Test in VOTE
    game_state.phase = GamePhase.VOTE
    success, error = game_state.call_vote()
    assert success is False
    assert error == "ERR_INVALID_PHASE"

    # Test in REVEAL
    game_state.phase = GamePhase.REVEAL
    success, error = game_state.call_vote()
    assert success is False
    assert error == "ERR_INVALID_PHASE"


def test_call_vote_cancels_round_timer():
    """Call vote cancels active round timer (ARCH-11)."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # Start round timer
    round_task = asyncio.create_task(asyncio.sleep(420))  # 7 minutes
    game_state._timers["round"] = round_task

    assert not round_task.done()

    # Call vote
    success, _ = game_state.call_vote()

    assert success is True
    assert round_task.cancelled()  # Round timer cancelled
    assert "round" not in game_state._timers


def test_call_vote_starts_vote_timer():
    """Call vote starts 60-second vote timer (ARCH-10)."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    success, _ = game_state.call_vote()

    assert success is True
    assert "vote" in game_state._timers
    assert game_state._timers["vote"] is not None
    # Timer duration verified by integration test


def test_call_vote_race_condition():
    """Multiple simultaneous call_vote requests handled correctly."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # First call succeeds
    success1, error1 = game_state.call_vote()
    assert success1 is True
    assert game_state.phase == GamePhase.VOTE

    # Second call (immediate) fails - already in VOTE
    success2, error2 = game_state.call_vote()
    assert success2 is False
    assert error2 == "ERR_INVALID_PHASE"
    assert game_state.phase == GamePhase.VOTE  # Still in VOTE
```

---

### Integration Tests

**Manual Test: Basic Vote Call Flow**
1. Start game with 4 players
2. Progress to QUESTIONING phase (complete Stories 3.x, 4.1, 4.2)
3. On any player device, tap "Call Vote" button
4. **VERIFY:** Button disables and shows "Calling Vote..."
5. **VERIFY:** All player devices transition to VOTE phase simultaneously
6. **VERIFY:** Round timer disappears, vote timer (60s) appears
7. **VERIFY:** Host display shows "VOTING" phase indicator

**Test Scenario: Race Condition**
1. Start game with multiple players
2. On two devices simultaneously, tap "Call Vote" at the exact same moment
3. **VERIFY:** Both players end up in VOTE phase (no error messages)
4. **VERIFY:** Only one timer is running (no duplicate timers)
5. **VERIFY:** Game state is consistent (check server logs)

**Test Scenario: Phase Guard**
1. In LOBBY phase, manually send `{"type": "call_vote"}` via browser console
2. **VERIFY:** Server returns `ERR_INVALID_PHASE` error
3. **VERIFY:** Game remains in LOBBY phase
4. Repeat for VOTE, REVEAL, SCORING, END phases
5. **VERIFY:** All return `ERR_INVALID_PHASE`

**Test Scenario: Timer Swap**
1. Start questioning with 7-minute round timer
2. Wait 2 minutes, then call vote
3. **VERIFY:** Round timer cancels (not at 5:00 remaining)
4. **VERIFY:** Vote timer starts at 60 seconds
5. **VERIFY:** Timer display updates correctly on all devices

---

## Security Considerations

**Phase Guard Enforcement (ARCH-17):**
- `call_vote()` MUST check phase before any state mutation
- Pattern: `if self.phase != GamePhase.QUESTIONING: return (False, error)`
- Prevents invalid transitions (can't call vote in lobby, during reveal, etc.)

**No Authentication Required:**
- Any connected player can call vote (FR29)
- No "host only" restriction on this action
- This is intentional - democratic game mechanic

**Race Condition Safety:**
- Phase guard naturally handles simultaneous calls
- First request changes phase to VOTE
- Second request sees VOTE phase, returns error
- No data corruption possible (single-threaded event loop)

---

## Definition of Done

- [x] `call_vote()` method implemented in `game/state.py`
- [x] Phase guard enforces QUESTIONING-only constraint (ARCH-17)
- [x] Round timer cancelled when vote called (ARCH-11)
- [x] Vote timer (60s) started when vote called (ARCH-10)
- [x] WebSocket handler `_handle_call_vote()` in `server/websocket.py`
- [x] "Call Vote" button in player UI (`www/js/player.js`)
- [x] Button styling in `www/css/styles.css` (48px+ touch target)
- [x] Error codes and messages in `const.py`
- [x] Unit tests pass (phase guard, timer cancellation, race condition)
- [ ] Integration test: Vote called successfully transitions all players
- [ ] Integration test: Race condition handled correctly
- [ ] Integration test: Phase guard rejects calls in wrong phase
- [ ] Code review completed
- [ ] Story marked as `done` in `sprint-status.yaml`

---

## Dependencies

**Upstream Dependencies:**
- Story 4.1 (Questioning Phase Transition) - MUST be complete
  - Provides QUESTIONING phase state
  - Implements phase transition mechanism
- Story 4.2 (Round Timer Implementation) - MUST be complete
  - Provides `start_timer()` and `cancel_timer()` methods
  - Implements timer system used by call_vote

**Downstream Dependencies:**
- Story 5.1 (Voting Phase UI) - consumes VOTE phase state created by this story
- Story 5.2 (Confidence Betting) - relies on vote timer started here
- Story 5.5 (Vote Timer Handling) - implements `_on_vote_timeout()` callback

**Parallel Development:**
- Story 4.3 (Question/Answer Selection) can be developed in parallel
- Story 4.4 (Timer Display) provides UI for timer countdown

---

## Notes

**Implementation Order:**
1. Add `call_vote()` method to `GameState` (pure logic, testable)
2. Add unit tests (red-green-refactor)
3. Add WebSocket handler `_handle_call_vote()`
4. Update frontend to add "Call Vote" button
5. Add CSS styling for button
6. Integration testing with multiple devices

**Common Pitfalls:**
- Forgetting to cancel round timer before starting vote timer (ARCH-11 violation)
- Not enforcing phase guard (allows vote calls in wrong phase)
- Button not disabled after click (allows spam clicks)
- Timer not included in broadcast state (clients don't see countdown)

**Related Architecture Decisions:**
- **ARCH-10**: Timer types - vote (60s)
- **ARCH-11**: Cancel existing timer before starting new one
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on all state-mutating methods
- **FR29**: Any player can call for a vote during questioning

**UX Considerations:**
- Button should be HIGHLY visible (players need to find it quickly)
- Fixed position prevents it from scrolling off-screen
- Large touch target (48px+) prevents mis-taps
- Immediate feedback (disable + text change) acknowledges action
- No confirmation dialog - tap to immediately trigger (reduces friction)

---

## Story Completion Checklist

When completing this story, developer MUST:

1. Run all unit tests: `pytest tests/test_state.py::test_call_vote* -v`
2. Start local game with 4+ players
3. Progress to QUESTIONING phase
4. Test vote call from different players
5. Verify timer swap (round → vote)
6. Test race condition (simultaneous calls)
7. Test phase guard (call in wrong phase)
8. Check server logs for proper logging (ARCH-16)
9. Request code review
10. Update `sprint-status.yaml` to `done`

---

**Story Ready for Implementation** ✅
**Priority:** Critical (Core Game Mechanic)
**Architectural Impact:** MEDIUM (introduces phase transition pattern)
