# Story 3.5: Spy Parity Visual Diagram

## Component Structure Comparison

This diagram shows the IDENTICAL structure of spy and non-spy views.

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│         INNOCENT VIEW               │     │           SPY VIEW                  │
├─────────────────────────────────────┤     ├─────────────────────────────────────┤
│                                     │     │                                     │
│  ╔═══════════════════════════════╗  │     │  ╔═══════════════════════════════╗  │
│  ║ .role-display__header         ║  │     │  ║ .role-display__header         ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   THE BEACH                   ║  │     │  ║   YOU ARE THE SPY             ║  │
│  ║   (32px, pink #ff2d6a)        ║  │     │  ║   (32px, red #ff0040 + glow)  ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ╚═══════════════════════════════╝  │     │  ╚═══════════════════════════════╝  │
│  ─────────────────────────────────  │     │  ─────────────────────────────────  │
│                                     │     │                                     │
│  ╔═══════════════════════════════╗  │     │  ╔═══════════════════════════════╗  │
│  ║ .role-display__content        ║  │     │  ║ .role-display__content        ║  │
│  ║ (min-height: 120px)           ║  │     │  ║ (min-height: 120px)           ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   YOUR ROLE:                  ║  │     │  ║   POSSIBLE LOCATIONS:         ║  │
│  ║   (14px, gray)                ║  │     │  ║   (14px, gray)                ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   Lifeguard                   ║  │     │  ║   (empty space for parity)    ║  │
│  ║   (24px, white)               ║  │     │  ║                               ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   You watch over swimmers...  ║  │     │  ║                               ║  │
│  ║   (16px, gray italic)         ║  │     │  ║                               ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ╚═══════════════════════════════╝  │     │  ╚═══════════════════════════════╝  │
│                                     │     │                                     │
│  ╔═══════════════════════════════╗  │     │  ╔═══════════════════════════════╗  │
│  ║ .role-display__other-roles    ║  │     │  ║ .role-display__other-roles    ║  │
│  ║ (flex: 1, overflow-y: auto)   ║  │     │  ║ (flex: 1, overflow-y: auto)   ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   OTHER ROLES AT LOCATION:    ║  │     │  ║   GUESS THE LOCATION:         ║  │
│  ║   (14px, gray, uppercase)     ║  │     │  ║   (14px, gray, uppercase)     ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   ┌─────────────────────────┐ ║  │     │  ║   ┌─────────────────────────┐ ║  │
│  ║   │ Tourist                 │ ║  │     │  ║   │ The Beach               │ ║  │
│  ║   └─────────────────────────┘ ║  │     │  ║   └─────────────────────────┘ ║  │
│  ║   ┌─────────────────────────┐ ║  │     │  ║   ┌─────────────────────────┐ ║  │
│  ║   │ Ice Cream Vendor        │ ║  │     │  ║   │ Hospital                │ ║  │
│  ║   └─────────────────────────┘ ║  │     │  ║   └─────────────────────────┘ ║  │
│  ║   ┌─────────────────────────┐ ║  │     │  ║   ┌─────────────────────────┐ ║  │
│  ║   │ Surfer                  │ ║  │     │  ║   │ School                  │ ║  │
│  ║   └─────────────────────────┘ ║  │     │  ║   └─────────────────────────┘ ║  │
│  ║   ┌─────────────────────────┐ ║  │     │  ║   ┌─────────────────────────┐ ║  │
│  ║   │ Photographer            │ ║  │     │  ║   │ Restaurant              │ ║  │
│  ║   └─────────────────────────┘ ║  │     │  ║   └─────────────────────────┘ ║  │
│  ║   ┌─────────────────────────┐ ║  │     │  ║   ┌─────────────────────────┐ ║  │
│  ║   │ Sunbather               │ ║  │     │  ║   │ Airport                 │ ║  │
│  ║   └─────────────────────────┘ ║  │     │  ║   └─────────────────────────┘ ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ║   (16px, gray, list items)    ║  │     │  ║   (16px, gray, list items)    ║  │
│  ║                               ║  │     │  ║                               ║  │
│  ╚═══════════════════════════════╝  │     │  ╚═══════════════════════════════╝  │
│                                     │     │                                     │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
    min-height: 480px                           min-height: 480px
    padding: 32px                                padding: 32px
    background: #12121a                          background: #12121a
    border-radius: 12px                          border-radius: 12px
```

---

## Key Parity Points

### ✅ IDENTICAL (Critical for Security)

1. **Container Dimensions**
   - `min-height: 480px` (prevents variable content tells)
   - `padding: 32px` (all sides)
   - `border-radius: 12px`
   - `background: #12121a`

2. **Section Heights**
   - Header: Auto (based on text)
   - Content: `min-height: 120px` (ensures consistency)
   - List: `flex: 1` (fills remaining space)

3. **Typography Sizes**
   - Header text: 32px (both views)
   - Label text: 14px uppercase (both views)
   - Main content: 24px (role name) vs. empty (spy maintains space)
   - List items: 16px (both views)

4. **Layout Structure**
   - BEM class structure: `.role-display__*`
   - Flex column layout
   - Gap: 24px between sections
   - Same number of sections (3)

5. **List Behavior**
   - Both scrollable (`overflow-y: auto`)
   - Same item styling (gray background, rounded)
   - Same padding (8px)
   - Same gap (8px)

---

## ❌ DIFFERENCES (Intentional)

### 1. Header Color
- **Innocent:** Pink (`#ff2d6a`) - accent color
- **Spy:** Red (`#ff0040`) with glow - dramatic spy reveal
- **Why Different:** Creates dramatic "YOU ARE THE SPY" moment
- **Security:** Header color alone doesn't reveal role without reading text

### 2. Text Content
- **Innocent:** Location name, role, hint, other roles
- **Spy:** "YOU ARE THE SPY", location list
- **Why Different:** Different information for different roles
- **Security:** Layout remains identical, only text differs

### 3. Content Section Usage
- **Innocent:** Role name + hint (fills 120px min-height)
- **Spy:** Empty space (maintains 120px min-height)
- **Why Different:** Spy doesn't have role/hint
- **Security:** Empty space maintains consistent section height

---

## Casual Glance Test Visualization

**From 6 feet away (2 meters), can you tell which is spy?**

```
┌──────────┐     ┌──────────┐
│          │     │          │
│  ████    │     │  ████    │    ← Same header size
│          │     │          │
│  ────    │     │  ────    │    ← Same section divider
│          │     │          │
│   Text   │     │   Text   │    ← Different text, same size
│          │     │          │
│  ────────│     │  ────────│    ← Same list appearance
│  ┌─────┐│     │  ┌─────┐│
│  └─────┘│     │  └─────┘│
│  ┌─────┐│     │  ┌─────┐│
│  └─────┘│     │  └─────┘│
│  ┌─────┐│     │  ┌─────┐│
│  └─────┘│     │  └─────┘│
│          │     │          │
└──────────┘     └──────────┘
  Innocent          Spy
```

**Expected Result:** Cannot distinguish which is spy without reading text.

---

## CSS Min-Height Strategy

### Problem
Variable content lengths could reveal role:
- Spy has no role/hint → shorter content section
- Lists have different item counts → different heights

### Solution
```css
.role-display {
  min-height: 480px; /* Container stays same height */
}

.role-display__content {
  min-height: 120px; /* Content section stays same height */
}

.role-display__other-roles {
  flex: 1; /* List fills remaining space */
  overflow-y: auto; /* Scrolls instead of expanding */
}
```

### Result
- Both views always 480px tall
- Content section always 120px minimum
- Lists scroll if needed, don't expand container
- **No visual tells from layout**

---

## Loading State (Prevents Data Flicker)

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│                                     │
│        Assigning roles...           │
│        (animated pulse)             │
│                                     │
│                                     │
│                                     │
└─────────────────────────────────────┘
      min-height: 480px
```

**Purpose:**
- Prevents partial data display
- No "The Beach" → "YOU ARE THE SPY" flicker
- All players see same loading state
- Atomic transition to final state

**Implementation:**
```javascript
if (!roleData || roleData.is_spy === undefined) {
  this.showRoleLoading(); // Show loading until complete
  return;
}
```

---

## DOM Structure Comparison

### Innocent View
```html
<div class="role-display" data-role-type="innocent">
  <div class="role-display__header">
    <h2 class="role-display__location">The Beach</h2>
  </div>
  <div class="role-display__content">
    <p class="role-display__your-role">Your Role:</p>
    <h3 class="role-display__role-name">Lifeguard</h3>
    <p class="role-display__hint">You watch over swimmers...</p>
  </div>
  <div class="role-display__other-roles">
    <h4 class="role-display__list-title">Other Roles at This Location:</h4>
    <ul class="role-display__role-list">
      <li>Tourist</li>
      <li>Ice Cream Vendor</li>
      <!-- ... more roles ... -->
    </ul>
  </div>
</div>
```

### Spy View
```html
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
      <li>The Beach</li>
      <li>Hospital</li>
      <!-- ... more locations ... -->
    </ul>
  </div>
</div>
```

### Structural Differences
**None.** Only `data-role-type` attribute and text content differ.

---

## Testing Checklist

Use this when performing manual visual parity test:

```
SIDE-BY-SIDE COMPARISON:
  [ ] Place phones side-by-side
  [ ] Outer dimensions IDENTICAL
  [ ] Section heights IDENTICAL
  [ ] Padding IDENTICAL
  [ ] Border radius IDENTICAL
  [ ] Background color IDENTICAL
  [ ] List item styling IDENTICAL

CASUAL GLANCE TEST (6 feet away):
  [ ] Cannot distinguish spy from innocent
  [ ] Overall "shape" identical
  [ ] No obvious layout differences
  [ ] Observer would need to read text to know

HEIGHT PARITY:
  [ ] Short location vs. "YOU ARE THE SPY" → same height
  [ ] Few roles (5) vs. many locations (12) → same height
  [ ] Both maintain 480px minimum
  [ ] Lists scroll, don't expand

SECURITY VERIFICATION:
  [ ] Screen peek cannot identify spy
  [ ] No visual tells from layout
  [ ] Loading state prevents flicker
  [ ] Only header color differs (acceptable)
```

---

## Security Notes

**CRITICAL:** If players can identify the spy by glancing at screen layouts, the game is broken.

**Attack Vectors Prevented:**
1. ❌ Height differences → Fixed min-height
2. ❌ Section size differences → Fixed content min-height
3. ❌ List overflow → Scrolling instead of expansion
4. ❌ Data flicker → Loading state until complete
5. ❌ Layout structure → Identical DOM/CSS structure

**Acceptable Differences:**
- ✅ Header color (pink vs. red) - requires reading to understand
- ✅ Text content - different roles have different information

**Pass Criteria:**
Casual observer at 6 feet cannot identify spy without reading text.

---

## References

- UX Spec: UX-9, UX-10 (Spy Parity Requirements)
- Story: `implementation-artifacts/3-5-role-display-ui-with-spy-parity.md`
- Testing Guide: `tests/VISUAL_PARITY_TESTING.md`
- Implementation: `www/js/player.js` + `www/css/styles.css`
