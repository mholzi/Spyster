---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
inputDocuments:
  - 'prd.md'
  - 'external: /Volumes/My Passport/Beatify/custom_components/beatify/www/'
workflowType: 'ux-design'
lastStep: 14
status: complete
completedAt: '2025-12-22'
project_name: 'Spyster'
user_name: 'Markusholzhaeuser'
date: '2025-12-22'
---

# UX Design Specification - Spyster

**Author:** Markusholzhaeuser
**Date:** 2025-12-22

---

## Executive Summary

### Project Vision

Spyster is a social deduction party game that runs as a Home Assistant custom component. The core innovation is **Confidence Betting** — players don't just vote on who the spy is, they secretly wager 1-3 points on their vote being correct. This transforms every vote into a high-stakes moment where the reveal generates genuine tension and table talk.

The game runs entirely on local network infrastructure, requiring no external accounts, subscriptions, or cloud services. Players join via QR code scan, making setup frictionless for party contexts.

### Target Users

**Primary: The Host**
- Home Assistant enthusiast who hosts game nights
- Wants to be the "tech wizard" friend with seamless party experiences
- Values reliability over features — the game must "just work"
- Success = guests asking "what are we playing next time?"

**Secondary: Party Guests**
- Mix of tech-savvy and casual players
- Joining via QR code on personal phones
- May have never played social deduction games before
- Success = understanding the game within 30 seconds, experiencing memorable moments

**Tertiary: The Spy**
- Any player who draws the spy role
- High-pressure position requiring deduction and deception
- Success = either successfully blending in OR pulling off a bold Double Agent play

### Key Design Challenges

1. **Dual Information Hierarchy** — Spy and non-spy players see fundamentally different information. UI must feel consistent across roles to prevent visual "tells"

2. **Tension Architecture** — The confidence betting reveal is the product's signature moment. UX must build anticipation and deliver satisfying payoff

3. **Mobile Information Density** — Players need role info, timer, game state, and action buttons on phone screens during active gameplay

4. **Zero-Tutorial Onboarding** — Party context means no patience for instructions. UI must be self-explanatory within seconds

5. **Dual Display Strategy** — Host display (TV/tablet) serves the room; player display (phone) serves individuals. Different content, different scales, same design language

### Design Opportunities

1. **Owning "The Reveal"** — Potential for signature UX moment during vote/bet reveals that generates stories and table talk

2. **Psychological Layer Support** — UI could surface betting patterns and suspicion signals that feed the meta-game

3. **Role-Specific Atmosphere** — Spy POV could feel subtly different, making the role feel special without revealing information

4. **Proven Design Foundation** — Beatify's dark neon party theme provides a tested visual language for the same platform and context

## Core User Experience

### Defining Experience

The core Spyster loop centers on **social deduction under personal stakes**. Unlike standard Spyfall where votes are binary guesses, every Spyster vote carries a wager that transforms the reveal into a high-tension moment.

**The Core Loop:**
1. **Role Reveal** — Private moment of dread (spy) or relief (non-spy)
2. **Questioning Phase** — Social deduction through strategic Q&A
3. **Call the Vote** — Accusation moment, drama spike
4. **Bet Your Read** — Confidence wager commits personal stakes
5. **The Reveal** — Peak tension as votes and bets are exposed simultaneously
6. **Scoring** — Validation, consequences, leaderboard shift

**Peak Experience Moment:** The Reveal (Step 5) is the product's signature moment. Everything else in the UX exists to make this moment land.

### Platform Strategy

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Primary Platform | Mobile web (phone browsers) | Party guests join on personal devices |
| Secondary Platform | TV/tablet host display | Room-visible game state |
| Input Method | Touch-only | Party context, no keyboards |
| Offline Support | Not required | Local network game |
| Camera Access | QR code scanning | Browser-native, no app install |

### Effortless Interactions

| Interaction | Target | How |
|-------------|--------|-----|
| Join game | < 30 seconds | QR scan → name entry → lobby |
| Understand role | Instant recognition | Clear visual hierarchy, large text |
| Know whose turn | Zero cognitive load | Persistent indicator, not buried |
| Submit vote + bet | 2 taps + confirm | Pre-selected defaults, large touch targets |
| Reconnect | Invisible | URL token restoration, no re-auth |

### Critical Success Moments

1. **First Role Reveal** — New player's first "I'm the spy" moment must feel special, not confusing
2. **The Reveal Sequence** — Must build anticipation (locked votes) and deliver payoff (simultaneous reveal)
3. **ALL IN Payoff** — When a 3-point bet succeeds or fails spectacularly, UI must amplify the drama
4. **Double Agent Success** — Spy framing an innocent at ALL IN deserves celebration/horror

### Experience Principles

1. **The Reveal is Sacred** — Every UX decision should support or not detract from the bet reveal moment
2. **Glanceable State** — Players must understand game state in < 2 seconds while socially engaged
3. **Touch-First, Phone-Sized** — Design for one-handed phone operation, minimum 44px touch targets
4. **No Instructions Needed** — UI must be self-explanatory; players won't read tutorials at parties
5. **Spy Parity** — Spy and non-spy screens must feel similar enough that screen-glancing doesn't reveal role

## Desired Emotional Response

### Primary Emotional Goals

**Peak Emotion:** Catharsis at The Reveal — the explosion of tension when votes and bets are exposed simultaneously

**Supporting Emotions:**
- **Dread + Excitement** when assigned as spy ("Oh no... oh YES")
- **Suspicion + Paranoia** during questioning (reading every answer)
- **Commitment + Risk** when setting confidence bets (personal stakes)
- **Vindication** when your read was correct (+6 points flash)
- **Schadenfreude** when someone's overconfident bet backfires

**Differentiating Emotion:** The "stomach-drop" moment before bets are revealed. This is what separates Spyster from standard Spyfall.

### Emotional Journey Mapping

| Phase | Primary Emotion | Secondary | Design Goal |
|-------|-----------------|-----------|-------------|
| Join | Curiosity | Anticipation | Frictionless, welcoming |
| Role Reveal | Dread (spy) / Relief (non-spy) | Excitement | Private moment, clear role |
| Questioning | Suspicion | Paranoia | Focus on conversation, not UI |
| Vote Called | Drama spike | Tension | Clear transition, urgency |
| Betting | Commitment | Risk | Personal stakes feel real |
| Pre-Reveal | Anticipation | Anxiety | Brief pause, build tension |
| The Reveal | Catharsis | Vindication/Horror | Maximum payoff, celebration |
| Scoring | Validation | Competition | Leaderboard drama |

### Micro-Emotions

**To Amplify:**
- Confidence when locking in a vote (satisfying confirmation)
- Vindication when correct (personal celebration moment)
- Schadenfreude at others' failed bets (reveal animation)
- "Villain energy" for successful Double Agent plays

**To Prevent:**
- Confusion (glanceable state, clear indicators)
- Exclusion (self-explanatory UI, no insider knowledge needed)
- Frustration (robust reconnection, clear errors)
- Boredom (submission tracker, countdown visibility)

### Design Implications

| Emotion | UX Implementation |
|---------|-------------------|
| Anticipation | Staggered reveal: votes first, then bets, with brief dramatic pause |
| Catharsis | Confetti/animation, large text feedback, sound cues (optional) |
| Personal Stakes | Bet amount (1/2/3) prominently displayed next to each vote |
| Villain Energy | Double Agent success gets unique visual celebration |
| Belonging | Shared countdown, real-time submission tracker |
| Confidence | Large touch targets, clear confirmation states |

### Emotional Design Principles

1. **Build Before You Release** — Create anticipation before reveals; never rush the payoff
2. **Amplify Peak Moments** — The Reveal deserves animation, feedback, drama
3. **Personal Stakes Are Visible** — Bet amounts shown prominently, not hidden
4. **Failure Is Funny, Not Frustrating** — Wrong bets should generate laughs, not anger
5. **Spy Experience Is Special** — Being the spy should feel thrilling, not punishing

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

#### Beatify (Primary Reference)
- Dark neon party theme proven in same environment (HA, party context)
- View-based architecture: loading → join → lobby → game → reveal → end
- Submission tracker creates social pressure ("3/6 submitted")
- Reveal sequence with confetti, emotion text, staggered information
- Admin control bar pattern for host-specific actions

#### Jackbox Party Pack
- Zero-tutorial onboarding — players figure it out in seconds
- Phone as private screen, room display as public screen
- Timer as central pressure element
- Simple lobby (names only, no profiles)

#### Poker/Betting Apps
- Bet amounts as prominent, weighty UI elements
- Commitment animations that feel final
- ALL IN gets special visual treatment
- Card flip reveal builds anticipation

#### Among Us
- Role reveal as dramatic private moment
- Vote UI as player grid, not dropdown
- Suspense pause before revealing impostor

### Transferable UX Patterns

| Pattern | Source | Spyster Application |
|---------|--------|---------------------|
| View State Machine | Beatify | Clean phase transitions throughout game |
| Submission Tracker | Beatify | "4/7 voted" during voting phase |
| Dark Neon Theme | Beatify | Party environment, proven readability |
| Private/Public Split | Jackbox | Phone = private; TV = public |
| Timer Prominence | Jackbox | Countdown as hero element |
| Bet as Commitment | Poker | Large buttons, weighty confirmation |
| ALL IN Treatment | Poker | Special glow/color for max bet |
| Role Reveal Drama | Among Us | Brief build-up before role display |
| Vote Grid | Among Us | Player cards, not dropdown |
| Suspense Pause | Among Us | Delay before spy identity reveal |

### Anti-Patterns to Avoid

| Anti-Pattern | Prevention |
|--------------|------------|
| Form-style voting | Large tappable player cards |
| Instant reveals | Always add suspense pause |
| Hidden timers | Timer always visible and prominent |
| Text-heavy instructions | Self-explanatory affordances |
| Modal overload | View transitions, not stacked modals |
| Small touch targets | Minimum 44px, ideally larger |
| Asymmetric spy UI | Spy and non-spy layouts must feel identical |

### Design Inspiration Strategy

**Adopt:** Beatify CSS tokens, view architecture, dark neon theme, submission tracker, touch targets

**Adapt:** Year slider → bet buttons; reveal sequence → vote/bet/score stagger; voting grid with bet indicators

**Avoid:** Dropdowns, instant reveals, asymmetric layouts, modals during gameplay, precision-required buttons

## Design System Foundation

### Design System Choice

**Custom CSS Design System** forked from Beatify's proven token architecture.

**Rationale:**
- Project requires vanilla JS with no external dependencies
- No build step needed — raw CSS loaded directly in browser
- Beatify's token system is battle-tested in same environment (HA party games)
- Full control over every component for Spyster-specific needs (betting UI, reveal sequences)

### Token Architecture

**Foundation:** CSS Custom Properties (`:root` variables)

**Token Categories:**
- **Colors:** Background, accent, semantic (success/warning/error), text
- **Spacing:** Consistent scale (4px base: xs/sm/md/lg/xl/2xl)
- **Typography:** Font families, sizes, weights
- **Effects:** Shadows, glows, transitions
- **Layout:** Border radius, z-index layers

**Source:** Forked from Beatify's `styles.css` design tokens with Spyster-specific adaptations.

### Implementation Approach

**File Structure:**
```
www/css/
├── tokens.css        # Design tokens
├── base.css          # Reset, body, typography
├── components.css    # Reusable UI components
├── views.css         # View-specific layouts
├── animations.css    # Reveal sequences, transitions
└── utilities.css     # Helper classes
```

**Loading:** Direct `<link>` tags, no bundling or preprocessing required.

### Customization Strategy

**Adopt from Beatify:**
- Dark neon background (#0a0a12)
- Spacing scale (4px base)
- Typography tokens (Outfit display font, system body)
- Glow effect patterns
- Touch target minimums (44px)

**Adapt for Spyster:**
- Accent colors may shift for spy/noir theming
- New tokens for betting UI (ALL IN special treatment)
- Role-specific subtle variations (spy vs non-spy atmosphere)
- Reveal sequence animation tokens

### Component Library

**Hand-crafted components (no external dependencies):**

| Component | Description |
|-----------|-------------|
| `.btn` | Primary, secondary, danger, glow variants |
| `.player-card` | Name, status, tappable for voting |
| `.timer` | Large countdown display |
| `.bet-buttons` | 1 / 2 / ALL IN selector |
| `.role-display` | Location/role or spy indicator |
| `.submission-tracker` | Vote progress indicator |
| `.leaderboard` | Score display (compact/expanded) |
| `.modal` | QR, confirmations |
| `.admin-bar` | Host floating controls |

## Defining Experience Deep Dive

### The Defining Interaction

**"Lock in your vote and bet, then watch everyone's cards flip."**

This is the signature Spyster moment — the interaction users will describe to friends and remember after the party. Everything else in the UX exists to make this reveal sequence land with maximum impact.

### User Mental Model

**Familiar Patterns:**
- Voting: Among Us-style player selection (tap to accuse)
- Betting: Poker's "all in" concept (risk/reward)
- Reveal: Game show dramatic pause before answer

**Novel Combination:**
- Voting + betting in same action creates dual-layer commitment
- Staggered reveal (votes → pause → bets) builds anticipation
- Personal stakes visible to room creates social accountability

### Experience Mechanics

**Phase 1: Vote Called**
- Trigger: Player taps "Call Vote" OR round timer expires
- Transition: Urgent animation, 60-second countdown begins
- All players enter voting simultaneously

**Phase 2: Select Target + Set Bet**
- Player grid: Tap card to select suspect
- Bet selector: 1 / 2 / ALL IN buttons with risk/reward labels
- ALL IN has special glow treatment (visual weight)
- "Lock It In" confirms — no undo after confirmation

**Phase 3: Waiting Period**
- Submission tracker: "4/7 voted" with visual indicators
- Cannot see others' selections, only completion status
- Countdown creates time pressure
- Anticipation builds as count approaches total

**Phase 4: The Reveal Sequence**
1. **"Votes are in..."** (1s pause) — transition marker
2. **Votes flip** (staggered 0.5s each) — see who accused whom
3. **"Now the bets..."** (1s pause) — stomach-drop moment
4. **Bets revealed** (simultaneous) — see commitment levels
5. **The Verdict** — spy identity + scoring with celebration/commiseration

### Success Criteria

| Metric | Target |
|--------|--------|
| Anticipation | Pre-bet-reveal pause creates audible room tension |
| Clarity | Outcome understood by all players in < 3 seconds |
| Drama | At least one audible reaction per reveal sequence |
| Memorability | Players reference specific bets in conversation after game |
| Pacing | Full reveal sequence completes in 8-12 seconds |

### Novel UX Patterns

**Staggered Information Reveal:**
- Borrowed from: Game shows, card games
- Innovation: Applied to social deduction voting with personal stakes
- Purpose: Maximize anticipation before the stakes (bets) are shown

**ALL IN as Visual Anchor:**
- Borrowed from: Poker UI patterns
- Innovation: Makes maximum bet feel weighty and memorable
- Purpose: Create stories ("Remember when Dave went ALL IN?")

## Visual Design Foundation

### Color System

**Base Palette:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg-primary` | `#0a0a12` | Main background |
| `--color-bg-secondary` | `#12121a` | Cards, elevated surfaces |
| `--color-bg-tertiary` | `#1a1a24` | Subtle differentiation |
| `--color-text-primary` | `#ffffff` | Primary text |
| `--color-text-secondary` | `#a0a0a8` | Muted text |

**Accent Colors:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-accent-primary` | `#ff2d6a` | Primary actions (pink) |
| `--color-accent-secondary` | `#00f5ff` | Secondary highlights (cyan) |

**Semantic Colors:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#39ff14` | Correct vote, positive |
| `--color-error` | `#ff0040` | Wrong vote, spy reveal |
| `--color-all-in` | `#ffd700` | ALL IN bet highlight |

### Typography System

**Font Stack:**
- Display: 'Outfit', system-ui, sans-serif
- Body: system-ui, -apple-system, sans-serif

**Type Scale:**

| Token | Size | Usage |
|-------|------|-------|
| Hero | 72px | Spy reveal, major announcements |
| Timer | 64px | Countdown display |
| Title | 32px | View titles |
| Heading | 24px | Section headings |
| Body | 16px | Default text |
| Small | 14px | Secondary info |

### Spacing & Layout Foundation

**Spacing Scale:** 4px base unit

| Token | Value |
|-------|-------|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 48px |
| 3xl | 64px |

**Touch Targets:**
- Minimum: 44px × 44px (iOS HIG)
- Primary actions: 48px
- Bet buttons: 56px (high-stakes feel)

**Border Radius:** sm(4px) / md(8px) / lg(12px) / xl(16px) / full(9999px)

### Effects System

**Glows:**
- Primary: `0 0 20px rgba(255, 45, 106, 0.5)` (pink)
- Secondary: `0 0 20px rgba(0, 245, 255, 0.5)` (cyan)
- Success: `0 0 20px rgba(57, 255, 20, 0.5)` (green)
- Error: `0 0 20px rgba(255, 0, 64, 0.5)` (red)
- ALL IN: `0 0 30px rgba(255, 215, 0, 0.7)` (gold, stronger)

**Transitions:**
- Fast: 150ms ease-out (micro-interactions)
- Normal: 300ms ease-out (standard)
- Slow: 500ms ease-out (deliberate)
- Reveal: 800ms cubic-bezier(0.34, 1.56, 0.64, 1) (dramatic)

### Accessibility Considerations

| Requirement | Implementation |
|-------------|----------------|
| Contrast Ratio | WCAG AA (7.2:1 for accent on dark) |
| Touch Targets | 44px minimum, 8px spacing |
| Focus States | Visible rings on all interactive elements |
| Color Independence | Never rely on color alone |
| Motion | Respect prefers-reduced-motion |

## Design Direction Decision

### Design Directions Explored

Three directions were evaluated:
- **Direction A: Beatify Sibling** — Same pink/cyan neon party aesthetic
- **Direction B: Spy Noir** — Darker, red/amber thriller atmosphere
- **Direction C: High Contrast Clean** — Minimal, accessibility-focused

### Chosen Direction

**Beatify Sibling with Spy Touches** (Direction A enhanced)

Maintains the proven party-friendly aesthetic from Beatify while adding Spyster-specific visual moments through semantic color additions (gold for ALL IN, red for spy reveals).

### Design Rationale

| Factor | Decision |
|--------|----------|
| Party Context | Pink/cyan neon works in dimmed rooms |
| Implementation Speed | Fork Beatify CSS directly |
| User Familiarity | Same system, different game |
| Memorable Moments | Gold ALL IN + Red spy reveal stand out |
| Accessibility | High contrast on dark background |

### Implementation Approach

1. **Fork Beatify's tokens.css** as starting point
2. **Add Spyster tokens:** `--color-all-in`, `--color-spy`
3. **Reuse component patterns:** buttons, cards, timer, modals
4. **Create new components:** bet buttons, vote grid, reveal sequence
5. **Customize animations:** slower, more dramatic reveal transitions

### Visual Identity Summary

| Role | Color | Usage |
|------|-------|-------|
| Primary Action | Pink (#ff2d6a) | Buttons, CTAs |
| Secondary Info | Cyan (#00f5ff) | Highlights, links |
| Success | Green (#39ff14) | Correct votes |
| Danger | Red (#ff0040) | Spy reveal, errors |
| High Stakes | Gold (#ffd700) | ALL IN emphasis |

## User Journey Flows

### Host Journey (Marcus)

**Flow:** Setup → Lobby → Game Loop → End

**Key Screens:**
1. Setup: Configure rounds, timer, location pack
2. Lobby: Display QR, show joined players, START when ready
3. Game: Show timer, current Q&A pair, orchestrate reveals
4. End: Final leaderboard, rematch option

**Host Controls:**

| Control | When | Action |
|---------|------|--------|
| START GAME | Lobby, 4+ players | Begin first round |
| SKIP TO VOTE | Questioning | Force voting early |
| NEXT ROUND | After scoring | Start new round |
| END GAME | Any time | Show final results |

### Player Journey (Jenna)

**Flow:** Join → Lobby → Play Rounds → Results

**Key Screens:**
1. Join: QR scan → name entry → confirmation
2. Lobby: "Waiting for host...", see other players
3. Role Reveal: Location + Role OR Spy view
4. Questioning: Timer, Q&A indicator, CALL VOTE button
5. Voting: Player grid, bet selector, LOCK IT IN
6. Reveal: Personal result, points change
7. Results: Leaderboard, next round

**Tap Economy:**
- Join game: 2 taps (enter name, submit)
- Submit vote: 3 taps (select player, select bet, confirm)

### Spy Journey (Dave)

**Flow:** Same as player with strategic decisions

**Key Differences:**
- Role reveal shows "SPY" + location list (not specific location)
- Must deduce location from questions
- Double Agent option: ALL IN on innocent for +10 bonus
- Layout identical to non-spy (spy parity critical)

**Spy Strategy Paths:**
1. Play Safe: Vote suspicious player, bet 1-2 points
2. Double Agent: Vote innocent, ALL IN for +10 bonus risk

### Reconnect Journey (Tom)

**Flow:** Connection Lost → Restore → Resume

**Reconnection Paths:**

| Scenario | Experience |
|----------|------------|
| URL token valid | Instant restore, no action |
| Token expired, game active | Select name → verify → restore |
| Game ended | Show results, offer new game |
| Unknown state | Standard join flow |

### Journey Patterns

| Pattern | Description |
|---------|-------------|
| State Persistence | All state server-side, URL tokens for recovery |
| Transitions | 300ms animations, clear phase indicators |
| Waiting States | Always show what/who we're waiting for |
| Confirmations | Critical actions require explicit confirm |
| Spy Parity | Identical layouts for spy and non-spy |

### Flow Optimization Principles

| Principle | Implementation |
|-----------|----------------|
| Minimize taps | Join: 2, Vote: 3 |
| Show progress | Submission tracker, timer always visible |
| Graceful degradation | Auto-reconnect → manual recovery |
| No dead ends | Every error has recovery path |
| Spy parity | All screens same layout regardless of role |

## Component Strategy

### Design System Components (from Beatify)

| Component | Status | Adaptation |
|-----------|--------|------------|
| `.btn` | Fork | Add danger, glow variants |
| `.card` | Fork | Base for player cards |
| `.timer` | Reuse | Same pattern |
| `.modal` | Fork | QR display, confirmations |
| `.admin-bar` | Reuse | Host controls |
| `.confetti` | Reuse | Celebration effects |

### Custom Components

#### Player Card (`.player-card`)
- **Purpose:** Selectable vote target
- **States:** default, hover, selected, reveal, disabled
- **Variants:** compact (lobby), vote (selection), reveal (results)
- **Accessibility:** `role="button"`, `aria-pressed`

#### Bet Buttons (`.bet-buttons`)
- **Purpose:** Confidence level selection (1/2/ALL IN)
- **States:** default, selected per level, disabled
- **Special:** ALL IN has gold glow, stronger visual weight
- **Accessibility:** `role="radiogroup"`, `aria-checked`

#### Role Display (`.role-display`)
- **Purpose:** Location/role OR spy indicator
- **Critical:** Identical dimensions for spy parity
- **Variants:** spy, innocent, hidden

#### Submission Tracker (`.submission-tracker`)
- **Purpose:** "4/7 voted" progress indicator
- **Updates:** Real-time via WebSocket
- **Accessibility:** `role="progressbar"`, `aria-valuenow`

#### Vote Grid (`.vote-grid`)
- **Purpose:** Player card layout for voting
- **Layout:** CSS Grid, 2-4 columns responsive
- **Behavior:** Self excluded from selection

#### Reveal Sequence (`.reveal-sequence`)
- **Purpose:** Staged dramatic reveal
- **Stages:** votes-intro → votes-flip → bets-intro → bets-show → verdict
- **Timing:** ~8-12 seconds total with dramatic pauses

### Component Implementation Strategy

| Aspect | Approach |
|--------|----------|
| CSS Architecture | BEM naming (`.component__element--modifier`) |
| Token Usage | All values from tokens.css |
| States | CSS classes (`.is-selected`, `.is-disabled`) |
| Animations | CSS animations + JS for staging |
| Responsive | Mobile-first, breakpoints for tablet/TV |
| Accessibility | ARIA roles, keyboard nav, focus management |

### Implementation Roadmap

| Phase | Components | Rationale |
|-------|------------|-----------|
| P0 | player-card, bet-buttons, role-display, submission-tracker, vote-grid | Core gameplay |
| P1 | reveal-sequence, leaderboard, phase-indicator, location-list | Experience polish |
| P2 | admin-bar, qr-display, game-settings | Host features |

## UX Consistency Patterns

### Button Hierarchy

| Type | Style | Usage |
|------|-------|-------|
| Primary | Pink bg, white text | One per screen: START, LOCK IT IN |
| Secondary | Pink outline | Cancel, Back, Skip |
| Danger | Red bg | END GAME, Leave |
| Ghost | Text only | Help, Settings |
| ALL IN | Gold glow, larger | Bet selector only |

### Feedback Patterns

| Type | Color | Animation | Duration |
|------|-------|-----------|----------|
| Success | Green (#39ff14) | Glow pulse | 300ms anim, 2s visible |
| Error | Red (#ff0040) | Shake | 200ms anim, until dismissed |
| Warning | Amber (#ffaa00) | None | Persistent until resolved |
| Info | Cyan (#00f5ff) | None | Real-time updates |
| Reveal | Mixed | Staged sequence | 8-12s total |

### State Transitions

**Pattern:** Exit (300ms) → Marker (500ms) → Enter (300ms)

**Transition Markers:**
- "ROUND 1" — lobby to game
- "VOTE CALLED" — questioning to voting
- "Votes are in..." — voting to reveal
- "RESULTS" — reveal to scoring
- "GAME OVER" — final results

**Rule:** Never instant content swap — always animate transitions

### Waiting Patterns

- Always show WHAT we're waiting for
- Show WHO completed (anonymized: "4/7 voted")
- Show time remaining if applicable
- Subtle animation indicates "alive" state

### Confirmation Patterns

| Action Type | Confirmation |
|-------------|--------------|
| Destructive | Modal required (END GAME, Leave) |
| Commitment | Single button → transforms to "LOCKED ✓" |
| Reversible | No confirmation (can change until locked) |

### Navigation Patterns

- **View-based:** State-driven, no traditional nav bar
- **Player:** Follow game flow, view leaderboard anytime
- **Host:** Admin bar fixed bottom, controls progression
- **No backward navigation** during active phases

## Responsive Design & Accessibility

### Display Contexts

| Context | Device | Purpose |
|---------|--------|---------|
| Player | Phone (320-428px) | Personal game interface |
| Host | Tablet/TV (768px+) | Room-visible display |

### Responsive Strategy

**Player View (Mobile-First):**
- Single column, full-width components
- 48px+ touch targets (thumb-zone optimized)
- No horizontal scrolling
- Priority: Role → Timer → Primary Action

**Host View (Tablet/TV):**
- Room-optimized scale (2-3x player)
- Massive timer display (96-144px)
- Landscape orientation preferred
- High contrast for varied lighting

### Breakpoint Strategy

| Breakpoint | Context | Changes |
|------------|---------|---------|
| Base (0+) | Phone | Single column, mobile scale |
| 768px | Tablet/Host | Switch to host layout, 1.5x scale |
| 1024px | Large display | 2x scale |
| 1440px+ | TV | Maximum scale, simplified |

### Accessibility Compliance (WCAG 2.1 AA)

**Color & Contrast:**
- 4.5:1 text contrast minimum (7.2:1 actual)
- Color never used as sole indicator
- All states have text/icon redundancy

**Touch & Motor:**
- 48px minimum touch targets
- 8px spacing between targets
- No precision required, forgiving hit areas

**Screen Readers:**

| Element | ARIA Implementation |
|---------|---------------------|
| Player cards | `role="button"`, `aria-pressed` |
| Bet buttons | `role="radiogroup"`, `aria-checked` |
| Timer | `role="timer"`, `aria-live="polite"` |
| Tracker | `role="progressbar"` |
| Transitions | `aria-live="assertive"` |

**Keyboard Navigation:**
- Arrow keys for player/bet selection
- Enter/Space to confirm
- Tab order follows visual order
- Focus visible on all interactive elements

**Motion:**
- Respect `prefers-reduced-motion`
- Skip animations, show final states immediately
- Essential state changes remain visible

### Testing Strategy

| Category | Method |
|----------|--------|
| Responsive | Physical devices (iPhone SE, Pro Max, iPad, TV) |
| Accessibility | axe DevTools, VoiceOver, keyboard-only |
| Real-world | Bright/dim rooms, mixed device parties |
