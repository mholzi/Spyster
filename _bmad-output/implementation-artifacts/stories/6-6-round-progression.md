# Story 6.6: Round Progression

**Epic:** Epic 6 - Scoring & Game Progression
**Story ID:** 6.6
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **system**,
I want **to advance through rounds until the configured count**,
So that **the game plays multiple rounds as configured**.

---

## Acceptance Criteria

### AC1: Transition to Next Round

**Given** the SCORING phase completes
**When** rounds remaining > 0
**Then** the game transitions to ROLES phase for next round (per FR53)
**And** new spy is assigned
**And** new location is selected

### AC2: Round Counter Display

**Given** round transitions occur
**When** displayed to players
**Then** "ROUND 2 of 5" indicator is visible
**And** round number updates correctly

### AC3: Game End Check

**Given** the configured number of rounds is reached
**When** scoring completes
**Then** the game transitions to END phase (not another round)
**And** no new spy is assigned

### AC4: State Reset Between Rounds

**Given** a new round begins
**When** transitioning from SCORING to ROLES
**Then** votes are cleared
**Then** current turn is reset
**Then** timer is reset to configured duration
**And** previous round data is preserved for history

### AC5: Location Variety

**Given** multiple rounds are played
**When** locations are selected
**Then** locations should not repeat until all are used (if possible)
**Or** random selection is used for MVP

### AC6: Spy History Tracking

**Given** spy assignments occur each round
**When** a player is selected as spy
**Then** the selection is random (may repeat per FR23)
**And** spy history is logged for debugging

---

## Requirements Coverage

### Functional Requirements

- **FR53**: System advances to next round after scoring reveal
- **FR23**: System randomly assigns spy each round (same player may be spy multiple times)
- **FR58**: System randomly selects location from chosen pack each round

### Architectural Requirements

- **ARCH-4**: Phase state machine (SCORING → ROLES or SCORING → END)
- **ARCH-6**: Spy assignment uses CSPRNG
- **ARCH-14**: Broadcast after mutations

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Add round progression methods:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        self.current_round: int = 0
        self.num_rounds: int = 5  # From config
        self.round_history: list[dict] = []  # History of past rounds

    def start_next_round(self) -> tuple[bool, str | None]:
        """
        Advance to next round (Story 6.6).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE, ERR_GAME_ENDED

        # Phase guard
        if self.phase != GamePhase.SCORING:
            return False, ERR_INVALID_PHASE

        # Check if game should end
        if self.current_round >= self.num_rounds:
            return False, ERR_GAME_ENDED

        # Save round history
        self._save_round_history()

        # Reset for new round
        self._reset_for_new_round()

        # Increment round counter
        self.current_round += 1

        # Assign new spy
        self._assign_spy()

        # Select new location
        self._select_location()

        # Transition to ROLES phase
        self.phase = GamePhase.ROLES

        _LOGGER.info(
            "Started round %d of %d",
            self.current_round,
            self.num_rounds
        )

        return True, None

    def _save_round_history(self) -> None:
        """Save current round data to history."""
        self.round_history.append({
            "round": self.current_round,
            "spy": self._spy_name,
            "location": self._current_location.get("id") if self._current_location else None,
            "convicted": self.convicted_player,
            "spy_caught": self.spy_caught,
            "scores": dict(self.round_scores),
        })

    def _reset_for_new_round(self) -> None:
        """Reset state for new round."""
        # Clear votes
        self.votes = {}
        self.vote_results = None
        self.convicted_player = None

        # Clear spy guess
        self.spy_guess = None

        # Clear round scores (cumulative stays)
        self.round_scores = {}
        self.spy_caught = False

        # Reset turn
        self._current_turn_index = 0

        # Clear timers
        self._cancel_all_timers()

    def should_end_game(self) -> bool:
        """Check if game should end after current round."""
        return self.current_round >= self.num_rounds

    def get_state(self, for_player: str | None = None) -> dict:
        # ... existing code ...

        # Add round info to all phases
        state["round_number"] = self.current_round
        state["total_rounds"] = self.num_rounds

        # In ROLES phase, include "Round X of Y" display
        if self.phase == GamePhase.ROLES:
            state["round_display"] = f"Round {self.current_round} of {self.num_rounds}"

        return state
```

#### 2. WebSocket Handler (`server/websocket.py`)

Handle round transition trigger:

```python
async def _handle_scoring_timeout(self) -> None:
    """Handle scoring phase timeout - advance to next round or end game."""
    game = self._get_game_state()

    if game.should_end_game():
        # Transition to END phase
        success, error = game.end_game()
        if success:
            await self._broadcast_state()
    else:
        # Start next round
        success, error = game.start_next_round()
        if success:
            await self._broadcast_state()
            # Start role display timer
            await self._start_timer("role_display", ROLE_DISPLAY_SECONDS)
```

#### 3. Timer for Scoring Phase

```python
# In const.py
SCORING_DISPLAY_SECONDS = 10  # Time to view leaderboard before next round

# In state.py or websocket.py
async def _on_scoring_timer_expired(self) -> None:
    """Scoring display time expired - advance game."""
    if self.game_state.should_end_game():
        self.game_state.end_game()
    else:
        self.game_state.start_next_round()
    await self._broadcast_state()
```

#### 4. Player Display Updates

```javascript
// In player.js - update handleStateUpdate
handleStateUpdate(state) {
    // ... existing code ...

    // Update round display in all phases
    this.updateRoundDisplay(state);

    // Handle phase transitions
    if (state.phase === 'ROLES' && state.round_number > 1) {
        // New round starting - show transition
        this.showRoundTransition(state);
    }
}

showRoundTransition(state) {
    // Brief "ROUND X" overlay before showing roles
    const overlay = document.createElement('div');
    overlay.className = 'round-transition-overlay';
    overlay.innerHTML = `
        <div class="round-transition-text">
            Round ${state.round_number}
        </div>
    `;
    document.body.appendChild(overlay);

    // Remove after animation
    setTimeout(() => {
        overlay.remove();
    }, 2000);
}

updateRoundDisplay(state) {
    const roundDisplays = document.querySelectorAll('.round-indicator');
    roundDisplays.forEach(el => {
        el.textContent = `Round ${state.round_number} of ${state.total_rounds}`;
    });
}
```

---

## Implementation Tasks

### Task 1: Add Round Tracking to GameState
- [ ] current_round counter
- [ ] num_rounds from config
- [ ] round_history list

### Task 2: Implement start_next_round()
- [ ] Phase guard (SCORING only)
- [ ] Check should_end_game()
- [ ] Save round history
- [ ] Reset state for new round
- [ ] Assign new spy
- [ ] Select new location
- [ ] Transition to ROLES

### Task 3: Update Timers
- [ ] Add SCORING_DISPLAY_SECONDS constant
- [ ] Timer for scoring phase
- [ ] Auto-trigger next round or end

### Task 4: Update State Broadcasting
- [ ] Include round_number in all phases
- [ ] Include total_rounds
- [ ] Add round_display string

### Task 5: Add UI Round Transitions
- [ ] Round transition overlay
- [ ] Round indicator in headers
- [ ] Update round display method

### Task 6: Write Tests
- [ ] Test round progression
- [ ] Test game end check
- [ ] Test state reset

---

## Definition of Done

- [ ] Game advances through configured number of rounds
- [ ] New spy assigned each round
- [ ] New location selected each round
- [ ] Round counter displays correctly
- [ ] State properly reset between rounds
- [ ] Game ends after final round
- [ ] No console errors
- [ ] Round transitions are smooth

---

## Dependencies

### Depends On
- **Story 6.5**: Leaderboard Display (SCORING phase)
- **Story 3.3**: Spy Assignment
- **Story 3.4**: Role Distribution

### Enables
- **Story 6.7**: Game End and Winner Declaration

---

## Dev Agent Record

### Agent Model Used
claude-opus-4-5-20251101

### Completion Notes List
- Added ERR_GAME_ENDED constant and message to const.py
- Implemented should_end_game() method to check if game should end
- Implemented start_next_round() with phase guard, history save, state reset, role assignment
- Implemented _save_round_history() to preserve round data
- Implemented _reset_for_new_round() to clear votes, spy guess, round scores, timers
- Added _on_scoring_timer_expired() to handle automatic round/game progression
- Added round_transition CSS with overlay and animation
- History tracking includes spy, location, convicted, spy_caught, scores per round

### File List
- custom_components/spyster/const.py
- custom_components/spyster/game/state.py
- custom_components/spyster/www/css/styles.css
