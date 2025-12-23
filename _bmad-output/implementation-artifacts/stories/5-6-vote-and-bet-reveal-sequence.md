# Story 5.6: Vote and Bet Reveal Sequence

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.6
**Status:** ready-for-dev
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to see everyone's votes and bets revealed dramatically**,
So that **I can experience the tension and excitement of the reveal**.

---

## Acceptance Criteria

### AC1: Reveal Phase Transition

**Given** the vote phase ends (timer or all voted)
**When** transitioning to REVEAL phase
**Then** a brief delay (3 seconds) builds anticipation (TIMER_REVEAL_DELAY)

### AC2: Vote Reveal Display

**Given** the reveal phase begins
**When** votes are displayed
**Then** each player's vote target is shown
**And** each player's confidence level is shown (1, 2, or ALL IN)
**And** abstentions are clearly marked

### AC3: Spy Guess Reveal

**Given** the spy chose to guess location
**When** votes are revealed
**Then** the spy's guess is shown separately
**And** whether the guess was correct is indicated

### AC4: Results Summary

**Given** all votes are revealed
**When** the summary is shown
**Then** the most-voted player is highlighted
**And** vote counts per player are visible

### AC5: Simultaneous Reveal

**Given** reveal is triggered
**When** votes are shown
**Then** all votes appear at the same time (no sequential reveal for MVP)
**And** all connected players see the same reveal simultaneously

---

## Requirements Coverage

### Functional Requirements

- **FR37**: Players can see who voted for whom and at what confidence level
- **FR38**: Voting results (who was convicted) are shown to all players simultaneously
- **FR43**: Spy location guess result is revealed

### UX Requirements

- **UX-10**: Reveal animations build tension

### Architectural Requirements

- **ARCH-4**: Flat phase state machine (VOTE → REVEAL → SCORING)
- **ARCH-10**: Reveal delay = 3 seconds
- **ARCH-14**: Broadcast after mutations

---

## Technical Design

### Component Changes

#### 1. Constants (`const.py`)

Verify reveal constants exist:

```python
# Timer durations (should already exist from Story 4.1)
TIMER_REVEAL_DELAY = 3  # Delay before reveal sequence

# Add reveal-specific constants
REVEAL_ANIMATION_DURATION = 0.5  # seconds per vote animation
```

#### 2. GameState (`game/state.py`)

Add reveal phase handling:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        # Story 5.6: Reveal tracking
        self.convicted_player: str | None = None  # Most voted player
        self.vote_results: dict = {}  # Aggregated vote results

    def calculate_vote_results(self) -> dict:
        """
        Calculate vote results for reveal (Story 5.6).

        Returns:
            dict with vote tallies and convicted player
        """
        # Count votes per target
        vote_counts: dict[str, int] = {}
        for voter_name, vote_data in self.votes.items():
            target = vote_data.get("target")
            if target:  # Ignore abstentions
                vote_counts[target] = vote_counts.get(target, 0) + 1

        # Find most voted (convicted) - ties go to first alphabetically
        convicted = None
        max_votes = 0
        for target, count in sorted(vote_counts.items()):
            if count > max_votes:
                max_votes = count
                convicted = target

        self.convicted_player = convicted
        self.vote_results = {
            "vote_counts": vote_counts,
            "convicted": convicted,
            "max_votes": max_votes,
            "total_votes": len([v for v in self.votes.values() if v.get("target")]),
            "abstentions": len([v for v in self.votes.values() if v.get("abstained")]),
        }

        _LOGGER.info(
            "Vote results calculated: convicted=%s (%d votes), %d abstentions",
            convicted,
            max_votes,
            self.vote_results["abstentions"]
        )

        return self.vote_results

    def get_state(self, for_player: str | None = None) -> dict[str, Any]:
        # ... existing code ...

        elif self.phase == GamePhase.REVEAL:
            # All votes visible in reveal (FR37)
            state["votes"] = [
                {
                    "voter": voter_name,
                    "target": vote_data.get("target"),
                    "confidence": vote_data.get("confidence", 0),
                    "abstained": vote_data.get("abstained", False),
                }
                for voter_name, vote_data in self.votes.items()
            ]

            # Vote results summary
            if not self.vote_results:
                self.calculate_vote_results()
            state["vote_results"] = self.vote_results
            state["convicted"] = self.convicted_player

            # Actual spy identity (revealed after voting)
            state["actual_spy"] = self._spy_name

            # Location reveal
            state["location"] = {
                "id": self._current_location.get("id"),
                "name": self._current_location.get("name"),
            }

            # Spy guess result (if applicable)
            if self.spy_guess:
                state["spy_guess"] = {
                    "guessed": True,
                    "location_id": self.spy_guess.get("location_id"),
                    "correct": self.spy_guess.get("correct"),
                }
            else:
                state["spy_guess"] = {"guessed": False}

        return state

    async def transition_to_reveal(self) -> tuple[bool, str | None]:
        """
        Transition to REVEAL phase with delay (Story 5.6).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE, TIMER_REVEAL_DELAY

        if self.phase != GamePhase.VOTE:
            return False, ERR_INVALID_PHASE

        # Cancel vote timer if still running
        self.cancel_timer("vote")

        # Calculate results before reveal
        self.calculate_vote_results()

        # Start reveal delay timer
        self.start_timer(
            "reveal_delay",
            float(TIMER_REVEAL_DELAY),
            self._on_reveal_delay_complete
        )

        _LOGGER.info("Starting reveal delay (%d seconds)", TIMER_REVEAL_DELAY)
        return True, None

    async def _on_reveal_delay_complete(self, timer_name: str) -> None:
        """Complete transition to REVEAL after delay."""
        _LOGGER.info("Reveal delay complete - transitioning to REVEAL phase")
        self.phase = GamePhase.REVEAL
        # Note: WebSocket handler will broadcast state
```

#### 3. WebSocket Handler (`server/websocket.py`)

Update reveal transition handling:

```python
async def _trigger_reveal(self) -> None:
    """Trigger transition to REVEAL phase."""
    if self.game_state.phase != GamePhase.VOTE:
        return

    # Calculate results and start reveal delay
    success, error = await self.game_state.transition_to_reveal()
    if not success:
        _LOGGER.error("Failed to start reveal transition: %s", error)
        return

    # Broadcast intermediate state (reveal pending)
    await self.broadcast_state()

    # Note: actual REVEAL phase broadcast happens after delay timer callback
```

#### 4. Player Display HTML (`www/player.html`)

Add reveal phase view:

```html
<!-- Reveal Phase View -->
<div id="reveal-view" class="phase-view" style="display: none;">
    <!-- Reveal header -->
    <div class="reveal-header">
        <h1 class="reveal-title">The Votes Are In!</h1>
    </div>

    <!-- Spy guess result (if applicable) -->
    <div id="spy-guess-result" class="reveal-section" style="display: none;">
        <div class="reveal-card reveal-card--spy">
            <h2 class="reveal-card-title">Spy's Location Guess</h2>
            <div id="spy-guess-location" class="reveal-highlight"></div>
            <div id="spy-guess-outcome" class="reveal-outcome"></div>
        </div>
    </div>

    <!-- Vote results grid -->
    <div class="reveal-section">
        <h2 class="reveal-section-title">Who Voted For Whom</h2>
        <div id="reveal-votes-grid" class="reveal-votes-grid">
            <!-- Vote cards injected dynamically -->
        </div>
    </div>

    <!-- Convicted player -->
    <div id="conviction-result" class="reveal-section">
        <div class="reveal-card reveal-card--convicted">
            <h2 class="reveal-card-title">Most Votes</h2>
            <div id="convicted-player" class="reveal-highlight"></div>
            <div id="conviction-count" class="reveal-subtext"></div>
        </div>
    </div>

    <!-- Actual spy reveal -->
    <div class="reveal-section">
        <div class="reveal-card reveal-card--spy-identity">
            <h2 class="reveal-card-title">The Spy Was...</h2>
            <div id="actual-spy" class="reveal-highlight reveal-spy-name"></div>
        </div>
    </div>

    <!-- Location reveal -->
    <div class="reveal-section">
        <div class="reveal-card reveal-card--location">
            <h2 class="reveal-card-title">The Location Was</h2>
            <div id="actual-location" class="reveal-highlight"></div>
        </div>
    </div>

    <!-- Continue to scoring -->
    <div class="reveal-actions">
        <div id="reveal-countdown" class="reveal-countdown">
            Scoring in <span id="scoring-countdown">5</span>...
        </div>
    </div>
</div>
```

#### 5. Player Display Logic (`www/js/player.js`)

Add reveal view rendering:

```javascript
class PlayerDisplay {
    showRevealView(state) {
        // Hide all other views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        const revealView = document.getElementById('reveal-view');
        if (revealView) {
            revealView.style.display = 'block';
        }

        // Render vote cards
        this.renderVoteCards(state.votes);

        // Show spy guess result if applicable
        if (state.spy_guess && state.spy_guess.guessed) {
            this.renderSpyGuessResult(state.spy_guess);
        }

        // Show convicted player
        if (state.vote_results) {
            this.renderConvictionResult(state.vote_results);
        }

        // Show actual spy
        if (state.actual_spy) {
            const spyEl = document.getElementById('actual-spy');
            if (spyEl) {
                spyEl.textContent = this.escapeHtml(state.actual_spy);

                // Highlight if current player is spy
                if (state.actual_spy === this.playerName) {
                    spyEl.classList.add('reveal-spy-name--self');
                }
            }
        }

        // Show location
        if (state.location) {
            const locationEl = document.getElementById('actual-location');
            if (locationEl) {
                locationEl.textContent = this.escapeHtml(state.location.name);
            }
        }

        // Start auto-transition countdown
        this.startScoringCountdown();
    }

    renderVoteCards(votes) {
        const grid = document.getElementById('reveal-votes-grid');
        if (!grid) return;

        grid.innerHTML = '';

        votes.forEach(vote => {
            const card = document.createElement('div');
            card.className = 'reveal-vote-card';

            if (vote.abstained) {
                card.classList.add('reveal-vote-card--abstained');
                card.innerHTML = `
                    <div class="vote-voter">${this.escapeHtml(vote.voter)}</div>
                    <div class="vote-arrow">→</div>
                    <div class="vote-target vote-abstained">Abstained</div>
                `;
            } else {
                // Add confidence styling
                const confidenceClass = vote.confidence === 3
                    ? 'confidence-all-in'
                    : `confidence-${vote.confidence}`;
                card.classList.add(confidenceClass);

                const confidenceLabel = vote.confidence === 3 ? 'ALL IN' : vote.confidence;

                card.innerHTML = `
                    <div class="vote-voter">${this.escapeHtml(vote.voter)}</div>
                    <div class="vote-arrow">→</div>
                    <div class="vote-target">${this.escapeHtml(vote.target)}</div>
                    <div class="vote-confidence">${confidenceLabel}</div>
                `;
            }

            grid.appendChild(card);
        });
    }

    renderSpyGuessResult(spyGuess) {
        const container = document.getElementById('spy-guess-result');
        if (!container) return;

        container.style.display = 'block';

        const locationEl = document.getElementById('spy-guess-location');
        const outcomeEl = document.getElementById('spy-guess-outcome');

        if (locationEl) {
            locationEl.textContent = spyGuess.location_id;  // TODO: Get location name
        }

        if (outcomeEl) {
            if (spyGuess.correct) {
                outcomeEl.textContent = 'CORRECT!';
                outcomeEl.className = 'reveal-outcome reveal-outcome--correct';
            } else {
                outcomeEl.textContent = 'WRONG!';
                outcomeEl.className = 'reveal-outcome reveal-outcome--wrong';
            }
        }
    }

    renderConvictionResult(voteResults) {
        const playerEl = document.getElementById('convicted-player');
        const countEl = document.getElementById('conviction-count');

        if (playerEl) {
            if (voteResults.convicted) {
                playerEl.textContent = this.escapeHtml(voteResults.convicted);
            } else {
                playerEl.textContent = 'No one convicted';
            }
        }

        if (countEl && voteResults.max_votes > 0) {
            countEl.textContent = `${voteResults.max_votes} vote${voteResults.max_votes > 1 ? 's' : ''}`;
        }
    }

    startScoringCountdown() {
        const countdownEl = document.getElementById('scoring-countdown');
        let seconds = 5;

        const interval = setInterval(() => {
            seconds--;
            if (countdownEl) {
                countdownEl.textContent = seconds.toString();
            }

            if (seconds <= 0) {
                clearInterval(interval);
                // Server will transition to SCORING
            }
        }, 1000);
    }

    onStateUpdate(state) {
        // ... existing code ...

        if (state.phase === 'REVEAL') {
            this.showRevealView(state);
        }
    }
}
```

#### 6. CSS Styles (`www/css/styles.css`)

Add reveal phase styles:

```css
/* =================================
   REVEAL PHASE LAYOUT
   ================================= */

#reveal-view {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    padding: var(--spacing-md);
    gap: var(--spacing-lg);
    animation: fadeIn 0.5s ease-out;
}

.reveal-header {
    text-align: center;
    padding: var(--spacing-lg);
}

.reveal-title {
    font-size: 28px;
    font-weight: 800;
    color: var(--color-text-primary);
    animation: slideDown 0.5s ease-out;
}

.reveal-section {
    animation: fadeIn 0.5s ease-out;
    animation-fill-mode: both;
}

.reveal-section:nth-child(2) { animation-delay: 0.2s; }
.reveal-section:nth-child(3) { animation-delay: 0.4s; }
.reveal-section:nth-child(4) { animation-delay: 0.6s; }
.reveal-section:nth-child(5) { animation-delay: 0.8s; }

.reveal-section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-md);
    text-align: center;
}

/* =================================
   REVEAL CARDS
   ================================= */

.reveal-card {
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    text-align: center;
    border: 2px solid var(--color-border);
}

.reveal-card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--spacing-sm);
}

.reveal-highlight {
    font-size: 24px;
    font-weight: 800;
    color: var(--color-text-primary);
}

.reveal-subtext {
    font-size: 14px;
    color: var(--color-text-secondary);
    margin-top: var(--spacing-xs);
}

/* Spy identity card */
.reveal-card--spy-identity {
    border-color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.1);
}

.reveal-spy-name {
    color: var(--color-accent-primary);
}

.reveal-spy-name--self {
    animation: pulse-glow 1s infinite;
}

/* Location card */
.reveal-card--location {
    border-color: var(--color-accent-secondary);
    background: rgba(0, 245, 255, 0.1);
}

.reveal-card--location .reveal-highlight {
    color: var(--color-accent-secondary);
}

/* =================================
   VOTE CARDS GRID
   ================================= */

.reveal-votes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-md);
}

.reveal-vote-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--color-border);
}

.vote-voter {
    font-weight: 600;
    color: var(--color-text-primary);
    min-width: 60px;
}

.vote-arrow {
    color: var(--color-text-tertiary);
}

.vote-target {
    flex: 1;
    font-weight: 500;
    color: var(--color-text-primary);
}

.vote-abstained {
    font-style: italic;
    color: var(--color-text-tertiary);
}

.vote-confidence {
    font-size: 12px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
}

/* Confidence styling */
.confidence-1 { border-left-color: var(--color-text-tertiary); }
.confidence-2 { border-left-color: var(--color-warning); }
.confidence-all-in {
    border-left-color: var(--color-gold);
}
.confidence-all-in .vote-confidence {
    background: var(--color-gold);
    color: black;
}

.reveal-vote-card--abstained {
    opacity: 0.6;
    border-left-color: var(--color-text-tertiary);
}

/* =================================
   SPY GUESS RESULT
   ================================= */

.reveal-card--spy {
    border-color: var(--color-accent-primary);
}

.reveal-outcome {
    font-size: 18px;
    font-weight: 800;
    margin-top: var(--spacing-sm);
}

.reveal-outcome--correct {
    color: var(--color-success);
}

.reveal-outcome--wrong {
    color: var(--color-danger);
}

/* =================================
   SCORING COUNTDOWN
   ================================= */

.reveal-countdown {
    text-align: center;
    font-size: 16px;
    color: var(--color-text-secondary);
    padding: var(--spacing-lg);
}

#scoring-countdown {
    font-weight: 700;
    color: var(--color-accent-secondary);
}

/* =================================
   ANIMATIONS
   ================================= */

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes pulse-glow {
    0%, 100% {
        text-shadow: 0 0 10px rgba(255, 45, 106, 0.5);
    }
    50% {
        text-shadow: 0 0 20px rgba(255, 45, 106, 0.8);
    }
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    #reveal-view,
    .reveal-section,
    .reveal-title {
        animation: none;
    }

    .reveal-spy-name--self {
        animation: none;
        text-shadow: 0 0 10px rgba(255, 45, 106, 0.5);
    }
}
```

---

## Implementation Tasks

### Task 1: Add Reveal Transition (AC: 1, 5)
- [x] transition_to_reveal() method
- [x] Reveal delay timer (3s)
- [x] Calculate vote results before reveal

### Task 2: Update get_state for Reveal (AC: 2, 3, 4)
- [x] Include all votes in REVEAL state
- [x] Include vote_results summary
- [x] Include spy identity
- [x] Include location
- [x] Include spy guess result

### Task 3: Add Vote Results Calculation (AC: 4)
- [x] calculate_vote_results() method
- [x] Count votes per target
- [x] Determine convicted player
- [x] Handle ties

### Task 4: Add Reveal View HTML (AC: 2, 3, 4)
- [x] Vote cards grid
- [x] Spy guess result section
- [x] Conviction result section
- [x] Spy/location reveal sections

### Task 5: Implement Reveal Rendering (AC: 2, 3, 4)
- [x] renderVoteCards() method
- [x] renderSpyGuessResult() method
- [x] renderConvictionResult() method
- [x] Confidence styling

### Task 6: Add CSS Styles (AC: All)
- [x] Reveal layout
- [x] Vote card styles
- [x] Confidence color coding
- [x] Entrance animations
- [x] Reduced motion support

### Task 7: Write Tests
- [ ] test_vote_results_calculation
- [ ] test_reveal_state_includes_all_data
- [ ] test_tie_handling

---

## Testing Strategy

### Unit Tests

```python
def test_calculate_vote_results(game_state_in_vote):
    """Test vote results calculation."""
    players = list(game_state_in_vote.players.keys())

    # Alice votes for Bob (conf 2)
    # Charlie votes for Bob (conf 3)
    # Bob votes for Alice (conf 1)
    game_state_in_vote.record_vote(players[0], players[1], 2)
    game_state_in_vote.record_vote(players[2], players[1], 3)
    game_state_in_vote.record_vote(players[1], players[0], 1)

    results = game_state_in_vote.calculate_vote_results()

    assert results["convicted"] == players[1]  # Bob (2 votes)
    assert results["max_votes"] == 2
    assert results["vote_counts"][players[1]] == 2

def test_reveal_state_includes_votes(game_state_in_reveal):
    """Test REVEAL state includes all votes."""
    state = game_state_in_reveal.get_state()

    assert "votes" in state
    assert "vote_results" in state
    assert "actual_spy" in state
    assert "location" in state
```

### Manual Testing Checklist

**Scenario 1: Vote to Reveal Transition**
- [ ] 3-second delay after voting ends
- [ ] Reveal view appears with animation
- [ ] All sections animate in sequence

**Scenario 2: Vote Display**
- [ ] All player votes visible
- [ ] Confidence levels shown (1, 2, ALL IN)
- [ ] Abstentions marked clearly
- [ ] Confidence color coding correct

**Scenario 3: Spy Guess**
- [ ] Spy guess section shows if applicable
- [ ] CORRECT/WRONG clearly indicated
- [ ] Guessed location shown

**Scenario 4: Results Summary**
- [ ] Most-voted player highlighted
- [ ] Vote count displayed
- [ ] Actual spy revealed
- [ ] Location revealed

---

## Definition of Done

- [x] 3-second reveal delay
- [x] All votes displayed with target and confidence
- [x] Abstentions marked
- [x] Spy guess result shown (if applicable)
- [x] Convicted player highlighted
- [x] Actual spy revealed
- [x] Location revealed
- [x] Entrance animations work
- [x] Reduced motion respected
- [ ] Unit tests pass
- [x] No console errors

---

## Dependencies

### Depends On
- **Story 5.3**: Vote Submission (votes data)
- **Story 5.4**: Spy Location Guess (spy guess data)
- **Story 5.5**: Vote Timer (timer expiry handling)

### Enables
- **Story 5.7**: Conviction Logic
- **Story 6.2**: Vote Scoring Calculation

---

## Architecture Decisions Referenced

- **ARCH-4**: Phase state machine (VOTE → REVEAL)
- **ARCH-10**: TIMER_REVEAL_DELAY = 3 seconds
- **ARCH-14**: Broadcast after mutations
- **UX-10**: Reveal animations

---

## Dev Notes

### Tie Breaking

For MVP, ties are broken alphabetically:
```python
for target, count in sorted(vote_counts.items()):
    if count > max_votes:
        max_votes = count
        convicted = target
```

Future enhancement: Random tie-breaker or shared conviction.

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/game/state.py` | Modify | Add reveal methods |
| `custom_components/spyster/server/websocket.py` | Modify | Update reveal trigger |
| `custom_components/spyster/www/player.html` | Modify | Add reveal-view HTML |
| `custom_components/spyster/www/js/player.js` | Modify | Add reveal rendering |
| `custom_components/spyster/www/css/styles.css` | Modify | Add reveal styles |
| `tests/test_state.py` | Modify | Add reveal tests |

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Completion Notes List
_To be filled during implementation_

### File List
_To be filled during implementation_
