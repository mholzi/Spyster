# Story 7.3: Player Status Display

Status: done

## Story

As a **host**,
I want **to see all players and their connection status**,
so that **I know who's ready to play**.

## Acceptance Criteria

1. **Given** the host display in LOBBY, **When** players are connected, **Then** all player names are visible in a grid/list **And** connected players show green indicator **And** disconnected players show yellow indicator.

2. **Given** players join or leave, **When** the state changes, **Then** the player list updates in real-time.

3. **Given** the host display during gameplay, **When** showing player list, **Then** compact view shows names with connection status **And** list doesn't dominate the screen (secondary to game state).

## Tasks / Subtasks

- [x] Task 1: Enhance lobby player display (AC: #1, #2)
  - [x] 1.1: Update `.player-card` styles for host display scale
  - [x] 1.2: Implement green/yellow status indicators with glow effects
  - [x] 1.3: Add player name with large, readable typography
  - [x] 1.4: Display host badge for host player
  - [x] 1.5: Create horizontal grid layout for TV viewing

- [x] Task 2: Implement compact gameplay player status (AC: #3)
  - [x] 2.1: Create `.player-status-compact` component for gameplay phases
  - [x] 2.2: Show player names in smaller, horizontal strip
  - [x] 2.3: Use colored dots instead of full status indicators
  - [x] 2.4: Position at top or bottom of screen (non-intrusive)

- [x] Task 3: Add real-time update animations (AC: #2)
  - [x] 3.1: Animate player card entry (fade-in + slide)
  - [x] 3.2: Animate status change (pulse on connect/disconnect)
  - [x] 3.3: Animate player removal (fade-out)
  - [x] 3.4: Use CSS transitions for smooth updates

- [x] Task 4: Update host.js player rendering (AC: #1, #2, #3)
  - [x] 4.1: Enhance `renderPlayerList()` for lobby with status colors
  - [x] 4.2: Enhance `updatePlayerStatusGrid()` for gameplay phases
  - [x] 4.3: Detect player state changes for animations
  - [x] 4.4: Handle player join/leave events smoothly

## Dev Notes

### Architecture Compliance

- **HTML Location**: `www/host.html`
- **CSS Location**: `www/css/styles.css`
- **JS Location**: `www/js/host.js`
- **WebSocket Protocol**: Player data in state messages

### Technical Requirements

- **Player Data Structure**: From server state:
  ```json
  {
    "players": [
      {"name": "Alice", "connected": true, "is_host": true, "disconnect_duration": null},
      {"name": "Bob", "connected": false, "is_host": false, "disconnect_duration": 45}
    ]
  }
  ```
- **Status Colors**: Green (#00ff00) connected, Yellow (#ffcc00) disconnected
- **Accessibility**: Status must not rely on color alone (include icon/text)

### Existing Code Analysis

From `host.html`:
- Lobby player list at lines 93-95: `<div id="player-list-section">` with `<div id="player-list">`
- Questioning phase grid at lines 148-150: `<div id="player-status-grid">`

From `host.js`:
- `renderPlayerList()` function at lines 229-303 handles lobby display
- `updatePlayerStatusGrid()` function at lines 441-456 handles gameplay display
- Both use `escapeHtml()` for XSS protection (good!)
- Status classes: `.status-connected` and `.status-disconnected`

### Implementation Approach

1. **Enhanced Player Card (Lobby)**:
   ```html
   <div class="player-card host-scale" data-connected="true">
     <div class="player-avatar">
       <span class="avatar-initial">A</span>
       <span class="status-ring"></span>
     </div>
     <div class="player-info">
       <span class="player-name">Alice</span>
       <span class="host-badge">HOST</span>
     </div>
   </div>
   ```

2. **Status Indicator Styles**:
   ```css
   .player-card[data-connected="true"] .status-ring {
     border-color: #00ff00;
     box-shadow: 0 0 10px #00ff00;
     animation: pulse-green 2s infinite;
   }

   .player-card[data-connected="false"] .status-ring {
     border-color: #ffcc00;
     box-shadow: 0 0 10px #ffcc00;
     animation: pulse-yellow 1s infinite;
   }
   ```

3. **Compact Gameplay Strip**:
   ```css
   .player-status-strip {
     display: flex;
     gap: var(--space-sm);
     position: fixed;
     bottom: var(--space-md);
     left: 50%;
     transform: translateX(-50%);
     background: rgba(0, 0, 0, 0.7);
     padding: var(--space-sm) var(--space-md);
     border-radius: var(--radius-lg);
   }

   .player-status-strip .player-dot {
     width: 12px;
     height: 12px;
     border-radius: 50%;
   }
   ```

4. **Animation on State Change**:
   ```javascript
   function renderPlayerList(players) {
     const existingCards = document.querySelectorAll('.player-card');
     const existingNames = new Set([...existingCards].map(c => c.dataset.name));

     players.forEach(player => {
       const card = document.querySelector(`[data-name="${player.name}"]`);
       if (!card) {
         // New player - animate in
         newCard.classList.add('entering');
       } else if (card.dataset.connected !== String(player.connected)) {
         // Status changed - pulse
         card.classList.add('status-changed');
       }
     });
   }
   ```

### File Structure Notes

- Modify: `custom_components/spyster/www/host.html`
- Modify: `custom_components/spyster/www/css/styles.css`
- Modify: `custom_components/spyster/www/js/host.js`
- No new files needed

### References

- [Source: _bmad-output/epics.md#Story 7.3: Player Status Display]
- [Source: _bmad-output/architecture.md#WebSocket Message Protocol]
- [Source: _bmad-output/project-context.md#WebSocket Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No runtime errors during implementation

### Completion Notes List

- **2025-12-23**: Implemented comprehensive player status display system
  - **CSS Task 1**: Enhanced lobby player display (lines 4053-4265)
    - `.player-card` with avatar initial, status ring, player info
    - Green glow for connected (`--color-success`), yellow pulse for disconnected
    - `data-connected` attribute for CSS state styling
    - Responsive grid layout: 2-5 columns based on screen size (768px, 1024px, 1440px breakpoints)
    - Host badge styling with accent color background
  - **CSS Task 2**: Compact gameplay player status (lines 4267-4404)
    - `.player-status-strip` for horizontal player list during gameplay
    - `.player-status-item` with compact dot and name
    - `.player-status-card` enhanced for questioning phase grid
    - TV-optimized scaling at all breakpoints
  - **CSS Task 3**: Real-time update animations (lines 4406-4540)
    - `@keyframes player-enter`: fade-in + slide (0.4s)
    - `@keyframes status-pulse`: scale + ring pulse on status change (0.6s)
    - `@keyframes player-exit`: fade-out + slide (0.3s)
    - `@keyframes connect-pulse` / `disconnect-pulse`: status ring animations
    - `prefers-reduced-motion` support for all animations
  - **JS Task 4**: Player rendering updates
    - `renderPlayerList()`: Enhanced with avatar, status ring, animation classes, state tracking
    - `updatePlayerStatusGrid()`: Enhanced with animation support, state change detection
    - `previousPlayerStates` Map for lobby phase tracking
    - `previousGameplayPlayerStates` Map for gameplay phase tracking
    - Auto-cleanup of animation classes after animation completes

### File List

- `custom_components/spyster/www/css/styles.css` - Player status styles (lines 4053-4540)
- `custom_components/spyster/www/js/host.js` - Enhanced renderPlayerList() and updatePlayerStatusGrid() functions

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Implemented Story 7.3: Player Status Display - lobby cards, gameplay strip, animations |
