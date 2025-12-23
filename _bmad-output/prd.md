---
stepsCompleted: [1, 2, 3, 4, 6, 7, 8, 9, 10, 11]
lastStep: 11
status: complete
completedAt: '2025-12-22'
inputDocuments:
  - 'analysis/brainstorming-session-2025-12-22.md'
  - 'external: /Volumes/My Passport/Beatify/_bmad-output/game-concepts/spyster-design.md'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 0
  externalDocs: 1
workflowType: 'prd'
lastStep: 0
project_name: 'Spyster'
user_name: 'Markusholzhaeuser'
date: '2025-12-22'
---

# Product Requirements Document - Spyster

**Author:** Markusholzhaeuser
**Date:** 2025-12-22

## Executive Summary

Spyster is a social deduction party game built as a Home Assistant custom component. Players join via phone (QR code), one is secretly assigned as the Spy, and through strategic questioning, players must identify the Spy before time runs out—while the Spy attempts to blend in and deduce the secret location.

**For the HA enthusiast who wants to be the ultimate party host.** The game runs entirely on your Home Assistant instance—no external servers, no accounts, no subscriptions. Player phones connect via WebSocket to a locally-hosted interface, turning your smart home into the game server.

### What Makes This Special

Casual party games often lack stakes. Everyone votes, someone wins, next round. Spyster adds just enough risk to make every round memorable without alienating casual players.

**Confidence Betting** transforms voting from a safe guess into a stomach-drop moment. Before votes are revealed, players secretly wager 1-3 points on being right. Lock in your vote, then watch the room as bets are revealed together. That moment when you realize you just went ALL IN on a hunch—that's the tension Spyfall never delivers.

The **Double Agent** mechanic rewards spy aggression. If the Spy bets big on framing an innocent player and succeeds, they score +10 points. No more passive blending—the Spy is incentivized to play bold.

**The meta-game hook:** Being "too confident" becomes a suspicion signal. Players start reading each other's betting patterns, adding a psychological layer that grows with each round.

**Core tension drivers:**
- That pause before bets are revealed
- The risk of looking *too* sure
- Spies rewarded for bold plays, not hiding
- Every vote becomes a story moment

## Project Classification

**Technical Type:** Home Assistant Custom Component + WebSocket Web App
**Domain:** Gaming/Entertainment
**Complexity:** Medium
**Project Context:** Greenfield

Python backend (HA custom component) with browser-based frontend. Real-time multiplayer via WebSocket, session management for 4-10 concurrent players.

## Success Criteria

### User Success

**Host Success:**
- Game runs without technical issues through a full session (5+ rounds)
- Guests engage without needing technical assistance
- Setup to first round in under 2 minutes

**Player Success:**
- QR scan to playing in under 30 seconds
- Experience tension moments: bet reveals, close votes, spy accusations
- No frustration from disconnects or lag

**Group Success:**
- Game generates memorable table talk and "remember when..." stories
- Players want to play again
- 5+ rounds feels like a complete, satisfying game night

### Business Success

**Primary Goal:** Works reliably at own parties
**Stretch Goal:** 100 HACS downloads within first 6 months

### Technical Success

| Metric | Target |
|--------|--------|
| Reliability | Zero crashes mid-game |
| Setup time | Host starts game in < 2 minutes |
| Player join | QR → playing in < 30 seconds |
| Concurrent players | 10 players without perceptible lag |
| Player reconnection | Reconnect within 60 seconds of disconnect |
| State preservation | Game state held for disconnected player up to 5 minutes |
| Host disconnect | Game pauses until host returns (up to 5 minutes) |

**Critical Risk:** Disconnects mid-game would kill the experience. Session persistence and reconnection handling are non-negotiable MVP requirements.

### Measurable Outcomes

**Technical:**
- Complete 5-round session without technical intervention
- All players remain connected or successfully reconnect
- Host would use it again for next party

**Experience:**
- At least one ALL IN bet per game session (players engage with risk mechanic)
- Spy wins at least 30% of rounds (spy gameplay is viable, not just passive hiding)

## Product Scope

### MVP - Minimum Viable Product

**Core Game:**
- Complete game loop (Lobby → Roles → Questioning → Vote → Reveal → Scoring)
- WebSocket multiplayer (4-10 concurrent players)
- Confidence Betting system (1-3 point wagers)
- Double Agent mechanic (+10 spy frame bonus)

**Content:**
- Classic content pack: 10 locations, 6-8 roles each

**Session Management:**
- Player session persistence (survives phone sleep/lock)
- Automatic reconnection on network restore (60s window, 5min state hold)
- Host disconnect handling (game pauses until host returns)
- QR code join flow

**UI:**
- Phone player interface
- Host display view

### Growth Features (Post-MVP)

- Additional content packs (Home, Sci-Fi, Fantasy, HA-Themed)
- 2-spy mode for 8+ player games
- Custom location/role creation
- Achievement system
- Seasonal content packs

### Vision (Future)

- Cross-household multiplayer via cloud relay
- AI spy player for solo practice
- Beatify integration for "party night" mode
- Tournament mode
- Voice chat integration

## User Journeys

### Journey 1: Marcus - The Host Who Delivers

Marcus is a Home Assistant enthusiast who loves hosting game nights. He's got the smart home setup, the big TV, and friends who expect something special. Tonight, after dinner winds down, someone asks "what should we play?" Marcus has been waiting for this moment.

He pulls out his phone, opens Home Assistant, and taps "Start Spyster." A QR code appears on his TV within seconds. "Connect to my WiFi first," he tells his 6 friends, "it's 'CasaMarcos' - the password's on the fridge." The next 3 minutes are cheerful chaos - people fumbling with WiFi passwords, scanning QR codes, typing names. One friend, Mike, gets a "Connection failed" message. Marcus checks the TV - Mike's name isn't in the lobby. "Are you on WiFi or cellular?" Cellular. Mike switches to WiFi, rescans, and he's in.

Within 3 minutes, all 7 names appear on the TV lobby screen. Marcus picks the "Classic" location pack, sets 7-minute rounds, and hits Start. The TV shows "Assigning roles..." for a brief moment, then each player's phone displays their private role. The room fills with nervous laughter and suspicious glances.

When someone yells "I'm calling a vote!" the energy spikes. A 60-second voting timer appears on everyone's screen. Five rounds later, everyone's arguing about who bet too confidently on that second round.

Marcus is already planning next month's game night. His reputation as the ultimate party host? Cemented.

**Capabilities revealed:** Game setup flow, QR code generation, lobby management, game config, host display, session management, WiFi requirement messaging, connection failure feedback, lobby status visibility, role assignment loading state, voting timeout.

---

### Journey 2: Jenna - First-Timer Finds Her Moment

Jenna has never played Spyster before. She connects to Marcus's WiFi, then scans the QR code on the TV with her phone camera. Her browser opens to a simple join screen. She types her name and taps Join. A brief "Connecting..." spinner appears, her name appears on the TV lobby, then she waits.

When Marcus starts the game, Jenna's screen shows "Assigning roles..." for a beat. Then it transitions cleanly to: "🏖️ THE BEACH - You are the LIFEGUARD" with a list of other possible roles at this location. No flicker, no partial data - just a clean reveal.

The game starts and Marcus asks her first: "What would you wear to work?" Her instinct is to say "swimsuit" but she catches herself—too obvious, might help the spy. "Something red and practical," she says carefully. A few questions later, Dave gives a weirdly vague answer about "enjoying the people-watching." Jenna's suspicious.

She taps "Call a Vote." The room goes quiet. A 60-second countdown appears. She selects Dave, then sees the betting screen. She's confident—she goes ALL IN with 3 points. Everyone locks in their votes and bets. Tom is in the bathroom and doesn't vote - when the timer expires, his vote counts as abstain with no bet.

The reveal is electric. Dave WAS the spy. Jenna's +6 points flash on screen. She screams. The table erupts. She's already hooked.

**Capabilities revealed:** QR join flow, connection feedback, role assignment loading state, role display, voting interface, voting timeout (60s), abstain handling, Confidence Betting UI, bet reveal animation, points display.

---

### Journey 3: Dave - The Spy Who Almost Won

When Marcus starts the game, Dave's screen shows "Assigning roles..." for a moment. Then it transitions to the screen every player dreads and secretly hopes for: "🕵️ YOU ARE THE SPY." Below it, a list of 10 possible locations. His heart rate spikes. The loading state ensured no accidental data leak - he never saw a flash of someone else's role.

Two questions in, someone asks him about the "atmosphere." He has no idea if it's a beach, hospital, or casino. "Pretty chill, you know, relaxed vibe," he says, keeping it vague. He watches the next few answers like a hawk. Someone mentions "getting sand everywhere." Beach. Got it.

He could tap "Guess Location" right now and end the round—but where's the fun in that? He decides to play it out, asking questions that sound knowledgeable without being specific. When Jenna calls a vote, Dave sees an opportunity. He goes ALL IN on framing Jenna—if the group votes her out instead, that's +10 points for the Double Agent bonus.

The votes come in: 4 for Dave, 2 for Jenna. Close, but not close enough. The reveal shows Dave was the spy, and the room explodes with "I KNEW IT" and "How did you know about the sand?!"

That near-miss? That's the story they'll tell for weeks.

**Capabilities revealed:** Role assignment loading state (prevents data leak), spy role screen, location list for guessing, spy guess flow, voting strategy, Double Agent mechanic, reveal drama.

---

### Journey 4: Tom - The Reconnection Save

Three rounds in, Tom's phone screen goes black. Dead battery. He frantically plugs it in while the group debates pausing the game.

"Give it 30 seconds," Marcus says, checking the host display. Tom's name shows a yellow "disconnected" indicator - this appeared after 30 seconds of no heartbeat from his device.

Tom's phone boots back up. He reopens the browser tab—the URL contains his session token, so the game recognizes him immediately and drops him right back in. Same role, same game phase, same score. He missed one question but the round is still going. He's back.

If Tom had taken longer than 5 minutes, or if Marcus had removed his "ghost" session from the lobby, Tom would have needed to rejoin as a new player (not possible mid-round).

The game continues without losing momentum. Tom makes a mental note to charge his phone before next game night.

**Capabilities revealed:** Session persistence via URL token, automatic reconnection, state preservation, disconnected indicator after 30s, 5-minute reconnection window, graceful recovery.

---

### Journey 5: Lisa - Connection Troubleshooting

Lisa scans the QR code but her screen shows: "Unable to connect. Make sure you're on the same WiFi network as the game host."

She checks her phone - she's still on cellular data. She switches to Marcus's WiFi, taps "Retry," and the join screen loads. She enters her name and sees "Connecting..." then her name appears on the TV.

But her friend Mike has a different problem - he scanned and got a blank white screen. Marcus suggests he try a different browser. Mike opens Chrome instead of his default Samsung browser, scans again, and this time it works.

The lobby shows 6 of 7 players ready. One name shows "disconnected" for over a minute - it's a ghost session from someone who closed their browser. After 60 seconds in "disconnected" state, a "Remove" button appears next to the name. Marcus taps it, confirms removal, and now everyone who's actually there is ready to play.

**Capabilities revealed:** Clear error messaging with resolution steps, retry functionality, browser compatibility notes, lobby management for host, connection status indicators (connected/disconnected), ghost session removal after 60s disconnected.

---

### Journey Requirements Summary

| Journey | Key Capabilities Required |
|---------|--------------------------|
| **Host (Marcus)** | HA integration, QR generation, lobby UI, game config, host display, session management, WiFi requirement display, connection troubleshooting visibility, role loading state, voting timeout |
| **Player Non-Spy (Jenna)** | QR join, connection feedback, role loading state, role display, voting UI, voting timeout + abstain, betting UI, reveal animations, scoring |
| **Player Spy (Dave)** | Role loading state (no data leak), spy role screen, location list, guess flow, betting strategy, Double Agent scoring |
| **Reconnection (Tom)** | Session persistence via URL token, auto-reconnect, state sync, disconnected status after 30s, 5-min reconnection window, host status indicators |
| **Connection Issues (Lisa)** | Error messages with guidance, retry flow, browser compatibility, ghost removal after 60s disconnected |

### Timing Hierarchy (Connection States)

| Event | Timing | State |
|-------|--------|-------|
| No heartbeat | 30 seconds | "Disconnected" indicator shown |
| Still disconnected | 60 seconds | Host can remove player |
| Player reopens URL | Within 5 minutes | Session restored |
| Player removed OR >5 min | - | Must rejoin (blocked mid-round) |

### Voting Timeout

- 60-second countdown for all votes
- Non-voters count as abstain (no bet placed)
- Game proceeds with votes received

### Role Assignment

- "Assigning roles..." loading state shown to all players
- Role screen only displayed after server confirms assignment
- No partial data or flicker possible

## Innovation & Novel Patterns

### Detected Innovation Areas

**Primary Innovation: Confidence Betting System**

Spyster introduces a point-wagering layer to the voting phase of social deduction games. Unlike standard Spyfall where voting is binary (guess or abstain), players secretly wager 1-3 points on their vote being correct before results are revealed.

This mechanic is borrowed from poker (betting on your read of opponents) and applied to social deduction for the first time in this combination. Market research shows existing social deduction games use standard voting without personal stakes.

**Secondary Innovation: Double Agent Mechanic**

The spy role is traditionally defensive—blend in, survive. Spyster's Double Agent bonus (+10 for successfully framing an innocent at high confidence) inverts this dynamic, incentivizing aggressive spy play and creating a "too confident?" suspicion meta-game.

### Market Context & Competitive Landscape

- Social deduction games (Spyfall, Werewolf, Blood on the Clocktower) dominate with role-based mechanics
- Betting/bidding mechanics exist in deduction games (Spectral Manor) but not combined with Spyfall-style social deduction
- No identified competitor combines point-wagering with vote outcomes in party social deduction
- Niche opportunity: players who want "more stakes" in casual party games

### Validation Approach

| Risk | Validation Method |
|------|-------------------|
| Betting adds friction, slows game | Playtest: measure round times with/without betting |
| Math-averse players confused | Playtest: observe first-timer onboarding |
| Betting overshadows deduction | Playtest: track question quality vs betting focus |
| Double Agent too powerful | Playtest: track spy win rates at different player counts |

**Minimum viable validation:** 3 game nights with different groups, tracking:
- Round completion time
- Player engagement during betting reveal
- Spy win rate
- "Would play again" feedback

### Risk Mitigation

| Innovation Risk | Fallback |
|-----------------|----------|
| Confidence Betting too complex | Ship with "Classic Mode" (no betting) as option |
| Double Agent unbalanced | Tunable point values (start at +10, adjust based on data) |
| Mechanic doesn't create tension | Worst case: it's still Spyfall, which works |

## Home Assistant Integration + Web App Requirements

### Project-Type Overview

Spyster is a **HACS-distributed Home Assistant custom integration** with a **browser-based player interface**. The backend runs as a Python custom component within HA, serving a real-time web frontend via WebSocket.

**Architecture Pattern:** Follow Beatify integration structure
**Distribution:** HACS (Home Assistant Community Store)

### Platform Requirements

| Platform | Requirement |
|----------|-------------|
| Home Assistant | 2025.11+ minimum |
| Python | As required by HA 2025.11 (likely 3.12+) |
| HACS | Compatible with current HACS standards |

### Browser Support Matrix

| Browser | Support Level |
|---------|---------------|
| Chrome (Android) | ✅ Last 2 years |
| Safari (iOS) | ✅ Last 2 years |
| Firefox Mobile | ✅ Last 2 years |
| Samsung Internet | ✅ Last 2 years |
| Older browsers / IE | ❌ Not supported |

**Rationale:** Party game context - guests will have modern phones. No need to support legacy browsers.

### Real-Time Architecture

| Component | Technology |
|-----------|------------|
| Client-Server | WebSocket (aiohttp) |
| State Sync | Server-authoritative game state |
| Reconnection | URL token-based session persistence |
| Heartbeat | 30-second interval for disconnect detection |

### Home Assistant Integration Structure

Following Beatify patterns:

```
custom_components/spyster/
├── __init__.py           # Integration setup, register views
├── manifest.json         # HACS manifest
├── const.py              # Constants
├── config_flow.py        # UI configuration (if needed)
├── game/
│   ├── state.py          # Game state management
│   ├── logic.py          # Game rules engine
│   └── scoring.py        # Points calculation
├── server/
│   ├── views.py          # HTTP endpoints (QR, static files)
│   └── websocket.py      # WebSocket handler
├── www/                  # Frontend assets
│   ├── player.html       # Player interface
│   ├── display.html      # TV/host display
│   ├── js/
│   └── css/
└── content/
    └── classic.json      # Location pack data
```

### Configuration Approach

| Method | Support |
|--------|---------|
| Config Flow (GUI) | Follow Beatify pattern |
| YAML | Not required if Config Flow implemented |

### Performance Targets

| Metric | Target |
|--------|--------|
| Initial page load | < 2 seconds on 4G |
| WebSocket latency | < 100ms local network |
| Concurrent players | 10 without degradation |
| Memory footprint | Minimal HA impact |

### Accessibility Level

**Minimal** - Party game context with in-person verbal interaction:
- Readable font sizes (mobile-friendly)
- Sufficient color contrast for readability
- No screen reader optimization required
- No keyboard navigation required (touch-only)

### HACS Distribution Requirements

| Requirement | Status |
|-------------|--------|
| Valid manifest.json | Required |
| Version tagging | Semantic versioning |
| README documentation | Required for HACS listing |
| hacs.json | Required for custom integration |

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience MVP
**Rationale:** Deliver the complete Spyster tension experience (Confidence Betting + Double Agent) from day one. A stripped-down Spyfall clone wouldn't validate the core innovation.

**Resource Profile:** Solo developer project
**Target Timeline:** Ship when ready, no external deadline pressure

### MVP Feature Boundaries

**In Scope (Must Ship):**

| Category | Features |
|----------|----------|
| Core Game | 6-phase loop (Lobby → Roles → Questioning → Vote → Reveal → Scoring) |
| Multiplayer | WebSocket, 4-10 players, session persistence |
| Mechanics | Confidence Betting (1-3 points), Double Agent (+10 frame bonus) |
| Content | Classic pack (10 locations, 6-8 roles each) |
| UX Polish | Role loading state, 60s vote timeout, reconnection handling |
| Host Tools | QR generation, lobby management, ghost session cleanup |
| Display | Phone player UI, TV/tablet host display |

**Explicitly Deferred (Post-MVP):**

| Feature | Why Deferred |
|---------|--------------|
| Additional content packs | Content, not core experience |
| 2-spy mode | Balance tuning needed first |
| Custom locations | Editor complexity |
| Achievements | Nice-to-have |
| Classic Mode (no betting) | Fallback if innovation fails - ship with betting first |

### Phased Development Roadmap

**Phase 1: MVP**
- Complete playable game with Confidence Betting
- 5+ round sessions without technical issues
- HACS-distributable

**Phase 2: Content Expansion**
- Home, Sci-Fi, Fantasy, HA-Themed packs
- 2-spy mode for 8+ players
- Seasonal content

**Phase 3: Platform Features**
- Custom location/role creation
- Achievement system
- Cross-household cloud relay

**Phase 4: Vision**
- AI spy for solo practice
- Beatify integration
- Tournament mode

### Risk Mitigation Strategy

| Risk | Mitigation |
|------|------------|
| **Confidence Betting too complex** | Clear UI, optional tutorial round, ship with betting first and add Classic Mode later if needed |
| **Double Agent unbalanced** | Tunable point values (+10 starting, adjust based on playtest data) |
| **Reconnection fails in practice** | URL token approach, 5-min window, tested disconnect/reconnect flows |
| **10 players causes lag** | Server-authoritative state, minimal payload, load test before ship |
| **Nobody downloads it** | Primary goal is personal use - 100 downloads is stretch goal |

### Scoping Constraints

**Hard Constraints:**
- HA 2025.11+ only (use latest APIs, no backwards compat burden)
- Modern browsers only (no polyfills)
- Single-spy mode only for MVP (2-spy is Growth feature)

**Soft Constraints:**
- Classic pack sufficient for MVP (more content is Growth)
- No config options beyond round duration and location pack

## Functional Requirements

### Game Session Management

- **FR1:** Host can create a new game session from Home Assistant
- **FR2:** Host can configure round duration before starting
- **FR3:** Host can select a location pack before starting
- **FR4:** Host can view a QR code for players to join
- **FR5:** Host can see all connected players in a lobby view
- **FR6:** Host can start the game when 4-10 players have joined
- **FR7:** Host can end the current game session at any time
- **FR8:** Host can configure number of rounds per game (fixed count only)

### Player Connection

- **FR9:** Player can join a game session by scanning a QR code
- **FR10:** Player can enter their display name when joining
- **FR11:** Player can see connection status feedback during join
- **FR12:** Player can see an error message with network requirements if connection fails
- **FR13:** Player can retry connection after a failure
- **FR14:** Player can automatically reconnect if disconnected (within 5 minutes)
- **FR15:** System detects player disconnect after 30 seconds of no heartbeat
- **FR16:** Host can see which players are connected vs disconnected
- **FR17:** Host can remove a disconnected player from the lobby
- **FR18:** System prevents duplicate sessions for same player name (removes old session)

### Role Assignment

- **FR19:** System assigns exactly one player as Spy per round
- **FR20:** Non-spy players can see the current location and their role
- **FR21:** Spy player can see the list of possible locations (but not the actual location)
- **FR22:** All players see a loading state during role assignment (no data leak)
- **FR23:** System randomly assigns spy each round (same player may be spy multiple times)

### Game Flow - Questioning Phase

- **FR24:** Player can view their assigned role at any time during the round
- **FR25:** System displays which player should ask a question
- **FR26:** System displays which player should answer
- **FR27:** Host display shows current questioner and answerer for the room
- **FR28:** Players can see the round timer counting down
- **FR29:** Any player can call for a vote during the questioning phase
- **FR30:** System auto-triggers voting when round timer expires

### Voting & Confidence Betting

- **FR31:** Player calling a vote (or timer expiry) triggers voting phase for all players
- **FR32:** All players can select who they suspect is the Spy
- **FR33:** All players can set their confidence bet (1, 2, or 3 points)
- **FR34:** Players see a countdown timer during voting (60 seconds)
- **FR35:** Players who don't vote before timeout are counted as abstain
- **FR36:** System reveals all votes and bets simultaneously after voting ends
- **FR37:** Players can see who voted for whom and at what confidence level
- **FR38:** System convicts player with plurality of votes (ties = no conviction, round continues)

### Spy Actions

- **FR39:** Spy must choose between guessing location OR voting (not both)
- **FR40:** Spy can attempt to guess the location instead of voting
- **FR41:** Spy can see the list of possible locations when guessing
- **FR42:** Spy can go ALL IN when voting to frame another player (Double Agent)
- **FR43:** Spy loses points if location guess is incorrect; round ends with spy revealed

### Scoring

- **FR44:** System calculates points based on vote accuracy and bet amount
- **FR45:** Correct vote at confidence 1 awards +2 points
- **FR46:** Correct vote at confidence 2 awards +4 points
- **FR47:** Correct vote at confidence 3 (ALL IN) awards +6 points
- **FR48:** Incorrect vote loses the bet amount (-1, -2, or -3 points)
- **FR49:** Spy earns +10 bonus if ALL IN frame succeeds (Double Agent)
- **FR50:** Spy earns points for correct location guess
- **FR51:** Players can see the current leaderboard between rounds
- **FR52:** Players can see final scores at game end

### Multi-Round Game

- **FR53:** System advances to next round after scoring reveal
- **FR54:** System tracks cumulative scores across all rounds
- **FR55:** System declares winner at end of configured rounds

### Content

- **FR56:** System includes Classic location pack with 10 locations
- **FR57:** Each location has 6-8 associated roles
- **FR58:** System randomly selects location from chosen pack each round

### Host Display

- **FR59:** Host display shows game state visible to the whole room
- **FR60:** Host display shows current phase (Lobby/Questioning/Voting/Reveal/Scoring)
- **FR61:** Host display shows player names and connection status
- **FR62:** Host display shows voting results during reveal phase
- **FR63:** Host display shows leaderboard between rounds

## Non-Functional Requirements

### Performance

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **NFR1:** Page Load | Player UI loads in < 2 seconds on 4G | First-time join shouldn't delay game start |
| **NFR2:** WebSocket Latency | Messages delivered in < 100ms on local network | Real-time game state sync |
| **NFR3:** Concurrent Players | System handles 10 players with no perceptible lag | Maximum game size |
| **NFR4:** State Sync | All players see same game state within 500ms of change | Vote reveals must feel simultaneous |
| **NFR5:** Timer Accuracy | Round/voting timers accurate to ±1 second | Fairness across all players |

### Security

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **NFR6:** Role Unpredictability | Spy assignment cannot be predicted or reverse-engineered from client data | Prevent cheating |
| **NFR7:** Role Privacy | Player cannot see another player's role via network inspection | Game integrity |
| **NFR8:** Session Isolation | Players in one game session cannot access another session's data | Multi-session host protection |
| **NFR9:** No Persistent Storage | No sensitive data stored on player devices | Privacy by design |

### Reliability

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **NFR10:** Session Stability | Complete 5-round game session without crash | Core success metric |
| **NFR11:** Disconnect Detection | Player disconnect detected within 30 seconds | Host awareness |
| **NFR12:** Reconnection Window | Player can reconnect within 5 minutes of disconnect | Battery/network recovery |
| **NFR13:** State Preservation | Game state survives individual player disconnects | Game continuity |
| **NFR14:** Graceful Degradation | Game continues with remaining players if one leaves permanently | Don't ruin game night |
| **NFR15:** Host Resilience | Game pauses (not crashes) if host device sleeps briefly | Common scenario |

### Integration

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **NFR16:** HA Compatibility | Works with Home Assistant 2025.11+ | Target platform |
| **NFR17:** HACS Distribution | Installable via HACS with single click | Standard distribution |
| **NFR18:** HA Resource Usage | Minimal CPU/memory impact on HA during idle | Good HA citizen |
| **NFR19:** Browser Compatibility | Functions on Chrome, Safari, Firefox (last 2 years) | Player device support |
| **NFR20:** No External Dependencies | Runs entirely on local network, no cloud services required | Privacy and reliability |

