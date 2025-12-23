# Story 5.2: Confidence Betting Selection

**Epic:** Epic 5 - Voting & Confidence Betting
**Story ID:** 5.2
**Status:** done
**Priority:** High
**Complexity:** Medium

---

## User Story

As a **player**,
I want **to set my confidence level (1, 2, or ALL IN)**,
So that **I can wager points on my vote being correct**.

---

## Acceptance Criteria

### AC1: Bet Options Display

**Given** a player is in the voting UI
**When** viewing the bet selection
**Then** three options are displayed: 1, 2, and ALL IN (3)
**And** each option shows risk/reward (+2/-1, +4/-2, +6/-3)

### AC2: ALL IN Special Treatment

**Given** the ALL IN option
**When** displayed
**Then** it has special gold styling with glow effect (UX-3)
**And** touch target is larger (56px per UX spec)

### AC3: Bet Selection Behavior

**Given** a player selects a confidence level
**When** the selection is made
**Then** the button shows selected state
**And** the selection is stored locally until submission

### AC4: Default Confidence

**Given** no confidence is explicitly selected
**When** a player submits their vote
**Then** confidence defaults to 1

### AC5: Radio Group Behavior

**Given** the confidence buttons
**When** interacting with them
**Then** only one can be selected at a time (radio group)
**And** proper ARIA radiogroup semantics are applied

---

## Requirements Coverage

### Functional Requirements

- **FR33**: All players can set their confidence bet (1, 2, or 3 points)

### UX Requirements

- **UX-3**: ALL IN special treatment: Gold (#ffd700) with stronger glow
- **UX-4**: Minimum touch targets: 44px (48px for primary, 56px for bet buttons)
- **UX-6**: Bet buttons: 1 / 2 / ALL IN with radio group behavior

### Architectural Requirements

- **ARCH-12**: Message format with snake_case fields
- **UX-12**: ARIA roles on interactive elements (radiogroup)

---

## Technical Design

### Component Changes

#### 1. Player Display HTML (`www/player.html`)

Add confidence betting section inside vote-view:

```html
<!-- Confidence betting section -->
<div id="confidence-section" class="vote-section confidence-section">
    <h2 class="vote-section-title">How confident are you?</h2>

    <div class="confidence-buttons" role="radiogroup" aria-label="Select your confidence level">
        <!-- Low confidence -->
        <button
            class="confidence-btn"
            data-confidence="1"
            role="radio"
            aria-checked="true"
            aria-label="Low confidence: win 2, lose 1"
        >
            <span class="confidence-value">1</span>
            <span class="confidence-label">SAFE</span>
            <span class="confidence-reward">+2 / -1</span>
        </button>

        <!-- Medium confidence -->
        <button
            class="confidence-btn"
            data-confidence="2"
            role="radio"
            aria-checked="false"
            aria-label="Medium confidence: win 4, lose 2"
        >
            <span class="confidence-value">2</span>
            <span class="confidence-label">BOLD</span>
            <span class="confidence-reward">+4 / -2</span>
        </button>

        <!-- ALL IN (High confidence) -->
        <button
            class="confidence-btn confidence-btn--all-in"
            data-confidence="3"
            role="radio"
            aria-checked="false"
            aria-label="All in: win 6, lose 3"
        >
            <span class="confidence-value">3</span>
            <span class="confidence-label">ALL IN</span>
            <span class="confidence-reward">+6 / -3</span>
        </button>
    </div>
</div>
```

#### 2. Player Display Logic (`www/js/player.js`)

Add confidence selection management:

```javascript
class PlayerDisplay {
    constructor() {
        // ... existing init ...
        this.selectedConfidence = 1; // Default to 1 (AC4)
    }

    setupEventListeners() {
        // ... existing listeners ...

        // Confidence button listeners
        document.querySelectorAll('.confidence-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const confidence = parseInt(e.currentTarget.dataset.confidence, 10);
                this.selectConfidence(confidence);
            });
        });
    }

    selectConfidence(confidence) {
        // Validate confidence value
        if (![1, 2, 3].includes(confidence)) {
            console.error('Invalid confidence value:', confidence);
            return;
        }

        // Update all buttons
        document.querySelectorAll('.confidence-btn').forEach(btn => {
            const btnConfidence = parseInt(btn.dataset.confidence, 10);
            const isSelected = btnConfidence === confidence;

            btn.classList.toggle('confidence-btn--selected', isSelected);
            btn.setAttribute('aria-checked', isSelected.toString());
        });

        this.selectedConfidence = confidence;
        console.log('Confidence selected:', confidence);

        // Provide haptic feedback on mobile (if available)
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }
    }

    showVoteView(state) {
        // ... existing code ...

        // Show confidence section
        const confidenceSection = document.getElementById('confidence-section');
        if (confidenceSection) {
            confidenceSection.style.display = 'block';
        }

        // Reset confidence to default (1)
        this.selectConfidence(1);
    }

    getVoteData() {
        return {
            target: this.selectedVoteTarget,
            confidence: this.selectedConfidence
        };
    }
}
```

#### 3. CSS Styles (`www/css/styles.css`)

Add confidence betting styles:

```css
/* =================================
   CONFIDENCE BETTING SECTION
   ================================= */

.confidence-section {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    margin-top: var(--spacing-lg);
}

.confidence-buttons {
    display: flex;
    gap: var(--spacing-md);
    justify-content: center;
}

/* =================================
   CONFIDENCE BUTTON COMPONENT
   ================================= */

.confidence-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-md);
    min-width: 90px;
    min-height: 90px;
    background: var(--color-bg-tertiary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: all 0.2s ease;

    /* Touch target */
    touch-action: manipulation;
}

.confidence-btn:hover:not(:disabled) {
    border-color: var(--color-accent-secondary);
    transform: translateY(-2px);
}

.confidence-btn:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 245, 255, 0.4);
}

/* Selected state */
.confidence-btn--selected {
    border-color: var(--color-accent-primary);
    background: rgba(255, 45, 106, 0.15);
    box-shadow: 0 0 15px rgba(255, 45, 106, 0.3);
}

/* Value display */
.confidence-value {
    font-size: 28px;
    font-weight: 800;
    color: var(--color-text-primary);
    line-height: 1;
}

/* Label (SAFE, BOLD, ALL IN) */
.confidence-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: var(--spacing-xs);
}

/* Reward display */
.confidence-reward {
    font-size: 11px;
    color: var(--color-text-tertiary);
    margin-top: var(--spacing-xs);
}

/* =================================
   ALL IN SPECIAL STYLING (UX-3)
   ================================= */

.confidence-btn--all-in {
    min-width: 100px;
    min-height: 100px; /* Larger touch target - 56px equivalent with padding */
    border-color: var(--color-gold);
    background: linear-gradient(
        135deg,
        rgba(255, 215, 0, 0.1) 0%,
        rgba(255, 215, 0, 0.05) 100%
    );
}

.confidence-btn--all-in .confidence-value {
    color: var(--color-gold);
    text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
}

.confidence-btn--all-in .confidence-label {
    color: var(--color-gold);
}

.confidence-btn--all-in:hover:not(:disabled) {
    border-color: var(--color-gold);
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

/* ALL IN selected state */
.confidence-btn--all-in.confidence-btn--selected {
    border-color: var(--color-gold);
    background: linear-gradient(
        135deg,
        rgba(255, 215, 0, 0.25) 0%,
        rgba(255, 215, 0, 0.15) 100%
    );
    box-shadow:
        0 0 25px rgba(255, 215, 0, 0.4),
        inset 0 0 15px rgba(255, 215, 0, 0.1);
}

.confidence-btn--all-in.confidence-btn--selected .confidence-value {
    text-shadow:
        0 0 15px rgba(255, 215, 0, 0.8),
        0 0 30px rgba(255, 215, 0, 0.4);
}

/* =================================
   CSS VARIABLES FOR GOLD (UX-3)
   ================================= */

:root {
    /* Existing variables... */
    --color-gold: #ffd700;
    --color-gold-glow: rgba(255, 215, 0, 0.5);
}

/* =================================
   REDUCED MOTION
   ================================= */

@media (prefers-reduced-motion: reduce) {
    .confidence-btn {
        transition: none;
    }

    .confidence-btn:hover:not(:disabled) {
        transform: none;
    }

    .confidence-btn--all-in .confidence-value {
        text-shadow: none;
    }

    .confidence-btn--all-in.confidence-btn--selected {
        box-shadow: 0 0 0 3px var(--color-gold);
    }
}

/* =================================
   RESPONSIVE - Smaller screens
   ================================= */

@media (max-width: 360px) {
    .confidence-buttons {
        gap: var(--spacing-sm);
    }

    .confidence-btn {
        min-width: 80px;
        min-height: 80px;
        padding: var(--spacing-sm);
    }

    .confidence-btn--all-in {
        min-width: 85px;
        min-height: 85px;
    }

    .confidence-value {
        font-size: 24px;
    }
}
```

---

## Implementation Tasks

### Task 1: Add Confidence HTML Structure (AC: 1, 2, 5)
- [x] Add confidence-section to vote-view
- [x] Create three confidence buttons
- [x] Add ARIA radiogroup attributes
- [x] Include risk/reward labels

### Task 2: Implement Selection Logic (AC: 3, 4, 5)
- [x] Create selectConfidence() method
- [x] Default to confidence 1
- [x] Radio group single-select behavior
- [x] Update ARIA attributes on selection

### Task 3: Add ALL IN Special Styling (AC: 2)
- [x] Gold color variable (#ffd700)
- [x] Gold border and background
- [x] Glow effect on hover and selected
- [x] Larger touch target (56px area)

### Task 4: Integrate with Vote Flow
- [x] Show confidence section in vote view
- [x] Reset to default on phase entry
- [x] Include confidence in getVoteData()

### Task 5: Write Tests
- [x] Test confidence selection toggle
- [x] Test default value (1)
- [x] Test single-select behavior

---

## Testing Strategy

### Unit Tests

```javascript
describe('ConfidenceBetting', () => {
    test('should default to confidence 1', () => {
        display.showVoteView({});
        expect(display.selectedConfidence).toBe(1);

        const btn1 = document.querySelector('[data-confidence="1"]');
        expect(btn1.getAttribute('aria-checked')).toBe('true');
    });

    test('should allow single selection only', () => {
        display.selectConfidence(2);
        display.selectConfidence(3);

        const selected = document.querySelectorAll('.confidence-btn--selected');
        expect(selected.length).toBe(1);
        expect(selected[0].dataset.confidence).toBe('3');
    });

    test('ALL IN button should have special styling', () => {
        const allInBtn = document.querySelector('.confidence-btn--all-in');
        expect(allInBtn).toBeTruthy();
        expect(allInBtn.dataset.confidence).toBe('3');
    });
});
```

### Manual Testing Checklist

**Scenario 1: Initial State**
- [ ] Three confidence buttons visible
- [ ] Button 1 (SAFE) selected by default
- [ ] Risk/reward labels visible on each button
- [ ] ALL IN has gold styling

**Scenario 2: Selection**
- [ ] Tap button 2 selects it, deselects button 1
- [ ] Tap ALL IN selects it with gold glow
- [ ] Only one button selected at a time
- [ ] Visual feedback on selection

**Scenario 3: ALL IN Styling**
- [ ] Gold border (#ffd700)
- [ ] Gold glow effect on hover
- [ ] Stronger glow when selected
- [ ] Larger button size than others

**Scenario 4: Touch Targets**
- [ ] All buttons at least 48px touch area
- [ ] ALL IN button 56px touch area
- [ ] Buttons tappable without precision

---

## Definition of Done

- [ ] Three confidence buttons displayed (1, 2, ALL IN)
- [ ] Risk/reward labels shown (+2/-1, +4/-2, +6/-3)
- [ ] Radio group single-select behavior
- [ ] Default to confidence 1
- [ ] ALL IN has gold styling (UX-3)
- [ ] ALL IN has larger touch target (56px)
- [ ] ARIA radiogroup semantics
- [ ] Responsive on small screens
- [ ] No console errors
- [ ] Manual testing completed

---

## Dependencies

### Depends On
- **Story 5.1**: Voting Phase UI (provides vote view structure)

### Enables
- **Story 5.3**: Vote Submission and Tracking (uses confidence value)
- **Story 6.2**: Vote Scoring Calculation (uses confidence for points)

---

## Architecture Decisions Referenced

- **UX-3**: ALL IN gold treatment (#ffd700) with glow
- **UX-4**: Touch targets 48px, 56px for bet buttons
- **UX-6**: Bet buttons with radio group behavior
- **UX-12**: ARIA roles (radiogroup)

---

## Dev Notes

### Project Context Reference
- **File**: `_bmad-output/project-context.md`
- **CSS Variables**: Add --color-gold: #ffd700

### Scoring Reference (from PRD)
| Confidence | Win | Lose |
|------------|-----|------|
| 1 (SAFE) | +2 | -1 |
| 2 (BOLD) | +4 | -2 |
| 3 (ALL IN) | +6 | -3 |

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/www/player.html` | Modify | Add confidence section HTML |
| `custom_components/spyster/www/js/player.js` | Modify | Add selectConfidence() |
| `custom_components/spyster/www/css/styles.css` | Modify | Add confidence button styles |

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Added confidence betting HTML with 3 buttons (1/SAFE, 2/BOLD, 3/ALL IN) with ARIA radiogroup semantics
- Implemented selectConfidence() method with radio group single-select behavior
- Added selectedConfidence property to PlayerClient (default: 1 per AC4)
- Added getVoteData() method returning {target, confidence}
- Added setupConfidenceListeners() and resetConfidence() methods
- Added comprehensive CSS styling for confidence buttons with ALL IN gold styling (UX-3)
- Integrated confidence betting into handleVotePhase() with auto-reset

### File List
| File | Change Type | Description |
|------|-------------|-------------|
| `custom_components/spyster/www/player.html` | Modified | Added confidence betting section with 3 buttons |
| `custom_components/spyster/www/js/player.js` | Modified | Added selectConfidence(), getVoteData(), setupConfidenceListeners(), resetConfidence() methods |
| `custom_components/spyster/www/css/styles.css` | Modified | Added ~180 lines of confidence button styles |
