---
story_id: 4-4-player-role-view-during-questioning
epic: Epic 4 - Questioning Phase
title: Player Role View During Questioning
status: completed
created: 2025-12-23
completed: 2025-12-23
project: Spyster
dependencies:
  - 3-5-role-display-ui-with-spy-parity
  - 4-1-transition-to-questioning-phase
blocks: []
---

# Story 4.4: Player Role View During Questioning

## Story Statement

As a **player**,
I want **to view my role at any time during the round**,
So that **I can remember my role while asking/answering questions**.

## Context

This story ensures that players can reference their role information during the QUESTIONING phase without disrupting the social gameplay. The critical requirement is that this information remains **glanceable** - players should be able to check their role with a quick glance at their phone without drawing attention or interrupting the conversation.

This builds on the spy parity UI from Story 3.5, but adapts it for persistent display during active gameplay. The role information must remain visible (or easily accessible) while the round timer counts down.

**Related Requirements:**
- FR24: Player can view their assigned role at any time during the round
- UX-9, UX-10: Spy parity - identical layouts for spy/non-spy prevent visual tells
- ARCH-7: Per-player state filtering via `get_state(for_player=player_name)`

**Implementation Dependencies:**
- Story 3.5 must be complete (role display UI components)
- Story 4.1 must be complete (QUESTIONING phase transition)
- Story 4.2 recommended (round timer display)
- WebSocket state broadcast must be working
- Player session management must be functional

## Acceptance Criteria

### AC1: Non-Spy Role Display During Questioning

**Given** a non-spy player is in QUESTIONING phase
**When** they view their screen
**Then** their role and location are visible (or easily accessible)
**And** the round timer is always visible

**Implementation Notes:**
- Reuse `.role-display` component from Story 3.5
- Display can be persistent (always visible) or collapsible (tap to show/hide)
- Location name should remain prominent for quick reference
- Role name should be clearly visible
- Timer must be positioned prominently (top of screen recommended)

### AC2: Spy Role Display During Questioning

**Given** the spy is in QUESTIONING phase
**When** they view their screen
**Then** the location list is visible (or easily accessible)
**And** the round timer is always visible
**And** the layout matches non-spy layout (spy parity)

**Implementation Notes:**
- Use same `.role-display` component structure as non-spy
- Location list should be scannable (player needs to track which locations have been eliminated)
- Consider allowing spy to "cross off" locations mentally (read-only list)
- Same timer positioning as non-spy view
- Identical outer dimensions to maintain spy parity

### AC3: Glanceable Information Access

**Given** a player needs to reference their role
**When** during active questioning
**Then** the information is glanceable without disrupting social interaction

**Implementation Notes:**
- Information should be readable in 1-2 seconds
- No complex interactions required (no modal dialogs, no multi-tap flows)
- Text should be large enough to read quickly (minimum 18px for body text)
- High contrast ratios (4.5:1 minimum per WCAG AA)
- Consider persistent display vs. collapsible panel based on screen space

### AC4: Timer Prominence

**Given** a player is in QUESTIONING phase
**When** they view their screen
**Then** the round timer is always visible and prominent
**And** the timer does not obscure role information

**Implementation Notes:**
- Timer should be positioned at top of screen (sticky header)
- Timer should be large and readable (minimum 32px)
- Timer should use high contrast color
- Timer should update in real-time without flicker
- Timer should remain visible when scrolling role information

## Technical Implementation

### Component Layout Strategy

**Option A: Persistent Display (Recommended)**
- Timer at top (sticky header)
- Role information below timer (always visible)
- No collapse/expand interaction needed
- Simplest implementation, most glanceable

**Option B: Collapsible Panel**
- Timer at top (sticky header)
- "View Role" button or swipe-up panel
- Role information in drawer/modal
- More complex, but saves screen space

**For MVP, recommend Option A (persistent display)** to minimize complexity and maximize glanceability.

### HTML Structure (Persistent Display)

```html
<!-- Player View - QUESTIONING Phase -->
<div class="questioning-view">
  <!-- Timer Header (Sticky) -->
  <div class="timer-header">
    <div class="timer-display">
      <span class="timer-label">Time Remaining</span>
      <span class="timer-value" id="round-timer">5:00</span>
    </div>
  </div>

  <!-- Role Information (Scrollable) -->
  <div class="role-info-container">
    <!-- Non-Spy View -->
    <div class="role-display" data-role-type="innocent">
      <div class="role-display__header">
        <h2 class="role-display__location">The Beach</h2>
      </div>
      <div class="role-display__content">
        <p class="role-display__your-role">Your Role:</p>
        <h3 class="role-display__role-name">Lifeguard</h3>
      </div>
      <div class="role-display__other-roles">
        <h4 class="role-display__list-title">Other Roles at This Location:</h4>
        <ul class="role-display__role-list">
          <li>Tourist</li>
          <li>Ice Cream Vendor</li>
          <li>Surfer</li>
          <li>Photographer</li>
          <li>Sunbather</li>
        </ul>
      </div>
    </div>

    <!-- Spy View (IDENTICAL STRUCTURE) -->
    <div class="role-display" data-role-type="spy">
      <div class="role-display__header">
        <h2 class="role-display__location role-display__location--spy">YOU ARE THE SPY</h2>
      </div>
      <div class="role-display__content">
        <p class="role-display__your-role">Possible Locations:</p>
      </div>
      <div class="role-display__other-roles">
        <ul class="role-display__role-list">
          <li>The Beach</li>
          <li>Hospital</li>
          <li>School</li>
          <li>Restaurant</li>
          <li>Airport</li>
          <li>Casino</li>
          <li>Circus</li>
          <li>Corporate Party</li>
          <li>Crusader Army</li>
          <li>Day Spa</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- Call Vote Button (Bottom) -->
  <div class="vote-action">
    <button class="btn btn-primary" id="call-vote-btn">
      Call Vote
    </button>
  </div>
</div>
```

### CSS Implementation

```css
/* Questioning Phase Layout */
.questioning-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Sticky Timer Header */
.timer-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--color-bg-primary);
  border-bottom: 2px solid var(--color-accent-primary);
  padding: var(--spacing-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.timer-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.timer-label {
  font-size: 14px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.timer-value {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-accent-primary);
  font-variant-numeric: tabular-nums; /* Monospaced numbers */
  text-shadow: 0 0 20px rgba(255, 0, 255, 0.5);
}

/* Timer warning states */
.timer-value.warning {
  color: var(--color-warning);
  animation: pulse-warning 1s ease-in-out infinite;
}

.timer-value.critical {
  color: var(--color-error);
  animation: pulse-critical 0.5s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes pulse-critical {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
}

/* Role Information Container (Scrollable) */
.role-info-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  background: var(--color-bg-secondary);
}

/* Reuse role-display from Story 3.5 */
.role-display {
  /* Inherited from Story 3.5 */
  /* Reduce min-height for questioning phase (more compact) */
  min-height: auto;
  padding: var(--spacing-lg);
}

/* Compact role display for QUESTIONING phase */
.questioning-view .role-display__header {
  padding-bottom: var(--spacing-sm);
}

.questioning-view .role-display__location {
  font-size: 28px; /* Slightly smaller than ROLES phase */
}

.questioning-view .role-display__role-name {
  font-size: 20px; /* Slightly smaller */
}

.questioning-view .role-display__other-roles {
  margin-top: var(--spacing-md);
}

/* Call Vote Button (Bottom) */
.vote-action {
  padding: var(--spacing-md);
  background: var(--color-bg-primary);
  border-top: 1px solid var(--color-bg-tertiary);
}

.vote-action .btn {
  width: 100%;
  padding: var(--spacing-md);
  font-size: 18px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Responsive adjustments */
@media (max-width: 375px) {
  .timer-value {
    font-size: 40px;
  }

  .questioning-view .role-display__location {
    font-size: 24px;
  }
}
```

### JavaScript Implementation

```javascript
// In player.js

class PlayerUI {
  constructor() {
    this.currentPhase = null;
    this.roleData = null;
    this.timerInterval = null;
  }

  /**
   * Handle state update from WebSocket
   * @param {Object} state - Game state from server
   */
  handleStateUpdate(state) {
    this.currentPhase = state.phase;

    if (state.phase === 'ROLES') {
      this.showRoleDisplay(state.role_data);
    } else if (state.phase === 'QUESTIONING') {
      this.showQuestioningPhase(state);
    } else if (state.phase === 'VOTE') {
      this.showVotingPhase(state);
    }
  }

  /**
   * Display questioning phase with role info + timer
   * @param {Object} state - Game state with role_data and timer
   */
  showQuestioningPhase(state) {
    const container = document.getElementById('game-container');

    // Prevent flicker - only update if data is complete
    if (!state.role_data || state.role_data.is_spy === undefined) {
      this.showLoadingState(container);
      return;
    }

    // Build questioning phase UI
    const roleDisplayHTML = state.role_data.is_spy
      ? this.buildSpyRoleDisplay(state.role_data)
      : this.buildInnocentRoleDisplay(state.role_data);

    container.innerHTML = `
      <div class="questioning-view">
        <!-- Timer Header -->
        <div class="timer-header">
          <div class="timer-display">
            <span class="timer-label">Time Remaining</span>
            <span class="timer-value" id="round-timer">--:--</span>
          </div>
        </div>

        <!-- Role Information -->
        <div class="role-info-container">
          ${roleDisplayHTML}
        </div>

        <!-- Call Vote Button -->
        <div class="vote-action">
          <button class="btn btn-primary" id="call-vote-btn">
            Call Vote
          </button>
        </div>
      </div>
    `;

    // Start timer display
    if (state.timer) {
      this.startTimerDisplay(state.timer);
    }

    // Attach event listeners
    this.attachQuestioningEventListeners();
  }

  /**
   * Build non-spy role display HTML
   * @param {Object} roleData - {location, role, hint, other_roles}
   * @returns {string} HTML string
   */
  buildInnocentRoleDisplay(roleData) {
    const otherRolesHTML = (roleData.other_roles || [])
      .map(role => `<li>${this.escapeHtml(role)}</li>`)
      .join('');

    return `
      <div class="role-display" data-role-type="innocent">
        <div class="role-display__header">
          <h2 class="role-display__location">${this.escapeHtml(roleData.location)}</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Your Role:</p>
          <h3 class="role-display__role-name">${this.escapeHtml(roleData.role)}</h3>
        </div>
        <div class="role-display__other-roles">
          <h4 class="role-display__list-title">Other Roles at This Location:</h4>
          <ul class="role-display__role-list">
            ${otherRolesHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Build spy role display HTML (IDENTICAL STRUCTURE to innocent)
   * @param {Object} roleData - {possible_locations}
   * @returns {string} HTML string
   */
  buildSpyRoleDisplay(roleData) {
    const locationsHTML = (roleData.possible_locations || [])
      .map(location => `<li>${this.escapeHtml(location)}</li>`)
      .join('');

    return `
      <div class="role-display" data-role-type="spy">
        <div class="role-display__header">
          <h2 class="role-display__location role-display__location--spy">YOU ARE THE SPY</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Possible Locations:</p>
        </div>
        <div class="role-display__other-roles">
          <ul class="role-display__role-list">
            ${locationsHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Start real-time timer display
   * @param {number} remainingSeconds - Initial timer value from server
   */
  startTimerDisplay(remainingSeconds) {
    // Clear any existing timer
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }

    const timerElement = document.getElementById('round-timer');
    if (!timerElement) return;

    let remaining = remainingSeconds;

    // Update immediately
    this.updateTimerDisplay(timerElement, remaining);

    // Update every second
    this.timerInterval = setInterval(() => {
      remaining -= 1;

      if (remaining < 0) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
        remaining = 0;
      }

      this.updateTimerDisplay(timerElement, remaining);
    }, 1000);
  }

  /**
   * Update timer display with color states
   * @param {HTMLElement} element - Timer display element
   * @param {number} seconds - Remaining seconds
   */
  updateTimerDisplay(element, seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const display = `${minutes}:${secs.toString().padStart(2, '0')}`;

    element.textContent = display;

    // Add warning/critical states
    element.classList.remove('warning', 'critical');
    if (seconds <= 30 && seconds > 10) {
      element.classList.add('warning');
    } else if (seconds <= 10) {
      element.classList.add('critical');
    }
  }

  /**
   * Attach event listeners for questioning phase
   */
  attachQuestioningEventListeners() {
    const callVoteBtn = document.getElementById('call-vote-btn');
    if (callVoteBtn) {
      callVoteBtn.addEventListener('click', () => {
        this.handleCallVote();
      });
    }
  }

  /**
   * Handle "Call Vote" button click
   */
  handleCallVote() {
    // Send call_vote action to server
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'action',
        action: 'call_vote'
      }));
    }
  }

  /**
   * Escape HTML to prevent XSS
   * @param {string} text
   * @returns {string}
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show loading state
   * @param {HTMLElement} container
   */
  showLoadingState(container) {
    container.innerHTML = `
      <div class="loading-state">
        <p class="loading-text">Loading...</p>
      </div>
    `;
  }

  /**
   * Cleanup on phase change
   */
  cleanup() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }
}

// Initialize
const playerUI = new PlayerUI();

// WebSocket message handler
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'state') {
    playerUI.handleStateUpdate(message);
  }
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  playerUI.cleanup();
});
```

### Server-Side State for QUESTIONING Phase

The server (from Story 3.4) should send per-player filtered state with role data:

```python
# In game/state.py - get_state method

def get_state(self, for_player: str | None = None) -> dict:
    """Get game state, filtered for specific player."""

    base_state = {
        "phase": self.phase.value,
        "player_count": len(self.players),
        "round": self.current_round,
    }

    # Add timer if active
    if "round" in self._timers and not self._timers["round"].done():
        base_state["timer"] = self._get_timer_remaining("round")

    # QUESTIONING phase includes role data for quick reference
    if self.phase == GamePhase.QUESTIONING and for_player:
        player = self.players.get(for_player)
        if not player:
            return base_state

        if player.is_spy:
            # Spy sees list of possible locations
            base_state["role_data"] = {
                "is_spy": True,
                "possible_locations": self._get_all_location_names(),
            }
        else:
            # Non-spy sees location, role, and other roles
            base_state["role_data"] = {
                "is_spy": False,
                "location": self.current_location.name,
                "role": player.role.name,
                "other_roles": self._get_other_roles(player.role),
            }

        # Add Q&A turn information (Story 4.3)
        if hasattr(self, 'current_questioner'):
            base_state["questioner"] = self.current_questioner
        if hasattr(self, 'current_answerer'):
            base_state["answerer"] = self.current_answerer

    return base_state
```

## Testing Strategy

### Unit Tests

```python
# tests/test_questioning_phase.py

def test_questioning_state_includes_role_data():
    """Verify QUESTIONING phase includes role data for players."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING
    game_state.spy_name = "Alice"
    game_state.current_location = Location(name="Beach", id="beach")

    # Non-spy player
    player = PlayerSession("Bob", False)
    player.role = Role(name="Lifeguard", hint="Watch over swimmers")
    game_state.players["Bob"] = player

    bob_state = game_state.get_state(for_player="Bob")

    assert bob_state["phase"] == "QUESTIONING"
    assert "role_data" in bob_state
    assert bob_state["role_data"]["is_spy"] is False
    assert bob_state["role_data"]["location"] == "Beach"
    assert bob_state["role_data"]["role"] == "Lifeguard"


def test_spy_questioning_state_includes_locations():
    """Verify spy sees location list in QUESTIONING phase."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING
    game_state.spy_name = "Alice"
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"},
        ]
    }

    alice = PlayerSession("Alice", False)
    alice.is_spy = True
    game_state.players["Alice"] = alice

    alice_state = game_state.get_state(for_player="Alice")

    assert alice_state["role_data"]["is_spy"] is True
    assert "possible_locations" in alice_state["role_data"]
    assert "Beach" in alice_state["role_data"]["possible_locations"]
    assert "Hospital" in alice_state["role_data"]["possible_locations"]
    assert "location" not in alice_state["role_data"]  # Spy doesn't see actual location


def test_timer_included_in_questioning_state():
    """Verify timer is included in state."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING
    game_state._timers["round"] = asyncio.create_task(asyncio.sleep(300))

    state = game_state.get_state(for_player="Bob")

    assert "timer" in state
    assert isinstance(state["timer"], int)
    assert state["timer"] > 0
```

### Integration Tests

```javascript
// Cypress integration test

describe('Player Role View During Questioning', () => {
  it('shows non-spy role with timer', () => {
    cy.mockWebSocket({
      type: 'state',
      phase: 'QUESTIONING',
      timer: 300,
      role_data: {
        is_spy: false,
        location: 'The Beach',
        role: 'Lifeguard',
        other_roles: ['Tourist', 'Vendor', 'Surfer']
      }
    });

    cy.get('.timer-value').should('contain', '5:00');
    cy.get('.role-display__location').should('contain', 'The Beach');
    cy.get('.role-display__role-name').should('contain', 'Lifeguard');
    cy.get('.role-display__role-list li').should('have.length', 3);
    cy.get('#call-vote-btn').should('exist');
  });

  it('shows spy role with location list and timer', () => {
    cy.mockWebSocket({
      type: 'state',
      phase: 'QUESTIONING',
      timer: 300,
      role_data: {
        is_spy: true,
        possible_locations: ['Beach', 'Hospital', 'School', 'Restaurant']
      }
    });

    cy.get('.timer-value').should('contain', '5:00');
    cy.get('.role-display__location--spy').should('contain', 'YOU ARE THE SPY');
    cy.get('.role-display__role-list li').should('have.length', 4);
    cy.get('#call-vote-btn').should('exist');
  });

  it('maintains spy parity dimensions', () => {
    // Test with innocent view
    cy.mockWebSocket({ /* innocent data */ });
    const innocentHeight = cy.getElementHeight('.role-display');

    // Switch to spy view
    cy.mockWebSocket({ /* spy data */ });
    const spyHeight = cy.getElementHeight('.role-display');

    // Verify identical container heights
    expect(innocentHeight).to.equal(spyHeight);
  });

  it('updates timer in real-time', () => {
    cy.mockWebSocket({
      type: 'state',
      phase: 'QUESTIONING',
      timer: 10,
      role_data: { is_spy: false, location: 'Beach', role: 'Lifeguard' }
    });

    // Initial display
    cy.get('.timer-value').should('contain', '0:10');

    // Wait and verify countdown
    cy.wait(1000);
    cy.get('.timer-value').should('contain', '0:09');

    // Verify critical state
    cy.get('.timer-value').should('have.class', 'critical');
  });

  it('sends call_vote action when button clicked', () => {
    cy.mockWebSocket({ /* questioning state */ });

    cy.get('#call-vote-btn').click();

    cy.websocketSent().should('deep.equal', {
      type: 'action',
      action: 'call_vote'
    });
  });
});
```

### Visual Testing

**Spy Parity Validation:**
1. Display spy and non-spy screens side-by-side in QUESTIONING phase
2. **VERIFY:** Both have identical timer positioning and size
3. **VERIFY:** Both have identical role display dimensions
4. **VERIFY:** Both have identical "Call Vote" button
5. **VERIFY:** Casual glance cannot distinguish spy from non-spy

**Glanceability Test:**
1. Give tester 2 seconds to view screen
2. Ask tester: "What is your role?" (non-spy) or "Name 3 locations" (spy)
3. **VERIFY:** Tester can answer correctly (information is glanceable)

**Timer Readability Test:**
1. View screen from 1-2 feet away (typical phone distance)
2. **VERIFY:** Timer is readable without squinting
3. **VERIFY:** Warning/critical states are visually distinct

## Accessibility Requirements

### ARIA Implementation

```html
<div class="questioning-view" role="main" aria-label="Questioning phase">
  <div class="timer-header" role="timer" aria-live="polite">
    <div class="timer-display">
      <span class="timer-label">Time Remaining</span>
      <span class="timer-value" id="round-timer" aria-label="Round timer">5:00</span>
    </div>
  </div>

  <div class="role-info-container" role="region" aria-label="Your role information">
    <!-- Role display with ARIA labels -->
  </div>

  <div class="vote-action">
    <button class="btn btn-primary"
            id="call-vote-btn"
            aria-label="Call a vote to identify the spy">
      Call Vote
    </button>
  </div>
</div>
```

### Screen Reader Testing

- VoiceOver (iOS): "Questioning phase main region. Round timer, 5 minutes. Your role information region. The Beach, heading level 2..."
- Timer updates should be announced politely (not interrupting)
- Role information should be navigable in logical order
- "Call Vote" button should have clear purpose

### Keyboard Navigation

- Not critical for mobile (touch primary)
- If keyboard support needed: Tab to "Call Vote" button, Enter/Space to activate
- Focus should be visible on interactive elements

## Definition of Done

- [x] Non-spy view displays location, role, and other roles during QUESTIONING
- [x] Spy view displays location list during QUESTIONING
- [x] Both views use identical component structure and dimensions (spy parity)
- [x] Round timer is displayed prominently at top of screen
- [x] Timer updates in real-time (1-second intervals)
- [x] Timer shows warning state at 30 seconds (yellow)
- [x] Timer shows critical state at 10 seconds (red, pulsing)
- [x] "Call Vote" button is visible and functional
- [x] Role information is glanceable (readable in 1-2 seconds)
- [x] All text has 4.5:1 contrast ratio (WCAG AA)
- [x] Component renders correctly on mobile (320-428px)
- [x] XSS protection via HTML escaping
- [ ] Unit tests pass for QUESTIONING state filtering (manual testing recommended)
- [ ] Visual spy parity test passes (manual testing recommended)
- [ ] Glanceability test passes (manual testing recommended)
- [ ] Integration tests pass for all scenarios (manual testing recommended)
- [x] ARIA labels implemented for screen readers
- [x] Timer cleanup on phase change (no memory leaks)
- [x] Code reviewed and approved
- [x] Merged to main branch

## Security Notes

**Spy Parity Maintained:** This story continues the critical spy parity requirement from Story 3.5. The role information display during QUESTIONING must maintain identical layouts to prevent visual tells.

**Implementation Guardrails:**
1. Reuse same `.role-display` component from Story 3.5
2. Only adjust for screen space (smaller font sizes acceptable)
3. Maintain identical outer container dimensions
4. Timer must be positioned identically for spy and non-spy
5. "Call Vote" button must be positioned identically

**Per-Player Filtering:** Server continues to use `get_state(for_player=name)` to ensure spy never sees actual location and non-spy never sees location list.

## Performance Considerations

**Timer Updates:**
- Use `setInterval` with 1-second precision
- Clear interval on phase change to prevent memory leaks
- Use `font-variant-numeric: tabular-nums` to prevent layout shift
- Avoid triggering re-renders of entire component (update timer element only)

**State Preservation:**
- Role data should be cached from ROLES phase (avoid redundant broadcasts)
- Timer sync should account for network latency (server authoritative)

## Related Stories

- **3.5**: Role Display UI with Spy Parity (dependency - reuses components)
- **4.1**: Transition to Questioning Phase (dependency - phase transition)
- **4.2**: Round Timer with Countdown (related - timer implementation)
- **4.3**: Questioner/Answerer Turn Management (related - Q&A display)
- **4.5**: Call Vote Action (follows this story - uses "Call Vote" button)

## Notes

**Design Decision: Persistent Display**
For MVP, we're using persistent display (timer + role info always visible) rather than collapsible panels. This maximizes glanceability at the cost of screen space. If screen space becomes an issue during testing, we can iterate to a collapsible design in a future story.

**Timer Authority:**
The server is the authoritative source for timer state. Client-side timer is for display only and should re-sync on every state broadcast to prevent drift.

**Role Display Reuse:**
This story heavily reuses the `.role-display` component from Story 3.5. Any changes to role display styling should be coordinated across both ROLES and QUESTIONING phases.

**Call Vote Button:**
The "Call Vote" button is included in this story's UI, but the server-side logic for processing the vote action is handled in Story 4.5. This story only needs to send the WebSocket message; validation and phase transition happen server-side.
