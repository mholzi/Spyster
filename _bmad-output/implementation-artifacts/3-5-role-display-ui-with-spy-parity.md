---
story_id: 3-5-role-display-ui-with-spy-parity
epic: Epic 3 - Game Configuration & Role Assignment
title: Role Display UI with Spy Parity
status: ready-for-dev
created: 2025-12-23
project: Spyster
dependencies:
  - 3-4-role-distribution-with-per-player-filtering
blocks: []
---

# Story 3.5: Role Display UI with Spy Parity

## Story Statement

As a **player**,
I want **to see my role clearly on my phone**,
So that **I know my role and can play accordingly**.

## Context

This story implements the player-facing UI for role display during the ROLES phase. The critical requirement is **spy parity** - the spy and non-spy screens must have identical layouts and dimensions so that casual observation cannot reveal who the spy is. This is a security requirement per UX-9 and UX-10.

**Related Requirements:**
- FR20: Non-spy players see location name and their role
- FR21: Spy player sees "YOU ARE THE SPY" and list of possible locations
- FR22: Loading state during role assignment prevents data leak
- UX-9, UX-10: Spy parity - identical layouts prevent visual tells
- ARCH-7: Per-player state filtering via `get_state(for_player=player_name)`

**Implementation Dependencies:**
- Story 3.4 must be complete (server-side per-player filtering)
- WebSocket state broadcast must be working
- Player session management must be functional

## Acceptance Criteria

### AC1: Non-Spy Role Display

**Given** a non-spy player is in ROLES phase
**When** their screen displays the role
**Then** they see:
- Location name prominently displayed (32px heading size)
- Their assigned role (24px text)
- A list of other possible roles at this location (16px text, muted)

**Implementation Notes:**
- Use `.role-display` component from UX design
- Location name should use `--color-accent-primary` (pink)
- Role list should be scrollable if more than 8 roles
- All text must have 4.5:1 contrast ratio (WCAG AA)

### AC2: Spy Role Display

**Given** the spy is in ROLES phase
**When** their screen displays the role
**Then** they see:
- "YOU ARE THE SPY" prominently displayed (32px heading size)
- The list of possible locations (16px text, muted)

**Implementation Notes:**
- Use same `.role-display` component structure as non-spy
- "YOU ARE THE SPY" should use `--color-error` (red) with subtle glow
- Location list should be scrollable if more than 10 locations
- Same padding, margins, and dimensions as non-spy view

### AC3: Spy Parity Layout

**Given** spy and non-spy screens are compared
**When** viewed side-by-side
**Then** the layouts have:
- Identical outer container dimensions
- Identical padding and margins
- Identical font sizes for comparable elements (heading/body/list)
- Same component structure (container → header → content → list)

**And** a casual glance cannot distinguish spy from non-spy

**Implementation Notes:**
- Critical security requirement - use same CSS classes
- Only text content differs, not layout/structure
- Both views must render at same height to prevent visual tells
- Test by placing phones side-by-side during development

### AC4: Loading State and Transition

**Given** all players see "Assigning roles..." loading state
**When** the transition to ROLES phase occurs
**Then**:
- No partial data or flicker is visible
- Role information appears atomically (all at once)
- Loading state persists until complete role data received

**And** this prevents data leak per FR22

**Implementation Notes:**
- Use loading skeleton that matches final layout dimensions
- Wait for complete WebSocket message before rendering role
- Transition should be smooth fade (300ms)
- Loading state should show "Assigning roles..." with subtle animation

## Technical Implementation

### Component Structure

```html
<!-- Non-Spy View -->
<div class="role-display" data-role-type="innocent">
  <div class="role-display__header">
    <h2 class="role-display__location">The Beach</h2>
  </div>
  <div class="role-display__content">
    <p class="role-display__your-role">Your Role:</p>
    <h3 class="role-display__role-name">Lifeguard</h3>
    <p class="role-display__hint">You watch over swimmers from your elevated chair</p>
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
    <!-- Empty space to match layout -->
  </div>
  <div class="role-display__other-roles">
    <h4 class="role-display__list-title">Guess the Location:</h4>
    <ul class="role-display__role-list">
      <li>The Beach</li>
      <li>Hospital</li>
      <li>School</li>
      <!-- ... all locations -->
    </ul>
  </div>
</div>
```

### CSS Implementation

```css
/* Base component - IDENTICAL for both spy and non-spy */
.role-display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-xl);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  min-height: 480px; /* CRITICAL: Fixed height for parity */
}

.role-display__header {
  text-align: center;
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-tertiary);
}

.role-display__location {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-accent-primary);
  margin: 0;
}

.role-display__location--spy {
  color: var(--color-error);
  text-shadow: 0 0 20px rgba(255, 0, 64, 0.5);
}

.role-display__content {
  min-height: 120px; /* CRITICAL: Ensures consistent spacing */
}

.role-display__your-role {
  font-size: 14px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 var(--spacing-sm);
}

.role-display__role-name {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md);
}

.role-display__hint {
  font-size: 16px;
  color: var(--color-text-secondary);
  font-style: italic;
  margin: 0;
}

.role-display__other-roles {
  flex: 1;
  overflow-y: auto;
}

.role-display__list-title {
  font-size: 14px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 var(--spacing-md);
}

.role-display__role-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.role-display__role-list li {
  font-size: 16px;
  color: var(--color-text-secondary);
  padding: var(--spacing-sm);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

/* Loading state */
.role-display--loading {
  justify-content: center;
  align-items: center;
}

.role-display__loading-text {
  font-size: 24px;
  color: var(--color-text-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
```

### JavaScript Implementation

```javascript
// In player.js

class PlayerUI {
  constructor() {
    this.currentPhase = null;
    this.roleData = null;
  }

  /**
   * Handle state update from WebSocket
   * @param {Object} state - Game state from server
   */
  handleStateUpdate(state) {
    if (state.phase === 'ROLES' && state.role_data) {
      this.showRoleDisplay(state.role_data);
    }
  }

  /**
   * Display role information with spy parity
   * @param {Object} roleData - Per-player role information
   */
  showRoleDisplay(roleData) {
    const container = document.getElementById('role-container');

    // Prevent flicker - only update if data is complete
    if (!roleData || !roleData.is_spy === undefined) {
      this.showLoadingState(container);
      return;
    }

    if (roleData.is_spy) {
      this.renderSpyView(container, roleData);
    } else {
      this.renderInnocentView(container, roleData);
    }

    // Smooth fade-in transition
    container.classList.add('fade-in');
  }

  /**
   * Show loading state during role assignment
   * @param {HTMLElement} container
   */
  showLoadingState(container) {
    container.innerHTML = `
      <div class="role-display role-display--loading">
        <p class="role-display__loading-text">Assigning roles...</p>
      </div>
    `;
  }

  /**
   * Render non-spy role view
   * @param {HTMLElement} container
   * @param {Object} roleData - {location, role, hint, other_roles}
   */
  renderInnocentView(container, roleData) {
    const otherRolesHTML = roleData.other_roles
      .map(role => `<li>${this.escapeHtml(role)}</li>`)
      .join('');

    container.innerHTML = `
      <div class="role-display" data-role-type="innocent">
        <div class="role-display__header">
          <h2 class="role-display__location">${this.escapeHtml(roleData.location)}</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Your Role:</p>
          <h3 class="role-display__role-name">${this.escapeHtml(roleData.role)}</h3>
          <p class="role-display__hint">${this.escapeHtml(roleData.hint)}</p>
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
   * Render spy role view (IDENTICAL STRUCTURE to innocent)
   * @param {HTMLElement} container
   * @param {Object} roleData - {possible_locations}
   */
  renderSpyView(container, roleData) {
    const locationsHTML = roleData.possible_locations
      .map(location => `<li>${this.escapeHtml(location)}</li>`)
      .join('');

    container.innerHTML = `
      <div class="role-display" data-role-type="spy">
        <div class="role-display__header">
          <h2 class="role-display__location role-display__location--spy">YOU ARE THE SPY</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Possible Locations:</p>
          <!-- Empty space maintains layout parity -->
        </div>
        <div class="role-display__other-roles">
          <h4 class="role-display__list-title">Guess the Location:</h4>
          <ul class="role-display__role-list">
            ${locationsHTML}
          </ul>
        </div>
      </div>
    `;
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
```

### Server-Side Payload Structure

The server (from Story 3.4) should send per-player filtered state:

```python
# In game/state.py - get_state method

def get_state(self, for_player: str | None = None) -> dict:
    """Get game state, filtered for specific player."""

    base_state = {
        "phase": self.phase.value,
        "player_count": len(self.players),
        "round": self.current_round,
    }

    if self.phase == GamePhase.ROLES and for_player:
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
            # Non-spy sees location, role, hint, and other roles
            base_state["role_data"] = {
                "is_spy": False,
                "location": self.current_location.name,
                "role": player.role.name,
                "hint": player.role.hint,
                "other_roles": self._get_other_roles(player.role),
            }

    return base_state
```

## Testing Strategy

### Unit Tests

```python
# tests/test_role_display.py

def test_spy_payload_structure():
    """Verify spy receives correct data structure."""
    state = game_state.get_state(for_player="Dave")
    assert state["role_data"]["is_spy"] is True
    assert "possible_locations" in state["role_data"]
    assert "location" not in state["role_data"]  # Spy doesn't see location

def test_innocent_payload_structure():
    """Verify non-spy receives correct data structure."""
    state = game_state.get_state(for_player="Jenna")
    assert state["role_data"]["is_spy"] is False
    assert "location" in state["role_data"]
    assert "role" in state["role_data"]
    assert "hint" in state["role_data"]
    assert "other_roles" in state["role_data"]

def test_loading_state_prevents_flicker():
    """Verify loading state persists until complete data."""
    # Incomplete data should trigger loading state
    incomplete_state = {"phase": "ROLES"}  # No role_data
    # UI should show loading state, not error
```

### Visual Testing

**Spy Parity Validation:**
1. Place two phones side-by-side (one spy, one innocent)
2. Verify identical outer dimensions
3. Verify identical spacing and padding
4. Verify font sizes match for comparable elements
5. Casual glance test: Can you tell which is spy?

**Expected Result:** Layouts should be visually indistinguishable except for text content.

### Integration Tests

```javascript
// Cypress integration test

describe('Role Display UI', () => {
  it('shows non-spy role with location and role list', () => {
    cy.mockWebSocket({
      type: 'state',
      phase: 'ROLES',
      role_data: {
        is_spy: false,
        location: 'The Beach',
        role: 'Lifeguard',
        hint: 'You watch over swimmers',
        other_roles: ['Tourist', 'Vendor', 'Surfer']
      }
    });

    cy.get('.role-display__location').should('contain', 'The Beach');
    cy.get('.role-display__role-name').should('contain', 'Lifeguard');
    cy.get('.role-display__role-list li').should('have.length', 3);
  });

  it('shows spy role with location list', () => {
    cy.mockWebSocket({
      type: 'state',
      phase: 'ROLES',
      role_data: {
        is_spy: true,
        possible_locations: ['Beach', 'Hospital', 'School', 'Restaurant']
      }
    });

    cy.get('.role-display__location--spy').should('contain', 'YOU ARE THE SPY');
    cy.get('.role-display__role-list li').should('have.length', 4);
  });

  it('shows loading state before role data arrives', () => {
    cy.get('.role-display--loading').should('exist');
    cy.get('.role-display__loading-text').should('contain', 'Assigning roles');
  });

  it('maintains spy parity dimensions', () => {
    // Get dimensions of innocent view
    const innocentDimensions = cy.getElementDimensions('.role-display[data-role-type="innocent"]');

    // Switch to spy view
    cy.mockWebSocket({ /* spy data */ });

    // Get dimensions of spy view
    const spyDimensions = cy.getElementDimensions('.role-display[data-role-type="spy"]');

    // Verify identical dimensions
    expect(innocentDimensions.height).to.equal(spyDimensions.height);
    expect(innocentDimensions.width).to.equal(spyDimensions.width);
  });
});
```

## Accessibility Requirements

### ARIA Implementation

```html
<div class="role-display"
     role="region"
     aria-label="Your role assignment">
  <div class="role-display__header">
    <h2 class="role-display__location"
        aria-live="polite">The Beach</h2>
  </div>
  <!-- ... -->
</div>
```

### Screen Reader Testing

- VoiceOver (iOS): "Your role assignment region, The Beach, heading level 2, Your Role: Lifeguard, heading level 3"
- All text must be readable in logical order
- List semantics must be preserved for role/location lists

### Keyboard Navigation

- Not required for this view (display-only, no interactive elements)
- Focus should remain on main game container
- Transition to next phase should be automatic (via timer)

## Definition of Done

- [ ] Non-spy view displays location, role, hint, and other roles
- [ ] Spy view displays "YOU ARE THE SPY" and location list
- [ ] Both views use identical component structure and CSS classes
- [ ] Layouts have identical dimensions (verified side-by-side)
- [ ] Loading state prevents data flicker/leak
- [ ] All text has 4.5:1 contrast ratio (WCAG AA)
- [ ] Component renders correctly on mobile (320-428px)
- [ ] XSS protection via HTML escaping
- [ ] Unit tests pass for both spy and innocent payloads
- [ ] Visual spy parity test passes
- [ ] Integration tests pass for all scenarios
- [ ] ARIA labels implemented for screen readers
- [ ] Code reviewed and approved
- [ ] Merged to main branch

## Security Notes

**Critical Security Requirement:** Spy parity is a security feature, not just aesthetics. If players can identify the spy by screen layout, the game is broken.

**Implementation Guardrails:**
1. Always use same base `.role-display` component
2. Never add spy-specific classes that change layout
3. Test with actual devices side-by-side before merging
4. Use fixed `min-height` to prevent height differences
5. Ensure list overflow behavior is identical

## Related Stories

- **3.4**: Role Distribution with Per-Player Filtering (dependency)
- **4.1**: Transition to Questioning Phase (follows this story)
- **4.4**: Player Role View During Questioning (reuses this component)

## Notes

This story implements the player-facing UI only. The host display does NOT show individual roles (that would break the game). Host sees "Roles Assigned" transition marker only.

The 5-second role display timer (ARCH-10) is handled by Story 4.1 (phase transition), not this story.
