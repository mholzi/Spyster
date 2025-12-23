# Story 4.5: Call Vote Functionality

**Epic:** Epic 4 - Questioning Phase
**Story ID:** 4.5
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to call for a vote at any time during questioning**,
So that **I can accuse someone when I'm suspicious**.

---

## Acceptance Criteria

### AC1: Call Vote Sends Message

**Given** the game is in QUESTIONING phase
**When** a player taps "Call Vote"
**Then** a vote message is sent to the server
**And** the game transitions from QUESTIONING to VOTE phase

### AC2: Vote Triggers for All Players

**Given** any connected player
**When** they call a vote
**Then** the vote triggers for ALL players simultaneously
**And** all players enter the voting phase together

### AC3: Round Timer Cancellation

**Given** a vote is called
**When** the transition occurs
**Then** the round timer is cancelled
**And** the vote timer (60 seconds) begins

### AC4: Simultaneous Vote Handling

**Given** multiple players try to call vote simultaneously
**When** the server receives multiple requests
**Then** only the first is processed
**And** subsequent requests are ignored (already in VOTE phase)

### AC5: Phase Guard Enforcement

**Given** the game is NOT in QUESTIONING phase
**When** a player tries to call vote
**Then** an error is returned
**And** the phase remains unchanged

### AC6: Vote Caller Attribution

**Given** a player calls a vote
**When** the transition is broadcast
**Then** the state includes who called the vote
**And** players see "[Player] called for a vote!"

---

## Requirements Coverage

### Functional Requirements

- **FR29**: Any player can call for a vote during the questioning phase
- **FR31**: Player calling a vote triggers voting phase for all players

### Non-Functional Requirements

- **NFR2**: WebSocket Latency - Messages delivered in < 100ms on local network
- **NFR4**: State Sync - All players see same game state within 500ms of change

### Architectural Requirements

- **ARCH-9**: Named timer dictionary pattern: `self._timers: dict[str, asyncio.Task]`
- **ARCH-10**: Timer types - vote (60s)
- **ARCH-11**: Cancel existing timer before starting new one
- **ARCH-12**: Message format: `{"type": "...", ...payload}` with snake_case fields
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on all state-mutating methods
- **ARCH-19**: Return pattern: `(success: bool, error_code: str | None)`

---

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Add vote-related constants:

```python
# Vote phase constants
TIMER_VOTE = 60  # 60 seconds for voting

# Error codes
ERR_VOTE_NOT_ALLOWED = "VOTE_NOT_ALLOWED"
ERR_ALREADY_IN_VOTE = "ALREADY_IN_VOTE"
ERR_PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"  # If not already defined

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_VOTE_NOT_ALLOWED: "You cannot call a vote right now.",
    ERR_ALREADY_IN_VOTE: "Voting has already started.",
    ERR_PLAYER_NOT_FOUND: "Player not found in this game.",
}
```

#### 2. GameState (`game/state.py`)

Add call vote and vote phase transition:

```python
class GameState:
    def __init__(self):
        # ... existing fields ...
        self.vote_caller: str | None = None  # Who called the vote
        self.votes: dict[str, dict] = {}  # player_name -> {target, confidence}
        self.vote_time_remaining: int = 0

    def call_vote(self, caller_name: str) -> tuple[bool, str | None]:
        """
        Handle a player calling for a vote.

        Args:
            caller_name: Name of player calling the vote

        Returns:
            (success: bool, error_code: str | None)
        """
        # Phase guard - must be in QUESTIONING
        if self.phase != GamePhase.QUESTIONING:
            _LOGGER.warning(
                "Cannot call vote - invalid phase: %s (caller: %s)",
                self.phase,
                caller_name
            )
            return False, ERR_INVALID_PHASE

        # Verify caller is a connected player
        player = self.players.get(caller_name)
        if not player or not player.connected:
            _LOGGER.warning("Vote called by unknown/disconnected player: %s", caller_name)
            return False, ERR_PLAYER_NOT_FOUND

        _LOGGER.info("Vote called by %s", caller_name)

        # Store vote caller for attribution
        self.vote_caller = caller_name

        # Transition to VOTE phase
        success, error = self._transition_to_vote()
        if not success:
            self.vote_caller = None  # Rollback
            return False, error

        return True, None

    def _transition_to_vote(self) -> tuple[bool, str | None]:
        """
        Internal: Transition from QUESTIONING to VOTE phase.

        Returns:
            (success: bool, error_code: str | None)
        """
        # Cancel round timer
        self._cancel_timer("round")
        _LOGGER.info("Round timer cancelled for vote transition")

        # Clear any existing votes
        self.votes = {}

        # Transition phase
        previous_phase = self.phase
        self.phase = GamePhase.VOTE

        # Start vote timer
        success, error = self._start_vote_timer()
        if not success:
            # Rollback phase on failure
            self.phase = previous_phase
            _LOGGER.error("Failed to start vote timer: %s", error)
            return False, error

        _LOGGER.info("Transitioned to VOTE phase (caller: %s)", self.vote_caller)

        return True, None

    def _start_vote_timer(self) -> tuple[bool, str | None]:
        """
        Start the 60-second vote timer.

        Returns:
            (success: bool, error_code: str | None)
        """
        # Cancel any existing vote timer
        self._cancel_timer("vote")

        # Initialize vote timer state
        self.vote_time_remaining = TIMER_VOTE

        # Create timer task
        timer_task = asyncio.create_task(
            self._vote_timer_task()
        )
        self._timers["vote"] = timer_task

        _LOGGER.info("Vote timer started (%d seconds)", TIMER_VOTE)

        return True, None

    async def _vote_timer_task(self) -> None:
        """Internal task for vote timer countdown."""
        try:
            start_time = asyncio.get_event_loop().time()
            end_time = start_time + TIMER_VOTE

            while True:
                current_time = asyncio.get_event_loop().time()
                remaining = int(end_time - current_time)

                if remaining <= 0:
                    # Timer expired - transition to reveal
                    _LOGGER.info("Vote timer expired - transitioning to REVEAL")
                    self.vote_time_remaining = 0
                    await self._on_vote_timer_expired()
                    break

                # Update remaining time
                if remaining != self.vote_time_remaining:
                    self.vote_time_remaining = remaining

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            _LOGGER.debug("Vote timer cancelled")
            raise
        finally:
            self._timers.pop("vote", None)

    async def _on_vote_timer_expired(self) -> None:
        """
        Handle vote timer expiration.
        Players who haven't voted are marked as abstain.
        """
        # Mark non-voters as abstain
        for player_name, player in self.players.items():
            if player.connected and player_name not in self.votes:
                _LOGGER.info("Player %s abstained (timeout)", player_name)
                self.votes[player_name] = {"target": None, "confidence": 0, "abstained": True}

        # Transition to REVEAL phase
        # (Will be fully implemented in Epic 5)
        self.phase = GamePhase.REVEAL
        _LOGGER.info("Transitioned to REVEAL phase")

    def on_round_timer_expired(self) -> None:
        """
        Handle round timer expiration (FR30).
        Auto-triggers voting when timer expires.
        """
        if self.phase != GamePhase.QUESTIONING:
            _LOGGER.warning("Round timer expired but not in QUESTIONING phase")
            return

        _LOGGER.info("Round timer expired - auto-triggering vote")

        # Set vote caller to "TIMER" for attribution
        self.vote_caller = "[TIMER]"

        # Transition to vote
        success, error = self._transition_to_vote()
        if not success:
            _LOGGER.error("Failed to auto-transition to vote: %s", error)

    def get_state(self, for_player: str | None = None) -> dict:
        """Get game state, filtered for specific player."""
        base_state = {
            "phase": self.phase.value,
            "player_count": len(self.players),
            "connected_count": self.get_connected_player_count(),
            "round": self.current_round,
        }

        # VOTE phase state
        if self.phase == GamePhase.VOTE:
            base_state["timer"] = {
                "name": "vote",
                "remaining": self.vote_time_remaining,
                "total": TIMER_VOTE,
            }
            base_state["vote_caller"] = self.vote_caller
            base_state["votes_submitted"] = len([v for v in self.votes.values() if not v.get("abstained")])
            base_state["votes_required"] = self.get_connected_player_count()

            # Include role data for reference (same as QUESTIONING)
            if for_player:
                player = self.players.get(for_player)
                if player:
                    # ... same role_data logic as QUESTIONING ...
                    pass

        return base_state
```

#### 3. WebSocket Handler (`server/websocket.py`)

Add call vote message handler:

```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    # ... existing handlers ...

    if msg_type == "call_vote":
        await self._handle_call_vote(ws, data)
        return

async def _handle_call_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle a player calling for a vote."""
    player_name = self._get_player_name_by_ws(ws)
    if not player_name:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_IN_GAME,
            "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
        })
        return

    success, error = self.game_state.call_vote(player_name)

    if not success:
        await ws.send_json({
            "type": "error",
            "code": error,
            "message": ERROR_MESSAGES.get(error, "Cannot call vote at this time.")
        })
        return

    _LOGGER.info("Vote called by %s - broadcasting to all players", player_name)

    # Broadcast phase transition to all players
    await self.broadcast_state()
```

#### 4. Player Display HTML (`www/player.html`)

Add vote button to questioning view (already partially done in previous stories):

```html
<!-- Inside questioning-view -->
<div class="vote-controls">
    <button
        id="call-vote-btn"
        class="btn-primary btn-large btn-call-vote"
        aria-label="Call for a vote to identify the spy"
    >
        CALL VOTE
    </button>
</div>
```

#### 5. Player Display Logic (`www/js/player.js`)

Add call vote functionality:

```javascript
class PlayerDisplay {
    constructor() {
        // ... existing init ...
        this.voteButtonEnabled = true;
    }

    setupEventListeners() {
        // ... existing listeners ...

        // Call vote button
        const callVoteBtn = document.getElementById('call-vote-btn');
        if (callVoteBtn) {
            callVoteBtn.addEventListener('click', () => this.callVote());
        }
    }

    callVote() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            this.showError('Connection lost. Please refresh.');
            return;
        }

        if (!this.voteButtonEnabled) {
            return;
        }

        // Disable button to prevent double-click
        this.voteButtonEnabled = false;
        const callVoteBtn = document.getElementById('call-vote-btn');
        if (callVoteBtn) {
            callVoteBtn.disabled = true;
            callVoteBtn.textContent = 'Calling Vote...';
        }

        // Send call_vote message
        this.ws.send(JSON.stringify({
            type: 'call_vote'
        }));

        console.log('Call vote message sent');
    }

    onStateUpdate(state) {
        this.state = state;

        // Update UI based on phase
        if (state.phase === 'QUESTIONING') {
            this.showQuestioningView(state);
            // Re-enable vote button
            this.enableVoteButton();
        } else if (state.phase === 'VOTE') {
            this.showVoteView(state);
        }
    }

    enableVoteButton() {
        this.voteButtonEnabled = true;
        const callVoteBtn = document.getElementById('call-vote-btn');
        if (callVoteBtn) {
            callVoteBtn.disabled = false;
            callVoteBtn.textContent = 'CALL VOTE';
        }
    }

    showVoteView(state) {
        // Hide all other views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        // Note: #vote-view element will be created in Epic 5 (Story 5.1)
        // For now, this provides the transition scaffolding
        const voteView = document.getElementById('vote-view');
        if (voteView) {
            voteView.style.display = 'block';
        }

        // Show vote caller notification
        if (state.vote_caller) {
            this.showVoteCallerNotification(state.vote_caller);
        }

        // Update vote timer
        if (state.timer) {
            this.updateVoteTimer(state.timer.remaining);
        }

        // Update submission tracker
        if (state.votes_submitted !== undefined && state.votes_required !== undefined) {
            this.updateVoteTracker(state.votes_submitted, state.votes_required);
        }
    }

    showVoteCallerNotification(caller) {
        const notificationEl = document.getElementById('vote-notification');
        if (!notificationEl) return;

        if (caller === '[TIMER]') {
            notificationEl.textContent = 'Time\'s up! Voting has begun.';
        } else {
            notificationEl.textContent = `${this.escapeHtml(caller)} called for a vote!`;
        }

        notificationEl.style.display = 'block';

        // Auto-hide after 3 seconds
        setTimeout(() => {
            notificationEl.style.display = 'none';
        }, 3000);
    }

    updateVoteTimer(timeRemaining) {
        const timerElement = document.getElementById('vote-timer');
        if (!timerElement) return;

        const seconds = timeRemaining;
        timerElement.textContent = `0:${seconds.toString().padStart(2, '0')}`;

        // Urgency styling
        const timerDisplay = timerElement.closest('.timer-display');
        if (timerDisplay) {
            timerDisplay.classList.toggle('timer-urgent', timeRemaining < 10);
            timerDisplay.classList.toggle('timer-warning', timeRemaining >= 10 && timeRemaining < 20);
        }
    }

    updateVoteTracker(submitted, required) {
        const trackerElement = document.getElementById('vote-tracker');
        if (!trackerElement) return;

        trackerElement.textContent = `${submitted}/${required} voted`;
        trackerElement.setAttribute('aria-valuenow', submitted);
        trackerElement.setAttribute('aria-valuemax', required);
    }
}
```

#### 6. CSS Styles (`www/css/styles.css`)

Add call vote button styles:

```css
/* =================================
   CALL VOTE BUTTON
   ================================= */

.btn-call-vote {
    width: 100%;
    padding: var(--spacing-lg) var(--spacing-xl);
    font-size: 20px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    min-height: 56px; /* Large touch target */
    background: linear-gradient(135deg, var(--color-accent-primary), #ff1a5c);
    border: none;
    border-radius: var(--radius-lg);
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(255, 45, 106, 0.3);
}

.btn-call-vote:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(255, 45, 106, 0.4);
}

.btn-call-vote:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(255, 45, 106, 0.3);
}

.btn-call-vote:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

.btn-call-vote:focus-visible {
    outline: none;
    box-shadow:
        0 4px 12px rgba(255, 45, 106, 0.3),
        0 0 0 3px rgba(255, 45, 106, 0.5);
}

/* =================================
   VOTE NOTIFICATION
   ================================= */

#vote-notification {
    position: fixed;
    top: var(--spacing-lg);
    left: 50%;
    transform: translateX(-50%);
    padding: var(--spacing-md) var(--spacing-xl);
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-accent-primary);
    border-radius: var(--radius-lg);
    color: var(--color-text-primary);
    font-size: 18px;
    font-weight: 600;
    text-align: center;
    z-index: 1000;
    animation: slideInDown 0.3s ease-out;
}

@keyframes slideInDown {
    from {
        opacity: 0;
        transform: translateX(-50%) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }
}

/* =================================
   VOTE TRACKER
   ================================= */

#vote-tracker {
    text-align: center;
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    font-size: 16px;
    color: var(--color-text-secondary);
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    .btn-call-vote {
        transition: none;
    }

    .btn-call-vote:hover:not(:disabled) {
        transform: none;
    }

    #vote-notification {
        animation: none;
    }
}
```

---

## Implementation Tasks

### Task 1: Add Constants (AC: All)
- [x] Add `TIMER_VOTE = 60` constant
- [x] Add `VOTE_TIMER_DURATION = 60` constant
- [x] Uses `ERR_INVALID_PHASE` for phase guard errors

### Task 2: Implement call_vote Method (AC: 1, 2, 4, 5)
- [x] Add `call_vote()` method with phase guard
- [x] Return error for invalid phase
- [x] Log vote transition

### Task 3: Implement Phase Transition (AC: 2, 3)
- [x] Cancel round timer before transition
- [x] Transition to VOTE phase
- [x] Start vote timer

### Task 4: Implement Vote Timer (AC: 3)
- [x] Start vote timer via `start_timer()`
- [x] Implement `_on_vote_timeout()` callback
- [x] Timer expires after 60 seconds

### Task 5: Update Round Timer Expiry (AC: 3)
- [x] Implement `_on_round_timer_expired()`
- [x] Auto-transitions to VOTE phase (FR30)

### Task 6: Add WebSocket Handler (AC: 1, 4)
- [x] Add `call_vote` message type handler
- [x] Verify player is in game
- [x] Call `game_state.call_vote()`
- [x] Broadcast state on success

### Task 7: Update State (AC: 2, 6)
- [x] VOTE phase state in `get_state()`
- [x] Timer info included

### Task 8: Update Frontend (AC: 1, 6)
- [x] CALL VOTE button in player.html
- [x] `handleCallVote()` sends call_vote message
- [x] Button disabled while processing

### Task 9: Write Tests (AC: All)
- [x] `test_call_vote_success`
- [x] `test_call_vote_invalid_phase`
- [x] `test_call_vote_cancels_round_timer`
- [x] `test_call_vote_starts_vote_timer`
- [x] `test_call_vote_race_condition`

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_call_vote_success(game_state_in_questioning):
    """Test successful vote call from QUESTIONING phase."""
    success, error = game_state_in_questioning.call_vote("Alice")

    assert success is True
    assert error is None
    assert game_state_in_questioning.phase == GamePhase.VOTE
    assert game_state_in_questioning.vote_caller == "Alice"
    assert "vote" in game_state_in_questioning._timers

@pytest.mark.asyncio
async def test_call_vote_invalid_phase(game_state):
    """Test vote call fails from non-QUESTIONING phase."""
    game_state.phase = GamePhase.LOBBY

    success, error = game_state.call_vote("Alice")

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert game_state.phase == GamePhase.LOBBY

@pytest.mark.asyncio
async def test_call_vote_cancels_round_timer(game_state_in_questioning):
    """Test round timer is cancelled when vote is called."""
    # Start round timer
    await game_state_in_questioning.start_round_timer()
    assert "round" in game_state_in_questioning._timers

    # Call vote
    success, _ = game_state_in_questioning.call_vote("Alice")
    assert success

    # Round timer should be cancelled
    assert "round" not in game_state_in_questioning._timers or \
           game_state_in_questioning._timers["round"].cancelled()

@pytest.mark.asyncio
async def test_simultaneous_vote_calls(game_state_in_questioning):
    """Test only first vote call is processed."""
    # First call succeeds
    success1, _ = game_state_in_questioning.call_vote("Alice")
    assert success1 is True
    assert game_state_in_questioning.phase == GamePhase.VOTE

    # Second call fails (already in VOTE phase)
    success2, error2 = game_state_in_questioning.call_vote("Bob")
    assert success2 is False
    assert error2 == ERR_INVALID_PHASE

    # Caller should be Alice, not Bob
    assert game_state_in_questioning.vote_caller == "Alice"

@pytest.mark.asyncio
async def test_round_timer_auto_triggers_vote(game_state_in_questioning):
    """Test round timer expiry auto-triggers vote (FR30)."""
    game_state_in_questioning.round_duration = 0.1  # Fast for testing

    await game_state_in_questioning.start_round_timer()

    # Wait for timer to expire
    await asyncio.sleep(0.2)

    # Should have transitioned to VOTE
    assert game_state_in_questioning.phase == GamePhase.VOTE
    assert game_state_in_questioning.vote_caller == "[TIMER]"

def test_get_state_includes_vote_data(game_state_in_vote):
    """Test get_state includes vote phase information."""
    game_state_in_vote.vote_caller = "Alice"
    game_state_in_vote.vote_time_remaining = 45

    state = game_state_in_vote.get_state()

    assert state["phase"] == "VOTE"
    assert state["vote_caller"] == "Alice"
    assert state["timer"]["remaining"] == 45
    assert state["timer"]["name"] == "vote"
    assert "votes_submitted" in state
    assert "votes_required" in state
```

### Manual Testing Checklist

**Scenario 1: Manual Vote Call**
- [ ] Player taps "CALL VOTE" during QUESTIONING
- [ ] Button shows "Calling Vote..." briefly
- [ ] Phase transitions to VOTE
- [ ] All players see "[Player] called for a vote!"
- [ ] Round timer disappears
- [ ] Vote timer (60s) starts

**Scenario 2: Timer Auto-Vote**
- [ ] Let round timer run to 0:00
- [ ] Phase auto-transitions to VOTE
- [ ] All players see "Time's up! Voting has begun."
- [ ] Vote timer (60s) starts

**Scenario 3: Simultaneous Vote Calls**
- [ ] Two players tap "CALL VOTE" at same time
- [ ] Only one player shown as vote caller
- [ ] No errors displayed
- [ ] Phase transitions once only

**Scenario 4: Vote Button States**
- [ ] Button enabled during QUESTIONING
- [ ] Button disabled after clicking
- [ ] Button not visible during VOTE phase
- [ ] Error shown if clicked in wrong phase

**Scenario 5: Timer Transition**
- [ ] Round timer cancelled on vote
- [ ] Vote timer starts at 60s
- [ ] Vote timer counts down
- [ ] Urgency styling at < 10s

---

## Definition of Done

- [ ] Call vote transitions from QUESTIONING to VOTE
- [ ] Round timer cancelled on transition
- [ ] Vote timer (60s) starts
- [ ] Vote caller attribution in state
- [ ] Phase guard prevents invalid calls
- [ ] Simultaneous calls handled correctly
- [ ] Auto-vote on round timer expiry (FR30)
- [ ] Frontend button disables during processing
- [ ] Vote caller notification displayed
- [ ] Constants in const.py
- [ ] Logging includes caller context
- [ ] All unit tests pass
- [ ] Manual testing completed
- [ ] No console errors

---

## Dependencies

### Depends On
- **Story 4.1**: Transition to Questioning Phase
- **Story 4.2**: Round Timer (provides timer infrastructure)
- **Story 4.3**: Turn Management (shares phase)
- **Story 4.4**: Role View (shares screen)

### Enables
- **Story 5.1**: Voting Phase UI (provides VOTE phase entry point)
- **Story 5.2**: Confidence Betting
- **Story 5.3**: Vote Submission

---

## Architecture Decisions Referenced

- **ARCH-9**: Named timer dictionary
- **ARCH-10**: Timer types (vote = 60s)
- **ARCH-11**: Cancel before starting new timer
- **ARCH-12**: Message format with snake_case
- **ARCH-14**: Broadcast after mutations
- **ARCH-17**: Phase guards
- **ARCH-19**: Return pattern `(bool, str | None)`

---

## Edge Cases to Handle

### 1. Player Disconnects While Vote Called
- Vote still triggers for remaining players
- Disconnected player marked as abstain if they don't reconnect in time

### 2. Host Disconnects During Vote
- Game pauses (PAUSED phase per ARCH-5)
- Vote timer pauses
- Resume when host reconnects

### 3. All Players Abstain
- Timer expires with no votes
- Transition to REVEAL
- "No votes cast" message displayed
- No conviction (round ends without spy reveal)

### 4. Vote Called at Timer Expiry
- Check for race condition
- First event processed (vote call or timer)
- State machine prevents double transition

---

## Notes

### Race Condition Prevention

The phase guard in `call_vote()` naturally handles race conditions:
- First request transitions phase to VOTE
- Second request sees VOTE phase
- Second request returns `ERR_INVALID_PHASE`

No explicit locking needed in single-threaded asyncio.

### Timer Attribution

The `[TIMER]` attribution for auto-vote distinguishes between:
- Player-initiated vote: Shows player name
- Timer-initiated vote: Shows "Time's up!" message

This improves UX by clarifying what triggered the vote.

### Button State Management

The vote button is:
1. **Enabled** during QUESTIONING phase
2. **Disabled + loading text** while processing
3. **Hidden** in other phases

This prevents double-clicks and provides clear feedback.

---

## Dev Agent Record

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/const.py` | Pre-existing | TIMER_VOTE, VOTE_TIMER_DURATION constants |
| `custom_components/spyster/game/state.py` | Pre-existing | `call_vote()`, `_on_vote_timeout()`, `_on_round_timer_expired()` methods |
| `custom_components/spyster/server/websocket.py` | Pre-existing | `_handle_call_vote()` handler |
| `custom_components/spyster/www/player.html` | Pre-existing | CALL VOTE button |
| `custom_components/spyster/www/js/player.js` | Pre-existing | `handleCallVote()` method |
| `tests/test_state.py` | Pre-existing | 5 call_vote tests (lines 1709-1805) |

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2025-12-23 | Story verification | Confirmed all tasks already implemented |

### Review Notes

- **Code Review Date:** 2025-12-23
- **Reviewer:** Amelia (Dev Agent)
- **Outcome:** APPROVED with fixes
- **Fix Applied:** Implemented AC6 (Vote Caller Attribution) - added vote_caller field, updated call_vote() to accept caller_name parameter, updated get_state() to include vote_caller in VOTE phase, added 3 new tests
