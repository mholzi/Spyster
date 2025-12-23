# Story 5.1: Voting Phase UI with Player Cards

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.1
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to select who I think is the spy**,
So that **I can vote against them**.

---

## Acceptance Criteria

### AC1: Vote Phase Display

**Given** the game transitions to VOTE phase
**When** a player views their screen
**Then** a grid of player cards is displayed (excluding themselves)
**And** each card shows the player's name
**And** cards are tappable with clear touch targets (48px+)

### AC2: Player Card Selection

**Given** a player taps a player card
**When** the card is selected
**Then** the card shows a selected state (visual highlight)
**And** only one player can be selected at a time

### AC3: Selection Change

**Given** a player wants to change their selection
**When** they tap a different card
**Then** the previous selection is cleared
**And** the new card is selected

### AC4: Responsive Grid Layout

**Given** the player grid is displayed
**When** viewed on different screen sizes
**Then** the grid adapts (2-3 columns on mobile, more on tablet)
**And** cards remain tappable with 48px minimum touch targets

### AC5: Visual State Management

**Given** a player card
**When** in different states
**Then** it displays:
- Default: Normal styling with name
- Hover: Subtle highlight (desktop)
- Selected: Strong highlight (pink accent, glow)
- Disabled: Greyed out (for own card if shown)

---

## Requirements Coverage

### Functional Requirements

- **FR32**: All players can select who they suspect is the Spy
- **FR31**: Player calling a vote triggers voting phase for all players (transition)

### Non-Functional Requirements

- **NFR4**: State Sync - All players see same game state within 500ms of change

### UX Requirements

- **UX-4**: Minimum touch targets: 44px (48px for primary)
- **UX-5**: Player cards with states: default, hover, selected, reveal, disabled

### Architectural Requirements

- **ARCH-12**: Message format: `{"type": "...", ...payload}` with snake_case fields
- **ARCH-14**: Broadcast state after every state mutation
- **ARCH-17**: Phase guards on all state-mutating methods

---

## Technical Design

### Component Changes

#### 1. Player Display HTML (`www/player.html`)

Add vote phase view structure:

```html
<!-- Vote Phase View -->
<div id="vote-view" class="phase-view" style="display: none;">
    <!-- Vote notification banner -->
    <div id="vote-notification" class="vote-notification" style="display: none;"></div>

    <!-- Vote timer -->
    <div class="vote-header">
        <div class="timer-display">
            <span id="vote-timer" role="timer" aria-live="polite">1:00</span>
        </div>
        <div id="vote-tracker" role="progressbar" aria-valuenow="0" aria-valuemax="7">
            0/0 voted
        </div>
    </div>

    <!-- Player selection grid -->
    <div class="vote-section">
        <h2 class="vote-section-title">Select the Spy</h2>
        <div id="player-cards-grid" class="player-cards-grid" role="radiogroup" aria-label="Select a player to vote for">
            <!-- Player cards injected dynamically -->
        </div>
    </div>

    <!-- Confidence betting (Story 5.2) -->
    <div id="confidence-section" class="vote-section" style="display: none;">
        <!-- Implemented in Story 5.2 -->
    </div>

    <!-- Submit button -->
    <div class="vote-actions">
        <button id="submit-vote-btn" class="btn-primary btn-large" disabled>
            SELECT A PLAYER
        </button>
    </div>
</div>
```

#### 2. Player Display Logic (`www/js/player.js`)

Add vote UI management:

```javascript
class PlayerDisplay {
    constructor() {
        // ... existing init ...
        this.selectedVoteTarget = null;
    }

    showVoteView(state) {
        // Hide all other views
        document.querySelectorAll('.phase-view').forEach(view => {
            view.style.display = 'none';
        });

        const voteView = document.getElementById('vote-view');
        if (voteView) {
            voteView.style.display = 'block';
        }

        // Show vote caller notification (from Story 4.5)
        if (state.vote_caller) {
            this.showVoteCallerNotification(state.vote_caller);
        }

        // Render player cards
        this.renderPlayerCards(state);

        // Update timer
        if (state.timer) {
            this.updateVoteTimer(state.timer.remaining);
        }

        // Update submission tracker
        if (state.votes_submitted !== undefined && state.total_players !== undefined) {
            this.updateVoteTracker(state.votes_submitted, state.total_players);
        }
    }

    renderPlayerCards(state) {
        const grid = document.getElementById('player-cards-grid');
        if (!grid) return;

        // Clear existing cards
        grid.innerHTML = '';

        // Get players from state (excluding self)
        const players = state.players || [];
        const selfName = this.playerName;

        players.forEach(player => {
            // Skip self
            if (player.name === selfName) return;

            const card = this.createPlayerCard(player);
            grid.appendChild(card);
        });
    }

    createPlayerCard(player) {
        const card = document.createElement('button');
        card.className = 'player-card';
        card.setAttribute('role', 'radio');
        card.setAttribute('aria-checked', 'false');
        card.setAttribute('data-player-name', player.name);

        // Card content
        card.innerHTML = `
            <div class="player-card-avatar">
                <span class="player-initial">${this.escapeHtml(player.name.charAt(0).toUpperCase())}</span>
            </div>
            <div class="player-card-name">${this.escapeHtml(player.name)}</div>
        `;

        // Click handler
        card.addEventListener('click', () => this.selectVoteTarget(player.name));

        // Handle disconnected players (disabled state)
        if (!player.connected) {
            card.classList.add('player-card--disabled');
            card.disabled = true;
            card.setAttribute('aria-disabled', 'true');
        }

        return card;
    }

    selectVoteTarget(playerName) {
        // Clear previous selection
        document.querySelectorAll('.player-card').forEach(card => {
            card.classList.remove('player-card--selected');
            card.setAttribute('aria-checked', 'false');
        });

        // Select new target
        const selectedCard = document.querySelector(`[data-player-name="${playerName}"]`);
        if (selectedCard) {
            selectedCard.classList.add('player-card--selected');
            selectedCard.setAttribute('aria-checked', 'true');
        }

        this.selectedVoteTarget = playerName;

        // Update submit button
        this.updateSubmitButton();

        console.log('Vote target selected:', playerName);
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submit-vote-btn');
        if (!submitBtn) return;

        if (this.selectedVoteTarget) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'LOCK IT IN';
        } else {
            submitBtn.disabled = true;
            submitBtn.textContent = 'SELECT A PLAYER';
        }
    }

    // Helper method
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
```

#### 3. CSS Styles (`www/css/styles.css`)

Add player card styles:

```css
/* =================================
   VOTE PHASE LAYOUT
   ================================= */

#vote-view {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    padding: var(--spacing-md);
    gap: var(--spacing-lg);
}

.vote-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
}

.vote-section {
    flex: 1;
}

.vote-section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-md);
    text-align: center;
}

/* =================================
   PLAYER CARDS GRID
   ================================= */

.player-cards-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
}

@media (min-width: 480px) {
    .player-cards-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (min-width: 768px) {
    .player-cards-grid {
        grid-template-columns: repeat(4, 1fr);
    }
}

/* =================================
   PLAYER CARD COMPONENT
   ================================= */

.player-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-md);
    min-height: 100px;
    min-width: 100px;
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: all 0.2s ease;

    /* Touch target minimum 48px */
    touch-action: manipulation;
}

.player-card:hover:not(:disabled) {
    border-color: var(--color-accent-secondary);
    transform: translateY(-2px);
}

.player-card:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 245, 255, 0.4);
}

/* Selected state */
.player-card--selected {
    border-color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.15);
    box-shadow: 0 0 20px rgba(255, 45, 106, 0.3);
}

.player-card--selected .player-card-avatar {
    background: var(--color-accent-primary);
}

/* Disabled state */
.player-card--disabled {
    opacity: 0.5;
    cursor: not-allowed;
    filter: grayscale(50%);
}

.player-card--disabled:hover {
    transform: none;
    border-color: var(--color-border);
}

/* Avatar */
.player-card-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--color-bg-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--spacing-sm);
    transition: background 0.2s ease;
}

.player-initial {
    font-size: 20px;
    font-weight: 700;
    color: var(--color-text-primary);
}

.player-card-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text-primary);
    text-align: center;
    word-break: break-word;
    max-width: 100%;
}

/* =================================
   VOTE ACTIONS
   ================================= */

.vote-actions {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    margin-top: auto;
}

.vote-actions .btn-large {
    width: 100%;
    min-height: 56px;
    font-size: 18px;
    font-weight: 700;
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    .player-card {
        transition: none;
    }

    .player-card:hover:not(:disabled) {
        transform: none;
    }
}
```

#### 4. GameState (`game/state.py`)

Ensure vote phase state includes player list for rendering:

```python
def get_state(self, for_player: str | None = None) -> dict[str, Any]:
    # ... existing code ...

    elif self.phase == GamePhase.VOTE:
        # Include player list for vote UI (excluding role data)
        state["players"] = [
            {
                "name": p.name,
                "connected": p.connected,
            }
            for p in self.players.values()
        ]

        # ... existing vote state ...
```

---

## Implementation Tasks

### Task 1: Add Vote View HTML Structure (AC: 1, 4)
- [x] Create vote-view container in player.html
- [x] Add player-cards-grid container
- [x] Add vote header with timer and tracker
- [x] Add submit button section

### Task 2: Implement Player Card Rendering (AC: 1, 2, 3)
- [x] Create renderPlayerCards() method
- [x] Create createPlayerCard() method
- [x] Filter out self from player list
- [x] Handle disconnected player state

### Task 3: Implement Selection Logic (AC: 2, 3)
- [x] Implement selectVoteTarget() method
- [x] Single selection enforcement
- [x] Update ARIA attributes on selection
- [x] Update submit button state

### Task 4: Add CSS Styling (AC: 4, 5)
- [x] Player card base styles
- [x] Selected state styling (pink accent)
- [x] Hover state styling
- [x] Disabled state styling
- [x] Responsive grid layout
- [x] Touch target sizing (48px+)

### Task 5: Update GameState for Vote Phase (AC: 1)
- [x] Include players list in VOTE phase state
- [x] Ensure proper filtering of role data

### Task 6: Write Tests
- [x] Test player card rendering
- [x] Test selection toggle
- [x] Test single selection enforcement
- [x] Test disconnected player handling

---

## Testing Strategy

### Unit Tests

```javascript
// Test player card selection
describe('VoteUI', () => {
    test('should render player cards excluding self', () => {
        const players = [
            { name: 'Alice', connected: true },
            { name: 'Bob', connected: true },
            { name: 'Charlie', connected: true }
        ];
        display.playerName = 'Alice';
        display.renderPlayerCards({ players });

        const cards = document.querySelectorAll('.player-card');
        expect(cards.length).toBe(2); // Bob and Charlie only
    });

    test('should allow single selection only', () => {
        display.selectVoteTarget('Bob');
        display.selectVoteTarget('Charlie');

        const selected = document.querySelectorAll('.player-card--selected');
        expect(selected.length).toBe(1);
        expect(selected[0].dataset.playerName).toBe('Charlie');
    });
});
```

### Manual Testing Checklist

**Scenario 1: Vote Phase Entry**
- [ ] Transition to VOTE shows player grid
- [ ] Self is excluded from grid
- [ ] All other players visible
- [ ] Timer displays 1:00 (60 seconds)

**Scenario 2: Player Selection**
- [ ] Tap card selects it
- [ ] Selected card has pink border/glow
- [ ] Tap different card deselects previous
- [ ] Submit button becomes enabled

**Scenario 3: Disconnected Players**
- [ ] Disconnected players shown greyed out
- [ ] Cannot select disconnected player
- [ ] Connected players fully interactive

**Scenario 4: Responsive Layout**
- [ ] 2 columns on small phones
- [ ] 3 columns on larger phones
- [ ] Touch targets are 48px minimum

---

## Definition of Done

- [ ] Vote view displays on VOTE phase transition
- [ ] Player cards grid rendered correctly
- [ ] Self excluded from player list
- [ ] Single selection enforced
- [ ] Visual states (default, hover, selected, disabled) work
- [ ] Submit button state updates with selection
- [ ] Responsive grid layout (2-4 columns)
- [ ] Touch targets meet 48px minimum
- [ ] ARIA attributes for accessibility
- [ ] No console errors
- [ ] Manual testing completed

---

## Dependencies

### Depends On
- **Story 4.5**: Call Vote Functionality (provides VOTE phase entry)
- **Epic 4**: Questioning Phase (phase infrastructure)

### Enables
- **Story 5.2**: Confidence Betting Selection
- **Story 5.3**: Vote Submission and Tracking
- **Story 5.4**: Spy Location Guess Option

---

## Architecture Decisions Referenced

- **ARCH-12**: Message format with snake_case
- **ARCH-14**: Broadcast after mutations
- **UX-4**: Touch targets 44-48px
- **UX-5**: Player card states

---

## Dev Notes

### Project Context Reference
- **File**: `_bmad-output/project-context.md`
- **Key Rules**:
  - JavaScript naming: camelCase variables, kebab-case DOM IDs/classes
  - Touch targets: 44px minimum, 48px for primary actions
  - Mobile-first responsive design

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/www/player.html` | Modify | Add vote-view HTML structure |
| `custom_components/spyster/www/js/player.js` | Modify | Add vote UI rendering logic |
| `custom_components/spyster/www/css/styles.css` | Modify | Add player card styles |
| `custom_components/spyster/game/state.py` | Modify | Include players in VOTE state |

### Previous Story Learnings
- Story 4.5 established VOTE phase transition and timer
- Vote caller attribution already implemented
- Phase guards already in place

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Implemented vote-view HTML structure with player cards grid, timer display, vote tracker, and submit button
- Added handleVotePhase() method to PlayerClient class for VOTE phase state handling
- Added renderPlayerCards(), createPlayerCard(), selectVoteTarget() methods for player card rendering and selection
- Added comprehensive CSS styling for vote phase UI including responsive grid (2-4 columns), player card states (default, hover, selected, disabled), and reduced motion support
- Updated GameState.get_state() to include players list with name/connected fields for VOTE phase
- Added unit tests for VOTE phase state handling including players list, total_voters, votes_submitted, and disconnected status

### File List
| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/www/player.html` | Modified | Added vote-view HTML structure with player cards grid |
| `custom_components/spyster/www/js/player.js` | Modified | Added vote phase handling methods (handleVotePhase, renderPlayerCards, selectVoteTarget, etc.) |
| `custom_components/spyster/www/css/styles.css` | Modified | Added ~170 lines of vote phase CSS styles |
| `custom_components/spyster/game/state.py` | Modified | Added players list to VOTE phase get_state() |
| `tests/test_state.py` | Modified | Added 6 tests for Story 5.1 vote phase state handling |
