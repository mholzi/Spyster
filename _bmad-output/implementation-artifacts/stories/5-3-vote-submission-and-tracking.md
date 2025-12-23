# Story 5.3: Vote Submission and Tracking

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.3
**Status:** ready-for-dev
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to lock in my vote and see who else has voted**,
So that **I know when everyone is ready for the reveal**.

---

## Acceptance Criteria

### AC1: Vote Submission

**Given** a player has selected a target and confidence
**When** they tap "Lock It In"
**Then** a `vote` message is sent with `{target, confidence}`
**And** the button transforms to "LOCKED ✓" (disabled)
**And** the player cannot change their vote

### AC2: Submission Tracking

**Given** votes are being submitted
**When** the server receives a vote
**Then** all clients receive updated submission count
**And** the tracker shows "4/7 voted" format

### AC3: Duplicate Vote Prevention

**Given** a player has already voted
**When** they try to vote again
**Then** they receive error `ERR_ALREADY_VOTED`

### AC4: Vote Data Storage

**Given** a vote is submitted
**When** stored on the server
**Then** it includes: player_name, target, confidence, timestamp

### AC5: All Votes Submitted Trigger

**Given** all connected players have voted
**When** the last vote is received
**Then** the vote timer is cancelled early
**And** transition to REVEAL phase begins immediately

---

## Requirements Coverage

### Functional Requirements

- **FR32**: All players can select who they suspect is the Spy
- **FR33**: All players can set their confidence bet (1, 2, or 3 points)
- **FR37**: Players can see who voted for whom and at what confidence level (after reveal)

### UX Requirements

- **UX-7**: Submission tracker: "4/7 voted" pattern with real-time updates

### Architectural Requirements

- **ARCH-12**: Message format: `{"type": "vote", "target": "...", "confidence": N}`
- **ARCH-13**: Error responses must include `code` + `message`
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on state-mutating methods
- **ARCH-19**: Return pattern: `(success: bool, error_code: str | None)`

---

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Add vote-related error codes:

```python
# Error codes for voting (Story 5.3)
ERR_ALREADY_VOTED = "ALREADY_VOTED"
ERR_INVALID_TARGET = "INVALID_TARGET"
ERR_NO_TARGET_SELECTED = "NO_TARGET_SELECTED"

# Add to ERROR_MESSAGES dict
ERROR_MESSAGES = {
    # ... existing messages ...
    ERR_ALREADY_VOTED: "You've already submitted your vote.",
    ERR_INVALID_TARGET: "Invalid vote target.",
    ERR_NO_TARGET_SELECTED: "Please select a player to vote for.",
}
```

#### 2. GameState (`game/state.py`)

Add vote storage and submission:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        # Story 5.3: Vote tracking
        self.votes: dict[str, dict] = {}  # {player_name: {target, confidence, timestamp}}

    def record_vote(
        self,
        player_name: str,
        target: str,
        confidence: int
    ) -> tuple[bool, str | None]:
        """
        Record a player's vote (Story 5.3).

        Args:
            player_name: Name of player casting vote
            target: Name of player being voted for
            confidence: Confidence level (1, 2, or 3)

        Returns:
            (success: bool, error_code: str | None)
        """
        import time
        from .const import (
            ERR_INVALID_PHASE,
            ERR_ALREADY_VOTED,
            ERR_INVALID_TARGET,
            ERR_PLAYER_NOT_FOUND,
        )

        # Phase guard (ARCH-17)
        if self.phase != GamePhase.VOTE:
            _LOGGER.warning(
                "Cannot record vote - invalid phase: %s (player: %s)",
                self.phase,
                player_name
            )
            return False, ERR_INVALID_PHASE

        # Verify voter exists and is connected
        if player_name not in self.players:
            _LOGGER.warning("Vote from unknown player: %s", player_name)
            return False, ERR_PLAYER_NOT_FOUND

        voter = self.players[player_name]
        if not voter.connected:
            _LOGGER.warning("Vote from disconnected player: %s", player_name)
            return False, ERR_PLAYER_NOT_FOUND

        # Check for duplicate vote (AC3)
        if player_name in self.votes:
            _LOGGER.warning("Duplicate vote attempt: %s", player_name)
            return False, ERR_ALREADY_VOTED

        # Validate target exists and is not self
        if target not in self.players:
            _LOGGER.warning("Vote for invalid target: %s -> %s", player_name, target)
            return False, ERR_INVALID_TARGET

        if target == player_name:
            _LOGGER.warning("Player tried to vote for self: %s", player_name)
            return False, ERR_INVALID_TARGET

        # Validate confidence (1, 2, or 3)
        if confidence not in [1, 2, 3]:
            confidence = 1  # Default to 1 if invalid

        # Record vote (AC4)
        self.votes[player_name] = {
            "target": target,
            "confidence": confidence,
            "timestamp": time.time(),
        }

        _LOGGER.info(
            "Vote recorded: %s -> %s (confidence: %d, total: %d/%d)",
            player_name,
            target,
            confidence,
            len(self.votes),
            len([p for p in self.players.values() if p.connected])
        )

        # Check if all votes are in (AC5)
        if self._all_votes_submitted():
            _LOGGER.info("All votes submitted - triggering early transition to REVEAL")
            # Cancel vote timer
            self.cancel_timer("vote")
            # Transition will be handled by caller

        return True, None

    def _all_votes_submitted(self) -> bool:
        """Check if all connected players have voted."""
        connected_players = [
            p.name for p in self.players.values() if p.connected
        ]
        return all(name in self.votes for name in connected_players)

    def get_vote_stats(self) -> dict:
        """Get vote submission statistics for tracker."""
        connected_count = len([p for p in self.players.values() if p.connected])
        voted_count = len(self.votes)
        return {
            "votes_submitted": voted_count,
            "total_players": connected_count,
            "all_voted": voted_count >= connected_count,
        }

    def reset_votes(self) -> None:
        """Reset votes for new round."""
        self.votes = {}
        _LOGGER.debug("Votes reset")

    def get_state(self, for_player: str | None = None) -> dict[str, Any]:
        # ... in VOTE phase section ...
        elif self.phase == GamePhase.VOTE:
            # Include vote stats for tracker (AC2)
            vote_stats = self.get_vote_stats()
            state.update(vote_stats)

            # Include if current player has voted (for UI state)
            if for_player:
                state["has_voted"] = for_player in self.votes
```

#### 3. WebSocket Handler (`server/websocket.py`)

Add vote message handler:

```python
async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    # ... existing handlers ...

    if msg_type == "vote":
        await self._handle_vote(ws, data)
        return

async def _handle_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
    """Handle vote submission."""
    from ..const import (
        ERR_NOT_IN_GAME,
        ERR_NO_TARGET_SELECTED,
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

    # Extract vote data
    target = data.get("target")
    confidence = data.get("confidence", 1)

    # Validate target provided
    if not target:
        await ws.send_json({
            "type": "error",
            "code": ERR_NO_TARGET_SELECTED,
            "message": ERROR_MESSAGES[ERR_NO_TARGET_SELECTED]
        })
        return

    # Record vote
    success, error = self.game_state.record_vote(player_name, target, confidence)

    if not success:
        await ws.send_json({
            "type": "error",
            "code": error,
            "message": ERROR_MESSAGES.get(error, "Could not record vote.")
        })
        return

    _LOGGER.info("Vote submitted: %s -> %s (confidence: %d)", player_name, target, confidence)

    # Broadcast updated state (includes vote count)
    await self.broadcast_state()

    # Check if all votes submitted - trigger reveal
    if self.game_state._all_votes_submitted():
        await self._trigger_reveal()

async def _trigger_reveal(self) -> None:
    """Trigger transition to REVEAL phase."""
    if self.game_state.phase != GamePhase.VOTE:
        return

    _LOGGER.info("Transitioning to REVEAL phase (all votes in)")
    self.game_state.phase = GamePhase.REVEAL

    # Broadcast the phase change
    await self.broadcast_state()
```

#### 4. Player Display Logic (`www/js/player.js`)

Add vote submission:

```javascript
class PlayerDisplay {
    constructor() {
        // ... existing init ...
        this.hasVoted = false;
    }

    setupEventListeners() {
        // ... existing listeners ...

        // Submit vote button
        const submitBtn = document.getElementById('submit-vote-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitVote());
        }
    }

    submitVote() {
        // Prevent double submission
        if (this.hasVoted) {
            console.log('Already voted');
            return;
        }

        // Validate selection
        if (!this.selectedVoteTarget) {
            this.showError('Please select a player to vote for.');
            return;
        }

        // Send vote message
        const voteData = {
            type: 'vote',
            target: this.selectedVoteTarget,
            confidence: this.selectedConfidence || 1
        };

        this.ws.send(JSON.stringify(voteData));
        console.log('Vote submitted:', voteData);

        // Update UI immediately (optimistic)
        this.lockVoteUI();
    }

    lockVoteUI() {
        this.hasVoted = true;

        // Disable submit button
        const submitBtn = document.getElementById('submit-vote-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'LOCKED ✓';
            submitBtn.classList.add('btn-locked');
        }

        // Disable player cards
        document.querySelectorAll('.player-card').forEach(card => {
            card.classList.add('player-card--locked');
            card.disabled = true;
        });

        // Disable confidence buttons
        document.querySelectorAll('.confidence-btn').forEach(btn => {
            btn.classList.add('confidence-btn--locked');
            btn.disabled = true;
        });
    }

    onStateUpdate(state) {
        // ... existing code ...

        // Update vote tracker
        if (state.votes_submitted !== undefined && state.total_players !== undefined) {
            this.updateVoteTracker(state.votes_submitted, state.total_players);
        }

        // Update local voted state from server
        if (state.has_voted !== undefined) {
            this.hasVoted = state.has_voted;
            if (this.hasVoted) {
                this.lockVoteUI();
            }
        }
    }

    updateVoteTracker(submitted, total) {
        const tracker = document.getElementById('vote-tracker');
        if (!tracker) return;

        tracker.textContent = `${submitted}/${total} voted`;
        tracker.setAttribute('aria-valuenow', submitted);
        tracker.setAttribute('aria-valuemax', total);

        // Visual feedback when all voted
        if (submitted >= total) {
            tracker.classList.add('vote-tracker--complete');
        }
    }

    showVoteView(state) {
        // ... existing code ...

        // Reset vote state for new round
        this.hasVoted = false;
        this.selectedVoteTarget = null;
        this.selectedConfidence = 1;
    }
}
```

#### 5. CSS Styles (`www/css/styles.css`)

Add locked state styles:

```css
/* =================================
   LOCKED VOTE STATE
   ================================= */

.btn-locked {
    background: var(--color-success) !important;
    border-color: var(--color-success) !important;
    cursor: not-allowed;
}

.player-card--locked {
    opacity: 0.6;
    cursor: not-allowed;
    pointer-events: none;
}

.confidence-btn--locked {
    opacity: 0.6;
    cursor: not-allowed;
    pointer-events: none;
}

/* =================================
   VOTE TRACKER
   ================================= */

#vote-tracker {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-secondary);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
}

.vote-tracker--complete {
    color: var(--color-success);
    background: rgba(0, 255, 100, 0.1);
}

/* =================================
   SUCCESS COLOR
   ================================= */

:root {
    --color-success: #00ff64;
}
```

---

## Implementation Tasks

### Task 1: Add Constants (AC: 3)
- [ ] Add ERR_ALREADY_VOTED error code
- [ ] Add ERR_INVALID_TARGET error code
- [ ] Add ERR_NO_TARGET_SELECTED error code
- [ ] Add error messages

### Task 2: Implement record_vote Method (AC: 1, 3, 4)
- [ ] Phase guard validation
- [ ] Duplicate vote check
- [ ] Target validation
- [ ] Store vote with timestamp
- [ ] Return (success, error) pattern

### Task 3: Implement Vote Stats (AC: 2, 5)
- [ ] get_vote_stats() method
- [ ] _all_votes_submitted() check
- [ ] Include in get_state()

### Task 4: Add WebSocket Handler (AC: 1, 3)
- [ ] Handle "vote" message type
- [ ] Validate payload
- [ ] Call record_vote()
- [ ] Broadcast updated state

### Task 5: Implement Frontend Submission (AC: 1)
- [ ] submitVote() method
- [ ] Send vote message
- [ ] Lock UI after submission
- [ ] Update button to "LOCKED ✓"

### Task 6: Implement Tracker UI (AC: 2)
- [ ] updateVoteTracker() method
- [ ] "X/Y voted" format
- [ ] ARIA progressbar attributes

### Task 7: Handle All Votes (AC: 5)
- [ ] Detect all votes submitted
- [ ] Cancel vote timer
- [ ] Trigger REVEAL transition

### Task 8: Write Tests
- [ ] test_record_vote_success
- [ ] test_record_vote_duplicate
- [ ] test_record_vote_invalid_target
- [ ] test_all_votes_triggers_reveal

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_record_vote_success(game_state_in_vote):
    """Test successful vote recording."""
    success, error = game_state_in_vote.record_vote("Alice", "Bob", 2)

    assert success is True
    assert error is None
    assert "Alice" in game_state_in_vote.votes
    assert game_state_in_vote.votes["Alice"]["target"] == "Bob"
    assert game_state_in_vote.votes["Alice"]["confidence"] == 2

@pytest.mark.asyncio
async def test_record_vote_duplicate(game_state_in_vote):
    """Test duplicate vote prevention."""
    game_state_in_vote.record_vote("Alice", "Bob", 2)
    success, error = game_state_in_vote.record_vote("Alice", "Charlie", 1)

    assert success is False
    assert error == ERR_ALREADY_VOTED

@pytest.mark.asyncio
async def test_record_vote_invalid_target(game_state_in_vote):
    """Test voting for invalid target."""
    success, error = game_state_in_vote.record_vote("Alice", "NonExistent", 1)

    assert success is False
    assert error == ERR_INVALID_TARGET

@pytest.mark.asyncio
async def test_record_vote_self(game_state_in_vote):
    """Test cannot vote for self."""
    success, error = game_state_in_vote.record_vote("Alice", "Alice", 1)

    assert success is False
    assert error == ERR_INVALID_TARGET

def test_all_votes_submitted(game_state_in_vote):
    """Test all votes detection."""
    # Vote for all but one player
    for i, player in enumerate(list(game_state_in_vote.players.keys())[:-1]):
        target = list(game_state_in_vote.players.keys())[(i+1) % len(game_state_in_vote.players)]
        game_state_in_vote.record_vote(player, target, 1)

    assert game_state_in_vote._all_votes_submitted() is False

    # Last player votes
    last_player = list(game_state_in_vote.players.keys())[-1]
    target = list(game_state_in_vote.players.keys())[0]
    game_state_in_vote.record_vote(last_player, target, 1)

    assert game_state_in_vote._all_votes_submitted() is True
```

### Manual Testing Checklist

**Scenario 1: Vote Submission**
- [ ] Select player card
- [ ] Select confidence
- [ ] Tap "Lock It In"
- [ ] Button shows "LOCKED ✓"
- [ ] Cards and buttons become disabled

**Scenario 2: Vote Tracker**
- [ ] Shows "0/7 voted" initially
- [ ] Updates as votes come in
- [ ] Real-time across all clients

**Scenario 3: Duplicate Prevention**
- [ ] Cannot click submit again after voting
- [ ] Server rejects duplicate vote message

**Scenario 4: All Votes Submitted**
- [ ] Timer cancels when all vote
- [ ] Immediate transition to REVEAL

---

## Definition of Done

- [ ] Vote submission sends {target, confidence} message
- [ ] Button transforms to "LOCKED ✓" after submit
- [ ] UI locked after submission
- [ ] Vote tracker updates in real-time
- [ ] Duplicate votes rejected with error
- [ ] All votes triggers early REVEAL transition
- [ ] Vote timer cancelled on all votes
- [ ] Error codes in const.py
- [ ] Unit tests pass
- [ ] No console errors

---

## Dependencies

### Depends On
- **Story 5.1**: Voting Phase UI (player selection)
- **Story 5.2**: Confidence Betting (confidence value)
- **Story 4.5**: Call Vote (VOTE phase entry)

### Enables
- **Story 5.5**: Vote Timer and Abstain Handling
- **Story 5.6**: Vote and Bet Reveal Sequence
- **Story 5.7**: Conviction Logic

---

## Architecture Decisions Referenced

- **ARCH-12**: Message format `{"type": "vote", ...}`
- **ARCH-13**: Error responses with code + message
- **ARCH-14**: Broadcast after mutations
- **ARCH-17**: Phase guards
- **ARCH-19**: Return pattern (bool, error)
- **UX-7**: Submission tracker pattern

---

## Dev Notes

### WebSocket Message Format

```json
// Client -> Server
{
    "type": "vote",
    "target": "Bob",
    "confidence": 2
}

// Server -> Client (state update)
{
    "type": "state",
    "phase": "VOTE",
    "votes_submitted": 4,
    "total_players": 7,
    "has_voted": true
}
```

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/const.py` | Modify | Add vote error codes |
| `custom_components/spyster/game/state.py` | Modify | Add record_vote(), vote tracking |
| `custom_components/spyster/server/websocket.py` | Modify | Add vote handler |
| `custom_components/spyster/www/js/player.js` | Modify | Add submitVote(), lockVoteUI() |
| `custom_components/spyster/www/css/styles.css` | Modify | Add locked state styles |
| `tests/test_state.py` | Modify | Add vote tests |

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Completion Notes List
_To be filled during implementation_

### File List
_To be filled during implementation_
