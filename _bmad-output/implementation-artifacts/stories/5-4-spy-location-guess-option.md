# Story 5.4: Spy Location Guess Option

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.4
**Status:** ready-for-dev
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **spy**,
I want **to guess the location instead of voting**,
So that **I can win by deduction rather than framing someone**.

---

## Acceptance Criteria

### AC1: Spy Mode Toggle

**Given** the spy is in VOTE phase
**When** they view their screen
**Then** they see two options: "Vote" or "Guess Location"

### AC2: Location List Display

**Given** the spy taps "Guess Location"
**When** the option is selected
**Then** a list of possible locations is displayed
**And** the spy can select one location

### AC3: Location Guess Submission

**Given** the spy selects a location
**When** they tap "Confirm Guess"
**Then** a `spy_guess` message is sent with `{location_id}`
**And** the spy cannot vote (mutually exclusive per FR39)

### AC4: Non-Spy Restriction

**Given** a non-spy player
**When** viewing the vote screen
**Then** the "Guess Location" option is NOT visible

### AC5: Mutual Exclusivity

**Given** the spy chooses to guess location
**When** they confirm the guess
**Then** they cannot vote (and vice versa per FR39)

---

## Requirements Coverage

### Functional Requirements

- **FR39**: Spy must choose between guessing location OR voting (not both)
- **FR40**: Spy can attempt to guess the location instead of voting
- **FR41**: Spy can see the list of possible locations when guessing
- **FR43**: Spy loses points if location guess is incorrect; round ends with spy revealed

### Architectural Requirements

- **ARCH-7**: Per-player state filtering via `get_state(for_player=player_name)`
- **ARCH-8**: Never broadcast same state to all players (role privacy)
- **ARCH-12**: Message format: `{"type": "spy_guess", "location_id": "..."}`
- **ARCH-17**: Phase guards on state-mutating methods

### UX Requirements

- **UX-9**: Spy and non-spy screens must have identical layouts (prevent visual tells)

---

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Add spy guess error codes:

```python
# Error codes for spy guess (Story 5.4)
ERR_NOT_SPY = "NOT_SPY"
ERR_SPY_ALREADY_ACTED = "SPY_ALREADY_ACTED"
ERR_INVALID_LOCATION = "INVALID_LOCATION"

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_NOT_SPY: "Only the spy can guess the location.",
    ERR_SPY_ALREADY_ACTED: "You've already made your choice.",
    ERR_INVALID_LOCATION: "Invalid location selection.",
}
```

#### 2. GameState (`game/state.py`)

Add spy guess handling:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        # Story 5.4: Spy action tracking
        self.spy_guess: dict | None = None  # {location_id, correct, timestamp}
        self.spy_action_taken: bool = False  # True if spy voted or guessed

    def record_spy_guess(
        self,
        player_name: str,
        location_id: str
    ) -> tuple[bool, str | None]:
        """
        Record spy's location guess (Story 5.4).

        Args:
            player_name: Name of player making guess (must be spy)
            location_id: ID of guessed location

        Returns:
            (success: bool, error_code: str | None)
        """
        import time
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_NOT_SPY,
            ERR_SPY_ALREADY_ACTED,
            ERR_INVALID_LOCATION,
        )

        # Phase guard (ARCH-17)
        if self.phase != GamePhase.VOTE:
            _LOGGER.warning(
                "Cannot record spy guess - invalid phase: %s",
                self.phase
            )
            return False, ERR_INVALID_PHASE

        # Verify player is the spy (AC4)
        if player_name != self._spy_name:
            _LOGGER.warning(
                "Non-spy tried to guess location: %s (spy is: %s)",
                player_name,
                self._spy_name
            )
            return False, ERR_NOT_SPY

        # Check if spy already acted (AC5)
        if self.spy_action_taken:
            _LOGGER.warning("Spy already acted: %s", player_name)
            return False, ERR_SPY_ALREADY_ACTED

        if player_name in self.votes:
            _LOGGER.warning("Spy already voted: %s", player_name)
            return False, ERR_SPY_ALREADY_ACTED

        # Validate location exists
        location_list = self._get_location_list()
        if location_id not in [loc["id"] for loc in location_list]:
            _LOGGER.warning("Invalid location guess: %s", location_id)
            return False, ERR_INVALID_LOCATION

        # Check if guess is correct
        correct = (location_id == self._current_location.get("id"))

        # Record the guess
        self.spy_guess = {
            "location_id": location_id,
            "correct": correct,
            "timestamp": time.time(),
        }
        self.spy_action_taken = True

        _LOGGER.info(
            "Spy guess recorded: %s guessed '%s' (correct: %s)",
            player_name,
            location_id,
            correct
        )

        # Spy guess ends voting immediately - cancel timer and transition
        self.cancel_timer("vote")

        return True, None

    def _get_location_list(self) -> list[dict]:
        """Get list of possible locations for spy."""
        from .content import get_location_pack
        pack = get_location_pack(self.config.location_pack)
        return pack.get("locations", [])

    def get_state(self, for_player: str | None = None) -> dict[str, Any]:
        # ... in VOTE phase section ...
        elif self.phase == GamePhase.VOTE:
            # ... existing code ...

            # Story 5.4: Include spy-specific data
            if for_player and for_player == self._spy_name:
                state["is_spy"] = True
                state["can_guess_location"] = not self.spy_action_taken
                state["location_list"] = [
                    {"id": loc["id"], "name": loc["name"]}
                    for loc in self._get_location_list()
                ]
            else:
                state["is_spy"] = False

            # Track if spy has acted (for reveal logic)
            state["spy_has_guessed"] = self.spy_guess is not None
```

#### 3. WebSocket Handler (`server/websocket.py`)

Add spy guess handler:

```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    # ... existing handlers ...

    if msg_type == "spy_guess":
        await self._handle_spy_guess(ws, data)
        return

async def _handle_spy_guess(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle spy location guess."""
    from ..const import (
        ERR_NOT_IN_GAME,
        ERROR_MESSAGES,
    )

    player_name = self._get_player_name_by_ws(ws)
    if not player_name:
        await ws.send_json({
            "type": "error",
            "code": ERR_NOT_IN_GAME,
            "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
        })
        return

    location_id = data.get("location_id")
    if not location_id:
        await ws.send_json({
            "type": "error",
            "code": ERR_INVALID_LOCATION,
            "message": ERROR_MESSAGES[ERR_INVALID_LOCATION]
        })
        return

    success, error = self.game_state.record_spy_guess(player_name, location_id)

    if not success:
        await ws.send_json({
            "type": "error",
            "code": error,
            "message": ERROR_MESSAGES.get(error, "Could not record guess.")
        })
        return

    _LOGGER.info("Spy guess submitted: %s -> %s", player_name, location_id)

    # Spy guess triggers immediate transition to REVEAL
    self.game_state.phase = GamePhase.REVEAL

    # Broadcast state (spy guess ends voting)
    await self.broadcast_state()
```

#### 4. Player Display HTML (`www/player.html`)

Add spy mode toggle and location list:

```html
<!-- Spy Mode Toggle (inside vote-view, before player cards) -->
<div id="spy-mode-toggle" class="spy-mode-toggle" style="display: none;">
    <div class="spy-mode-options" role="tablist">
        <button
            id="spy-vote-tab"
            class="spy-mode-tab spy-mode-tab--active"
            role="tab"
            aria-selected="true"
            aria-controls="vote-panel"
        >
            Vote
        </button>
        <button
            id="spy-guess-tab"
            class="spy-mode-tab"
            role="tab"
            aria-selected="false"
            aria-controls="guess-panel"
        >
            Guess Location
        </button>
    </div>
</div>

<!-- Location Guess Panel (hidden by default) -->
<div id="guess-panel" class="vote-section" style="display: none;" role="tabpanel">
    <h2 class="vote-section-title">Where do you think they are?</h2>
    <div id="location-list" class="location-list" role="radiogroup" aria-label="Select a location">
        <!-- Location items injected dynamically -->
    </div>
    <div class="vote-actions">
        <button id="submit-guess-btn" class="btn-primary btn-large" disabled>
            CONFIRM GUESS
        </button>
    </div>
</div>
```

#### 5. Player Display Logic (`www/js/player.js`)

Add spy guess functionality:

```javascript
class PlayerDisplay {
    constructor() {
        // ... existing init ...
        this.isSpy = false;
        this.selectedLocation = null;
        this.spyActionTaken = false;
    }

    setupEventListeners() {
        // ... existing listeners ...

        // Spy mode tabs
        document.getElementById('spy-vote-tab')?.addEventListener('click', () => {
            this.setSpyMode('vote');
        });
        document.getElementById('spy-guess-tab')?.addEventListener('click', () => {
            this.setSpyMode('guess');
        });

        // Submit guess button
        document.getElementById('submit-guess-btn')?.addEventListener('click', () => {
            this.submitLocationGuess();
        });
    }

    showVoteView(state) {
        // ... existing code ...

        // Story 5.4: Show spy mode toggle if player is spy
        this.isSpy = state.is_spy || false;
        const spyToggle = document.getElementById('spy-mode-toggle');
        if (spyToggle) {
            spyToggle.style.display = this.isSpy ? 'block' : 'none';
        }

        // Render location list for spy
        if (this.isSpy && state.location_list) {
            this.renderLocationList(state.location_list);
        }

        // Check if spy can still act
        this.spyActionTaken = !state.can_guess_location;
    }

    setSpyMode(mode) {
        const voteTab = document.getElementById('spy-vote-tab');
        const guessTab = document.getElementById('spy-guess-tab');
        const votePanel = document.getElementById('player-cards-grid')?.closest('.vote-section');
        const guessPanel = document.getElementById('guess-panel');
        const confidenceSection = document.getElementById('confidence-section');

        if (mode === 'vote') {
            voteTab?.classList.add('spy-mode-tab--active');
            voteTab?.setAttribute('aria-selected', 'true');
            guessTab?.classList.remove('spy-mode-tab--active');
            guessTab?.setAttribute('aria-selected', 'false');

            if (votePanel) votePanel.style.display = 'block';
            if (guessPanel) guessPanel.style.display = 'none';
            if (confidenceSection) confidenceSection.style.display = 'block';
        } else if (mode === 'guess') {
            guessTab?.classList.add('spy-mode-tab--active');
            guessTab?.setAttribute('aria-selected', 'true');
            voteTab?.classList.remove('spy-mode-tab--active');
            voteTab?.setAttribute('aria-selected', 'false');

            if (votePanel) votePanel.style.display = 'none';
            if (guessPanel) guessPanel.style.display = 'block';
            if (confidenceSection) confidenceSection.style.display = 'none';
        }
    }

    renderLocationList(locations) {
        const list = document.getElementById('location-list');
        if (!list) return;

        list.innerHTML = '';

        locations.forEach(location => {
            const item = document.createElement('button');
            item.className = 'location-item';
            item.setAttribute('role', 'radio');
            item.setAttribute('aria-checked', 'false');
            item.setAttribute('data-location-id', location.id);

            item.innerHTML = `
                <span class="location-name">${this.escapeHtml(location.name)}</span>
            `;

            item.addEventListener('click', () => this.selectLocation(location.id));
            list.appendChild(item);
        });
    }

    selectLocation(locationId) {
        // Clear previous selection
        document.querySelectorAll('.location-item').forEach(item => {
            item.classList.remove('location-item--selected');
            item.setAttribute('aria-checked', 'false');
        });

        // Select new location
        const selectedItem = document.querySelector(`[data-location-id="${locationId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('location-item--selected');
            selectedItem.setAttribute('aria-checked', 'true');
        }

        this.selectedLocation = locationId;

        // Enable submit button
        const submitBtn = document.getElementById('submit-guess-btn');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'CONFIRM GUESS';
        }
    }

    submitLocationGuess() {
        if (!this.selectedLocation || this.spyActionTaken) {
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'spy_guess',
            location_id: this.selectedLocation
        }));

        // Lock UI
        this.spyActionTaken = true;
        const submitBtn = document.getElementById('submit-guess-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'GUESS LOCKED ✓';
        }

        document.querySelectorAll('.location-item').forEach(item => {
            item.disabled = true;
            item.classList.add('location-item--locked');
        });
    }
}
```

#### 6. CSS Styles (`www/css/styles.css`)

Add spy mode and location list styles:

```css
/* =================================
   SPY MODE TOGGLE
   ================================= */

.spy-mode-toggle {
    margin-bottom: var(--spacing-lg);
}

.spy-mode-options {
    display: flex;
    gap: var(--spacing-sm);
    background: var(--color-bg-secondary);
    padding: var(--spacing-xs);
    border-radius: var(--radius-lg);
}

.spy-mode-tab {
    flex: 1;
    padding: var(--spacing-md);
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.spy-mode-tab--active {
    background: var(--color-accent-primary);
    color: white;
}

.spy-mode-tab:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(255, 45, 106, 0.4);
}

/* =================================
   LOCATION LIST
   ================================= */

.location-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    max-height: 300px;
    overflow-y: auto;
    padding: var(--spacing-sm);
}

.location-item {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    width: 100%;
}

.location-item:hover:not(:disabled) {
    border-color: var(--color-accent-secondary);
}

.location-item--selected {
    border-color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.15);
}

.location-item--locked {
    opacity: 0.6;
    cursor: not-allowed;
}

.location-name {
    font-size: 16px;
    font-weight: 500;
    color: var(--color-text-primary);
}

.location-item:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 245, 255, 0.4);
}
```

---

## Implementation Tasks

### Task 1: Add Constants (AC: All)
- [x] Add ERR_NOT_SPY error code
- [x] Add ERR_SPY_ALREADY_ACTED error code
- [x] Add ERR_INVALID_LOCATION error code

### Task 2: Implement record_spy_guess (AC: 3, 5)
- [x] Phase guard validation
- [x] Spy identity check
- [x] Duplicate action prevention
- [x] Location validation
- [x] Store guess result

### Task 3: Update get_state for Spy (AC: 1, 4)
- [x] Include is_spy flag
- [x] Include location_list for spy only
- [x] Include can_guess_location flag

### Task 4: Add WebSocket Handler (AC: 3)
- [x] Handle "spy_guess" message type
- [x] Validate spy identity
- [x] Trigger REVEAL on guess

### Task 5: Implement Frontend Spy Mode (AC: 1, 2)
- [x] Spy mode toggle tabs
- [x] Location list rendering
- [x] Mode switching logic

### Task 6: Add Location Selection (AC: 2, 3)
- [x] selectLocation() method
- [x] submitLocationGuess() method
- [x] Lock UI after submission

### Task 7: Add CSS Styles
- [x] Spy mode toggle styles
- [x] Location list styles
- [x] Selected/locked states

### Task 8: Write Tests
- [ ] test_spy_guess_success
- [ ] test_non_spy_cannot_guess
- [ ] test_spy_guess_mutual_exclusion
- [ ] test_invalid_location

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_spy_guess_success(game_state_in_vote_with_spy):
    """Test spy can guess location."""
    spy_name = game_state_in_vote_with_spy._spy_name
    location_id = game_state_in_vote_with_spy._current_location["id"]

    success, error = game_state_in_vote_with_spy.record_spy_guess(
        spy_name, location_id
    )

    assert success is True
    assert error is None
    assert game_state_in_vote_with_spy.spy_guess is not None
    assert game_state_in_vote_with_spy.spy_guess["correct"] is True

@pytest.mark.asyncio
async def test_non_spy_cannot_guess(game_state_in_vote_with_spy):
    """Test non-spy cannot guess location."""
    non_spy = [p for p in game_state_in_vote_with_spy.players.keys()
               if p != game_state_in_vote_with_spy._spy_name][0]

    success, error = game_state_in_vote_with_spy.record_spy_guess(
        non_spy, "beach"
    )

    assert success is False
    assert error == ERR_NOT_SPY

@pytest.mark.asyncio
async def test_spy_guess_prevents_voting(game_state_in_vote_with_spy):
    """Test spy cannot vote after guessing."""
    spy_name = game_state_in_vote_with_spy._spy_name

    # Make guess
    game_state_in_vote_with_spy.record_spy_guess(spy_name, "beach")

    # Try to vote
    target = [p for p in game_state_in_vote_with_spy.players.keys()
              if p != spy_name][0]
    success, error = game_state_in_vote_with_spy.record_vote(spy_name, target, 1)

    assert success is False
    assert error == ERR_ALREADY_VOTED
```

### Manual Testing Checklist

**Scenario 1: Spy Mode Toggle**
- [ ] Spy sees Vote/Guess Location tabs
- [ ] Non-spy does NOT see tabs
- [ ] Clicking tabs switches views

**Scenario 2: Location List**
- [ ] Location list shows all pack locations
- [ ] Can select a location
- [ ] Selected location highlighted
- [ ] Submit button enables

**Scenario 3: Guess Submission**
- [ ] Tap "CONFIRM GUESS" submits
- [ ] UI locks after submission
- [ ] Transitions to REVEAL immediately

**Scenario 4: Mutual Exclusivity**
- [ ] After guessing, cannot vote
- [ ] After voting, cannot guess

---

## Definition of Done

- [x] Spy sees Vote/Guess tabs
- [x] Non-spy does NOT see tabs
- [x] Location list rendered for spy
- [x] Location selection works
- [x] spy_guess message sent correctly
- [x] Mutual exclusivity enforced
- [x] REVEAL triggered on guess
- [x] Error codes in const.py
- [ ] Unit tests pass
- [x] No console errors

---

## Dependencies

### Depends On
- **Story 5.1**: Voting Phase UI (vote view structure)
- **Story 3.4**: Role Distribution (spy assignment)

### Enables
- **Story 5.6**: Vote and Bet Reveal Sequence (handles spy guess reveal)
- **Story 6.4**: Spy Location Guess Scoring

---

## Architecture Decisions Referenced

- **ARCH-7**: Per-player state filtering
- **ARCH-8**: Role privacy (never broadcast spy identity)
- **ARCH-12**: Message format
- **ARCH-17**: Phase guards
- **UX-9**: Spy parity (identical layouts)

---

## Dev Notes

### Security Considerations

**CRITICAL**: The location list is ONLY sent to the spy. Non-spy players should never receive the full location list in the VOTE phase state.

```python
# In get_state() - only spy gets location_list
if for_player and for_player == self._spy_name:
    state["location_list"] = [...]
```

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/const.py` | Modify | Add spy guess error codes |
| `custom_components/spyster/game/state.py` | Modify | Add record_spy_guess() |
| `custom_components/spyster/server/websocket.py` | Modify | Add spy_guess handler |
| `custom_components/spyster/www/player.html` | Modify | Add spy mode toggle, location list |
| `custom_components/spyster/www/js/player.js` | Modify | Add spy guess logic |
| `custom_components/spyster/www/css/styles.css` | Modify | Add spy mode styles |

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Completion Notes List
_To be filled during implementation_

### File List
_To be filled during implementation_
