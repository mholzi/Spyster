# Story 6.5: Leaderboard Display

**Epic:** Epic 6 - Scoring & Game Progression
**Story ID:** 6.5
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to see the current standings between rounds**,
So that **I know how I'm doing compared to others**.

---

## Acceptance Criteria

### AC1: Cumulative Score Tracking

**Given** the SCORING phase begins
**When** points are calculated
**Then** cumulative scores are updated for all players (per FR54)
**And** scores persist across all rounds

### AC2: Leaderboard Sorting

**Given** the leaderboard is displayed
**When** between rounds
**Then** all players are listed with their total scores
**And** players are sorted by score (highest first)
**And** tied players show same rank

### AC3: Round Score Changes

**Given** the leaderboard is displayed
**When** showing player scores
**Then** point changes from last round are highlighted (+X / -Y)
**And** positive changes show green styling
**And** negative changes show red styling

### AC4: Player View

**Given** a player views their phone
**When** in SCORING phase
**Then** they see their personal score change prominently
**And** they see the full leaderboard
**And** their name is highlighted in the list

### AC5: Host View

**Given** the host display
**When** in SCORING phase
**Then** the leaderboard is visible to the room
**And** top 3 players are emphasized
**And** round number is displayed

### AC6: Transition Timer

**Given** the leaderboard is displayed
**When** auto-advancing to next round
**Then** a countdown timer shows (e.g., "Next round in 10s")
**And** host can skip the countdown

---

## Requirements Coverage

### Functional Requirements

- **FR51**: Players can see the current leaderboard between rounds
- **FR54**: System tracks cumulative scores across all rounds

### Architectural Requirements

- **ARCH-14**: Broadcast after mutations
- **ARCH-4**: Phase state machine (REVEAL → SCORING)

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Update SCORING phase state:

```python
def get_state(self, for_player: str | None = None) -> dict:
    # ... existing code ...

    elif self.phase == GamePhase.SCORING:
        # Include standings with round changes
        standings = []
        for player in sorted(
            self.players.values(),
            key=lambda p: p.score,
            reverse=True
        ):
            round_score = self.round_scores.get(player.name, {})
            standings.append({
                "name": player.name,
                "score": player.score,
                "round_change": round_score.get("points", 0),
                "is_self": player.name == for_player,
            })

        state["standings"] = standings
        state["round_number"] = self.current_round
        state["total_rounds"] = self.num_rounds
        state["scoring_timer"] = self._get_timer_remaining("scoring")
```

#### 2. Player Display HTML (`www/player.html`)

Add scoring view structure:

```html
<!-- Scoring View (Story 6.5) -->
<div id="scoring-view" class="phase-view" style="display: none;">
    <div class="scoring-header">
        <h1 class="scoring-title">Round <span id="round-number">1</span> Complete</h1>
        <div id="next-round-timer" class="next-round-countdown">
            Next round in <span id="scoring-countdown-value">10</span>s
        </div>
    </div>

    <!-- Personal Score Change -->
    <div id="personal-score-change" class="personal-score-card">
        <div class="score-label">Your Score</div>
        <div id="player-total-score" class="total-score">0</div>
        <div id="player-round-change" class="round-change"></div>
    </div>

    <!-- Leaderboard -->
    <div class="leaderboard-section">
        <h2 class="leaderboard-title">Standings</h2>
        <div id="leaderboard-list" class="leaderboard-list">
            <!-- Leaderboard items injected dynamically -->
        </div>
    </div>
</div>
```

#### 3. Player Display Logic (`www/js/player.js`)

Add scoring phase handling:

```javascript
class PlayerClient {
    handleScoringPhase(state) {
        this.hideAllViews();

        const scoringView = document.getElementById('scoring-view');
        if (scoringView) {
            scoringView.style.display = 'block';
        }

        // Update round number
        this.updateRoundInfo(state);

        // Show personal score change
        this.showPersonalScore(state);

        // Render leaderboard
        this.renderLeaderboard(state.standings);

        // Start countdown to next round
        if (state.scoring_timer) {
            this.startScoringCountdown(state.scoring_timer);
        }
    }

    showPersonalScore(state) {
        const standings = state.standings || [];
        const myStanding = standings.find(s => s.is_self);

        if (!myStanding) return;

        const totalEl = document.getElementById('player-total-score');
        const changeEl = document.getElementById('player-round-change');

        if (totalEl) {
            totalEl.textContent = myStanding.score;
        }

        if (changeEl) {
            const change = myStanding.round_change;
            const sign = change >= 0 ? '+' : '';
            changeEl.textContent = `${sign}${change}`;
            changeEl.className = `round-change ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}`;
        }
    }

    renderLeaderboard(standings) {
        const list = document.getElementById('leaderboard-list');
        if (!list) return;

        list.innerHTML = '';

        standings.forEach((player, index) => {
            const rank = index + 1;
            const item = document.createElement('div');
            item.className = `leaderboard-item ${player.is_self ? 'leaderboard-item--self' : ''}`;

            // Top 3 styling
            if (rank <= 3) {
                item.classList.add(`leaderboard-item--rank-${rank}`);
            }

            const changeSign = player.round_change >= 0 ? '+' : '';
            const changeClass = player.round_change > 0 ? 'positive' : player.round_change < 0 ? 'negative' : 'neutral';

            item.innerHTML = `
                <span class="leaderboard-rank">${rank}</span>
                <span class="leaderboard-name">${this.escapeHtml(player.name)}</span>
                <span class="leaderboard-score">${player.score}</span>
                <span class="leaderboard-change ${changeClass}">${changeSign}${player.round_change}</span>
            `;

            list.appendChild(item);
        });
    }

    updateRoundInfo(state) {
        const roundEl = document.getElementById('round-number');
        if (roundEl && state.round_number) {
            roundEl.textContent = state.round_number;
        }
    }
}
```

#### 4. CSS Styles (`www/css/styles.css`)

Add leaderboard styles:

```css
/* ============================================================================
   STORY 6.5: SCORING/LEADERBOARD VIEW
   ============================================================================ */

#scoring-view {
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
    padding: var(--space-md);
}

.scoring-header {
    text-align: center;
}

.scoring-title {
    font-size: 24px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-md);
}

.next-round-countdown {
    font-size: 16px;
    color: var(--color-text-secondary);
}

/* Personal Score Card */
.personal-score-card {
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-accent-primary);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    text-align: center;
}

.score-label {
    font-size: 14px;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.total-score {
    font-size: 48px;
    font-weight: var(--font-weight-black);
    color: var(--color-text-primary);
    line-height: 1;
    margin: var(--space-sm) 0;
}

.round-change {
    font-size: 24px;
    font-weight: var(--font-weight-bold);
}

.round-change.positive { color: var(--color-success); }
.round-change.negative { color: var(--color-error); }
.round-change.neutral { color: var(--color-text-secondary); }

/* Leaderboard */
.leaderboard-section {
    flex: 1;
}

.leaderboard-title {
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-secondary);
    text-align: center;
    margin-bottom: var(--space-md);
}

.leaderboard-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
}

.leaderboard-item {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
    border: 2px solid transparent;
}

.leaderboard-item--self {
    border-color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.1);
}

/* Top 3 styling */
.leaderboard-item--rank-1 { border-color: var(--color-all-in); }
.leaderboard-item--rank-2 { border-color: #c0c0c0; }
.leaderboard-item--rank-3 { border-color: #cd7f32; }

.leaderboard-rank {
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-secondary);
    min-width: 30px;
}

.leaderboard-item--rank-1 .leaderboard-rank { color: var(--color-all-in); }
.leaderboard-item--rank-2 .leaderboard-rank { color: #c0c0c0; }
.leaderboard-item--rank-3 .leaderboard-rank { color: #cd7f32; }

.leaderboard-name {
    flex: 1;
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
}

.leaderboard-score {
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
}

.leaderboard-change {
    font-size: 14px;
    font-weight: var(--font-weight-semibold);
    min-width: 40px;
    text-align: right;
}

.leaderboard-change.positive { color: var(--color-success); }
.leaderboard-change.negative { color: var(--color-error); }
.leaderboard-change.neutral { color: var(--color-text-secondary); }
```

---

## Implementation Tasks

### Task 1: Update GameState for SCORING
- [ ] Add scoring timer (10 seconds default)
- [ ] Update get_state() for SCORING phase
- [ ] Include round_change in standings

### Task 2: Add Scoring View HTML
- [ ] Personal score card structure
- [ ] Leaderboard list container
- [ ] Next round countdown

### Task 3: Implement JavaScript Methods
- [ ] handleScoringPhase() method
- [ ] showPersonalScore() method
- [ ] renderLeaderboard() method
- [ ] Update handleStateUpdate() for SCORING

### Task 4: Add CSS Styles
- [ ] Personal score card styling
- [ ] Leaderboard item styling
- [ ] Top 3 rank styling
- [ ] Score change colors

### Task 5: Write Tests
- [ ] Test leaderboard sorting
- [ ] Test score change calculation
- [ ] Test tie handling

---

## Definition of Done

- [ ] Cumulative scores tracked across rounds
- [ ] Leaderboard sorted by score (highest first)
- [ ] Round changes displayed with +/- styling
- [ ] Personal score highlighted
- [ ] Top 3 players have special styling
- [ ] Countdown to next round displayed
- [ ] No console errors
- [ ] Responsive on mobile

---

## Dependencies

### Depends On
- **Story 5.7**: Conviction Logic (round_scores data)
- **Story 6.1-6.4**: Scoring calculations (done in 5.7)

### Enables
- **Story 6.6**: Round Progression
- **Story 6.7**: Game End

---

## Dev Agent Record

### Agent Model Used
claude-opus-4-5-20251101

### Completion Notes List
- Added SCORING_DISPLAY_SECONDS constant (10s) to const.py
- Updated get_state() for SCORING phase with standings including round_change and is_self
- Added scoring timer to transition_to_scoring()
- Implemented SCORING view HTML in player.html with personal score card and leaderboard
- Implemented handleScoringPhase(), showPersonalScore(), renderLeaderboard(), updateRoundInfo(), startNextRoundCountdown() in player.js
- Added comprehensive CSS for leaderboard with top-3 styling, self-highlighting, and score change colors

### File List
- custom_components/spyster/const.py
- custom_components/spyster/game/state.py
- custom_components/spyster/www/player.html
- custom_components/spyster/www/js/player.js
- custom_components/spyster/www/css/styles.css
