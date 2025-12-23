# Story 3.5: Visual Parity Testing Guide

## Overview

This document provides comprehensive testing instructions for Story 3.5: Role Display UI with Spy Parity.

**CRITICAL SECURITY REQUIREMENT:** Spy and non-spy views must have IDENTICAL layouts and dimensions. If players can identify the spy by screen layout, the game is broken.

## Automated Tests

Run automated tests first:

```bash
pytest tests/test_role_display.py -v
pytest tests/test_visual_parity.py -v
```

These tests verify:
- ✅ Payload structure correctness
- ✅ Data privacy (spy can't see location, innocents can't see other roles)
- ✅ Component structure parity
- ✅ List size similarity
- ✅ Loading state behavior

## Manual Visual Parity Tests

Automated tests cannot verify visual appearance. Manual testing is REQUIRED.

### Prerequisites

- [ ] Two physical phones OR two browser windows/emulators
- [ ] Game running with 4+ players
- [ ] One player assigned as spy, one as innocent
- [ ] Both phones at similar brightness levels
- [ ] Test in both bright and dim lighting conditions

### Test Procedure

#### 1. Side-by-Side Comparison

1. **Setup:**
   - Join game with 4+ players
   - Ensure roles are assigned (one spy, rest innocent)
   - Place two phones side-by-side showing spy and innocent views

2. **Layout Verification:**
   - [ ] Outer container dimensions IDENTICAL
   - [ ] Top padding IDENTICAL
   - [ ] Bottom padding IDENTICAL
   - [ ] Left/right margins IDENTICAL
   - [ ] Border radius IDENTICAL
   - [ ] Background color IDENTICAL

3. **Typography Verification:**
   - [ ] Header font size IDENTICAL (32px)
   - [ ] Header font weight IDENTICAL
   - [ ] Content text size IDENTICAL (24px for role, 14px for labels)
   - [ ] List item size IDENTICAL (16px)
   - [ ] Line heights IDENTICAL

4. **Component Structure:**
   - [ ] Same number of sections (header → content → list)
   - [ ] Same vertical spacing between sections
   - [ ] Same padding within each section
   - [ ] Same border treatment

#### 2. Casual Glance Test

**This is the critical security test.**

1. **Setup:**
   - Place phones side-by-side
   - Step back 6 feet (2 meters)
   - Blur your eyes slightly

2. **Questions to Answer:**
   - [ ] Can you tell which is spy WITHOUT reading text?
   - [ ] Are the layouts visually indistinguishable at a glance?
   - [ ] Is the overall "shape" of both screens identical?
   - [ ] Would a casual observer notice any difference?

**PASS CRITERIA:** Observer cannot distinguish spy from innocent without reading text content.

#### 3. Height Parity Test

**Purpose:** Verify min-height prevents variable content from revealing role.

1. **Test Scenarios:**
   - [ ] Short location name vs. "YOU ARE THE SPY"
   - [ ] Few other roles (5) vs. many locations (12)
   - [ ] Long hints vs. no hint (spy)

2. **Verification:**
   - [ ] Both views maintain same overall height
   - [ ] List scrolling behavior identical
   - [ ] No "stretching" or "squashing" visible

#### 4. Loading State Test

**Purpose:** Verify no data flicker reveals role before full display.

1. **Test Procedure:**
   - Join as player
   - Watch transition from lobby → roles
   - Observe loading state

2. **Verification:**
   - [ ] "Assigning roles..." appears for all players
   - [ ] No partial data visible (no location name then spy text)
   - [ ] Transition is smooth fade (300ms)
   - [ ] Final state appears atomically (all at once)

#### 5. Color and Contrast Test

**Purpose:** Verify color differences don't reveal role.

1. **Innocent View:**
   - [ ] Location name: Pink (`#ff2d6a`)
   - [ ] Role name: White (`#ffffff`)
   - [ ] Hint: Gray (`#a0a0a8`)
   - [ ] List items: Gray on darker background

2. **Spy View:**
   - [ ] "YOU ARE THE SPY": Red (`#ff0040`) with glow
   - [ ] "Possible Locations:" label: Gray
   - [ ] List items: Gray on darker background (SAME as innocent)

3. **Parity Check:**
   - [ ] Only header color differs (pink vs. red)
   - [ ] Content and list sections IDENTICAL colors
   - [ ] Glow effect only on spy header (intentional drama)
   - [ ] No other color differences

#### 6. Accessibility Test

1. **VoiceOver (iOS) or TalkBack (Android):**
   - [ ] Reading order is logical (top to bottom)
   - [ ] All text is announced
   - [ ] ARIA labels present: "Your role assignment region"
   - [ ] Lists announced with item counts

2. **Contrast Ratios:**
   - [ ] Pink on dark: 7.2:1 (WCAG AAA)
   - [ ] Red on dark: 7.0:1 (WCAG AAA)
   - [ ] White on dark: 21:1 (WCAG AAA)
   - [ ] Gray on dark: 4.5:1 minimum (WCAG AA)

3. **Touch Targets:**
   - [ ] Not applicable (display-only view)

#### 7. Responsive Test

Test on multiple device sizes:

1. **iPhone SE (320px):**
   - [ ] No horizontal scrolling
   - [ ] All content readable
   - [ ] Lists scroll vertically if needed

2. **iPhone 14 Pro Max (428px):**
   - [ ] Layout scales appropriately
   - [ ] No excessive whitespace
   - [ ] Parity maintained

3. **Tablet (768px+):**
   - [ ] NOT applicable (player view is mobile-only)

## Common Issues and Fixes

### Issue: Different Heights

**Symptom:** Spy and innocent views have different overall heights.

**Diagnosis:**
- Check `.role-display { min-height: 480px; }` is applied
- Verify `.role-display__content { min-height: 120px; }` is applied

**Fix:** Ensure fixed min-heights in CSS are not being overridden.

### Issue: Visual Tell from List Length

**Symptom:** Spy's location list (12 items) looks longer than innocent's role list (5 items).

**Diagnosis:**
- Check `.role-display__other-roles { flex: 1; overflow-y: auto; }` is applied
- Verify both lists have scrolling enabled

**Fix:** Lists should scroll, not expand container. Outer container remains fixed height.

### Issue: Loading State Flicker

**Symptom:** Location name briefly appears before switching to spy view.

**Diagnosis:**
- Check `if (!state.role_data || roleData.is_spy === undefined)` condition
- Verify loading state shows until complete data received

**Fix:** Server must send complete role_data in single message, not partial updates.

### Issue: Color Differences Too Obvious

**Symptom:** Red spy header vs. pink innocent header is too distinct.

**Diagnosis:**
- Intentional design choice
- Header color difference is acceptable (content stays hidden)

**Fix:** Not a bug. Only header differs; content/list sections must be identical.

## Test Results Template

```
STORY 3.5 VISUAL PARITY TEST RESULTS
=====================================

Tester: ___________________
Date: ___________________
Devices Tested: ___________________

AUTOMATED TESTS:
  [ ] test_role_display.py: PASS / FAIL
  [ ] test_visual_parity.py: PASS / FAIL

MANUAL TESTS:
  [ ] Side-by-Side Comparison: PASS / FAIL
  [ ] Casual Glance Test: PASS / FAIL
  [ ] Height Parity Test: PASS / FAIL
  [ ] Loading State Test: PASS / FAIL
  [ ] Color and Contrast Test: PASS / FAIL
  [ ] Accessibility Test: PASS / FAIL
  [ ] Responsive Test: PASS / FAIL

CRITICAL SECURITY TEST:
  Can a casual observer identify the spy by screen layout alone?
  [ ] YES (FAIL) / [ ] NO (PASS)

ISSUES FOUND:
  1. ___________________
  2. ___________________
  3. ___________________

OVERALL RESULT: PASS / FAIL

NOTES:
___________________
___________________
___________________
```

## Acceptance Criteria Checklist

Before marking Story 3.5 as complete:

- [ ] **AC1:** Non-spy sees location, role, hint, other roles (verified)
- [ ] **AC2:** Spy sees "YOU ARE THE SPY", location list (verified)
- [ ] **AC3:** Layouts have identical dimensions (MANUAL TEST REQUIRED)
- [ ] **AC4:** Loading state prevents data flicker (verified)
- [ ] All automated tests pass
- [ ] Manual visual parity test passes
- [ ] Code reviewed and approved
- [ ] Merged to main branch

## Security Notes

**WHY THIS MATTERS:**

If players can identify the spy by screen layout, the entire game is broken. Players could:
- Glance at each other's phones during role reveal
- Notice different screen heights/layouts
- Use timing of loading states to deduce roles

**IMPLEMENTATION GUARDRAILS:**

1. Always use same base `.role-display` component
2. Never add spy-specific classes that change layout
3. Test with actual devices side-by-side before merging
4. Use fixed `min-height` to prevent height differences
5. Ensure list overflow behavior is identical

## References

- Story File: `implementation-artifacts/3-5-role-display-ui-with-spy-parity.md`
- UX Spec: UX-9, UX-10 (Spy Parity Requirements)
- Functional Requirements: FR20, FR21, FR22
- Architecture: ARCH-7 (Per-Player State Filtering)
