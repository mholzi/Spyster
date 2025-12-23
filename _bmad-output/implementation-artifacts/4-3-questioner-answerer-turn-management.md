---
story_id: "4.3"
epic_id: "4"
epic_name: "Questioning Phase"
story_name: "Questioner/Answerer Turn Management"
priority: "medium"
estimated_effort: "3 hours"
dependencies: ["4.1", "4.2"]
status: "completed"
created: "2025-12-23"
---

# Story 4.3: Questioner/Answerer Turn Management

As a **player**,
I want **to know whose turn it is to ask and answer**,
So that **the questioning flows smoothly**.

## Acceptance Criteria

### AC1: Turn Designation

**Given** the game is in QUESTIONING phase
**When** a turn begins
**Then** the system designates a questioner and an answerer
**And** both player and host displays show "Player A asks Player B"

### AC2: Verbal Q&A Flow

**Given** the current questioner
**When** they complete their question verbally (no UI action needed)
**Then** the answerer responds verbally
**And** turns rotate naturally (no enforced turn advancement in MVP)

### AC3: Host Display Visibility

**Given** the host display
**When** showing Q&A state
**Then** the current questioner and answerer names are prominently visible to the room

## Requirements Coverage

### Functional Requirements

- **FR25**: System displays which player should ask a question
- **FR26**: System displays which player should answer
- **FR27**: Host display shows current questioner and answerer for the room

### Non-Functional Requirements

- **NFR4**: State Sync - All players see same game state within 500ms of change

### Architectural Requirements

- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on all state-mutating methods

### UX Design Requirements

- **UX-16**: Host view tablet/TV optimized (768px+, 2-3x scale)

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Add constants for turn management:

```python
# Turn management
TURN_ROTATION_MODE = "sequential"  # MVP: sequential turn rotation

# Add to existing constants if needed
```

#### 2. GameState (`game/state.py`)

Add turn tracking and rotation logic:

```python
class GameState:
    def __init__(self, ...):
        # ... existing fields ...
        self.current_questioner_id: str | None = None
        self.current_answerer_id: str | None = None
        self._turn_order: list[str] = []  # Player IDs in turn order

    def initialize_turn_order(self) -> None:
        """
        Initialize turn order when entering QUESTIONING phase.
        Creates a shuffled list of connected player IDs.
        """
        connected_players = [
            player_id for player_id, player in self.players.items()
            if player.connected
        ]

        # Shuffle to randomize starting player
        import random
        random.shuffle(connected_players)

        self._turn_order = connected_players
        _LOGGER.info("Turn order initialized with %d players", len(self._turn_order))

        # Set initial questioner and answerer
        if len(self._turn_order) >= 2:
            self.current_questioner_id = self._turn_order[0]
            self.current_answerer_id = self._turn_order[1]
            _LOGGER.info(
                "Initial turn: %s asks %s",
                self.players[self.current_questioner_id].name,
                self.players[self.current_answerer_id].name
            )

    def advance_turn(self) -> None:
        """
        Advance to next questioner/answerer pair.

        MVP Implementation:
        - Sequential rotation through turn order
        - Questioner becomes answerer
        - Next player becomes new questioner
        - Skips disconnected players
        """
        if not self._turn_order or len(self._turn_order) < 2:
            _LOGGER.warning("Cannot advance turn - insufficient players")
            return

        # Find current questioner index
        if self.current_questioner_id not in self._turn_order:
            # Current questioner disconnected, restart from beginning
            _LOGGER.warning("Current questioner not in turn order, restarting")
            self.initialize_turn_order()
            return

        current_idx = self._turn_order.index(self.current_questioner_id)

        # Answerer becomes next questioner
        next_questioner_idx = (current_idx + 1) % len(self._turn_order)
        next_answerer_idx = (current_idx + 2) % len(self._turn_order)

        self.current_questioner_id = self._turn_order[next_questioner_idx]
        self.current_answerer_id = self._turn_order[next_answerer_idx]

        _LOGGER.info(
            "Turn advanced: %s asks %s",
            self.players[self.current_questioner_id].name,
            self.players[self.current_answerer_id].name
        )

    def get_current_turn_info(self) -> dict:
        """
        Get current turn information for state broadcast.

        Returns:
            dict with questioner and answerer details, or empty if not applicable
        """
        if self.phase != GamePhase.QUESTIONING:
            return {}

        if not self.current_questioner_id or not self.current_answerer_id:
            return {}

        questioner = self.players.get(self.current_questioner_id)
        answerer = self.players.get(self.current_answerer_id)

        if not questioner or not answerer:
            _LOGGER.warning("Turn info requested but player(s) not found")
            return {}

        return {
            "questioner": {
                "id": self.current_questioner_id,
                "name": questioner.name
            },
            "answerer": {
                "id": self.current_answerer_id,
                "name": answerer.name
            }
        }

    def get_state(self, for_player: str | None = None) -> dict:
        """
        Enhanced to include turn information.

        Args:
            for_player: Player ID for personalized state (role filtering)

        Returns:
            Game state dict with turn info
        """
        state = {
            # ... existing state fields ...
            "phase": self.phase.value,
            "player_count": len(self.players),
            # ... other fields ...
        }

        # Add turn information if in QUESTIONING phase
        turn_info = self.get_current_turn_info()
        if turn_info:
            state["current_turn"] = turn_info

        # ... existing role filtering logic ...

        return state
```

Update phase transition to initialize turns:

```python
def transition_to_questioning(self) -> tuple[bool, str | None]:
    """
    Transition from ROLES to QUESTIONING phase.

    Returns:
        (success: bool, error_code: str | None)
    """
    # Phase guard
    if self.phase != GamePhase.ROLES:
        _LOGGER.warning("Cannot transition to QUESTIONING - invalid phase: %s", self.phase)
        return False, ERR_INVALID_PHASE

    # Transition to QUESTIONING
    self.phase = GamePhase.QUESTIONING

    # Initialize turn order
    self.initialize_turn_order()

    # Start round timer (handled in timer system)

    _LOGGER.info("Transitioned to QUESTIONING phase")
    return True, None
```

#### 3. Host Display UI (`www/host.html`)

Add turn display section for QUESTIONING phase:

```html
<!-- Questioning Phase View -->
<div id="questioning-view" class="phase-view">
    <div class="phase-header">
        <h1>Questioning Phase</h1>
        <div id="round-timer-host" class="timer-display large">
            <span class="timer-value">0:00</span>
        </div>
    </div>

    <!-- Current Turn Display -->
    <div id="turn-display" class="turn-indicator">
        <div class="turn-label">CURRENT TURN</div>
        <div class="turn-info">
            <div class="questioner-box">
                <div class="role-label">ASKING</div>
                <div id="questioner-name" class="player-name-large">
                    Player Name
                </div>
            </div>
            <div class="turn-arrow">→</div>
            <div class="answerer-box">
                <div class="role-label">ANSWERING</div>
                <div id="answerer-name" class="player-name-large">
                    Player Name
                </div>
            </div>
        </div>
    </div>

    <!-- Player Status Grid -->
    <div id="player-status-grid" class="player-grid">
        <!-- Populated by JavaScript -->
    </div>
</div>
```

#### 4. Host Display Logic (`www/js/host.js`)

Add turn display update logic:

```javascript
class HostDisplay {
    // ... existing methods ...

    updateQuestioningView(state) {
        // Update round timer
        this.updateRoundTimer(state.round_time_remaining || 0);

        // Update turn display
        if (state.current_turn) {
            this.updateTurnDisplay(state.current_turn);
        }

        // Update player status grid
        this.renderPlayerStatus(state.players || []);
    }

    updateTurnDisplay(turnInfo) {
        const questionerElem = document.getElementById('questioner-name');
        const answererElem = document.getElementById('answerer-name');

        if (questionerElem && turnInfo.questioner) {
            questionerElem.textContent = this.escapeHtml(turnInfo.questioner.name);
        }

        if (answererElem && turnInfo.answerer) {
            answererElem.textContent = this.escapeHtml(turnInfo.answerer.name);
        }
    }

    updateRoundTimer(timeRemaining) {
        const timerElem = document.getElementById('round-timer-host');
        if (!timerElem) return;

        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        const timerValue = timerElem.querySelector('.timer-value');

        if (timerValue) {
            timerValue.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    renderPlayerStatus(players) {
        const gridElem = document.getElementById('player-status-grid');
        if (!gridElem) return;

        gridElem.innerHTML = players.map(player => `
            <div class="player-status-card ${player.connected ? 'connected' : 'disconnected'}">
                <span class="player-name">${this.escapeHtml(player.name)}</span>
                <span class="connection-dot ${player.connected ? 'online' : 'offline'}"></span>
            </div>
        `).join('');
    }

    onStateUpdate(state) {
        this.state = state;

        // Hide all phase views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        // Show appropriate view
        switch (state.phase) {
            case 'LOBBY':
                this.showLobbyView(state);
                break;
            case 'ROLES':
                this.showRolesView(state);
                break;
            case 'QUESTIONING':
                this.showQuestioningView(state);
                break;
            // ... other phases ...
        }
    }

    showQuestioningView(state) {
        const questioningView = document.getElementById('questioning-view');
        if (questioningView) {
            questioningView.style.display = 'block';
            this.updateQuestioningView(state);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
const hostDisplay = new HostDisplay();
```

#### 5. Player Display UI (`www/player.html`)

Add turn indicator for player view:

```html
<!-- Questioning Phase View -->
<div id="questioning-view-player" class="phase-view">
    <div class="phase-header">
        <h2>Questioning Phase</h2>
        <div id="round-timer-player" class="timer-display">
            <span class="timer-value">0:00</span>
        </div>
    </div>

    <!-- Turn Info (subtle, informative) -->
    <div id="turn-info-player" class="turn-info-compact">
        <span id="questioner-name-player" class="name-highlight">Player A</span>
        <span class="turn-text">asks</span>
        <span id="answerer-name-player" class="name-highlight">Player B</span>
    </div>

    <!-- Role Reference (collapsible or always visible) -->
    <div id="role-reference" class="role-reference">
        <!-- Populated by JavaScript based on player role -->
    </div>

    <!-- Call Vote Button -->
    <div class="action-controls">
        <button id="call-vote-btn" class="btn-primary btn-large">
            CALL VOTE
        </button>
    </div>
</div>
```

#### 6. Player Display Logic (`www/js/player.js`)

Add turn info display:

```javascript
class PlayerDisplay {
    // ... existing methods ...

    updateQuestioningView(state) {
        // Update timer
        this.updateRoundTimer(state.round_time_remaining || 0);

        // Update turn info
        if (state.current_turn) {
            this.updateTurnInfo(state.current_turn);
        }

        // Update role reference based on player's role
        this.updateRoleReference(state);
    }

    updateTurnInfo(turnInfo) {
        const questionerElem = document.getElementById('questioner-name-player');
        const answererElem = document.getElementById('answerer-name-player');

        if (questionerElem && turnInfo.questioner) {
            questionerElem.textContent = this.escapeHtml(turnInfo.questioner.name);
        }

        if (answererElem && turnInfo.answerer) {
            answererElem.textContent = this.escapeHtml(turnInfo.answerer.name);
        }
    }

    updateRoundTimer(timeRemaining) {
        const timerElem = document.getElementById('round-timer-player');
        if (!timerElem) return;

        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        const timerValue = timerElem.querySelector('.timer-value');

        if (timerValue) {
            timerValue.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    updateRoleReference(state) {
        const roleRefElem = document.getElementById('role-reference');
        if (!roleRefElem) return;

        // Display role info based on whether player is spy
        if (state.is_spy) {
            // Show location list for spy
            roleRefElem.innerHTML = `
                <div class="role-header">Possible Locations:</div>
                <div class="location-list">
                    ${(state.location_list || []).map(loc =>
                        `<div class="location-item">${this.escapeHtml(loc)}</div>`
                    ).join('')}
                </div>
            `;
        } else {
            // Show location and role for non-spy
            roleRefElem.innerHTML = `
                <div class="role-info">
                    <div class="location-display">
                        <span class="label">Location:</span>
                        <span class="value">${this.escapeHtml(state.location || 'Unknown')}</span>
                    </div>
                    <div class="role-display">
                        <span class="label">Your Role:</span>
                        <span class="value">${this.escapeHtml(state.role || 'Unknown')}</span>
                    </div>
                </div>
            `;
        }
    }

    onStateUpdate(state) {
        this.state = state;

        // Hide all phase views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        // Show appropriate view
        switch (state.phase) {
            case 'LOBBY':
                this.showLobbyView(state);
                break;
            case 'ROLES':
                this.showRolesView(state);
                break;
            case 'QUESTIONING':
                this.showQuestioningView(state);
                break;
            // ... other phases ...
        }
    }

    showQuestioningView(state) {
        const questioningView = document.getElementById('questioning-view-player');
        if (questioningView) {
            questioningView.style.display = 'block';
            this.updateQuestioningView(state);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
const playerDisplay = new PlayerDisplay();
```

#### 7. CSS Styles (`www/css/styles.css`)

Add styling for turn displays:

```css
/* Host Display - Turn Indicator */
.turn-indicator {
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 2rem;
    margin: 2rem 0;
    text-align: center;
}

.turn-label {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-secondary);
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
}

.turn-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2rem;
}

.questioner-box,
.answerer-box {
    flex: 1;
    max-width: 300px;
}

.role-label {
    font-size: 0.9rem;
    color: var(--accent-secondary);
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.player-name-large {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--accent-primary);
    text-shadow: 0 0 20px var(--accent-primary-glow);
}

.turn-arrow {
    font-size: 3rem;
    color: var(--accent-secondary);
    animation: pulse-arrow 2s ease-in-out infinite;
}

@keyframes pulse-arrow {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
}

/* Player Display - Turn Info Compact */
.turn-info-compact {
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin: 1rem 0;
    text-align: center;
    font-size: 1rem;
    color: var(--text-primary);
}

.name-highlight {
    color: var(--accent-primary);
    font-weight: 700;
}

.turn-text {
    color: var(--text-secondary);
    padding: 0 0.5rem;
}

/* Role Reference */
.role-reference {
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin: 1rem 0;
}

.role-header {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--accent-secondary);
    margin-bottom: 0.5rem;
}

.location-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
}

.location-item {
    background: var(--background-color);
    padding: 0.5rem;
    border-radius: 4px;
    font-size: 0.85rem;
    text-align: center;
}

.role-info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.location-display,
.role-display {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.label {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

.value {
    color: var(--accent-primary);
    font-weight: 700;
    font-size: 1.1rem;
}

/* Player Status Grid (Host) */
.player-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 2rem;
}

.player-status-card {
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.connection-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}

.connection-dot.online {
    background: var(--success-color);
    box-shadow: 0 0 8px var(--success-color);
}

.connection-dot.offline {
    background: var(--error-color);
    opacity: 0.5;
}

/* Responsive - Host View (Tablet/TV) */
@media (min-width: 768px) {
    .player-name-large {
        font-size: 3.5rem;
    }

    .turn-indicator {
        padding: 3rem;
    }
}

/* Responsive - Player View (Mobile) */
@media (max-width: 428px) {
    .location-list {
        grid-template-columns: 1fr;
    }
}
```

### State Flow Diagram

```
ROLES Phase:
  └─> Role display timer expires (5s)
       └─> transition_to_questioning() called
            └─> Phase = QUESTIONING
            └─> initialize_turn_order():
                 ├─> Shuffle connected players
                 ├─> Set _turn_order
                 ├─> Set current_questioner_id = _turn_order[0]
                 ├─> Set current_answerer_id = _turn_order[1]
                 └─> Log initial turn
            └─> Broadcast state with current_turn:
                 ├─> Host: Shows large turn display
                 ├─> Players: Shows compact turn info
                 └─> All: Round timer starts

QUESTIONING Phase (Ongoing):
  └─> Players ask/answer verbally (no UI action)
       └─> Turn rotation (manual/future):
            └─> advance_turn() called (future enhancement)
                 ├─> Rotate questioner/answerer
                 ├─> Broadcast updated state
                 └─> UI updates automatically
```

### Turn Rotation Logic (MVP)

**MVP Implementation:**
- Turn order initialized on phase entry
- No automatic turn advancement
- Players self-manage turn rotation verbally
- Turn info displayed for reference only

**Future Enhancements:**
- Manual "Next Turn" button for host
- Automatic rotation after configurable time
- Skip disconnected players automatically
- Turn history tracking

## Implementation Tasks

### Task 1: Add Turn Fields to GameState

**File:** `custom_components/spyster/game/state.py`

1. Add `current_questioner_id` field to `__init__`
2. Add `current_answerer_id` field to `__init__`
3. Add `_turn_order` list field to `__init__`
4. Verify fields are initialized to `None` or empty list

**Validation:**
- Fields follow naming conventions (snake_case)
- Fields properly typed with type hints
- No runtime errors on GameState initialization

### Task 2: Implement Turn Management Methods

**File:** `custom_components/spyster/game/state.py`

1. Implement `initialize_turn_order()` method
2. Implement `advance_turn()` method (for future use)
3. Implement `get_current_turn_info()` helper
4. Add logging for all turn changes
5. Handle edge cases (disconnected players, < 2 players)

**Validation:**
- Turn order shuffled randomly each game
- First questioner/answerer set correctly
- Logging includes player names
- No crashes if player disconnects mid-turn

### Task 3: Update Phase Transition

**File:** `custom_components/spyster/game/state.py`

1. Modify `transition_to_questioning()` to call `initialize_turn_order()`
2. Ensure turn initialization happens before state broadcast
3. Add logging for turn initialization

**Validation:**
- Turns initialized immediately on phase entry
- State broadcast includes turn info
- No race conditions

### Task 4: Enhance State Serialization

**File:** `custom_components/spyster/game/state.py`

1. Update `get_state()` to include `current_turn` field
2. Call `get_current_turn_info()` for QUESTIONING phase only
3. Ensure turn info excluded in other phases

**Validation:**
- Turn info only present when phase == QUESTIONING
- Turn info includes questioner and answerer names + IDs
- No PII leaks (only name and ID included)

### Task 5: Create Host Display HTML

**File:** `custom_components/spyster/www/host.html`

1. Add QUESTIONING phase view structure
2. Add turn display section with questioner/answerer boxes
3. Add round timer display
4. Add player status grid
5. Ensure proper semantic HTML and ARIA attributes

**Validation:**
- Turn display prominently visible
- Layout works on 768px+ viewports
- Text readable from distance (large font sizes)

### Task 6: Implement Host Display Logic

**File:** `custom_components/spyster/www/js/host.js`

1. Add `updateQuestioningView()` method
2. Implement `updateTurnDisplay()` for turn info
3. Implement `updateRoundTimer()` for timer
4. Implement `renderPlayerStatus()` for player grid
5. Add phase routing for QUESTIONING
6. Add XSS escaping for all player names

**Validation:**
- Turn display updates in real-time
- Timer updates smoothly (no flicker)
- Player status reflects connection state
- No console errors

### Task 7: Create Player Display HTML

**File:** `custom_components/spyster/www/player.html`

1. Add QUESTIONING phase view structure
2. Add compact turn info display
3. Add round timer display
4. Add role reference section
5. Add "Call Vote" button (Story 4.5)

**Validation:**
- Layout works on 320-428px viewports
- Touch targets meet 44px minimum
- All interactive elements accessible

### Task 8: Implement Player Display Logic

**File:** `custom_components/spyster/www/js/player.js`

1. Add `updateQuestioningView()` method
2. Implement `updateTurnInfo()` for compact display
3. Implement `updateRoundTimer()` for timer
4. Implement `updateRoleReference()` for spy/non-spy layouts
5. Add phase routing for QUESTIONING
6. Add XSS escaping for all dynamic content

**Validation:**
- Turn info updates in real-time
- Spy and non-spy layouts identical dimensions (spy parity)
- Role info always accessible
- No console errors

### Task 9: Add CSS Styles

**File:** `custom_components/spyster/www/css/styles.css`

1. Style `.turn-indicator` for host display
2. Style `.player-name-large` with glow effect
3. Style `.turn-info-compact` for player display
4. Style `.role-reference` for both spy/non-spy
5. Add responsive breakpoints (768px, 428px)
6. Add animations (pulse-arrow, etc.)
7. Respect `prefers-reduced-motion`

**Validation:**
- Host view readable from 3+ meters
- Player view readable on small phones
- Animations smooth (60fps)
- Reduced motion respected

## Testing Strategy

### Unit Tests

**File:** `tests/test_state.py`

```python
def test_initialize_turn_order(game_state_with_players):
    """Test turn order initialization."""
    game_state_with_players.phase = GamePhase.QUESTIONING
    game_state_with_players.initialize_turn_order()

    assert len(game_state_with_players._turn_order) == 4
    assert game_state_with_players.current_questioner_id is not None
    assert game_state_with_players.current_answerer_id is not None
    assert game_state_with_players.current_questioner_id != game_state_with_players.current_answerer_id

def test_initialize_turn_order_shuffled(game_state_with_players):
    """Test turn order is shuffled (probabilistic)."""
    orders = []
    for _ in range(10):
        state = create_game_state_with_players(4)
        state.initialize_turn_order()
        orders.append(state._turn_order.copy())

    # At least some variation in 10 runs
    unique_orders = len(set(tuple(o) for o in orders))
    assert unique_orders > 1

def test_advance_turn(game_state_with_turns):
    """Test turn advancement."""
    initial_questioner = game_state_with_turns.current_questioner_id
    initial_answerer = game_state_with_turns.current_answerer_id

    game_state_with_turns.advance_turn()

    # Answerer became questioner
    assert game_state_with_turns.current_questioner_id == initial_answerer
    # New answerer is different
    assert game_state_with_turns.current_answerer_id != initial_answerer

def test_get_current_turn_info(game_state_with_turns):
    """Test turn info retrieval."""
    turn_info = game_state_with_turns.get_current_turn_info()

    assert "questioner" in turn_info
    assert "answerer" in turn_info
    assert "id" in turn_info["questioner"]
    assert "name" in turn_info["questioner"]

def test_get_current_turn_info_wrong_phase(game_state):
    """Test turn info empty in non-QUESTIONING phase."""
    game_state.phase = GamePhase.LOBBY
    turn_info = game_state.get_current_turn_info()

    assert turn_info == {}

def test_get_state_includes_turn_info(game_state_with_turns):
    """Test state includes turn info in QUESTIONING phase."""
    state = game_state_with_turns.get_state()

    assert "current_turn" in state
    assert state["current_turn"]["questioner"]["name"] is not None
```

### Integration Tests

**File:** `tests/test_integration_questioning.py`

```python
async def test_questioning_phase_turn_initialization(websocket_handler):
    """Test turns initialized on QUESTIONING phase entry."""
    # Setup: Game with 4 players in ROLES phase
    websocket_handler.game_state.phase = GamePhase.ROLES
    add_players(websocket_handler.game_state, 4)

    # Transition to QUESTIONING
    success, _ = websocket_handler.game_state.transition_to_questioning()

    assert success is True
    assert websocket_handler.game_state.current_questioner_id is not None
    assert websocket_handler.game_state.current_answerer_id is not None

async def test_turn_broadcast_to_all_players(websocket_handler, mock_websockets):
    """Test turn info broadcasted to all players."""
    # Setup: 4 players, QUESTIONING phase
    websocket_handler.game_state.phase = GamePhase.QUESTIONING
    websocket_handler.game_state.initialize_turn_order()

    # Broadcast state
    await websocket_handler.broadcast_state()

    # Verify all players received turn info
    for ws in mock_websockets:
        ws.send_json.assert_called()
        call_args = ws.send_json.call_args[0][0]
        assert "current_turn" in call_args
```

### Manual Testing Checklist

**Scenario 1: Turn Display on Phase Entry**
- [ ] Game transitions from ROLES to QUESTIONING
- [ ] Host display shows "Player A asks Player B" prominently
- [ ] Player displays show compact turn info
- [ ] Turn info matches on host and all players
- [ ] No console errors

**Scenario 2: Different Players Each Game**
- [ ] Play multiple games in a row
- [ ] First questioner is different each time (shuffled)
- [ ] Turn order varies between games
- [ ] All connected players included in rotation

**Scenario 3: Player Disconnection Handling**
- [ ] Game in QUESTIONING phase with 5 players
- [ ] Current questioner disconnects
- [ ] Turn info still displayed correctly
- [ ] No crashes or blank displays

**Scenario 4: Host Display Visibility**
- [ ] View host display from 3+ meters away
- [ ] Player names clearly readable
- [ ] Turn arrow visible
- [ ] Round timer prominent

**Scenario 5: Player Display Usability**
- [ ] View player display on phone (320px width)
- [ ] Turn info readable
- [ ] Role reference accessible
- [ ] "Call Vote" button reachable

**Scenario 6: Spy Parity**
- [ ] Non-spy player sees: Location + Role
- [ ] Spy player sees: Location list
- [ ] Both layouts have same height/spacing
- [ ] No visual tell to distinguish spy screen

## Definition of Done

- [ ] All code implemented following architecture patterns
- [ ] Turn order initialized on QUESTIONING phase entry
- [ ] Turn rotation logic implemented (for future use)
- [ ] State includes `current_turn` field when applicable
- [ ] Host display shows prominent turn indicator
- [ ] Player display shows compact turn info
- [ ] Role reference visible for both spy/non-spy
- [ ] All unit tests pass (100% coverage)
- [ ] Integration tests pass
- [ ] Manual testing scenarios completed
- [ ] XSS protection for all player names
- [ ] Logging includes turn changes
- [ ] No console errors or warnings
- [ ] Meets NFR4: State sync within 500ms
- [ ] Host view readable from distance (UX-16)
- [ ] Player view works on 320-428px (UX-15)
- [ ] Spy parity maintained (UX-9, UX-10)
- [ ] Accessibility: ARIA roles, semantic HTML
- [ ] Respects `prefers-reduced-motion`

## Notes

### Design Decisions

**MVP Turn Management:**
- No enforced turn advancement in UI
- Players manage turn rotation verbally
- Turn display is informational/reference only
- Simplifies initial implementation

**Rationale:**
- Spy Fall is a social deduction game
- Verbal interaction is core to gameplay
- Forced turn timers would disrupt natural flow
- UI provides structure without being restrictive

### Future Enhancements

1. **Manual Turn Advancement**: Host button to advance turn
2. **Turn Timer**: Optional timer per turn (e.g., 60s per Q&A)
3. **Turn History**: Track who has asked whom
4. **Smart Rotation**: Prevent asking same person twice in a row
5. **Turn Skipping**: Skip disconnected players automatically

### Performance Considerations

1. **Turn Order Shuffling**: O(n) on phase entry, not performance-critical
2. **State Broadcast**: Turn info adds ~100 bytes per broadcast
3. **UI Updates**: Minimal DOM manipulation (2 text updates)

### Security Considerations

1. **No Exploitable State**: Turn order doesn't reveal spy
2. **XSS Protection**: All player names escaped
3. **State Isolation**: Each player receives same turn info (no filtering needed)

## Related Stories

- **Depends On**:
  - Story 4.1: Transition to Questioning Phase (phase transition logic)
  - Story 4.2: Round Timer with Countdown (timer system)

- **Blocks**:
  - Story 4.4: Player Role View During Questioning (role reference UI)
  - Story 4.5: Call Vote Functionality (voting trigger)

- **Related**:
  - Story 3.5: Role Display UI (spy parity patterns)
  - Story 5.1: Voting Phase UI (next phase after vote called)

## Implementation Priority

**Priority**: MEDIUM
**Sprint**: Sprint 3
**Estimated Effort**: 3 hours

This story is important for gameplay clarity but does not block core functionality. Can be implemented alongside Story 4.4 (Role View) as they share UI components.
