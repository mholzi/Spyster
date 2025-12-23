# Story 5.5: Vote Timer and Abstain Handling

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.5
**Status:** ready-for-dev
**Priority:** High
**Complexity:** Low

---

## User Story

As a **player**,
I want **to see how much time remains to vote**,
So that **I can make my decision in time or abstain by choice**.

---

## Acceptance Criteria

### AC1: Timer Display

**Given** the game is in VOTE phase
**When** viewing the screen
**Then** a countdown timer shows seconds remaining
**And** timer syncs with server time (±1 second accuracy per NFR5)

### AC2: Timer Urgency States

**Given** the vote timer is running
**When** time remaining drops
**Then** visual urgency increases:
- Normal: > 20 seconds (no special styling)
- Warning: 10-20 seconds (yellow glow)
- Urgent: < 10 seconds (red glow + animation per UX-8)

### AC3: Abstain Handling

**Given** a player does NOT vote before timer expires
**When** the timer reaches 0:00
**Then** they are marked as "abstain" automatically
**And** their vote counts as null (no target, no confidence)

### AC4: Abstain Option (MVP)

**Given** a player wants to abstain
**When** they don't make a selection
**Then** the system handles abstention on timer expiry (no explicit abstain button for MVP)

### AC5: Timer Expiry Transition

**Given** the vote timer expires
**When** transition occurs
**Then** all non-voters are marked abstain (FR36)
**And** transition to REVEAL phase begins

---

## Requirements Coverage

### Functional Requirements

- **FR30**: Voting ends when timer expires OR all players have submitted
- **FR36**: Players can abstain from voting (no points won or lost)

### Non-Functional Requirements

- **NFR5**: Timer accuracy within ±1 second across clients

### UX Requirements

- **UX-8**: Urgency states: < 10s = red glow + pulse animation

### Architectural Requirements

- **ARCH-9**: Named timer dictionary pattern
- **ARCH-10**: Vote timer = 60 seconds
- **ARCH-11**: Cancel timer before starting new one
- **ARCH-14**: Broadcast state after mutations

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Most timer logic is already implemented in Story 4.5. This story enhances:

```python
class GameState:
    async def _on_vote_timeout(self, timer_name: str) -> None:
        """
        Handle vote timer expiration (Story 5.5 enhancement).

        Non-voters are automatically marked as abstain.
        Transition to REVEAL phase.
        """
        from ..const import VOTE_TIMER_DURATION

        _LOGGER.info("Vote timer expired - processing abstentions")

        # Mark non-voters as abstain (AC3)
        connected_players = [
            p.name for p in self.players.values() if p.connected
        ]

        for player_name in connected_players:
            if player_name not in self.votes:
                # Check if this is the spy who guessed
                if self.spy_guess and player_name == self._spy_name:
                    continue  # Spy guessed, not abstaining

                self.votes[player_name] = {
                    "target": None,
                    "confidence": 0,
                    "abstained": True,
                    "timestamp": time.time(),
                }
                _LOGGER.info("Player %s abstained (timeout)", player_name)

        votes_cast = len([v for v in self.votes.values() if not v.get("abstained")])
        abstentions = len([v for v in self.votes.values() if v.get("abstained")])

        _LOGGER.info(
            "Vote phase complete: %d voted, %d abstained",
            votes_cast,
            abstentions
        )

        # Transition to REVEAL
        self.phase = GamePhase.REVEAL

    def get_vote_timer_state(self) -> dict:
        """Get vote timer state for frontend display."""
        if "vote" not in self._timers or self._timers["vote"].done():
            return {
                "name": "vote",
                "remaining": 0,
                "total": VOTE_TIMER_DURATION,
                "expired": True,
            }

        remaining = self._get_timer_remaining("vote")
        return {
            "name": "vote",
            "remaining": int(remaining),
            "total": VOTE_TIMER_DURATION,
            "expired": False,
        }
```

#### 2. Player Display Logic (`www/js/player.js`)

Enhance timer display with urgency states:

```javascript
class PlayerDisplay {
    updateVoteTimer(timeRemaining) {
        const timerEl = document.getElementById('vote-timer');
        if (!timerEl) return;

        // Format as M:SS
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        // Get timer container for styling
        const timerDisplay = timerEl.closest('.timer-display');
        if (!timerDisplay) return;

        // Remove all urgency classes first
        timerDisplay.classList.remove('timer-normal', 'timer-warning', 'timer-urgent');

        // Apply urgency state (AC2)
        if (timeRemaining > 20) {
            timerDisplay.classList.add('timer-normal');
        } else if (timeRemaining > 10) {
            timerDisplay.classList.add('timer-warning');
        } else {
            timerDisplay.classList.add('timer-urgent');
        }

        // Update ARIA for screen readers
        timerEl.setAttribute('aria-valuenow', timeRemaining);

        // Announce urgency changes
        if (timeRemaining === 20) {
            this.announceToScreenReader('20 seconds remaining');
        } else if (timeRemaining === 10) {
            this.announceToScreenReader('10 seconds remaining - hurry!');
        } else if (timeRemaining === 5) {
            this.announceToScreenReader('5 seconds!');
        }
    }

    announceToScreenReader(message) {
        const announcer = document.getElementById('sr-announcer');
        if (announcer) {
            announcer.textContent = message;
        }
    }

    onStateUpdate(state) {
        // ... existing code ...

        // Update timer
        if (state.timer && state.timer.name === 'vote') {
            this.updateVoteTimer(state.timer.remaining);
        }

        // Handle timer expiry locally
        if (state.timer && state.timer.remaining <= 0 && !this.hasVoted) {
            this.showAbstainNotification();
        }
    }

    showAbstainNotification() {
        const notification = document.getElementById('vote-notification');
        if (notification) {
            notification.textContent = 'Time expired - you abstained from voting';
            notification.classList.add('notification--warning');
            notification.style.display = 'block';
        }
    }
}
```

#### 3. CSS Styles (`www/css/styles.css`)

Add timer urgency styles:

```css
/* =================================
   VOTE TIMER DISPLAY
   ================================= */

.timer-display {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-border);
    transition: all 0.3s ease;
}

#vote-timer {
    font-size: 32px;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-primary);
}

/* =================================
   TIMER URGENCY STATES (AC2)
   ================================= */

/* Normal state (> 20s) */
.timer-normal {
    border-color: var(--color-border);
    background: var(--color-bg-tertiary);
}

/* Warning state (10-20s) */
.timer-warning {
    border-color: var(--color-warning);
    background: rgba(255, 200, 0, 0.1);
    box-shadow: 0 0 15px rgba(255, 200, 0, 0.3);
}

.timer-warning #vote-timer {
    color: var(--color-warning);
}

/* Urgent state (< 10s) - UX-8 */
.timer-urgent {
    border-color: var(--color-danger);
    background: rgba(255, 50, 50, 0.15);
    box-shadow: 0 0 20px rgba(255, 50, 50, 0.4);
    animation: pulse-urgent 0.5s ease-in-out infinite;
}

.timer-urgent #vote-timer {
    color: var(--color-danger);
    animation: pulse-text 0.5s ease-in-out infinite;
}

@keyframes pulse-urgent {
    0%, 100% {
        box-shadow: 0 0 20px rgba(255, 50, 50, 0.4);
    }
    50% {
        box-shadow: 0 0 30px rgba(255, 50, 50, 0.6);
    }
}

@keyframes pulse-text {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.7;
    }
}

/* =================================
   CSS VARIABLES FOR COLORS
   ================================= */

:root {
    /* Existing variables... */
    --color-warning: #ffc800;
    --color-danger: #ff3232;
}

/* =================================
   ABSTAIN NOTIFICATION
   ================================= */

.notification--warning {
    border-color: var(--color-warning);
    background: rgba(255, 200, 0, 0.1);
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    .timer-urgent {
        animation: none;
        box-shadow: 0 0 20px rgba(255, 50, 50, 0.4);
    }

    .timer-urgent #vote-timer {
        animation: none;
    }
}

/* =================================
   SCREEN READER ANNOUNCER
   ================================= */

#sr-announcer {
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}
```

#### 4. Player Display HTML (`www/player.html`)

Add screen reader announcer:

```html
<!-- Screen reader live region -->
<div id="sr-announcer" aria-live="assertive" aria-atomic="true"></div>
```

---

## Implementation Tasks

### Task 1: Enhance Timer Expiry Handler (AC: 3, 5)
- [x] Mark non-voters as abstain
- [x] Skip spy if they guessed location
- [x] Log vote/abstain counts
- [x] Transition to REVEAL

### Task 2: Implement Timer Display (AC: 1)
- [x] Format time as M:SS
- [x] Sync with server time
- [x] Update ARIA attributes

### Task 3: Add Urgency States (AC: 2)
- [x] Normal state (> 20s)
- [x] Warning state (10-20s) - yellow
- [x] Urgent state (< 10s) - red + pulse

### Task 4: Add CSS Animations (AC: 2)
- [x] Pulse animation for urgent state
- [x] Color transitions
- [x] Respect reduced motion

### Task 5: Handle Abstain Notification (AC: 3, 4)
- [x] Show abstain message on timeout
- [x] Appropriate styling

### Task 6: Add Accessibility
- [x] Screen reader announcer
- [x] Announce urgency thresholds
- [x] ARIA live regions

### Task 7: Write Tests
- [ ] test_abstain_on_timeout
- [ ] test_timer_accuracy

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_abstain_on_timeout(game_state_in_vote):
    """Test non-voters marked as abstain on timer expiry."""
    # Only one player votes
    players = list(game_state_in_vote.players.keys())
    game_state_in_vote.record_vote(players[0], players[1], 1)

    # Simulate timer expiry
    await game_state_in_vote._on_vote_timeout("vote")

    # All other players should be abstained
    for player_name in players[1:]:
        assert player_name in game_state_in_vote.votes
        vote = game_state_in_vote.votes[player_name]
        if player_name != players[0]:
            assert vote.get("abstained") is True
            assert vote.get("target") is None
            assert vote.get("confidence") == 0

def test_abstain_does_not_include_spy_guess(game_state_in_vote_with_spy):
    """Test spy who guessed is not marked as abstain."""
    spy_name = game_state_in_vote_with_spy._spy_name

    # Spy guesses location
    game_state_in_vote_with_spy.record_spy_guess(spy_name, "beach")

    # Simulate timer expiry
    await game_state_in_vote_with_spy._on_vote_timeout("vote")

    # Spy should not be in votes dict (they guessed instead)
    if spy_name in game_state_in_vote_with_spy.votes:
        assert game_state_in_vote_with_spy.votes[spy_name].get("abstained") is False
```

### Manual Testing Checklist

**Scenario 1: Timer Display**
- [ ] Timer shows 1:00 at vote phase start
- [ ] Timer counts down smoothly
- [ ] Time synced with server (±1 second)

**Scenario 2: Urgency States**
- [ ] Normal styling > 20 seconds
- [ ] Yellow glow at 20 seconds
- [ ] Red glow + pulse at 10 seconds
- [ ] Animation continues until 0

**Scenario 3: Abstain Handling**
- [ ] Don't vote, wait for timer
- [ ] Abstain notification shown
- [ ] Marked as abstain in results

**Scenario 4: Reduced Motion**
- [ ] Enable prefers-reduced-motion
- [ ] Animations disabled
- [ ] Urgency colors still visible

---

## Definition of Done

- [x] Timer displays countdown in M:SS format
- [x] Timer syncs with server (±1 second)
- [x] Normal state styling (> 20s)
- [x] Warning state styling (10-20s)
- [x] Urgent state with pulse animation (< 10s)
- [x] Non-voters marked as abstain on expiry
- [x] Screen reader announcements at thresholds
- [x] Respects reduced motion preference
- [ ] Unit tests pass
- [x] No console errors

---

## Dependencies

### Depends On
- **Story 4.5**: Call Vote Functionality (vote timer infrastructure)
- **Story 5.3**: Vote Submission and Tracking (vote recording)

### Enables
- **Story 5.6**: Vote and Bet Reveal Sequence
- **Story 6.2**: Vote Scoring (handles abstain = 0 points)

---

## Architecture Decisions Referenced

- **ARCH-9**: Named timer dictionary
- **ARCH-10**: Vote timer = 60 seconds
- **ARCH-11**: Timer cancellation before restart
- **ARCH-14**: Broadcast after mutations
- **UX-8**: Urgency states (< 10s = red + pulse)
- **NFR5**: Timer accuracy ±1 second

---

## Dev Notes

### Timer Sync Strategy

Server sends `timer.remaining` in state updates. Client uses this to sync:

```javascript
// On state update
if (state.timer) {
    this.serverTimeRemaining = state.timer.remaining;
    this.lastSyncTime = Date.now();
}

// On render tick
function getDisplayTime() {
    const elapsed = (Date.now() - this.lastSyncTime) / 1000;
    return Math.max(0, Math.round(this.serverTimeRemaining - elapsed));
}
```

### Abstain vs No Vote

- **Abstain**: Player chose not to vote (or timed out)
- **No target**: `target: null, confidence: 0`
- **Scoring**: 0 points for abstain (no win, no loss)

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/game/state.py` | Modify | Enhance _on_vote_timeout |
| `custom_components/spyster/www/js/player.js` | Modify | Add timer urgency logic |
| `custom_components/spyster/www/css/styles.css` | Modify | Add urgency state styles |
| `custom_components/spyster/www/player.html` | Modify | Add sr-announcer element |
| `tests/test_state.py` | Modify | Add abstain tests |

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Completion Notes List
_To be filled during implementation_

### File List
_To be filled during implementation_
