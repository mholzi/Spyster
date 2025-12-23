# Story 7.2: Phase Indicators

Status: review

## Story

As a **viewer (anyone in the room)**,
I want **to clearly see the current game phase**,
so that **I know what's happening in the game**.

## Acceptance Criteria

1. **Given** the host display, **When** in LOBBY phase, **Then** "LOBBY" indicator is visible with player count.

2. **Given** the host display, **When** in QUESTIONING phase, **Then** "QUESTIONING" indicator shows with round number **And** the timer is prominently displayed.

3. **Given** the host display, **When** in VOTE phase, **Then** "VOTING" indicator shows with submission count.

4. **Given** the host display, **When** in REVEAL phase, **Then** "REVEAL" indicator shows during the sequence.

5. **Given** the host display, **When** in SCORING phase, **Then** "RESULTS" indicator shows with leaderboard.

6. **Given** phase transitions, **When** a phase changes, **Then** a transition marker animation plays (e.g., "ROUND 1", "VOTE CALLED").

## Tasks / Subtasks

- [x] Task 1: Create phase indicator component (AC: #1-5)
  - [x] 1.1: Add `.phase-indicator` container in host.html header
  - [x] 1.2: Style phase badge with large, visible typography
  - [x] 1.3: Add phase-specific colors (LOBBY=cyan, QUESTIONING=pink, VOTING=gold, etc.)
  - [x] 1.4: Include secondary info slot (player count, round number, etc.)

- [x] Task 2: Implement phase-specific content in indicators (AC: #1-5)
  - [x] 2.1: LOBBY: Show "LOBBY" + "X/10 players" count
  - [x] 2.2: QUESTIONING: Show "QUESTIONING" + "Round X of Y"
  - [x] 2.3: VOTE: Show "VOTING" + "X/Y voted" submission tracker
  - [x] 2.4: REVEAL: Show "REVEAL" with no secondary info
  - [x] 2.5: SCORING: Show "RESULTS" + "Round X Complete"

- [x] Task 3: Implement phase transition animations (AC: #6)
  - [x] 3.1: Create `.phase-transition-overlay` full-screen element
  - [x] 3.2: Add CSS animations for fade-in, scale-up, fade-out sequence
  - [x] 3.3: Display transition text ("ROUND 1", "VOTE CALLED", "SPY CAUGHT!")
  - [x] 3.4: Auto-dismiss overlay after 2-3 seconds
  - [x] 3.5: Respect `prefers-reduced-motion` media query

- [x] Task 4: Update host.js for phase indicator rendering (AC: #1-6)
  - [x] 4.1: Add `updatePhaseIndicator(phase, data)` function
  - [x] 4.2: Call from each render function (renderLobby, renderQuestioning, etc.)
  - [x] 4.3: Track previous phase for transition detection
  - [x] 4.4: Trigger transition overlay on phase change
  - [x] 4.5: Update vote submission count in VOTE phase

## Dev Notes

### Architecture Compliance

- **HTML Location**: `www/host.html`
- **CSS Location**: `www/css/styles.css`
- **JS Location**: `www/js/host.js`
- **No External Dependencies**: Vanilla HTML/CSS/JS only

### Technical Requirements

- **WebSocket Protocol**: Phase info comes in `state` messages as `phase` field
- **Message Format**: `{"type": "state", "phase": "QUESTIONING", "round_number": 1, ...}`
- **Accessibility**: Phase indicator should have `aria-live="polite"` for screen readers

### Existing Code Analysis

From `host.html`:
- Phase badge exists at line 16: `<span id="phase-display" class="phase-badge" aria-live="polite"></span>`
- Already has basic ARIA support

From `host.js`:
- `setText('phase-display', 'LOBBY')` called in `renderLobby()` (line 181)
- Each render function sets phase text independently
- No transition animation system exists

### Implementation Approach

1. **Phase Indicator HTML Structure**:
   ```html
   <div class="phase-indicator">
     <span id="phase-name" class="phase-name">LOBBY</span>
     <span id="phase-info" class="phase-info">5/10 players</span>
   </div>
   ```

2. **Phase Colors**:
   ```css
   .phase-indicator[data-phase="LOBBY"] { --phase-color: var(--color-cyan); }
   .phase-indicator[data-phase="QUESTIONING"] { --phase-color: var(--color-pink); }
   .phase-indicator[data-phase="VOTE"] { --phase-color: var(--color-gold); }
   .phase-indicator[data-phase="REVEAL"] { --phase-color: var(--color-white); }
   .phase-indicator[data-phase="SCORING"] { --phase-color: var(--color-cyan); }
   ```

3. **Transition Overlay**:
   ```css
   .phase-transition-overlay {
     position: fixed;
     inset: 0;
     display: flex;
     align-items: center;
     justify-content: center;
     background: rgba(0, 0, 0, 0.9);
     animation: phase-transition 2.5s ease-out forwards;
   }

   @keyframes phase-transition {
     0% { opacity: 0; transform: scale(0.8); }
     20% { opacity: 1; transform: scale(1); }
     80% { opacity: 1; transform: scale(1); }
     100% { opacity: 0; transform: scale(1.1); }
   }
   ```

4. **JavaScript Phase Tracking**:
   ```javascript
   let previousPhase = null;

   function updatePhaseIndicator(phase, data) {
     if (phase !== previousPhase) {
       showPhaseTransition(phase, data);
       previousPhase = phase;
     }
     // Update indicator content
   }
   ```

### File Structure Notes

- Modify: `custom_components/spyster/www/host.html`
- Modify: `custom_components/spyster/www/css/styles.css`
- Modify: `custom_components/spyster/www/js/host.js`
- No new files needed

### References

- [Source: _bmad-output/epics.md#Story 7.2: Phase Indicators]
- [Source: _bmad-output/architecture.md#WebSocket Message Protocol]
- [Source: _bmad-output/project-context.md#JavaScript Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No runtime errors during implementation

### Completion Notes List

- **2025-12-23**: Implemented comprehensive phase indicator system
  - **HTML**: Added `.phase-indicator` component with `#phase-name` and `#phase-info` slots
  - **HTML**: Added `.phase-transition-overlay` for dramatic phase change animations
  - **CSS**: Phase-specific colors via `data-phase` attribute:
    - LOBBY: Cyan (`--color-accent-secondary`)
    - ROLES: Purple (#9945ff)
    - QUESTIONING: Pink (`--color-accent-primary`)
    - VOTE: Gold (`--color-all-in`)
    - REVEAL: White
    - SCORING: Green (`--color-success`)
    - PAUSED: Orange with pulse animation
  - **CSS**: Transition overlay with scale-up, fade-in/out animation (2.5s)
  - **CSS**: Host display scaling for phase indicator at all breakpoints
  - **CSS**: `prefers-reduced-motion` support for all animations
  - **JS**: Added `updatePhaseIndicator(phase, data)` function
  - **JS**: Added `showPhaseTransition(phase, data)` function
  - **JS**: Added `getPhaseInfo()` for phase-specific secondary info
  - **JS**: Added `getTransitionContent()` for transition text/type
  - **JS**: Updated all render functions to call updatePhaseIndicator
  - **JS**: Handles all phases: LOBBY, ROLES, QUESTIONING, VOTE, REVEAL, SCORING, END, PAUSED

### File List

- `custom_components/spyster/www/host.html` - Phase indicator and transition overlay HTML (lines 16-29)
- `custom_components/spyster/www/css/styles.css` - Phase indicator styles (lines 3774-4051)
- `custom_components/spyster/www/js/host.js` - Phase indicator functions and render updates

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Implemented Story 7.2: Phase Indicators - indicator component, phase-specific colors/content, transition animations |
