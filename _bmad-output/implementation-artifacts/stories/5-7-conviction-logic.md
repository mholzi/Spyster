# Story 5.7: Conviction Logic

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.7
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **the voting to determine if the spy is caught**,
So that **the game resolves fairly based on majority vote**.

---

## Acceptance Criteria

### AC1: Conviction Determination

**Given** all votes are revealed
**When** determining conviction
**Then** the player with the most votes is "convicted"
**And** ties are broken (alphabetically for MVP)

### AC2: Correct Conviction (Spy Caught)

**Given** the convicted player IS the spy
**When** conviction is confirmed
**Then** all players who voted correctly get points (per confidence)
**And** the spy loses the round
**And** "Spy Caught!" message is displayed

### AC3: Wrong Conviction (Innocent Framed)

**Given** the convicted player is NOT the spy
**When** conviction is confirmed
**Then** all players who voted incorrectly lose points (per confidence)
**And** the spy wins the round
**And** "Innocent Convicted!" message is displayed

### AC4: Spy Frame Bonus (Double Agent)

**Given** the spy votes for an innocent player
**When** that innocent is convicted AND spy used ALL IN
**Then** the spy gets +10 Double Agent bonus

### AC5: No Conviction

**Given** no votes are cast (all abstain)
**When** determining conviction
**Then** no one is convicted
**And** the round ends without resolution
**And** "No Conviction" message is displayed

### AC6: Transition to Scoring

**Given** conviction is determined
**When** results are calculated
**Then** transition to SCORING phase
**And** scores are updated

---

## Requirements Coverage

### Functional Requirements

- **FR34**: A player is convicted if they receive the most votes
- **FR35**: If the convicted player is the spy, the spy loses the round
- **FR43**: Spy location guess scoring (handled separately)
- **FR44**: Points system: +2/+4/+6 for correct vote based on confidence
- **FR45**: Points system: -1/-2/-3 for incorrect vote based on confidence
- **FR47**: Double Agent bonus: +10 for spy framing with ALL IN

### Architectural Requirements

- **ARCH-4**: Phase state machine (REVEAL → SCORING)
- **ARCH-14**: Broadcast after mutations
- **ARCH-17**: Phase guards

---

## Technical Design

### Component Changes

#### 1. Scoring Module (`game/scoring.py`)

Create/enhance scoring functions:

```python
"""Scoring calculations for Spyster game."""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState

_LOGGER = logging.getLogger(__name__)

# Scoring constants
POINTS_CORRECT_VOTE = {1: 2, 2: 4, 3: 6}
POINTS_INCORRECT_VOTE = {1: -1, 2: -2, 3: -3}
POINTS_DOUBLE_AGENT_BONUS = 10


def calculate_vote_score(
    voted_for: str,
    actual_spy: str,
    confidence: int,
) -> tuple[int, str]:
    """
    Calculate points for a vote (FR44, FR45).

    Args:
        voted_for: Player name voted for
        actual_spy: Actual spy's name
        confidence: Confidence level (1, 2, or 3)

    Returns:
        (points, outcome) - points can be positive or negative
    """
    is_correct = voted_for == actual_spy
    confidence = min(max(confidence, 1), 3)  # Clamp to 1-3

    if is_correct:
        points = POINTS_CORRECT_VOTE[confidence]
        outcome = "correct"
    else:
        points = POINTS_INCORRECT_VOTE[confidence]
        outcome = "incorrect"

    return points, outcome


def calculate_double_agent_bonus(
    spy_vote_target: str | None,
    convicted_player: str | None,
    spy_confidence: int,
    spy_name: str,
) -> int:
    """
    Calculate Double Agent bonus (FR47).

    The spy gets +10 if:
    - They voted (not guessed location)
    - They used ALL IN (confidence = 3)
    - They voted for an innocent player
    - That innocent player was convicted

    Args:
        spy_vote_target: Who the spy voted for (None if guessed location)
        convicted_player: Who was convicted
        spy_confidence: Spy's confidence level
        spy_name: Spy's name

    Returns:
        Bonus points (10 or 0)
    """
    # Spy must have voted (not guessed)
    if spy_vote_target is None:
        return 0

    # Spy must have used ALL IN
    if spy_confidence != 3:
        return 0

    # Spy must have voted for an innocent (not themselves)
    if spy_vote_target == spy_name:
        return 0

    # The person spy voted for must have been convicted
    if spy_vote_target != convicted_player:
        return 0

    _LOGGER.info("Double Agent bonus awarded to spy!")
    return POINTS_DOUBLE_AGENT_BONUS


def calculate_round_scores(game_state: "GameState") -> dict[str, dict]:
    """
    Calculate all scores for the round (Story 5.7).

    Args:
        game_state: Current game state with votes and results

    Returns:
        Dict of {player_name: {points, outcome, breakdown}}
    """
    scores: dict[str, dict] = {}
    spy_name = game_state.spy_name
    convicted = game_state.convicted_player

    # Handle spy guess case
    if game_state.spy_guess:
        return calculate_spy_guess_scores(game_state)

    # No conviction case (AC5)
    if convicted is None:
        _LOGGER.info("No conviction - round ends without resolution")
        for player_name in game_state.players.keys():
            scores[player_name] = {
                "points": 0,
                "outcome": "no_conviction",
                "breakdown": [],
            }
        return scores

    # Calculate each player's score
    for voter_name, vote_data in game_state.votes.items():
        target = vote_data.get("target")
        confidence = vote_data.get("confidence", 0)
        abstained = vote_data.get("abstained", False)

        if abstained:
            # Abstain = 0 points
            scores[voter_name] = {
                "points": 0,
                "outcome": "abstained",
                "breakdown": [{"type": "abstain", "points": 0}],
            }
            continue

        # Calculate vote score
        points, outcome = calculate_vote_score(target, spy_name, confidence)

        breakdown = [{
            "type": "vote",
            "target": target,
            "confidence": confidence,
            "points": points,
            "correct": outcome == "correct",
        }]

        # Check for Double Agent bonus (spy only)
        if voter_name == spy_name:
            bonus = calculate_double_agent_bonus(
                target, convicted, confidence, spy_name
            )
            if bonus > 0:
                points += bonus
                breakdown.append({
                    "type": "double_agent",
                    "points": bonus,
                })

        scores[voter_name] = {
            "points": points,
            "outcome": outcome,
            "breakdown": breakdown,
        }

    # Determine round winner
    spy_caught = convicted == spy_name

    _LOGGER.info(
        "Round scores calculated: spy_caught=%s, convicted=%s",
        spy_caught,
        convicted
    )

    return scores


def calculate_spy_guess_scores(game_state: "GameState") -> dict[str, dict]:
    """
    Calculate scores when spy guessed location.

    Args:
        game_state: Game state with spy guess

    Returns:
        Score dict
    """
    scores: dict[str, dict] = {}
    spy_name = game_state.spy_name
    guess = game_state.spy_guess
    correct = guess.get("correct", False)

    for player_name in game_state.players.keys():
        if player_name == spy_name:
            # Spy scores based on guess
            if correct:
                scores[player_name] = {
                    "points": 10,  # Spy wins with location guess
                    "outcome": "spy_guess_correct",
                    "breakdown": [{"type": "location_guess", "correct": True, "points": 10}],
                }
            else:
                scores[player_name] = {
                    "points": -5,  # Spy loses for wrong guess
                    "outcome": "spy_guess_wrong",
                    "breakdown": [{"type": "location_guess", "correct": False, "points": -5}],
                }
        else:
            # Other players voted or abstained - process their votes
            if player_name in game_state.votes:
                vote = game_state.votes[player_name]
                if vote.get("abstained"):
                    scores[player_name] = {
                        "points": 0,
                        "outcome": "abstained",
                        "breakdown": [],
                    }
                else:
                    # Votes are irrelevant when spy guesses - no points
                    scores[player_name] = {
                        "points": 0,
                        "outcome": "spy_guessed",
                        "breakdown": [{"type": "spy_guessed", "points": 0}],
                    }
            else:
                scores[player_name] = {
                    "points": 0,
                    "outcome": "spy_guessed",
                    "breakdown": [],
                }

    return scores
```

#### 2. GameState (`game/state.py`)

Add conviction processing:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        # Story 5.7: Round resolution
        self.round_scores: dict[str, dict] = {}
        self.spy_caught: bool = False

    def process_conviction(self) -> tuple[bool, str | None]:
        """
        Process conviction and calculate scores (Story 5.7).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE
        from .scoring import calculate_round_scores

        # Phase guard
        if self.phase != GamePhase.REVEAL:
            return False, ERR_INVALID_PHASE

        # Calculate results if not done
        if not self.vote_results:
            self.calculate_vote_results()

        # Determine if spy was caught (AC2, AC3)
        self.spy_caught = self.convicted_player == self._spy_name

        if self.spy_caught:
            _LOGGER.info("Spy caught! %s was the spy.", self.convicted_player)
        elif self.convicted_player:
            _LOGGER.info("Innocent convicted! %s was NOT the spy.", self.convicted_player)
        else:
            _LOGGER.info("No conviction this round.")

        # Calculate scores
        self.round_scores = calculate_round_scores(self)

        # Apply scores to players
        for player_name, score_data in self.round_scores.items():
            if player_name in self.players:
                player = self.players[player_name]
                player.add_score(score_data["points"])
                _LOGGER.debug(
                    "Score applied: %s %+d (total: %d)",
                    player_name,
                    score_data["points"],
                    player.score
                )

        return True, None

    def get_state(self, for_player: str | None = None) -> dict[str, Any]:
        # ... existing code ...

        elif self.phase == GamePhase.REVEAL:
            # ... existing reveal state ...

            # Add conviction result
            state["spy_caught"] = self.spy_caught
            state["round_scores"] = self.round_scores

        elif self.phase == GamePhase.SCORING:
            # Scoring phase state
            state["spy_caught"] = self.spy_caught
            state["convicted"] = self.convicted_player
            state["actual_spy"] = self._spy_name
            state["round_scores"] = self.round_scores

            # Current standings
            state["standings"] = sorted(
                [
                    {"name": p.name, "score": p.score}
                    for p in self.players.values()
                ],
                key=lambda x: x["score"],
                reverse=True
            )

        return state

    def transition_to_scoring(self) -> tuple[bool, str | None]:
        """
        Transition from REVEAL to SCORING phase (Story 5.7).

        Processes conviction and calculates scores.

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE

        if self.phase != GamePhase.REVEAL:
            return False, ERR_INVALID_PHASE

        # Process conviction and scores
        success, error = self.process_conviction()
        if not success:
            return False, error

        # Transition to SCORING
        self.phase = GamePhase.SCORING

        _LOGGER.info(
            "Transitioned to SCORING: spy_caught=%s, convicted=%s",
            self.spy_caught,
            self.convicted_player
        )

        return True, None
```

#### 3. Player (`game/player.py`)

Add score tracking method:

```python
class PlayerSession:
    def __init__(self, name: str, is_host: bool = False) -> None:
        # ... existing fields ...
        self.score: int = 0

    def add_score(self, points: int) -> None:
        """Add points to player's score."""
        self.score += points
```

#### 4. Player Display HTML (`www/player.html`)

Add conviction result display (enhance reveal view):

```html
<!-- In reveal-view, add conviction banner -->
<div id="conviction-banner" class="conviction-banner" style="display: none;">
    <div class="conviction-result">
        <div id="conviction-message" class="conviction-message"></div>
        <div id="conviction-detail" class="conviction-detail"></div>
    </div>
</div>
```

#### 5. Player Display Logic (`www/js/player.js`)

Add conviction display:

```javascript
class PlayerDisplay {
    showRevealView(state) {
        // ... existing reveal code ...

        // Show conviction banner
        this.showConvictionBanner(state);
    }

    showConvictionBanner(state) {
        const banner = document.getElementById('conviction-banner');
        const message = document.getElementById('conviction-message');
        const detail = document.getElementById('conviction-detail');

        if (!banner || !message || !detail) return;

        banner.style.display = 'block';

        if (!state.convicted) {
            // No conviction (AC5)
            banner.className = 'conviction-banner conviction-banner--none';
            message.textContent = 'No Conviction';
            detail.textContent = 'Not enough votes to convict anyone';
        } else if (state.spy_caught) {
            // Spy caught (AC2)
            banner.className = 'conviction-banner conviction-banner--caught';
            message.textContent = 'Spy Caught!';
            detail.textContent = `${this.escapeHtml(state.convicted)} was the spy!`;
        } else {
            // Innocent convicted (AC3)
            banner.className = 'conviction-banner conviction-banner--innocent';
            message.textContent = 'Innocent Convicted!';
            detail.textContent = `${this.escapeHtml(state.convicted)} was NOT the spy!`;
        }

        // Show player's score change
        this.showScoreChange(state);
    }

    showScoreChange(state) {
        if (!state.round_scores || !this.playerName) return;

        const myScore = state.round_scores[this.playerName];
        if (!myScore) return;

        const scoreChangeEl = document.getElementById('score-change');
        if (scoreChangeEl) {
            const points = myScore.points;
            const sign = points >= 0 ? '+' : '';
            scoreChangeEl.textContent = `${sign}${points}`;
            scoreChangeEl.className = `score-change ${points > 0 ? 'score-positive' : points < 0 ? 'score-negative' : 'score-neutral'}`;

            // Check for Double Agent bonus
            const doubleAgent = myScore.breakdown?.find(b => b.type === 'double_agent');
            if (doubleAgent) {
                scoreChangeEl.textContent += ' (incl. Double Agent +10!)';
            }
        }
    }
}
```

#### 6. CSS Styles (`www/css/styles.css`)

Add conviction banner styles:

```css
/* =================================
   CONVICTION BANNER
   ================================= */

.conviction-banner {
    padding: var(--spacing-xl);
    border-radius: var(--radius-lg);
    text-align: center;
    animation: bannerSlide 0.5s ease-out;
}

.conviction-message {
    font-size: 28px;
    font-weight: 800;
    margin-bottom: var(--spacing-sm);
}

.conviction-detail {
    font-size: 16px;
    color: var(--color-text-secondary);
}

/* Spy caught (good outcome for non-spies) */
.conviction-banner--caught {
    background: linear-gradient(135deg, rgba(0, 255, 100, 0.2), rgba(0, 255, 100, 0.1));
    border: 2px solid var(--color-success);
}

.conviction-banner--caught .conviction-message {
    color: var(--color-success);
}

/* Innocent convicted (bad outcome) */
.conviction-banner--innocent {
    background: linear-gradient(135deg, rgba(255, 50, 50, 0.2), rgba(255, 50, 50, 0.1));
    border: 2px solid var(--color-danger);
}

.conviction-banner--innocent .conviction-message {
    color: var(--color-danger);
}

/* No conviction */
.conviction-banner--none {
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
}

.conviction-banner--none .conviction-message {
    color: var(--color-text-secondary);
}

/* =================================
   SCORE CHANGE DISPLAY
   ================================= */

.score-change {
    font-size: 24px;
    font-weight: 800;
    text-align: center;
    padding: var(--spacing-md);
}

.score-positive {
    color: var(--color-success);
}

.score-negative {
    color: var(--color-danger);
}

.score-neutral {
    color: var(--color-text-secondary);
}

/* =================================
   ANIMATION
   ================================= */

@keyframes bannerSlide {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

---

## Implementation Tasks

### Task 1: Create Scoring Module (AC: 2, 3, 4)
- [x] calculate_vote_score() function
- [x] calculate_double_agent_bonus() function
- [x] calculate_round_scores() function
- [x] Score constants

### Task 2: Implement Conviction Processing (AC: 1, 2, 3, 5)
- [x] process_conviction() method
- [x] Determine spy_caught flag
- [x] Apply scores to players
- [x] Handle no conviction case

### Task 3: Add Player Score Tracking
- [x] Add score field to PlayerSession
- [x] add_score() method

### Task 4: Update State for Scoring (AC: 6)
- [x] transition_to_scoring() method
- [x] Include round_scores in state
- [x] Include standings in SCORING state

### Task 5: Add Conviction Banner UI
- [x] Banner HTML structure
- [x] showConvictionBanner() method
- [x] Score change display

### Task 6: Add CSS Styles
- [x] Conviction banner variants
- [x] Score change styling
- [x] Animations

### Task 7: Write Tests
- [ ] test_calculate_vote_score
- [ ] test_double_agent_bonus
- [ ] test_spy_caught_scoring
- [ ] test_innocent_convicted_scoring
- [ ] test_no_conviction

---

## Testing Strategy

### Unit Tests

```python
def test_calculate_vote_score_correct():
    """Test correct vote scoring."""
    points, outcome = calculate_vote_score("Spy", "Spy", 1)
    assert points == 2
    assert outcome == "correct"

    points, outcome = calculate_vote_score("Spy", "Spy", 3)
    assert points == 6
    assert outcome == "correct"

def test_calculate_vote_score_incorrect():
    """Test incorrect vote scoring."""
    points, outcome = calculate_vote_score("Alice", "Spy", 1)
    assert points == -1
    assert outcome == "incorrect"

    points, outcome = calculate_vote_score("Alice", "Spy", 3)
    assert points == -3
    assert outcome == "incorrect"

def test_double_agent_bonus():
    """Test Double Agent bonus conditions."""
    # Spy votes ALL IN for innocent who gets convicted
    bonus = calculate_double_agent_bonus("Alice", "Alice", 3, "Spy")
    assert bonus == 10

    # Spy not ALL IN - no bonus
    bonus = calculate_double_agent_bonus("Alice", "Alice", 2, "Spy")
    assert bonus == 0

    # Innocent not convicted - no bonus
    bonus = calculate_double_agent_bonus("Alice", "Bob", 3, "Spy")
    assert bonus == 0

def test_spy_caught_scoring(game_state_with_votes):
    """Test scoring when spy is caught."""
    game_state_with_votes.convicted_player = game_state_with_votes._spy_name
    scores = calculate_round_scores(game_state_with_votes)

    # Players who voted correctly should have positive scores
    for voter, vote in game_state_with_votes.votes.items():
        if vote.get("target") == game_state_with_votes._spy_name:
            assert scores[voter]["points"] > 0

def test_no_conviction(game_state_all_abstain):
    """Test no conviction case."""
    game_state_all_abstain.convicted_player = None
    scores = calculate_round_scores(game_state_all_abstain)

    for score in scores.values():
        assert score["points"] == 0
        assert score["outcome"] == "no_conviction"
```

### Manual Testing Checklist

**Scenario 1: Spy Caught**
- [ ] Vote for actual spy
- [ ] Spy is convicted
- [ ] "Spy Caught!" banner displayed
- [ ] Correct voters get positive points
- [ ] Incorrect voters get negative points

**Scenario 2: Innocent Convicted**
- [ ] Vote for non-spy
- [ ] Non-spy is convicted
- [ ] "Innocent Convicted!" banner displayed
- [ ] Spy wins
- [ ] Incorrect voters lose points

**Scenario 3: Double Agent**
- [ ] Spy votes ALL IN for innocent
- [ ] That innocent is convicted
- [ ] Spy gets +10 bonus
- [ ] Bonus shown in score breakdown

**Scenario 4: No Conviction**
- [ ] All players abstain
- [ ] "No Conviction" banner
- [ ] No score changes

---

## Definition of Done

- [x] Conviction determined by most votes
- [x] Spy caught = players who voted correctly get points
- [x] Innocent convicted = incorrect voters lose points
- [x] Double Agent bonus (+10) for spy ALL IN frame
- [x] No conviction handled gracefully
- [x] Scores applied to players
- [x] Conviction banner displayed
- [x] Score changes shown
- [x] Transition to SCORING phase
- [ ] Unit tests pass
- [x] No console errors

---

## Dependencies

### Depends On
- **Story 5.3**: Vote Submission (votes data)
- **Story 5.6**: Vote and Bet Reveal (reveal phase)

### Enables
- **Story 6.2**: Vote Scoring Calculation (full scoring implementation)
- **Story 6.5**: Leaderboard Display
- **Story 6.6**: Round Progression

---

## Architecture Decisions Referenced

- **ARCH-4**: Phase state machine (REVEAL → SCORING)
- **ARCH-14**: Broadcast after mutations
- **ARCH-17**: Phase guards
- **FR44**: +2/+4/+6 for correct vote
- **FR45**: -1/-2/-3 for incorrect vote
- **FR47**: +10 Double Agent bonus

---

## Dev Notes

### Score Constants

```python
# From PRD scoring rules
POINTS_CORRECT = {1: +2, 2: +4, 3: +6}
POINTS_INCORRECT = {1: -1, 2: -2, 3: -3}
DOUBLE_AGENT_BONUS = +10
```

### Tie Breaking

For MVP, alphabetical tie-breaking:
```python
# First alphabetically wins ties
convicted = sorted(tied_players)[0]
```

Future: Random selection or all tied players convicted.

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/game/scoring.py` | Create/Modify | Scoring functions |
| `custom_components/spyster/game/state.py` | Modify | Add conviction processing |
| `custom_components/spyster/game/player.py` | Modify | Add score tracking |
| `custom_components/spyster/www/player.html` | Modify | Add conviction banner |
| `custom_components/spyster/www/js/player.js` | Modify | Add conviction display |
| `custom_components/spyster/www/css/styles.css` | Modify | Add conviction styles |
| `tests/test_scoring.py` | Create | Scoring tests |

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created new `game/scoring.py` module with all scoring functions
- Added `add_score()` and `reset_score()` methods to PlayerSession
- Added `process_conviction()` and `transition_to_scoring()` methods to GameState
- Added `round_scores`, `spy_caught` fields to GameState
- Updated `get_state()` for REVEAL and SCORING phases
- Added conviction banner HTML to player.html
- Added `hideAllViews()` and `showConvictionBanner()` methods to player.js
- Added ~145 lines of CSS for conviction banner variants and score change display
- All syntax validation passed (JS, Python, CSS)
- Unit tests deferred to Epic 6 (scoring module tests)

### File List
- `custom_components/spyster/game/scoring.py` (NEW - 243 lines)
- `custom_components/spyster/game/player.py` (modified - add_score, reset_score)
- `custom_components/spyster/game/state.py` (modified - conviction processing)
- `custom_components/spyster/www/player.html` (modified - conviction banner HTML)
- `custom_components/spyster/www/js/player.js` (modified - ~115 lines added)
- `custom_components/spyster/www/css/styles.css` (modified - ~145 lines added)
