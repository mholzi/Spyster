# Story 4.3: Questioner/Answerer Turn Management

**Epic:** Epic 4 - Questioning Phase
**Story ID:** 4.3
**Status:** done
**Priority:** Medium
**Complexity:** Low

---

## User Story

As a **player**,
I want **to know whose turn it is to ask and answer**,
So that **the questioning flows smoothly**.

---

## Acceptance Criteria

### AC1: Turn Designation on Phase Start

**Given** the game is in QUESTIONING phase
**When** a turn begins
**Then** the system designates a questioner and an answerer
**And** both player and host displays show "Player A asks Player B"

### AC2: Natural Turn Rotation

**Given** the current questioner
**When** they complete their question verbally (no UI action needed)
**Then** the answerer responds verbally
**And** turns rotate naturally (no enforced turn advancement in MVP)

### AC3: Host Display Q&A State

**Given** the host display
**When** showing Q&A state
**Then** the current questioner and answerer names are prominently visible to the room

### AC4: Turn Order Initialization

**Given** the game transitions to QUESTIONING phase
**When** the turn order is initialized
**Then** players are arranged in a randomized order
**And** the first player in order becomes the initial questioner
**And** the second player in order becomes the initial answerer

### AC5: Manual Turn Advancement (Host Only)

**Given** the host wants to advance the turn manually
**When** they tap "Next Turn" on the host display
**Then** the questioner becomes the previous answerer
**And** the answerer becomes the next player in order
**And** all displays update to show new Q&A pair

---

## Requirements Coverage

### Functional Requirements

- **FR25**: System displays which player should ask a question
- **FR26**: System displays which player should answer
- **FR27**: Host display shows current questioner and answerer for the room

### Non-Functional Requirements

- **NFR2**: WebSocket Latency - Messages delivered in < 100ms on local network
- **NFR4**: State Sync - All players see same game state within 500ms of change

### Architectural Requirements

- **ARCH-12**: Message format: `{"type": "...", ...payload}` with snake_case fields
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-15**: Constants in `const.py` - never hardcode values
- **ARCH-17**: Phase guards on all state-mutating methods

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Add turn management fields and methods:

```python
import secrets
from typing import Optional

from .const import (
    ERR_INVALID_PHASE,
    ERR_INSUFFICIENT_PLAYERS,
    ERR_TURN_NOT_INITIALIZED,
)

class GameState:
    def __init__(self):
        # ... existing fields ...
        self.turn_order: list[str] = []  # Randomized player order
        self.current_questioner: str | None = None
        self.current_answerer: str | None = None
        self.turn_index: int = 0  # Index of current questioner in turn_order

    def initialize_turn_order(self) -> tuple[bool, str | None]:
        """
        Initialize randomized turn order for QUESTIONING phase.

        Returns:
            (success: bool, error_code: str | None)
        """
        # Phase guard
        if self.phase not in [GamePhase.ROLES, GamePhase.QUESTIONING]:
            _LOGGER.warning("Cannot initialize turn order - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        # Get connected player names
        player_names = [
            name for name, player in self.players.items()
            if player.connected
        ]

        if len(player_names) < 2:
            _LOGGER.error("Not enough players for turn management: %d", len(player_names))
            return False, ERR_INSUFFICIENT_PLAYERS

        # Shuffle for random order using CSPRNG
        self.turn_order = player_names.copy()
        secrets.SystemRandom().shuffle(self.turn_order)

        # Set initial questioner and answerer
        self.turn_index = 0
        self.current_questioner = self.turn_order[0]
        self.current_answerer = self.turn_order[1]

        _LOGGER.info(
            "Turn order initialized: %s asks %s (order: %s)",
            self.current_questioner,
            self.current_answerer,
            self.turn_order
        )

        return True, None

    def advance_turn(self) -> tuple[bool, str | None]:
        """
        Advance to next questioner/answerer pair.

        Returns:
            (success: bool, error_code: str | None)
        """
        # Phase guard
        if self.phase != GamePhase.QUESTIONING:
            _LOGGER.warning("Cannot advance turn - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        if not self.turn_order or len(self.turn_order) < 2:
            _LOGGER.error("Turn order not initialized")
            return False, ERR_TURN_NOT_INITIALIZED

        # Previous answerer becomes new questioner
        # Next in order becomes new answerer
        self.turn_index = (self.turn_index + 1) % len(self.turn_order)
        next_index = (self.turn_index + 1) % len(self.turn_order)

        self.current_questioner = self.turn_order[self.turn_index]
        self.current_answerer = self.turn_order[next_index]

        _LOGGER.info(
            "Turn advanced: %s asks %s",
            self.current_questioner,
            self.current_answerer
        )

        return True, None

    def get_state(self, for_player: str | None = None) -> dict:
        """Get game state, filtered for specific player."""
        base_state = {
            # ... existing fields ...
        }

        # Add turn info for QUESTIONING phase
        if self.phase == GamePhase.QUESTIONING:
            base_state["turn"] = {
                "questioner": self.current_questioner,
                "answerer": self.current_answerer,
            }
            # ... existing timer and role_data ...

        return base_state
```

#### 2. Constants (`const.py`)

Add turn management error codes:

```python
# Turn management error codes
ERR_INSUFFICIENT_PLAYERS = "INSUFFICIENT_PLAYERS"
ERR_TURN_NOT_INITIALIZED = "TURN_NOT_INITIALIZED"
ERR_PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_INSUFFICIENT_PLAYERS: "Not enough players to start the game.",
    ERR_TURN_NOT_INITIALIZED: "Turn order has not been initialized.",
    ERR_PLAYER_NOT_FOUND: "Player not found in this game.",
}
```

#### 3. WebSocket Handler (`server/websocket.py`)

Add admin action for turn advancement:

```python
async def _handle_admin_action(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle admin/host actions."""
    action = data.get("action")

    # ... existing actions ...

    if action == "advance_turn":
        success, error = self.game_state.advance_turn()
        if not success:
            await ws.send_json({
                "type": "error",
                "code": error,
                "message": ERROR_MESSAGES[error]
            })
            return

        _LOGGER.info("Turn advanced by host")
        await self.broadcast_state()
```

#### 4. Player Display (`www/js/player.js`)

Update questioning view to show turn info:

```javascript
showQuestioningView(state) {
    // ... existing code ...

    // Update turn display
    this.updateTurnDisplay(state.turn);
}

updateTurnDisplay(turnData) {
    const turnElement = document.getElementById('turn-display');
    if (!turnElement || !turnData) return;

    const questionerName = this.escapeHtml(turnData.questioner);
    const answererName = this.escapeHtml(turnData.answerer);

    turnElement.innerHTML = `
        <div class="turn-info">
            <span class="questioner">${questionerName}</span>
            <span class="turn-arrow">asks</span>
            <span class="answerer">${answererName}</span>
        </div>
    `;

    // Highlight if current player is involved
    const isQuestioner = turnData.questioner === this.playerName;
    const isAnswerer = turnData.answerer === this.playerName;

    turnElement.classList.toggle('my-turn-questioner', isQuestioner);
    turnElement.classList.toggle('my-turn-answerer', isAnswerer);
}
```

#### 5. Player Display HTML (`www/player.html`)

Add turn display element:

```html
<!-- Inside questioning-view -->
<div id="turn-display" class="turn-display" role="status" aria-live="polite">
    <!-- Populated by JavaScript -->
</div>
```

#### 6. Host Display (`www/js/host.js`)

Show prominent Q&A display and next turn button:

```javascript
showQuestioningView(state) {
    // ... existing code ...

    // Update Q&A display
    this.updateQADisplay(state.turn);
}

updateQADisplay(turnData) {
    const qaElement = document.getElementById('qa-display');
    if (!qaElement || !turnData) return;

    const questionerName = this.escapeHtml(turnData.questioner);
    const answererName = this.escapeHtml(turnData.answerer);

    qaElement.innerHTML = `
        <div class="qa-current">
            <div class="qa-label">ASKING</div>
            <div class="qa-name questioner-name">${questionerName}</div>
        </div>
        <div class="qa-arrow">→</div>
        <div class="qa-current">
            <div class="qa-label">ANSWERING</div>
            <div class="qa-name answerer-name">${answererName}</div>
        </div>
    `;
}

advanceTurn() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected');
        return;
    }

    this.ws.send(JSON.stringify({
        type: 'admin',
        action: 'advance_turn'
    }));
}
```

#### 7. Host Display HTML (`www/host.html`)

Add Q&A display and control:

```html
<!-- Q&A Display for Host -->
<div id="qa-display" class="qa-display" role="status">
    <!-- Populated by JavaScript -->
</div>

<!-- Host Admin Controls -->
<div class="host-controls">
    <button id="next-turn-btn" class="btn-secondary">
        NEXT TURN
    </button>
    <!-- ... other controls ... -->
</div>
```

#### 8. CSS Styles (`www/css/styles.css`)

Add turn display styles:

```css
/* Turn Display - Player View */
.turn-display {
    text-align: center;
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-lg);
}

.turn-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-md);
    font-size: 18px;
}

.turn-arrow {
    color: var(--color-text-secondary);
    font-style: italic;
}

.questioner, .answerer {
    font-weight: 600;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
}

.questioner {
    color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.1);
}

.answerer {
    color: var(--color-accent-secondary);
    background: rgba(0, 245, 255, 0.1);
}

/* Highlight when it's my turn */
.my-turn-questioner {
    border: 2px solid var(--color-accent-primary);
    animation: glow-pink 2s ease-in-out infinite;
}

.my-turn-answerer {
    border: 2px solid var(--color-accent-secondary);
    animation: glow-cyan 2s ease-in-out infinite;
}

@keyframes glow-pink {
    0%, 100% { box-shadow: 0 0 10px rgba(255, 45, 106, 0.3); }
    50% { box-shadow: 0 0 20px rgba(255, 45, 106, 0.6); }
}

@keyframes glow-cyan {
    0%, 100% { box-shadow: 0 0 10px rgba(0, 245, 255, 0.3); }
    50% { box-shadow: 0 0 20px rgba(0, 245, 255, 0.6); }
}

/* Q&A Display - Host View */
.qa-display {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-xl);
    padding: var(--spacing-xxl);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-xl);
    margin-bottom: var(--spacing-xl);
}

.qa-current {
    text-align: center;
}

.qa-label {
    font-size: 14px;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: var(--spacing-sm);
}

.qa-name {
    font-size: 48px;
    font-weight: 700;
}

.questioner-name {
    color: var(--color-accent-primary);
}

.answerer-name {
    color: var(--color-accent-secondary);
}

.qa-arrow {
    font-size: 48px;
    color: var(--color-text-secondary);
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
    .my-turn-questioner,
    .my-turn-answerer {
        animation: none;
    }
}

/* Host Controls */
.host-controls {
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    position: fixed;
    bottom: var(--spacing-lg);
    right: var(--spacing-lg);
}
```

---

## Implementation Tasks

### Task 1: Update Constants (AC: All)
- [x] Add `ERR_INSUFFICIENT_PLAYERS` constant
- [x] Add `ERR_TURN_NOT_INITIALIZED` constant
- [x] Add error messages to `ERROR_MESSAGES` dict

### Task 2: Add Turn Management to GameState (AC: 1, 4)
- [x] Add `turn_order`, `current_questioner`, `current_answerer`, `turn_index` fields
- [x] Implement `initialize_turn_order()` with CSPRNG shuffle
- [x] Implement `advance_turn()` with wrap-around
- [x] Update `get_state()` to include turn data in QUESTIONING phase
- [x] Add logging for turn events

### Task 3: Integrate Turn Init with Phase Transition (AC: 1, 4)
- [x] Call `initialize_turn_order()` when transitioning to QUESTIONING
- [x] Ensure turn data is included in first broadcast

### Task 4: Add Admin Action for Turn Advancement (AC: 5)
- [x] Add `advance_turn` action handler in WebSocket
- [x] Broadcast state after turn advancement
- [x] Log turn advancement events

### Task 5: Update Player Display (AC: 1)
- [x] Add `turn-display` element to player.html
- [x] Implement `updateTurnDisplay()` in player.js
- [x] Highlight when current player is questioner/answerer

### Task 6: Update Host Display (AC: 3, 5)
- [x] Add `qa-display` element to host.html
- [x] Implement `updateQADisplay()` in host.js
- [x] Add "Next Turn" button with click handler
- [x] Implement `advanceTurn()` function

### Task 7: Add CSS Styles (AC: 1, 3)
- [x] Style `.turn-display` for player view
- [x] Style `.qa-display` for host view (large, prominent)
- [x] Add glow animations for active turn
- [x] Respect `prefers-reduced-motion`

### Task 8: Write Tests (AC: All)
- [x] Test `initialize_turn_order()` creates valid order
- [x] Test `advance_turn()` cycles through players
- [x] Test phase guard prevents turn management in wrong phase
- [x] Test state includes turn data in QUESTIONING phase

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_initialize_turn_order_success(game_state_in_roles):
    """Test turn order initialization with enough players."""
    # Add test players
    game_state_in_roles.add_player("Alice", mock_ws())
    game_state_in_roles.add_player("Bob", mock_ws())
    game_state_in_roles.add_player("Charlie", mock_ws())

    success, error = game_state_in_roles.initialize_turn_order()

    assert success is True
    assert error is None
    assert len(game_state_in_roles.turn_order) == 3
    assert game_state_in_roles.current_questioner in ["Alice", "Bob", "Charlie"]
    assert game_state_in_roles.current_answerer in ["Alice", "Bob", "Charlie"]
    assert game_state_in_roles.current_questioner != game_state_in_roles.current_answerer

@pytest.mark.asyncio
async def test_advance_turn_cycles(game_state_in_questioning):
    """Test turn advancement cycles through all players."""
    game_state_in_questioning.turn_order = ["Alice", "Bob", "Charlie"]
    game_state_in_questioning.turn_index = 0
    game_state_in_questioning.current_questioner = "Alice"
    game_state_in_questioning.current_answerer = "Bob"

    # First advance: Bob asks Charlie
    success, _ = game_state_in_questioning.advance_turn()
    assert success
    assert game_state_in_questioning.current_questioner == "Bob"
    assert game_state_in_questioning.current_answerer == "Charlie"

    # Second advance: Charlie asks Alice (wrap around)
    success, _ = game_state_in_questioning.advance_turn()
    assert success
    assert game_state_in_questioning.current_questioner == "Charlie"
    assert game_state_in_questioning.current_answerer == "Alice"

def test_get_state_includes_turn_data(game_state_in_questioning):
    """Test get_state includes turn information."""
    game_state_in_questioning.current_questioner = "Alice"
    game_state_in_questioning.current_answerer = "Bob"

    state = game_state_in_questioning.get_state()

    assert "turn" in state
    assert state["turn"]["questioner"] == "Alice"
    assert state["turn"]["answerer"] == "Bob"
```

### Manual Testing Checklist

- [ ] Game starts and turn order is randomized
- [ ] Player display shows "Alice asks Bob" format
- [ ] Host display shows large Q&A names
- [ ] Current player sees highlight when they're questioner/answerer
- [ ] Host can click "Next Turn" to advance
- [ ] Turn wraps around when reaching end of player list
- [ ] All players see updated turn info after advancement

---

## Definition of Done

- [ ] Turn order initialized with CSPRNG shuffle
- [ ] Questioner and answerer displayed on all clients
- [ ] Host can manually advance turns
- [ ] State includes turn data in QUESTIONING phase
- [ ] Phase guards prevent turn ops in wrong phase
- [ ] Constants for error codes in const.py
- [ ] Logging includes turn context
- [ ] All unit tests pass
- [ ] Manual testing completed
- [ ] ARIA attributes on turn display
- [ ] Respects `prefers-reduced-motion`
- [ ] No console errors

---

## Dependencies

### Depends On
- **Story 4.1**: Transition to Questioning Phase (provides QUESTIONING phase)
- **Story 4.2**: Round Timer (shares QUESTIONING phase UI)

### Enables
- **Story 4.4**: Player Role View (shares screen with turn display)
- **Story 4.5**: Call Vote (player may call vote during any turn)

---

## Architecture Decisions Referenced

- **ARCH-12**: Message format with snake_case
- **ARCH-14**: Broadcast state after mutations
- **ARCH-15**: Constants in const.py
- **ARCH-17**: Phase guards on state-mutating methods

---

## Notes

### Design Decision: No Enforced Turn Advancement

Per the PRD (FR25-27), the turn system is **informational only** for MVP. Players ask and answer verbally - the UI simply suggests who should go next. The host can manually advance turns if desired.

This is simpler than tracking who actually spoke and avoids awkward forced turn-taking in a social party game.

### Future Enhancement

Post-MVP could add:
- Auto-advance after a configurable time (e.g., 30 seconds per turn)
- Track question count per player
- Prevent same player from being questioner twice in a row

---

## Dev Agent Record

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/const.py` | Modified | Added ERR_INSUFFICIENT_PLAYERS, ERR_TURN_NOT_INITIALIZED constants |
| `custom_components/spyster/game/state.py` | Modified | Added turn management fields and methods (initialize_turn_order, advance_turn, get_current_turn_info) |
| `custom_components/spyster/server/websocket.py` | Modified | Added advance_turn admin action handler |
| `custom_components/spyster/www/host.html` | Modified | Added Next Turn button in questioning section |
| `custom_components/spyster/www/js/host.js` | Modified | Added advanceTurn() function and button event listener |
| `custom_components/spyster/www/player.html` | Pre-existing | Turn display section already existed |
| `custom_components/spyster/www/js/player.js` | Pre-existing | Turn display handling already existed |
| `custom_components/spyster/www/css/styles.css` | Pre-existing | Turn display styles already existed |
| `tests/test_state.py` | Pre-existing | Turn management tests already existed (lines 1818-2017) |

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2025-12-23 | Initial implementation | Story 4-3 development |
| 2025-12-23 | Code review fixes | Fixed random.shuffle → secrets.SystemRandom().shuffle for CSPRNG compliance |
| 2025-12-23 | Cleanup | Removed state.py.backup file |

### Review Notes

- **Code Review Date:** 2025-12-23
- **Reviewer:** Amelia (Dev Agent)
- **Outcome:** APPROVED with fixes applied
- **Issues Found:** 1 HIGH (CSPRNG), 3 MEDIUM (documentation)
- **Issues Fixed:** All HIGH and MEDIUM issues resolved
