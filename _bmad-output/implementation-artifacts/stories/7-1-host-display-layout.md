# Story 7.1: Host Display Layout

Status: done

## Story

As a **host**,
I want **a TV-optimized display for the room**,
so that **all players can see the game state from their seats**.

## Acceptance Criteria

1. **Given** the host display is viewed on a large screen, **When** the page loads, **Then** content is scaled 2-3x larger than player displays (per UX-16) **And** text is readable from across the room.

2. **Given** the host display, **When** in any phase, **Then** the layout uses landscape orientation **And** key information is centered and prominent.

3. **Given** responsive breakpoints, **When** viewport is 768px+, **Then** host layout activates with larger typography **And** timer displays at 96-144px font size.

## Tasks / Subtasks

- [x] Task 1: Update host display CSS for TV optimization (AC: #1, #3)
  - [x] 1.1: Add `.host-display` body class for host-specific scaling
  - [x] 1.2: Create responsive breakpoints for 768px+, 1024px+, 1440px+ viewports
  - [x] 1.3: Scale typography: headings 3x, body text 2x, timer 96-144px
  - [x] 1.4: Increase spacing and padding for readability at distance
  - [x] 1.5: Ensure minimum contrast ratios for TV viewing (4.5:1 per WCAG AA)

- [x] Task 2: Optimize layout structure for landscape orientation (AC: #2)
  - [x] 2.1: Update `.main-content` to use landscape-optimized grid
  - [x] 2.2: Center key information (timer, phase indicator, player names)
  - [x] 2.3: Implement horizontal player grid layout for lobby
  - [x] 2.4: Add max-width constraints for ultra-wide screens

- [x] Task 3: Enhance phase-specific layouts for host (AC: #1, #2, #3)
  - [x] 3.1: Lobby phase: QR code prominent center, player list horizontal
  - [x] 3.2: Questioning phase: Timer center-top, Q&A pair prominent
  - [x] 3.3: Voting phase: Submission tracker large, vote count prominent
  - [x] 3.4: Reveal/Scoring phases: Full-screen results display

- [x] Task 4: Add host-specific CSS variables (AC: #1, #3)
  - [x] 4.1: Define `--host-scale-factor` CSS custom property
  - [x] 4.2: Create `--host-font-size-*` scale for headings/body
  - [x] 4.3: Add `--host-spacing-*` for increased margins/padding
  - [x] 4.4: Apply variables conditionally via media queries

## Dev Notes

### Architecture Compliance

- **CSS Location**: All styles in `www/css/styles.css` (no build step per architecture)
- **Body Class**: `.host-display` already present in `host.html:9`
- **No External Dependencies**: Vanilla CSS only, no frameworks

### Technical Requirements

- **Responsive Design**: Mobile-first with host overrides at 768px+
- **CSS Custom Properties**: Use variables for theme consistency
- **Accessibility**: Maintain WCAG AA contrast (4.5:1 minimum)
- **Performance**: No JavaScript for layout (CSS-only responsive)

### Existing Code Analysis

From `host.html`:
- Body already has class `host-display` (line 9)
- Phase sections use `.phase-section` class
- Timer uses `.timer-display.large` class
- Player grid uses `.player-grid` class

From `host.js`:
- `showPhaseSection()` function handles phase visibility (line 544-565)
- Phase sections: lobby, roles, questioning, vote, reveal, scoring, end

### Implementation Approach

1. **Scale Factor Strategy**:
   ```css
   @media (min-width: 768px) {
     .host-display {
       --host-scale: 2;
       font-size: calc(1rem * var(--host-scale));
     }
   }
   @media (min-width: 1440px) {
     .host-display {
       --host-scale: 3;
     }
   }
   ```

2. **Timer Sizing**:
   ```css
   .host-display .timer-value {
     font-size: clamp(48px, 12vw, 144px);
   }
   ```

3. **Landscape Grid**:
   ```css
   .host-display .main-content {
     display: grid;
     grid-template-columns: 1fr 2fr 1fr;
     align-items: center;
   }
   ```

### File Structure Notes

- Primary file: `custom_components/spyster/www/css/styles.css`
- Alignment: Follows architecture pattern of single CSS file
- No new files needed

### References

- [Source: _bmad-output/architecture.md#Implementation Patterns - UX-15, UX-16]
- [Source: _bmad-output/epics.md#Story 7.1: Host Display Layout]
- [Source: _bmad-output/project-context.md#Technology Stack & Versions]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - CSS-only implementation with no runtime errors

### Completion Notes List

- **2025-12-23**: Implemented comprehensive TV-optimized host display styles
  - Added `--host-scale-factor` CSS custom property with progressive scaling (1x → 1.5x → 2x → 2.5x → 3x)
  - Created `--host-font-size-*` variables for typography scaling
  - Created `--host-space-*` variables for spacing scaling
  - Timer displays at 96-144px across breakpoints (AC#3 satisfied)
  - Responsive breakpoints: 768px+, 1024px+, 1440px+, 1920px+, 2560px+
  - Landscape-optimized grid layout with centered content (AC#2 satisfied)
  - Horizontal player grid for lobby phase
  - Phase-specific layouts for all phases: lobby, questioning, voting, reveal, scoring, end
  - QR code scales from 300px → 400px → 500px → 600px
  - WCAG AA contrast verified (all ratios > 4.5:1)
  - Enhanced text shadows for TV readability
  - Reduced motion support for accessibility

### File List

- `custom_components/spyster/www/css/styles.css` - Host display responsive styles (lines 3223-3773 added)

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Implemented Story 7.1: Host Display Layout - TV optimization with responsive scaling, landscape layouts, and phase-specific styles |
