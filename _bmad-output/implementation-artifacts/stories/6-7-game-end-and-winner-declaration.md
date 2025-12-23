# Story 6.7: Game End and Winner Declaration

**Epic:** Epic 6 - Scoring & Game Progression
**Story ID:** 6.7
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to see final results and the winner**,
So that **the game has a satisfying conclusion**.

---

## Acceptance Criteria

### AC1: Final Scores Display

**Given** all rounds are complete
**When** the game transitions to END phase
**Then** final scores are displayed (per FR52)
**And** all players see cumulative totals

### AC2: Winner Declaration

**Given** final scores are calculated
**When** displayed to players
**Then** the winner is declared (highest score per FR55)
**And** winner's name is prominently displayed

### AC3: Tie Handling

**Given** a tie for first place
**When** calculating winner
**Then** all tied players are declared co-winners
**And** both/all names are displayed

### AC4: Play Again Option

**Given** the host is viewing END phase
**When** the game has concluded
**Then** they see a "Play Again" button to start a new game
**And** player roster is preserved for new game

### AC5: End Session Option

**Given** the host is viewing END phase
**When** they want to end the session
**Then** they see an "End Session" button
**And** clicking it returns all to lobby state
**And** scores are reset

### AC6: Manual End Game

**Given** the host is in any phase (FR7)
**When** they tap "End Game" in admin controls
**Then** a confirmation modal appears
**And** confirming transitions to END phase immediately
**And** current scores become final scores

### AC7: Game Statistics

**Given** the game ends
**When** viewing final results
**Then** summary statistics are shown:
- Total rounds played
- Most caught spy (player caught most as spy)
- Best double agent (if any)

---

## Requirements Coverage

### Functional Requirements

- **FR7**: Host can end the current game session at any time
- **FR52**: Players can see final scores at game end
- **FR55**: System declares winner at end of configured rounds

### Architectural Requirements

- **ARCH-4**: Phase state machine (SCORING → END)
- **ARCH-14**: Broadcast after mutations

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Add game end methods:

```python
class GameState:
    def __init__(self) -> None:
        # ... existing fields ...
        self.winner: list[str] | None = None  # Can be multiple if tie
        self.final_standings: list[dict] = []
        self.game_stats: dict = {}

    def end_game(self) -> tuple[bool, str | None]:
        """
        End the game and calculate final results (Story 6.7).

        Returns:
            (success: bool, error_code: str | None)
        """
        # Can be called from SCORING (normal) or any phase (forced)
        if self.phase == GamePhase.END:
            return False, "ERR_ALREADY_ENDED"

        # Calculate final standings
        self._calculate_final_standings()

        # Determine winner(s)
        self._determine_winner()

        # Calculate game statistics
        self._calculate_game_stats()

        # Transition to END phase
        self.phase = GamePhase.END

        _LOGGER.info(
            "Game ended: winner(s)=%s, rounds_played=%d",
            self.winner,
            self.current_round
        )

        return True, None

    def _calculate_final_standings(self) -> None:
        """Calculate final standings sorted by score."""
        self.final_standings = sorted(
            [
                {
                    "name": player.name,
                    "score": player.score,
                    "rank": 0,  # Will be set below
                }
                for player in self.players.values()
            ],
            key=lambda x: x["score"],
            reverse=True
        )

        # Assign ranks (handling ties)
        current_rank = 1
        for i, standing in enumerate(self.final_standings):
            if i > 0 and standing["score"] < self.final_standings[i-1]["score"]:
                current_rank = i + 1
            standing["rank"] = current_rank

    def _determine_winner(self) -> None:
        """Determine winner(s) - handles ties."""
        if not self.final_standings:
            self.winner = []
            return

        top_score = self.final_standings[0]["score"]
        self.winner = [
            standing["name"]
            for standing in self.final_standings
            if standing["score"] == top_score
        ]

    def _calculate_game_stats(self) -> None:
        """Calculate game statistics for display."""
        # Count times each player was spy
        spy_counts: dict[str, int] = {}
        spy_caught_counts: dict[str, int] = {}
        double_agent_count: dict[str, int] = {}

        for round_data in self.round_history:
            spy = round_data.get("spy")
            if spy:
                spy_counts[spy] = spy_counts.get(spy, 0) + 1
                if round_data.get("spy_caught"):
                    spy_caught_counts[spy] = spy_caught_counts.get(spy, 0) + 1

            # Check for double agent in round scores
            for player, score_data in round_data.get("scores", {}).items():
                breakdown = score_data.get("breakdown", [])
                for item in breakdown:
                    if item.get("type") == "double_agent":
                        double_agent_count[player] = double_agent_count.get(player, 0) + 1

        self.game_stats = {
            "rounds_played": self.current_round,
            "total_rounds": self.num_rounds,
            "spy_counts": spy_counts,
            "spy_caught_counts": spy_caught_counts,
            "double_agent_counts": double_agent_count,
            "most_caught_spy": max(spy_caught_counts, key=spy_caught_counts.get) if spy_caught_counts else None,
            "best_double_agent": max(double_agent_count, key=double_agent_count.get) if double_agent_count else None,
        }

    def reset_for_new_game(self) -> tuple[bool, str | None]:
        """
        Reset game state for a new game (Play Again).

        Preserves player roster, resets scores and game state.
        """
        if self.phase != GamePhase.END:
            return False, "ERR_INVALID_PHASE"

        # Reset scores
        for player in self.players.values():
            player.reset_score()

        # Reset game state
        self.current_round = 0
        self.round_history = []
        self.winner = None
        self.final_standings = []
        self.game_stats = {}
        self.votes = {}
        self.vote_results = None
        self.convicted_player = None
        self.spy_guess = None
        self.round_scores = {}
        self.spy_caught = False
        self._spy_name = None
        self._current_location = None

        # Return to LOBBY
        self.phase = GamePhase.LOBBY

        _LOGGER.info("Game reset for new game, players preserved")
        return True, None

    def get_state(self, for_player: str | None = None) -> dict:
        # ... existing code ...

        elif self.phase == GamePhase.END:
            state["winner"] = self.winner
            state["final_standings"] = self.final_standings
            state["game_stats"] = self.game_stats
            state["is_winner"] = for_player in (self.winner or [])

        return state
```

#### 2. WebSocket Handler (`server/websocket.py`)

Add admin actions for end game:

```python
async def _handle_admin_action(self, action: str, data: dict) -> None:
    """Handle admin actions from host."""
    if action == "end_game":
        await self._handle_end_game()
    elif action == "play_again":
        await self._handle_play_again()
    elif action == "end_session":
        await self._handle_end_session()

async def _handle_end_game(self) -> None:
    """Force end the game."""
    game = self._get_game_state()
    success, error = game.end_game()
    if success:
        await self._broadcast_state()
    else:
        await self._send_error(error)

async def _handle_play_again(self) -> None:
    """Start a new game with same players."""
    game = self._get_game_state()
    success, error = game.reset_for_new_game()
    if success:
        await self._broadcast_state()

async def _handle_end_session(self) -> None:
    """End session completely, clear all players."""
    # Reset to fresh state
    game = self._get_game_state()
    game.reset_all()
    await self._broadcast_state()
```

#### 3. Player Display HTML (`www/player.html`)

Add end game view:

```html
<!-- End Game View (Story 6.7) -->
<div id="end-view" class="phase-view" style="display: none;">
    <!-- Winner Banner -->
    <div id="winner-banner" class="winner-banner">
        <div class="winner-crown">&#128081;</div>
        <h1 id="winner-title" class="winner-title">Winner!</h1>
        <div id="winner-names" class="winner-names"></div>
    </div>

    <!-- Personal Result -->
    <div id="personal-result" class="personal-result-card">
        <div class="result-rank">
            <span id="final-rank">#1</span>
        </div>
        <div class="result-score">
            <span id="final-score">0</span> points
        </div>
    </div>

    <!-- Final Standings -->
    <div class="final-standings-section">
        <h2 class="section-title">Final Standings</h2>
        <div id="final-standings-list" class="standings-list">
            <!-- Standings items injected dynamically -->
        </div>
    </div>

    <!-- Game Stats -->
    <div id="game-stats" class="game-stats-section">
        <h2 class="section-title">Game Stats</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-label">Rounds Played</span>
                <span id="stat-rounds" class="stat-value">0</span>
            </div>
            <div class="stat-item" id="stat-spy-hunter" style="display: none;">
                <span class="stat-label">Best Spy Hunter</span>
                <span id="stat-spy-hunter-name" class="stat-value"></span>
            </div>
            <div class="stat-item" id="stat-double-agent" style="display: none;">
                <span class="stat-label">Master Double Agent</span>
                <span id="stat-double-agent-name" class="stat-value"></span>
            </div>
        </div>
    </div>

    <!-- Host Controls (only visible to host) -->
    <div id="host-end-controls" class="host-controls" style="display: none;">
        <button id="play-again-btn" class="btn btn-primary btn-large">
            Play Again
        </button>
        <button id="end-session-btn" class="btn btn-secondary">
            End Session
        </button>
    </div>
</div>
```

#### 4. Player Display Logic (`www/js/player.js`)

```javascript
class PlayerClient {
    handleEndPhase(state) {
        this.hideAllViews();

        const endView = document.getElementById('end-view');
        if (endView) {
            endView.style.display = 'block';
        }

        // Show winner banner
        this.showWinnerBanner(state);

        // Show personal result
        this.showPersonalResult(state);

        // Render final standings
        this.renderFinalStandings(state.final_standings);

        // Show game stats
        this.showGameStats(state.game_stats);

        // Setup host controls if applicable
        if (this.isHost) {
            this.setupHostEndControls();
        }
    }

    showWinnerBanner(state) {
        const banner = document.getElementById('winner-banner');
        const title = document.getElementById('winner-title');
        const names = document.getElementById('winner-names');

        if (!banner || !title || !names) return;

        const winners = state.winner || [];

        if (winners.length === 0) {
            title.textContent = 'Game Over';
            names.textContent = 'No winner';
        } else if (winners.length === 1) {
            title.textContent = 'Winner!';
            names.textContent = this.escapeHtml(winners[0]);
        } else {
            title.textContent = 'Winners!';
            names.textContent = winners.map(n => this.escapeHtml(n)).join(' & ');
        }

        // Highlight if current player won
        if (state.is_winner) {
            banner.classList.add('winner-banner--self');
        }
    }

    showPersonalResult(state) {
        const standings = state.final_standings || [];
        const myStanding = standings.find(s => s.name === this.playerName);

        if (!myStanding) return;

        const rankEl = document.getElementById('final-rank');
        const scoreEl = document.getElementById('final-score');

        if (rankEl) {
            rankEl.textContent = `#${myStanding.rank}`;
        }
        if (scoreEl) {
            scoreEl.textContent = myStanding.score;
        }

        // Special styling for podium positions
        const card = document.getElementById('personal-result');
        if (card) {
            card.classList.remove('rank-1', 'rank-2', 'rank-3');
            if (myStanding.rank <= 3) {
                card.classList.add(`rank-${myStanding.rank}`);
            }
        }
    }

    renderFinalStandings(standings) {
        const list = document.getElementById('final-standings-list');
        if (!list) return;

        list.innerHTML = '';

        standings.forEach((player) => {
            const item = document.createElement('div');
            const isSelf = player.name === this.playerName;
            item.className = `standing-item ${isSelf ? 'standing-item--self' : ''} standing-rank-${Math.min(player.rank, 4)}`;

            // Medal/trophy for top 3
            let rankIcon = player.rank.toString();
            if (player.rank === 1) rankIcon = '&#129351;'; // Gold medal
            if (player.rank === 2) rankIcon = '&#129352;'; // Silver medal
            if (player.rank === 3) rankIcon = '&#129353;'; // Bronze medal

            item.innerHTML = `
                <span class="standing-rank">${rankIcon}</span>
                <span class="standing-name">${this.escapeHtml(player.name)}</span>
                <span class="standing-score">${player.score}</span>
            `;

            list.appendChild(item);
        });
    }

    showGameStats(stats) {
        if (!stats) return;

        const roundsEl = document.getElementById('stat-rounds');
        if (roundsEl) {
            roundsEl.textContent = stats.rounds_played;
        }

        if (stats.most_caught_spy) {
            const container = document.getElementById('stat-spy-hunter');
            const nameEl = document.getElementById('stat-spy-hunter-name');
            if (container && nameEl) {
                container.style.display = 'block';
                nameEl.textContent = this.escapeHtml(stats.most_caught_spy);
            }
        }

        if (stats.best_double_agent) {
            const container = document.getElementById('stat-double-agent');
            const nameEl = document.getElementById('stat-double-agent-name');
            if (container && nameEl) {
                container.style.display = 'block';
                nameEl.textContent = this.escapeHtml(stats.best_double_agent);
            }
        }
    }

    setupHostEndControls() {
        const controls = document.getElementById('host-end-controls');
        if (controls) {
            controls.style.display = 'flex';
        }

        const playAgainBtn = document.getElementById('play-again-btn');
        const endSessionBtn = document.getElementById('end-session-btn');

        if (playAgainBtn && !playAgainBtn._hasListener) {
            playAgainBtn.addEventListener('click', () => {
                this.sendMessage({ type: 'admin', action: 'play_again' });
            });
            playAgainBtn._hasListener = true;
        }

        if (endSessionBtn && !endSessionBtn._hasListener) {
            endSessionBtn.addEventListener('click', () => {
                if (confirm('End session and return to lobby?')) {
                    this.sendMessage({ type: 'admin', action: 'end_session' });
                }
            });
            endSessionBtn._hasListener = true;
        }
    }
}
```

#### 5. CSS Styles (`www/css/styles.css`)

```css
/* ============================================================================
   STORY 6.7: END GAME VIEW
   ============================================================================ */

#end-view {
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
    padding: var(--space-md);
    text-align: center;
}

/* Winner Banner */
.winner-banner {
    padding: var(--space-xl);
    background: linear-gradient(135deg, var(--color-bg-secondary), var(--color-bg-tertiary));
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-all-in);
}

.winner-banner--self {
    border-color: var(--color-accent-primary);
    background: linear-gradient(135deg, rgba(255, 45, 106, 0.1), rgba(255, 45, 106, 0.05));
    animation: winner-pulse 2s infinite;
}

.winner-crown {
    font-size: 48px;
    margin-bottom: var(--space-sm);
}

.winner-title {
    font-size: 32px;
    font-weight: var(--font-weight-black);
    color: var(--color-all-in);
    text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
    margin-bottom: var(--space-sm);
}

.winner-names {
    font-size: 24px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
}

/* Personal Result Card */
.personal-result-card {
    padding: var(--space-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-bg-tertiary);
}

.personal-result-card.rank-1 {
    border-color: var(--color-all-in);
    background: rgba(255, 215, 0, 0.1);
}

.personal-result-card.rank-2 {
    border-color: #c0c0c0;
    background: rgba(192, 192, 192, 0.1);
}

.personal-result-card.rank-3 {
    border-color: #cd7f32;
    background: rgba(205, 127, 50, 0.1);
}

.result-rank {
    font-size: 36px;
    font-weight: var(--font-weight-black);
    color: var(--color-text-primary);
}

.result-score {
    font-size: 18px;
    color: var(--color-text-secondary);
}

/* Final Standings */
.final-standings-section {
    flex: 1;
}

.section-title {
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-secondary);
    margin-bottom: var(--space-md);
}

.standings-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
}

.standing-item {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
}

.standing-item--self {
    border: 2px solid var(--color-accent-primary);
}

.standing-rank-1 { background: rgba(255, 215, 0, 0.15); }
.standing-rank-2 { background: rgba(192, 192, 192, 0.15); }
.standing-rank-3 { background: rgba(205, 127, 50, 0.15); }

.standing-rank {
    font-size: 20px;
    min-width: 40px;
}

.standing-name {
    flex: 1;
    font-weight: var(--font-weight-medium);
    text-align: left;
}

.standing-score {
    font-weight: var(--font-weight-bold);
    color: var(--color-text-secondary);
}

/* Game Stats */
.game-stats-section {
    padding: var(--space-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: var(--space-md);
}

.stat-item {
    text-align: center;
}

.stat-label {
    display: block;
    font-size: 12px;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.stat-value {
    display: block;
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-top: var(--space-xs);
}

/* Host Controls */
.host-controls {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    padding: var(--space-lg);
}

/* Animations */
@keyframes winner-pulse {
    0%, 100% {
        box-shadow: 0 0 20px rgba(255, 45, 106, 0.3);
    }
    50% {
        box-shadow: 0 0 40px rgba(255, 45, 106, 0.5);
    }
}

@media (prefers-reduced-motion: reduce) {
    .winner-banner--self {
        animation: none;
    }
}
```

---

## Implementation Tasks

### Task 1: Implement end_game() Method
- [ ] Calculate final standings
- [ ] Determine winner(s) with tie handling
- [ ] Calculate game statistics
- [ ] Transition to END phase

### Task 2: Implement reset_for_new_game()
- [ ] Reset all scores
- [ ] Clear game state
- [ ] Preserve player roster
- [ ] Transition to LOBBY

### Task 3: Add Admin Actions
- [ ] Handle end_game action
- [ ] Handle play_again action
- [ ] Handle end_session action

### Task 4: Add End View HTML
- [ ] Winner banner with crown
- [ ] Personal result card
- [ ] Final standings list
- [ ] Game stats section
- [ ] Host controls

### Task 5: Implement JavaScript Methods
- [ ] handleEndPhase() method
- [ ] showWinnerBanner() method
- [ ] showPersonalResult() method
- [ ] renderFinalStandings() method
- [ ] showGameStats() method
- [ ] setupHostEndControls()

### Task 6: Add CSS Styles
- [ ] Winner banner styling
- [ ] Podium rank styling
- [ ] Final standings styling
- [ ] Stats grid styling
- [ ] Animations

### Task 7: Write Tests
- [ ] Test winner calculation
- [ ] Test tie handling
- [ ] Test game stats calculation
- [ ] Test play again flow

---

## Definition of Done

- [ ] Final scores displayed correctly
- [ ] Winner declared with celebration
- [ ] Ties handled (co-winners)
- [ ] "Play Again" resets game with same players
- [ ] "End Session" returns to lobby
- [ ] Host can force end game from any phase
- [ ] Game statistics displayed
- [ ] No console errors
- [ ] Responsive on mobile

---

## Dependencies

### Depends On
- **Story 6.5**: Leaderboard Display
- **Story 6.6**: Round Progression

### Enables
- Complete game loop
- Replayability

---

## Dev Agent Record

### Agent Model Used
claude-opus-4-5-20251101

### Completion Notes List
- Added END phase handling to get_state() with winner info and final standings
- Implemented _determine_winner() with tie handling (returns is_tie flag and tied_players list)
- Implemented _get_game_stats() for end screen statistics (total_rounds, spies_caught)
- Added END view HTML in player.html with winner card, final leaderboard, game stats, waiting message
- Implemented handleEndPhase(), showWinner(), renderFinalLeaderboard(), showGameStats() in player.js
- Added comprehensive CSS for end game with winner pulse animation, gold styling, tie handling
- Phase transitions SCORING → END when should_end_game() is true

### File List
- custom_components/spyster/game/state.py
- custom_components/spyster/www/player.html
- custom_components/spyster/www/js/player.js
- custom_components/spyster/www/css/styles.css
