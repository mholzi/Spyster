# Story 7.4: Vote Results Visualization

Status: done

## Story

As a **viewer**,
I want **to see voting results on the big screen**,
so that **the whole room experiences the reveal together**.

## Acceptance Criteria

1. **Given** the host display in REVEAL phase, **When** votes are being shown, **Then** each player's vote target is displayed **And** confidence levels are visible (1/2/ALL IN with gold).

2. **Given** the reveal sequence on host display, **When** the staged reveal plays, **Then** it matches the timing of player displays **And** room can watch votes flip one by one.

3. **Given** the conviction result, **When** displayed, **Then** "SPY CAUGHT!" or "INNOCENT!" is shown large **And** the actual spy is revealed (if caught).

4. **Given** voting in progress, **When** submission tracker updates, **Then** host display shows "4/7 voted" prominently.

## Tasks / Subtasks

- [x] Task 1: Implement vote submission tracker UI (AC: #4)
  - [x] 1.1: Add large submission counter in vote-section HTML
  - [x] 1.2: Style counter with prominent typography and progress ring
  - [x] 1.3: Animate count changes (increment with pulse)
  - [x] 1.4: Update `renderVoting()` in host.js to display tracker

- [x] Task 2: Create vote reveal grid layout (AC: #1)
  - [x] 2.1: Design vote card showing: voter name → target name
  - [x] 2.2: Add confidence badge (1/2/ALL IN) with gold styling for ALL IN
  - [x] 2.3: Create grid layout for all player votes
  - [x] 2.4: Style vote arrows and connections

- [x] Task 3: Implement staged reveal animation (AC: #2)
  - [x] 3.1: Create reveal sequence timing (match player display 8-12s total)
  - [x] 3.2: Step 1: "Votes are in..." text (1s pause)
  - [x] 3.3: Step 2: Votes flip one by one (staggered ~0.5s each)
  - [x] 3.4: Step 3: "Now the bets..." text (1s pause)
  - [x] 3.5: Step 4: Confidence bets reveal simultaneously
  - [x] 3.6: Add flip animations using CSS transforms

- [x] Task 4: Implement conviction result display (AC: #3)
  - [x] 4.1: Create full-screen verdict overlay
  - [x] 4.2: Display "SPY CAUGHT!" with celebration effect
  - [x] 4.3: Display "INNOCENT!" with failure effect
  - [x] 4.4: Display "TIE - No conviction" if applicable
  - [x] 4.5: Reveal spy identity with dramatic animation
  - [x] 4.6: Handle spy location guess result ("SPY WINS - Location Guessed!")

- [x] Task 5: Update host.js for reveal rendering (AC: #1-4)
  - [x] 5.1: Implement `renderVoting()` with submission tracker
  - [x] 5.2: Implement `renderReveal()` with staged sequence
  - [x] 5.3: Add `runRevealSequence()` for timed animations
  - [x] 5.4: Handle all reveal state data from server
  - [x] 5.5: Add conviction result rendering

## Dev Notes

### Architecture Compliance

- **HTML Location**: `www/host.html`
- **CSS Location**: `www/css/styles.css`
- **JS Location**: `www/js/host.js`
- **Timing**: Match player reveal sequence (8-12s total per UX-8)

### Technical Requirements

- **WebSocket Data**: Reveal phase state structure:
  ```json
  {
    "type": "state",
    "phase": "REVEAL",
    "reveal_step": 1,
    "votes": [
      {"voter": "Alice", "target": "Bob", "confidence": 3},
      {"voter": "Charlie", "target": "Bob", "confidence": 1}
    ],
    "conviction": {
      "convicted_player": "Bob",
      "is_spy": true,
      "actual_spy": "Bob"
    }
  }
  ```
- **ALL IN Styling**: Gold (#ffd700) with glow effect per UX-3
- **Accessibility**: Reveal sequence should be pausable with keyboard

### Existing Code Analysis

From `host.html`:
- Vote section at lines 164-167: Placeholder only
- Reveal section at lines 169-172: Placeholder only
- Scoring section at lines 174-177: Placeholder only

From `host.js`:
- `renderVoting()` at lines 476-479: Placeholder with TODO
- `renderReveal()` at lines 484-488: Placeholder with TODO
- Both need full implementation

### Implementation Approach

1. **Submission Tracker HTML**:
   ```html
   <section id="vote-section" class="phase-section hidden">
     <h2>Voting Phase</h2>
     <div class="vote-timer-large" role="timer" aria-live="polite">
       <span id="vote-timer-value">60</span>
     </div>
     <div class="submission-tracker">
       <svg class="progress-ring">...</svg>
       <span id="vote-count">0</span>/<span id="vote-total">7</span>
       <span class="tracker-label">voted</span>
     </div>
   </section>
   ```

2. **Vote Card Structure**:
   ```html
   <div class="vote-card" data-revealed="false">
     <div class="voter-name">Alice</div>
     <div class="vote-arrow">→</div>
     <div class="target-name hidden">Bob</div>
     <div class="confidence-badge hidden" data-level="3">ALL IN</div>
   </div>
   ```

3. **Reveal Sequence JavaScript**:
   ```javascript
   async function runRevealSequence(votes, conviction) {
     // Step 1: Intro
     showRevealText("Votes are in...");
     await delay(1500);

     // Step 2: Flip votes one by one
     for (const vote of votes) {
       revealVote(vote.voter);
       await delay(500);
     }

     // Step 3: Bets intro
     showRevealText("Now the bets...");
     await delay(1500);

     // Step 4: Reveal all bets simultaneously
     revealAllBets();
     await delay(2000);

     // Step 5: Conviction result
     showConvictionResult(conviction);
   }
   ```

4. **Flip Animation CSS**:
   ```css
   .vote-card {
     transform-style: preserve-3d;
     transition: transform 0.6s;
   }

   .vote-card[data-revealed="true"] .target-name {
     animation: flip-reveal 0.6s ease-out forwards;
   }

   @keyframes flip-reveal {
     0% { transform: rotateY(-90deg); opacity: 0; }
     100% { transform: rotateY(0); opacity: 1; }
   }
   ```

5. **Conviction Overlay**:
   ```css
   .conviction-overlay {
     position: fixed;
     inset: 0;
     display: flex;
     flex-direction: column;
     align-items: center;
     justify-content: center;
     background: rgba(0, 0, 0, 0.95);
   }

   .conviction-overlay.spy-caught {
     --verdict-color: #00ff00;
     animation: celebration 1s ease-out;
   }

   .conviction-overlay.innocent {
     --verdict-color: #ff2d6a;
     animation: failure 1s ease-out;
   }
   ```

### File Structure Notes

- Modify: `custom_components/spyster/www/host.html` - Add vote/reveal section structure
- Modify: `custom_components/spyster/www/css/styles.css` - Add reveal animations
- Modify: `custom_components/spyster/www/js/host.js` - Implement reveal sequence

### References

- [Source: _bmad-output/epics.md#Story 7.4: Vote Results Visualization]
- [Source: _bmad-output/epics.md#Story 5.6: Vote and Bet Reveal Sequence - timing details]
- [Source: _bmad-output/architecture.md#UX-3 ALL IN styling]
- [Source: _bmad-output/architecture.md#UX-8 Reveal sequence timing]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No runtime errors during implementation

### Completion Notes List

- **2025-12-23**: Implemented comprehensive vote results visualization system
  - **HTML Task 1**: Vote section with submission tracker
    - SVG progress ring with animatable stroke-dashoffset
    - Vote count display (X/Y voted)
    - Vote timer and status message
  - **HTML Task 2 & 4**: Reveal section structure
    - Vote cards grid with placeholders
    - Reveal stage text element
    - Conviction overlay with verdict, details, and spy reveal sections
  - **CSS Task 1**: Submission tracker styles (lines 4550-4693)
    - Progress ring animation with stroke-dashoffset
    - Count pulse animation on increment
    - Responsive scaling (150px → 280px at 1440px+)
  - **CSS Task 2**: Vote card grid (lines 4695-4884)
    - Card layout with voter → target → confidence
    - Confidence badges: ×1 (subtle), ×2 (pink), ALL IN (gold glow)
    - Abstain styling with reduced opacity
  - **CSS Task 3**: Staged reveal animations (lines 4886-4975)
    - `reveal-stage-text` fade-in/out transitions
    - `vote-flip-reveal` rotateY animation for vote targets
    - `bet-pop-reveal` scale animation for confidence badges
    - Staggered delays via nth-child (0.5s per card)
  - **CSS Task 4**: Conviction overlay (lines 4977-5204)
    - Full-screen verdict display with themed colors
    - SPY CAUGHT: Green celebration with flash
    - INNOCENT: Pink/red failure effect
    - TIE: Gold styling
    - SPY WINS: Location guess success
    - Spy identity reveal with dramatic entrance
    - `prefers-reduced-motion` support for all animations
  - **JS Task 5**: Reveal rendering functions
    - `renderVoting()`: Timer + submission tracker updates
    - `updateSubmissionTracker()`: Progress ring + pulse animations
    - `renderVoteCards()`: Build card grid from vote data
    - `runRevealSequence()`: Async staged animation sequence
    - `showConvictionResult()`: Verdict overlay with all scenarios
    - `delay()`: Promise-based timing utility
    - State tracking to prevent duplicate sequences

### File List

- `custom_components/spyster/www/host.html` - Vote/reveal section structure (lines 175-231)
- `custom_components/spyster/www/css/styles.css` - Vote visualization styles (lines 4542-5205)
- `custom_components/spyster/www/js/host.js` - Reveal sequence implementation

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Implemented Story 7.4: Vote Results Visualization - tracker, cards, animations, conviction overlay |
