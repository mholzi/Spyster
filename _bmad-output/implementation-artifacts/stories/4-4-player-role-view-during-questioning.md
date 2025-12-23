# Story 4.4: Player Role View During Questioning

**Epic:** Epic 4 - Questioning Phase
**Story ID:** 4.4
**Status:** done
**Priority:** High
**Complexity:** Low

---

## User Story

As a **player**,
I want **to view my role at any time during the round**,
So that **I can remember my role while asking/answering questions**.

---

## Acceptance Criteria

### AC1: Non-Spy Role Display During Questioning

**Given** a non-spy player is in QUESTIONING phase
**When** they view their screen
**Then** their role and location are visible (or easily accessible)
**And** the round timer is always visible

### AC2: Spy Role Display During Questioning

**Given** the spy is in QUESTIONING phase
**When** they view their screen
**Then** the location list is visible (or easily accessible)
**And** the round timer is always visible
**And** the layout matches non-spy layout (spy parity)

### AC3: Glanceable Role Information

**Given** a player needs to reference their role
**When** during active questioning
**Then** the information is glanceable without disrupting social interaction

### AC4: Persistent Timer Visibility

**Given** a player is viewing their role information
**When** the role info is expanded/shown
**Then** the round timer remains visible at all times
**And** timer urgency styling still applies

### AC5: Spy Parity Maintained

**Given** spy and non-spy screens are compared during QUESTIONING
**When** viewed side-by-side
**Then** the layouts have identical dimensions and structure
**And** a casual glance cannot distinguish spy from non-spy

---

## Requirements Coverage

### Functional Requirements

- **FR24**: Player can view their assigned role at any time during the round

### Non-Functional Requirements

- **NFR2**: WebSocket Latency - Messages delivered in < 100ms on local network
- **NFR4**: State Sync - All players see same game state within 500ms of change

### UX Design Requirements

- **UX-9**: Spy and non-spy screens must have identical layouts (prevent visual tells)
- **UX-10**: Role display dimensions must be identical for spy vs non-spy
- **UX-11**: WCAG 2.1 AA compliance (4.5:1 contrast minimum)
- **UX-14**: Keyboard navigation support

### Architectural Requirements

- **ARCH-7**: Per-player state filtering via `get_state(for_player=player_name)`
- **ARCH-8**: Never broadcast same state to all players (role privacy)
- **ARCH-14**: Broadcast state after every state mutation

---

## Technical Design

### Component Changes

#### 1. GameState (`game/state.py`)

Ensure role data is included in QUESTIONING phase state (already partially implemented in Story 4.1):

```python
def get_state(self, for_player: str | None = None) -> dict:
    """Get game state, filtered for specific player."""
    base_state = {
        "phase": self.phase.value,
        "player_count": len(self.players),
        "connected_count": self.get_connected_player_count(),
        "round": self.current_round,
    }

    # Add phase-specific state
    if self.phase == GamePhase.QUESTIONING:
        # Timer info (from Story 4.2)
        base_state["timer"] = {
            "name": "round",
            "remaining": self._get_timer_remaining("round"),
            "total": self._timer_durations.get("round", 0),
        }

        # Turn info (from Story 4.3)
        base_state["turn"] = {
            "questioner": self.current_questioner,
            "answerer": self.current_answerer,
        }

        # Role data for player to view during questioning
        if for_player:
            player = self.players.get(for_player)
            if player:
                if player.is_spy:
                    base_state["role_data"] = {
                        "is_spy": True,
                        "possible_locations": self._get_all_location_names(),
                    }
                else:
                    base_state["role_data"] = {
                        "is_spy": False,
                        "location": self.current_location.name,
                        "role": player.role.name,
                        "hint": player.role.hint,
                        "other_roles": self._get_other_roles_at_location(),
                    }

    return base_state
```

#### 2. Player Display HTML (`www/player.html`)

Add role reference section to questioning view:

```html
<!-- Questioning Phase View -->
<div id="questioning-view" class="phase-view" style="display: none;">
    <div class="questioning-container">
        <!-- Round Timer - ALWAYS VISIBLE -->
        <div class="timer-display" role="timer" aria-live="polite">
            <div class="timer-label">Time Remaining</div>
            <div id="round-timer" class="timer-value">5:00</div>
        </div>

        <!-- Turn Display (from Story 4.3) -->
        <div id="turn-display" class="turn-display" role="status" aria-live="polite">
            <!-- Populated by JavaScript -->
        </div>

        <!-- Role Reference - Persistent but Collapsible -->
        <div class="role-reference" role="region" aria-label="Your role information">
            <button
                id="role-toggle"
                class="role-toggle-btn"
                aria-expanded="false"
                aria-controls="role-info"
            >
                <span class="role-toggle-icon">▶</span>
                <span class="role-toggle-text">View My Role</span>
            </button>
            <div
                id="role-info"
                class="role-info"
                aria-hidden="true"
                style="display: none;"
            >
                <!-- Populated by JavaScript with role data -->
            </div>
        </div>

        <!-- Call Vote Button -->
        <div class="vote-controls">
            <button id="call-vote-btn" class="btn-primary btn-large">
                CALL VOTE
            </button>
        </div>

        <!-- Status Message -->
        <div id="questioning-status" class="status-text">
            Ask and answer questions to find the spy
        </div>
    </div>
</div>
```

#### 3. Player Display Logic (`www/js/player.js`)

Implement role reference display with spy parity:

```javascript
class PlayerDisplay {
    constructor() {
        this.state = null;
        this.ws = null;
        this.playerName = null;
        this.roleExpanded = false;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Role toggle
        const roleToggle = document.getElementById('role-toggle');
        if (roleToggle) {
            roleToggle.addEventListener('click', () => this.toggleRoleDisplay());
            // Keyboard support
            roleToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleRoleDisplay();
                }
            });
        }
    }

    onStateUpdate(state) {
        this.state = state;

        // Show appropriate view based on phase
        if (state.phase === 'QUESTIONING') {
            this.showQuestioningView(state);
        }
    }

    showQuestioningView(state) {
        const questioningView = document.getElementById('questioning-view');
        if (questioningView) {
            // Hide all other views
            document.querySelectorAll('.phase-view').forEach(view => {
                view.style.display = 'none';
            });
            questioningView.style.display = 'block';
        }

        // Update timer (always visible)
        if (state.timer) {
            this.updateRoundTimer(state.timer.remaining);
        }

        // Update turn display (from Story 4.3)
        if (state.turn) {
            this.updateTurnDisplay(state.turn);
        }

        // Update role reference content (but preserve expanded state)
        if (state.role_data) {
            this.updateRoleContent(state.role_data);
        }
    }

    updateRoleContent(roleData) {
        const roleInfo = document.getElementById('role-info');
        if (!roleInfo || !roleData) return;

        // Generate content with SPY PARITY
        // Both spy and non-spy have same structure:
        // - Title (large text)
        // - Subtitle (medium text)
        // - List section (scrollable list)

        if (roleData.is_spy) {
            const locationsHTML = roleData.possible_locations
                .map(location => `<li class="role-list-item">${this.escapeHtml(location)}</li>`)
                .join('');

            roleInfo.innerHTML = `
                <div class="role-display-compact" data-role-type="spy">
                    <div class="role-title">YOU ARE THE SPY</div>
                    <div class="role-subtitle">Possible Locations:</div>
                    <ul class="role-list" aria-label="Possible locations">${locationsHTML}</ul>
                </div>
            `;
        } else {
            const otherRolesHTML = roleData.other_roles
                .map(role => `<li class="role-list-item">${this.escapeHtml(role)}</li>`)
                .join('');

            roleInfo.innerHTML = `
                <div class="role-display-compact" data-role-type="innocent">
                    <div class="role-title">${this.escapeHtml(roleData.location)}</div>
                    <div class="role-subtitle">
                        Your Role: <strong>${this.escapeHtml(roleData.role)}</strong>
                    </div>
                    <div class="role-hint">${this.escapeHtml(roleData.hint)}</div>
                    <div class="role-section-label">Other Roles at Location:</div>
                    <ul class="role-list" aria-label="Other roles">${otherRolesHTML}</ul>
                </div>
            `;
        }
    }

    toggleRoleDisplay() {
        const roleInfo = document.getElementById('role-info');
        const roleToggle = document.getElementById('role-toggle');
        const toggleIcon = roleToggle?.querySelector('.role-toggle-icon');
        const toggleText = roleToggle?.querySelector('.role-toggle-text');

        if (!roleInfo || !roleToggle) return;

        this.roleExpanded = !this.roleExpanded;

        // Update visibility
        roleInfo.style.display = this.roleExpanded ? 'block' : 'none';
        roleInfo.setAttribute('aria-hidden', (!this.roleExpanded).toString());

        // Update toggle button
        roleToggle.setAttribute('aria-expanded', this.roleExpanded.toString());
        if (toggleIcon) {
            toggleIcon.textContent = this.roleExpanded ? '▼' : '▶';
        }
        if (toggleText) {
            toggleText.textContent = this.roleExpanded ? 'Hide My Role' : 'View My Role';
        }
    }

    updateRoundTimer(timeRemaining) {
        const timerElement = document.getElementById('round-timer');
        if (!timerElement) return;

        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        const formatted = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        timerElement.textContent = formatted;

        // Timer urgency styling
        const timerDisplay = timerElement.closest('.timer-display');
        if (timerDisplay) {
            timerDisplay.classList.toggle('timer-urgent', timeRemaining < 30);
            timerDisplay.classList.toggle('timer-warning', timeRemaining >= 30 && timeRemaining < 60);
        }

        // Screen reader announcements at key intervals
        if (timeRemaining === 60 || timeRemaining === 30 || timeRemaining === 10) {
            this.announceToScreenReader(`${timeRemaining} seconds remaining`);
        }
    }

    announceToScreenReader(message) {
        const announcer = document.getElementById('sr-announcer') || this.createAnnouncer();
        announcer.textContent = message;
    }

    createAnnouncer() {
        const announcer = document.createElement('div');
        announcer.id = 'sr-announcer';
        announcer.setAttribute('aria-live', 'assertive');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        document.body.appendChild(announcer);
        return announcer;
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

#### 4. CSS Styles (`www/css/styles.css`)

Add role reference styles with spy parity:

```css
/* =================================
   ROLE REFERENCE (Questioning Phase)
   ================================= */

.role-reference {
    width: 100%;
    margin-bottom: var(--spacing-lg);
}

.role-toggle-btn {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 48px; /* Touch target */
}

.role-toggle-btn:hover,
.role-toggle-btn:focus {
    background: var(--color-bg-secondary);
    border-color: var(--color-accent-primary);
    outline: none;
}

.role-toggle-btn:focus-visible {
    box-shadow: 0 0 0 2px var(--color-accent-primary);
}

.role-toggle-icon {
    font-size: 12px;
    transition: transform 0.2s ease;
}

.role-info {
    margin-top: var(--spacing-sm);
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--color-accent-primary);
    animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* =================================
   ROLE DISPLAY COMPACT (Spy Parity)
   =================================
   CRITICAL: Spy and non-spy must have
   identical visual dimensions and structure
   to prevent visual tells.
   ================================= */

.role-display-compact {
    /* Fixed dimensions for parity */
    min-height: 180px;
    max-height: 280px;
    overflow-y: auto;
}

.role-display-compact .role-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0 0 var(--spacing-sm);
    /* Same height for both spy and location name */
    min-height: 32px;
    line-height: 1.3;
}

.role-display-compact .role-subtitle {
    font-size: 16px;
    color: var(--color-text-primary);
    margin: 0 0 var(--spacing-sm);
    /* Same height for both "Possible Locations:" and "Your Role:" */
    min-height: 24px;
}

.role-display-compact .role-hint {
    font-size: 14px;
    color: var(--color-text-secondary);
    font-style: italic;
    margin: 0 0 var(--spacing-md);
    /* Spy has no hint, but we keep same spacing */
    min-height: 20px;
}

/* Hide hint for spy (but keep space for parity) */
.role-display-compact[data-role-type="spy"] .role-hint {
    visibility: hidden;
}

.role-display-compact .role-section-label {
    font-size: 12px;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: var(--spacing-md) 0 var(--spacing-sm);
}

/* Spy doesn't have this label, add equivalent spacing */
.role-display-compact[data-role-type="spy"] .role-list {
    margin-top: calc(var(--spacing-md) + 20px); /* Match non-spy spacing */
}

.role-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
}

.role-list-item {
    font-size: 13px;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-sm);
    color: var(--color-text-primary);
}

/* =================================
   TIMER STATES
   ================================= */

.timer-display.timer-warning .timer-value {
    color: var(--color-warning, #ffa500);
}

.timer-display.timer-urgent {
    border-color: var(--color-error, #ff4444);
}

.timer-display.timer-urgent .timer-value {
    color: var(--color-error, #ff4444);
    animation: pulse-urgent 1s ease-in-out infinite;
}

@keyframes pulse-urgent {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.8;
        transform: scale(1.02);
    }
}

/* =================================
   ACCESSIBILITY
   ================================= */

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    .role-info {
        animation: none;
    }

    .timer-display.timer-urgent .timer-value {
        animation: none;
    }

    .role-toggle-icon {
        transition: none;
    }
}

/* =================================
   MOBILE RESPONSIVE
   ================================= */

@media (max-width: 360px) {
    .role-display-compact .role-title {
        font-size: 20px;
    }

    .role-display-compact .role-subtitle {
        font-size: 14px;
    }

    .role-list-item {
        font-size: 12px;
    }
}
```

---

## Implementation Tasks

### Task 1: Verify GameState Role Data (AC: 1, 2)
- [x] Confirm `get_state()` includes `role_data` in QUESTIONING phase
- [x] Verify spy sees `possible_locations` array
- [x] Verify non-spy sees `location`, `role`, `hint`, `other_roles`
- [x] Add `_get_other_roles_at_location()` helper if missing

### Task 2: Update Player HTML (AC: 1, 2, 3, 4)
- [x] Add role reference section to questioning view
- [x] Add ARIA attributes for accessibility
- [x] Ensure timer is outside collapsible area (always visible)

### Task 3: Implement Role Content Display (AC: 1, 2, 5)
- [x] Implement `buildInnocentRoleDisplay()` and `buildSpyRoleDisplay()` in player.js
- [x] Generate spy-parity HTML structure
- [x] Use `data-role-type` attribute for CSS targeting

### Task 4: Implement Toggle Functionality (AC: 3, 4)
- [x] Role info displayed directly for better glanceability (design decision)
- [x] Timer remains visible at all times
- [x] State updates preserve display

### Task 5: Add Timer Integration (AC: 4)
- [x] Verify timer remains visible when role expanded
- [x] Add warning state at 30 seconds
- [x] Add urgent state at 10 seconds
- [x] Timer display updates from server broadcasts

### Task 6: Apply Spy Parity CSS (AC: 5)
- [x] Set fixed dimensions for role display
- [x] Match spacing for spy vs non-spy
- [x] Use `min-height` to ensure equal sizes
- [x] Identical HTML structure for spy/non-spy

### Task 7: Accessibility (AC: All)
- [x] ARIA attributes on role-display
- [x] `aria-live="polite"` on timer
- [x] Semantic HTML structure

### Task 8: Write Tests (AC: All)
- [x] Test role data included in QUESTIONING state
- [x] Test ROLES to QUESTIONING transition
- [x] Tests exist in test_state.py

---

## Testing Strategy

### Unit Tests

```python
def test_get_state_includes_spy_role_data(game_state_in_questioning):
    """Test spy receives location list in QUESTIONING phase."""
    spy_player = game_state_in_questioning.players["Alice"]
    spy_player.is_spy = True

    state = game_state_in_questioning.get_state(for_player="Alice")

    assert "role_data" in state
    assert state["role_data"]["is_spy"] is True
    assert "possible_locations" in state["role_data"]
    assert isinstance(state["role_data"]["possible_locations"], list)
    assert "location" not in state["role_data"]  # Spy doesn't see actual location

def test_get_state_includes_non_spy_role_data(game_state_in_questioning):
    """Test non-spy receives location and role in QUESTIONING phase."""
    player = game_state_in_questioning.players["Bob"]
    player.is_spy = False
    player.role = MockRole(name="Lifeguard", hint="Watch over swimmers")

    state = game_state_in_questioning.get_state(for_player="Bob")

    assert "role_data" in state
    assert state["role_data"]["is_spy"] is False
    assert "location" in state["role_data"]
    assert "role" in state["role_data"]
    assert "hint" in state["role_data"]
    assert "other_roles" in state["role_data"]
```

### Manual Testing Checklist

**Scenario 1: Non-Spy Role View**
- [ ] Click "View My Role" button
- [ ] See location name prominently
- [ ] See role name and hint
- [ ] See list of other roles at location
- [ ] Click again to hide
- [ ] Timer remains visible throughout

**Scenario 2: Spy Role View**
- [ ] Click "View My Role" button
- [ ] See "YOU ARE THE SPY" prominently
- [ ] See list of possible locations
- [ ] No actual location revealed
- [ ] Timer remains visible throughout

**Scenario 3: Spy Parity**
- [ ] Open spy view and non-spy view side by side
- [ ] Verify same overall height
- [ ] Verify same structure (title, subtitle, list)
- [ ] Cannot distinguish by layout alone

**Scenario 4: Timer Visibility**
- [ ] Expand role info
- [ ] Timer still visible
- [ ] Timer updates in real-time
- [ ] Timer urgency styling works when < 30s

**Scenario 5: Accessibility**
- [ ] Tab to toggle button
- [ ] Press Enter to toggle
- [ ] Press Space to toggle
- [ ] Screen reader announces toggle state
- [ ] Screen reader announces timer at 60s, 30s, 10s

---

## Definition of Done

- [ ] Role data included in QUESTIONING phase state
- [ ] Per-player filtering maintains role privacy
- [ ] Role toggle button works with click and keyboard
- [ ] Timer always visible when role expanded
- [ ] Spy parity: layouts have identical dimensions
- [ ] ARIA attributes for accessibility
- [ ] Screen reader announcements
- [ ] Respects `prefers-reduced-motion`
- [ ] Mobile responsive (320-428px)
- [ ] All tests pass
- [ ] Manual testing completed
- [ ] No console errors

---

## Dependencies

### Depends On
- **Story 4.1**: Transition to Questioning Phase
- **Story 4.2**: Round Timer with Countdown
- **Story 3.4**: Role Distribution (provides role data structure)
- **Story 3.5**: Role Display UI (reuses role components)

### Enables
- **Story 4.5**: Call Vote (shares same screen)

---

## Architecture Decisions Referenced

- **ARCH-7**: Per-player state filtering
- **ARCH-8**: Never broadcast same state to all
- **ARCH-14**: Broadcast state after mutations
- **UX-9, UX-10**: Spy parity requirements

---

## Notes

### Spy Parity is Critical

The #1 security concern for Spyfall is **visual tells**. If someone glances at a spy's phone and sees a different layout, the game is ruined.

This story implements strict parity:
- Same container dimensions
- Same element structure (title → subtitle → list)
- Same font sizes and spacing
- CSS uses `min-height` to enforce equal sizes

### Role Reference Design

The role reference is **collapsible** rather than always-visible because:
1. Reduces screen clutter during social gameplay
2. Players know their role after initial reveal
3. Makes room for timer and turn display
4. Toggle serves as a "cheat sheet" when needed

### Timer Visibility

The timer is placed **above** the collapsible role section and **outside** any toggle container. This ensures players always know how much time remains, which is critical for the game's tension.

---

## Dev Agent Record

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/game/state.py` | Pre-existing | `get_state()` includes `role_data` in QUESTIONING phase |
| `custom_components/spyster/www/player.html` | Pre-existing | Questioning view with timer, turn info, role display |
| `custom_components/spyster/www/js/player.js` | Pre-existing | `handleQuestioningPhase()`, `buildSpyRoleDisplay()`, `buildInnocentRoleDisplay()` |
| `custom_components/spyster/www/css/styles.css` | Pre-existing | Role display styles with spy parity |
| `tests/test_state.py` | Pre-existing | QUESTIONING phase transition tests |

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2025-12-23 | Story verification | Confirmed all tasks already implemented |

### Review Notes

- **Code Review Date:** 2025-12-23
- **Reviewer:** Amelia (Dev Agent)
- **Outcome:** APPROVED - Implementation complete
- **Design Decision:** Role info displayed directly (no toggle) for better glanceability during active gameplay
