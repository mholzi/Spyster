# Story 7.5: Host Admin Controls

Status: done

## Story

As a **host**,
I want **admin controls to manage the game**,
so that **I can pause, skip, or end as needed**.

## Acceptance Criteria

1. **Given** the host display, **When** viewing the game, **Then** a floating admin bar is visible (fixed position) **And** controls don't obstruct main game display.

2. **Given** the admin bar in QUESTIONING phase, **When** host wants to speed up, **Then** "SKIP TO VOTE" button is available.

3. **Given** the admin bar in any phase, **When** host needs to pause, **Then** "PAUSE" button transitions game to PAUSED phase **And** all players see "Game Paused" message.

4. **Given** the admin bar, **When** host wants to end, **Then** "END GAME" button is available with confirmation modal.

5. **Given** the PAUSED phase, **When** host taps "RESUME", **Then** game returns to previous phase **And** timers resume from where they paused.

## Tasks / Subtasks

- [x] Task 1: Create floating admin bar component (AC: #1)
  - [x] 1.1: Add `.admin-bar` fixed position container in host.html
  - [x] 1.2: Style admin bar for non-intrusive visibility (translucent, bottom-right)
  - [x] 1.3: Add collapse/expand toggle button
  - [x] 1.4: Ensure bar doesn't obstruct critical game information

- [x] Task 2: Implement phase-specific controls (AC: #2, #3, #4)
  - [x] 2.1: Add "SKIP TO VOTE" button (visible in QUESTIONING phase only)
  - [x] 2.2: Add "PAUSE" button (visible in QUESTIONING/VOTE phases)
  - [x] 2.3: Add "END GAME" button (visible in all phases)
  - [x] 2.4: Add "NEXT ROUND" button (visible in SCORING phase)
  - [x] 2.5: Show/hide buttons based on current phase

- [x] Task 3: Implement pause/resume functionality (AC: #3, #5)
  - [x] 3.1: Send `pause_game` admin action on PAUSE button click
  - [x] 3.2: Send `resume_game` admin action on RESUME button click
  - [x] 3.3: Update PAUSE button to show "RESUME" when paused
  - [x] 3.4: Display paused state on host display (dim overlay + "PAUSED" text)
  - [x] 3.5: Handle server state for timer preservation

- [x] Task 4: Implement end game with confirmation (AC: #4)
  - [x] 4.1: Show confirmation modal on END GAME click
  - [x] 4.2: Modal text: "End the game? Current scores will be final."
  - [x] 4.3: Confirm button sends `end_game` admin action
  - [x] 4.4: Cancel button dismisses modal
  - [x] 4.5: Style modal with dark theme matching game

- [x] Task 5: Update host.js for admin control logic (AC: #1-5)
  - [x] 5.1: Add `initAdminControls()` function
  - [x] 5.2: Add `updateAdminBarVisibility(phase)` function
  - [x] 5.3: Add handlers for each admin action
  - [x] 5.4: Add modal show/hide functions
  - [x] 5.5: Track pause state and previous phase locally

## Dev Notes

### Architecture Compliance

- **HTML Location**: `www/host.html`
- **CSS Location**: `www/css/styles.css`
- **JS Location**: `www/js/host.js`
- **WebSocket Protocol**: Admin actions use `{"type": "admin", "action": "..."}`

### Technical Requirements

- **Admin Actions** (from architecture):
  - `pause_game` - Manual pause
  - `resume_game` - Resume from PAUSED
  - `end_game` - Force end current game
  - `skip_to_vote` - Skip remaining question time (not in original list, new for Epic 7)

- **Phase State Machine**:
  - Any → PAUSED (host pause or disconnect)
  - PAUSED → Previous (host resume)

- **Timer Preservation**: Server handles timer pause/resume

### Existing Code Analysis

From `host.html`:
- Host controls exist at lines 153-161 in questioning section
- NEXT TURN button already implemented
- No floating admin bar exists

From `host.js`:
- `sendMessage()` function at lines 335-341 for WebSocket messages
- `startGame()` at lines 793-805 sends admin action
- `advanceTurn()` at lines 843-855 sends admin action
- Pattern established for admin actions

### Implementation Approach

1. **Admin Bar HTML**:
   ```html
   <div id="admin-bar" class="admin-bar collapsed">
     <button id="admin-toggle" class="admin-toggle" aria-label="Toggle admin controls">
       <span class="toggle-icon">⚙️</span>
     </button>
     <div class="admin-controls">
       <button id="btn-skip-vote" class="admin-btn" data-phases="QUESTIONING">
         SKIP TO VOTE
       </button>
       <button id="btn-pause" class="admin-btn" data-phases="QUESTIONING,VOTE">
         PAUSE
       </button>
       <button id="btn-end-game" class="admin-btn danger" data-phases="*">
         END GAME
       </button>
     </div>
   </div>
   ```

2. **Admin Bar CSS**:
   ```css
   .admin-bar {
     position: fixed;
     bottom: var(--space-md);
     right: var(--space-md);
     display: flex;
     gap: var(--space-sm);
     background: rgba(10, 10, 18, 0.9);
     border: 1px solid var(--color-pink);
     border-radius: var(--radius-lg);
     padding: var(--space-sm);
     z-index: 1000;
     transition: transform 0.3s ease;
   }

   .admin-bar.collapsed .admin-controls {
     display: none;
   }

   .admin-btn {
     padding: var(--space-sm) var(--space-md);
     background: var(--color-surface);
     border: 1px solid var(--color-pink);
     color: var(--color-text);
     border-radius: var(--radius-md);
     cursor: pointer;
   }

   .admin-btn.danger {
     border-color: #ff4444;
     color: #ff4444;
   }
   ```

3. **Confirmation Modal**:
   ```html
   <div id="confirm-modal" class="modal hidden" role="dialog" aria-modal="true">
     <div class="modal-content">
       <h3 id="modal-title">End Game?</h3>
       <p id="modal-message">Current scores will be final.</p>
       <div class="modal-actions">
         <button id="modal-cancel" class="btn-secondary">Cancel</button>
         <button id="modal-confirm" class="btn-danger">End Game</button>
       </div>
     </div>
   </div>
   ```

4. **Admin Control JavaScript**:
   ```javascript
   function initAdminControls() {
     // Toggle expand/collapse
     getElement('admin-toggle').addEventListener('click', () => {
       getElement('admin-bar').classList.toggle('collapsed');
     });

     // Admin action handlers
     getElement('btn-skip-vote').addEventListener('click', () => {
       sendMessage({ type: 'admin', action: 'skip_to_vote' });
     });

     getElement('btn-pause').addEventListener('click', handlePauseResume);
     getElement('btn-end-game').addEventListener('click', showEndGameModal);
   }

   function updateAdminBarVisibility(phase) {
     const buttons = document.querySelectorAll('.admin-btn[data-phases]');
     buttons.forEach(btn => {
       const phases = btn.dataset.phases.split(',');
       btn.style.display = (phases.includes(phase) || phases.includes('*'))
         ? 'block'
         : 'none';
     });

     // Update pause button text
     const pauseBtn = getElement('btn-pause');
     pauseBtn.textContent = phase === 'PAUSED' ? 'RESUME' : 'PAUSE';
   }

   let isPaused = false;

   function handlePauseResume() {
     const action = isPaused ? 'resume_game' : 'pause_game';
     sendMessage({ type: 'admin', action: action });
   }
   ```

5. **Paused Overlay**:
   ```css
   .paused-overlay {
     position: fixed;
     inset: 0;
     background: rgba(0, 0, 0, 0.8);
     display: flex;
     align-items: center;
     justify-content: center;
     z-index: 900;
   }

   .paused-overlay .paused-text {
     font-size: clamp(48px, 10vw, 120px);
     color: var(--color-cyan);
     text-shadow: 0 0 20px var(--color-cyan);
     animation: pulse 2s infinite;
   }
   ```

### File Structure Notes

- Modify: `custom_components/spyster/www/host.html` - Add admin bar and modal
- Modify: `custom_components/spyster/www/css/styles.css` - Admin bar and modal styles
- Modify: `custom_components/spyster/www/js/host.js` - Admin control logic

### Backend Considerations

The server-side handlers for these admin actions should already exist or need to be verified:
- `pause_game`: Sets phase to PAUSED, stores previous phase and timer state
- `resume_game`: Restores previous phase, resumes timers
- `end_game`: Transitions to END phase immediately
- `skip_to_vote`: Transitions QUESTIONING → VOTE immediately (new action)

**Note**: If `skip_to_vote` action doesn't exist on server, it needs to be added to `server/websocket.py`.

### References

- [Source: _bmad-output/epics.md#Story 7.5: Host Admin Controls]
- [Source: _bmad-output/architecture.md#Admin Actions]
- [Source: _bmad-output/architecture.md#Phase State Machine - PAUSED handling]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No runtime errors during implementation

### Completion Notes List

- **2025-12-23**: Implemented comprehensive host admin controls system
  - **HTML Task 1**: Floating admin bar (lines 252-270)
    - Collapsible bar with toggle button (⚙ icon)
    - Four action buttons: SKIP TO VOTE, NEXT ROUND, PAUSE, END GAME
    - data-phases attributes for phase-specific visibility
  - **HTML Task 3**: Paused overlay (lines 273-279)
    - Full-screen dimmed overlay with "PAUSED" text
    - Hint text for host
  - **HTML Task 4**: Confirmation modal (lines 281-292)
    - Modal with backdrop, title, message, cancel/confirm buttons
    - ARIA attributes for accessibility
  - **CSS Task 1**: Admin bar styles (lines 5206-5381)
    - Fixed position bottom-right, translucent background
    - Collapse animation with max-width transition
    - Toggle button with rotate animation
    - Responsive scaling for TV displays
  - **CSS Task 3**: Paused overlay styles (lines 5383-5457)
    - Cyan "PAUSED" text with pulsing animation
    - Full-screen semi-transparent background
  - **CSS Task 4**: Modal styles (lines 5459-5609)
    - Dark themed modal with backdrop
    - Scale animation on show
    - Danger button styling for confirm
    - `prefers-reduced-motion` support
  - **JS Task 5**: Admin control functions (lines 1509-1769)
    - `initAdminControls()`: Event listener setup
    - `toggleAdminBar()`: Expand/collapse with ARIA
    - `updateAdminBarVisibility()`: Phase-based button visibility
    - `handleSkipToVote()`, `handleNextRound()`, `handlePauseResume()`
    - `showPausedOverlay()`, `hidePausedOverlay()`
    - `showEndGameModal()`, `hideConfirmModal()`, `handleEndGameConfirm()`
    - Escape key handling for modal dismissal
    - Integration with updatePhaseIndicator()

### File List

- `custom_components/spyster/www/host.html` - Admin bar, paused overlay, confirmation modal (lines 252-292)
- `custom_components/spyster/www/css/styles.css` - Admin UI styles (lines 5206-5610)
- `custom_components/spyster/www/js/host.js` - Admin control handlers (lines 1509-1769)

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Implemented Story 7.5: Host Admin Controls - floating bar, pause/resume, end game modal |
