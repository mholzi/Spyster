# Story 4.2: Round Timer with Countdown

**Epic:** Epic 4 - Questioning Phase
**Story ID:** 4.2
**Status:** Done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to see the round timer counting down**,
So that **I know how much time remains before voting**.

---

## Acceptance Criteria

### AC1: Timer Initialization
**Given** the game is in QUESTIONING phase
**When** the phase begins
**Then** a named timer `round` starts with the configured duration
**And** the timer is registered in `self._timers` dictionary (per ARCH-9)
**And** any existing `round` timer is cancelled first (per ARCH-11)

### AC2: Real-Time Display
**Given** the round timer is running
**When** players view their screens
**Then** the remaining time is displayed prominently (large, visible)
**And** the timer updates in real-time (synced across all clients)
**And** the display format is MM:SS (e.g., "07:00", "03:45", "00:30")

### AC3: Auto-Transition on Expiry
**Given** the round timer reaches zero
**When** the timer expires
**Then** the voting phase is automatically triggered
**And** a `vote` transition occurs without player action (per FR30)
**And** the `round` timer is removed from `self._timers`

### AC4: Timer Accuracy
**Given** a timer is displayed
**When** the accuracy is measured
**Then** the timer is accurate to ±1 second across all clients (per NFR5)
**And** all players see synchronized countdown values

---

## Technical Requirements

### Architecture Compliance
- **ARCH-9**: Named timer dictionary pattern: `self._timers: dict[str, asyncio.Task]`
- **ARCH-10**: Timer types - round (configurable, default 7 min)
- **ARCH-11**: Cancel existing timer before starting new one with same name
- **ARCH-14**: Broadcast state after every state mutation

### Non-Functional Requirements
- **NFR5**: Timer Accuracy - Round/voting timers accurate to ±1 second

### Dependencies
- Story 4.1: Transition to Questioning Phase (must be complete)
- Story 3.1: Game Configuration UI (for round duration config)

---

## Implementation Guidance

### Backend Changes

#### 1. `game/state.py` - Timer Management

**Add timer infrastructure:**
```python
class GameState:
    def __init__(self):
        # ... existing init ...
        self._timers: dict[str, asyncio.Task] = {}  # ARCH-9
        self._timer_start_times: dict[str, float] = {}  # For accuracy
        self._timer_durations: dict[str, float] = {}  # For remaining calc

    def _cancel_timer(self, timer_name: str) -> None:
        """Cancel a named timer if it exists (ARCH-11)."""
        if timer_name in self._timers:
            self._timers[timer_name].cancel()
            del self._timers[timer_name]
            if timer_name in self._timer_start_times:
                del self._timer_start_times[timer_name]
            if timer_name in self._timer_durations:
                del self._timer_durations[timer_name]
            _LOGGER.info("Timer cancelled: %s", timer_name)

    def _get_timer_remaining(self, timer_name: str) -> float:
        """Get remaining time for a named timer in seconds."""
        if timer_name not in self._timer_start_times:
            return 0.0

        elapsed = time.time() - self._timer_start_times[timer_name]
        duration = self._timer_durations[timer_name]
        remaining = max(0.0, duration - elapsed)
        return remaining

    async def _start_round_timer(self, duration: float) -> None:
        """Start the round countdown timer (ARCH-10)."""
        # Cancel existing round timer (ARCH-11)
        self._cancel_timer("round")

        # Record start time and duration
        self._timer_start_times["round"] = time.time()
        self._timer_durations["round"] = duration

        async def timer_task():
            try:
                await asyncio.sleep(duration)
                # Timer expired - auto-trigger vote (FR30)
                _LOGGER.info("Round timer expired - auto-triggering vote")
                await self.transition_to_vote()
            except asyncio.CancelledError:
                _LOGGER.info("Round timer cancelled")

        self._timers["round"] = asyncio.create_task(timer_task())
        _LOGGER.info("Round timer started: %d seconds", duration)

    async def transition_to_questioning(self) -> None:
        """Transition from ROLES to QUESTIONING phase."""
        if self.phase != GamePhase.ROLES:
            raise ValueError(f"Cannot transition to QUESTIONING from {self.phase}")

        self.phase = GamePhase.QUESTIONING

        # Start round timer with configured duration (ARCH-10)
        round_duration = self.config.get("round_duration", 420)  # Default 7 min
        await self._start_round_timer(round_duration)

        _LOGGER.info("Phase transition: ROLES -> QUESTIONING (timer: %ds)", round_duration)
```

**Update `get_state()` to include timer:**
```python
def get_state(self, for_player: str | None = None) -> dict:
    """Get game state with optional per-player filtering."""
    state = {
        "phase": self.phase.value,
        "round": self.current_round,
        "total_rounds": self.config.get("total_rounds", 5),
    }

    # Add timer info for QUESTIONING and VOTE phases
    if self.phase == GamePhase.QUESTIONING:
        state["timer"] = {
            "name": "round",
            "remaining": self._get_timer_remaining("round"),
            "total": self._timer_durations.get("round", 0),
        }

    # ... rest of get_state implementation ...

    return state
```

#### 2. `server/websocket.py` - Timer Broadcasts

**Add periodic timer updates:**
```python
class SpysterWebSocketHandler:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self._timer_broadcast_task: asyncio.Task | None = None

    async def start_timer_broadcasts(self) -> None:
        """Broadcast timer updates every second for accuracy (NFR5)."""
        async def broadcast_loop():
            while True:
                await asyncio.sleep(1.0)  # Update every second

                # Only broadcast if in a timed phase
                if self.game_state.phase in [GamePhase.QUESTIONING, GamePhase.VOTE]:
                    await self.broadcast_state()

        if self._timer_broadcast_task:
            self._timer_broadcast_task.cancel()

        self._timer_broadcast_task = asyncio.create_task(broadcast_loop())

    async def stop_timer_broadcasts(self) -> None:
        """Stop periodic timer broadcasts."""
        if self._timer_broadcast_task:
            self._timer_broadcast_task.cancel()
            self._timer_broadcast_task = None
```

**Start broadcasts on QUESTIONING transition:**
```python
async def handle_admin_action(self, action: str) -> dict:
    """Handle host admin actions."""
    if action == "start_questioning":
        await self.game_state.transition_to_questioning()
        await self.start_timer_broadcasts()  # Start periodic updates
        await self.broadcast_state()
        return {"success": True}
```

### Frontend Changes

#### 3. `www/js/player.js` - Timer Display

**Add timer rendering:**
```javascript
class SpysterPlayerUI {
    handleStateUpdate(state) {
        // ... existing phase handling ...

        if (state.phase === "QUESTIONING") {
            this.renderQuestioningPhase(state);
        }
    }

    renderQuestioningPhase(state) {
        const container = document.getElementById("game-container");

        // Render timer prominently
        const timerHtml = state.timer ?
            this.renderTimer(state.timer.remaining) : '';

        container.innerHTML = `
            <div class="questioning-phase">
                ${timerHtml}
                <div class="role-reminder">
                    <!-- Role info from Story 4.4 -->
                </div>
                <div class="qa-display">
                    <!-- Q&A info from Story 4.3 -->
                </div>
                <button class="btn-call-vote">Call Vote</button>
            </div>
        `;

        // Store timer interval for updates
        this.startTimerUpdates(state.timer);
    }

    renderTimer(remainingSeconds) {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = Math.floor(remainingSeconds % 60);
        const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        return `
            <div class="timer-display ${this.getTimerClass(remainingSeconds)}">
                <div class="timer-label">Time Remaining</div>
                <div class="timer-value">${this.escapeHtml(display)}</div>
            </div>
        `;
    }

    getTimerClass(remainingSeconds) {
        if (remainingSeconds <= 30) return 'timer-critical';
        if (remainingSeconds <= 60) return 'timer-warning';
        return 'timer-normal';
    }

    startTimerUpdates(timerData) {
        // Clear any existing interval
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }

        // Server broadcasts every second, so we just update display
        // No local countdown needed - server is source of truth (NFR5)
    }
}
```

#### 4. `www/css/styles.css` - Timer Styling

**Add prominent timer styles:**
```css
/* Timer Display - Large and Visible */
.timer-display {
    text-align: center;
    padding: 2rem;
    margin-bottom: 2rem;
    border-radius: 16px;
    background: var(--color-surface-secondary);
    border: 2px solid var(--color-accent-secondary);
}

.timer-label {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-text-secondary);
    margin-bottom: 0.5rem;
}

.timer-value {
    font-size: 72px;
    font-weight: 700;
    font-family: monospace;
    color: var(--color-accent-secondary);
    line-height: 1;
}

/* Timer States - Visual Urgency */
.timer-warning .timer-value {
    color: var(--color-warning, #ffa500);
}

.timer-critical .timer-value {
    color: var(--color-accent-primary);
    animation: pulse-timer 1s ease-in-out infinite;
}

@keyframes pulse-timer {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(1.05); }
}

/* Responsive - Even Larger on Host Display */
@media (min-width: 768px) {
    .timer-value {
        font-size: 144px;  /* 2x scale for host/TV */
    }
}
```

---

## Testing Strategy

### Unit Tests (`tests/test_state.py`)

```python
import pytest
import asyncio
from custom_components.spyster.game.state import GameState, GamePhase

class TestRoundTimer:
    @pytest.mark.asyncio
    async def test_round_timer_starts_on_questioning(self):
        """AC1: Timer starts when QUESTIONING phase begins."""
        game = GameState()
        game.phase = GamePhase.ROLES
        game.config = {"round_duration": 420}

        await game.transition_to_questioning()

        assert "round" in game._timers
        assert "round" in game._timer_start_times
        assert game._timer_durations["round"] == 420

    @pytest.mark.asyncio
    async def test_round_timer_cancels_existing(self):
        """AC1: Existing timer is cancelled before starting new one (ARCH-11)."""
        game = GameState()
        game.phase = GamePhase.ROLES

        # Start first timer
        await game.transition_to_questioning()
        first_timer = game._timers["round"]

        # Start second timer (simulating new round)
        game.phase = GamePhase.ROLES
        await game.transition_to_questioning()

        assert first_timer.cancelled()
        assert "round" in game._timers
        assert game._timers["round"] != first_timer

    @pytest.mark.asyncio
    async def test_timer_remaining_accuracy(self):
        """AC4: Timer remaining calculation is accurate."""
        game = GameState()
        game._timer_start_times["round"] = time.time() - 10  # 10 seconds elapsed
        game._timer_durations["round"] = 60

        remaining = game._get_timer_remaining("round")

        # Should be ~50 seconds remaining (60 - 10)
        assert 49 <= remaining <= 51

    @pytest.mark.asyncio
    async def test_timer_auto_transitions_to_vote(self):
        """AC3: Timer expiry triggers vote transition (FR30)."""
        game = GameState()
        game.phase = GamePhase.ROLES
        game.config = {"round_duration": 0.1}  # 100ms for fast test

        await game.transition_to_questioning()
        await asyncio.sleep(0.2)  # Wait for timer to expire

        assert game.phase == GamePhase.VOTE
        assert "round" not in game._timers

    def test_get_state_includes_timer_in_questioning(self):
        """AC2: get_state() includes timer data during QUESTIONING."""
        game = GameState()
        game.phase = GamePhase.QUESTIONING
        game._timer_start_times["round"] = time.time()
        game._timer_durations["round"] = 420

        state = game.get_state()

        assert "timer" in state
        assert state["timer"]["name"] == "round"
        assert state["timer"]["total"] == 420
        assert 0 <= state["timer"]["remaining"] <= 420
```

### Integration Tests

**Manual Testing Checklist:**

1. **Timer Start:**
   - [ ] Start game and assign roles
   - [ ] Verify timer starts immediately when QUESTIONING phase begins
   - [ ] Verify timer shows configured duration (default 7:00)

2. **Real-Time Updates:**
   - [ ] Open game on 3 different devices
   - [ ] Verify all timers count down in sync
   - [ ] Check accuracy is within ±1 second across devices (NFR5)

3. **Auto-Transition:**
   - [ ] Let timer run to 00:00 without calling vote
   - [ ] Verify game automatically transitions to VOTE phase
   - [ ] Verify no manual action is required (FR30)

4. **Visual Display:**
   - [ ] Verify timer is large and easily readable
   - [ ] Check timer changes color when < 60 seconds (warning)
   - [ ] Check timer pulses when < 30 seconds (critical)

---

## Definition of Done

- [ ] Backend: `_start_round_timer()` method implemented in `game/state.py`
- [ ] Backend: Timer cancellation logic (ARCH-11) implemented
- [ ] Backend: `get_state()` includes timer data for QUESTIONING phase
- [ ] Backend: Auto-transition to VOTE on timer expiry (FR30)
- [ ] Backend: Periodic state broadcasts every second for accuracy
- [ ] Frontend: Timer display component in `player.js`
- [ ] Frontend: MM:SS format rendering
- [ ] Frontend: Timer styling with warning/critical states in `styles.css`
- [ ] Tests: Unit tests pass (5+ tests covering all scenarios)
- [ ] Tests: Integration test confirms ±1 second accuracy (NFR5)
- [ ] Tests: Manual test confirms synchronized display across devices
- [ ] Code Review: ADVERSARIAL review completed
- [ ] Documentation: Implementation summary created
- [ ] Status: Story marked as `done` in `sprint-status.yaml`

---

## Dependencies

### Depends On (Must Complete First)
- **Story 4.1**: Transition to Questioning Phase - provides phase transition mechanism
- **Story 3.1**: Game Configuration UI - provides round_duration config

### Enables (Can Start After This)
- **Story 4.3**: Questioner/Answerer Turn Management - shares QUESTIONING phase UI
- **Story 4.4**: Player Role View During Questioning - shares screen with timer
- **Story 4.5**: Call Vote Functionality - cancels timer when vote is called

---

## Architecture Decisions Referenced

- **ARCH-9**: Named timer dictionary pattern
- **ARCH-10**: Timer types and default durations
- **ARCH-11**: Cancel existing timer before starting new one
- **ARCH-14**: Broadcast state after mutations
- **ARCH-16**: Logging format for timer events

---

## Non-Functional Requirements

- **NFR5**: Timer Accuracy - ±1 second across all clients
  - **Implementation**: Server is source of truth, broadcasts every second
  - **Validation**: Multi-device synchronization test

---

## Edge Cases to Handle

1. **Host Disconnect During Timer:**
   - Transition to PAUSED phase (ARCH-5)
   - Preserve timer state for resume

2. **Player Disconnect During Timer:**
   - Timer continues for remaining players
   - Reconnected player receives current timer state

3. **Vote Called Before Timer Expires:**
   - Cancel round timer (Story 4.5)
   - Transition to VOTE immediately

4. **Timer Drift Over Long Rounds:**
   - Server calculates remaining time from start timestamp
   - Prevents cumulative drift from repeated updates

5. **Browser Tab Inactive:**
   - WebSocket continues receiving updates
   - Timer updates when tab regains focus
   - No client-side countdown prevents accuracy issues

---

## Implementation Notes

### Common Pitfalls to Avoid
- **Don't use client-side countdown**: Server is source of truth for accuracy (NFR5)
- **Don't forget to cancel timer**: Must cancel on vote call or phase change (ARCH-11)
- **Don't hardcode duration**: Use configured value from GameState (ARCH-15)
- **Don't skip broadcasts**: Real-time sync requires periodic updates (every 1s)

### Best Practices
- Use `asyncio.Task` for timer management (ARCH-9)
- Store start time + duration for accurate remaining calculation
- Log all timer events (start, cancel, expire) with context (ARCH-16)
- Broadcast state immediately after phase transition (ARCH-14)
- Handle `asyncio.CancelledError` gracefully in timer tasks

---

## Estimated Effort

- **Backend Implementation**: 3-4 hours
- **Frontend Implementation**: 2-3 hours
- **Testing**: 2 hours
- **Total**: 7-9 hours

---

## Notes for Developer

This is a foundational story for the Questioning Phase. The timer system established here will be reused for:
- Vote timer (60s, Story 5.5)
- Role display timer (5s, Story 3.5)
- Reveal delay (3s, Story 5.6)
- Disconnect timers (Stories 2.4, 2.5)

Pay special attention to:
1. **Accuracy**: Server-side time calculation prevents drift
2. **Synchronization**: All clients must see same countdown
3. **Cancellation**: Clean up timers on phase transitions
4. **Auto-transition**: FR30 requires no manual action at timer expiry

The pattern established here (named timers, periodic broadcasts, accurate remaining calculation) is critical for the entire game experience.

---

**Ready for Implementation** - All dependencies clear, acceptance criteria well-defined.
