---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/prd.md'
  - '_bmad-output/architecture.md'
  - '_bmad-output/ux-design-specification.md'
workflowType: 'epics-and-stories'
lastStep: 4
status: 'complete'
completedAt: '2025-12-22'
project_name: 'Spyster'
user_name: 'Markusholzhaeuser'
date: '2025-12-22'
---

# Spyster - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Spyster, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Game Session Management (FR1-FR8)**
- FR1: Host can create a new game session from Home Assistant
- FR2: Host can configure round duration before starting
- FR3: Host can select a location pack before starting
- FR4: Host can view a QR code for players to join
- FR5: Host can see all connected players in a lobby view
- FR6: Host can start the game when 4-10 players have joined
- FR7: Host can end the current game session at any time
- FR8: Host can configure number of rounds per game (fixed count only)

**Player Connection (FR9-FR18)**
- FR9: Player can join a game session by scanning a QR code
- FR10: Player can enter their display name when joining
- FR11: Player can see connection status feedback during join
- FR12: Player can see an error message with network requirements if connection fails
- FR13: Player can retry connection after a failure
- FR14: Player can automatically reconnect if disconnected (within 5 minutes)
- FR15: System detects player disconnect after 30 seconds of no heartbeat
- FR16: Host can see which players are connected vs disconnected
- FR17: Host can remove a disconnected player from the lobby
- FR18: System prevents duplicate sessions for same player name (removes old session)

**Role Assignment (FR19-FR23)**
- FR19: System assigns exactly one player as Spy per round
- FR20: Non-spy players can see the current location and their role
- FR21: Spy player can see the list of possible locations (but not the actual location)
- FR22: All players see a loading state during role assignment (no data leak)
- FR23: System randomly assigns spy each round (same player may be spy multiple times)

**Game Flow - Questioning Phase (FR24-FR30)**
- FR24: Player can view their assigned role at any time during the round
- FR25: System displays which player should ask a question
- FR26: System displays which player should answer
- FR27: Host display shows current questioner and answerer for the room
- FR28: Players can see the round timer counting down
- FR29: Any player can call for a vote during the questioning phase
- FR30: System auto-triggers voting when round timer expires

**Voting & Confidence Betting (FR31-FR38)**
- FR31: Player calling a vote (or timer expiry) triggers voting phase for all players
- FR32: All players can select who they suspect is the Spy
- FR33: All players can set their confidence bet (1, 2, or 3 points)
- FR34: Players see a countdown timer during voting (60 seconds)
- FR35: Players who don't vote before timeout are counted as abstain
- FR36: System reveals all votes and bets simultaneously after voting ends
- FR37: Players can see who voted for whom and at what confidence level
- FR38: System convicts player with plurality of votes (ties = no conviction, round continues)

**Spy Actions (FR39-FR43)**
- FR39: Spy must choose between guessing location OR voting (not both)
- FR40: Spy can attempt to guess the location instead of voting
- FR41: Spy can see the list of possible locations when guessing
- FR42: Spy can go ALL IN when voting to frame another player (Double Agent)
- FR43: Spy loses points if location guess is incorrect; round ends with spy revealed

**Scoring (FR44-FR55)**
- FR44: System calculates points based on vote accuracy and bet amount
- FR45: Correct vote at confidence 1 awards +2 points
- FR46: Correct vote at confidence 2 awards +4 points
- FR47: Correct vote at confidence 3 (ALL IN) awards +6 points
- FR48: Incorrect vote loses the bet amount (-1, -2, or -3 points)
- FR49: Spy earns +10 bonus if ALL IN frame succeeds (Double Agent)
- FR50: Spy earns points for correct location guess
- FR51: Players can see the current leaderboard between rounds
- FR52: Players can see final scores at game end
- FR53: System advances to next round after scoring reveal
- FR54: System tracks cumulative scores across all rounds
- FR55: System declares winner at end of configured rounds

**Content (FR56-FR58)**
- FR56: System includes Classic location pack with 10 locations
- FR57: Each location has 6-8 associated roles
- FR58: System randomly selects location from chosen pack each round

**Host Display (FR59-FR63)**
- FR59: Host display shows game state visible to the whole room
- FR60: Host display shows current phase (Lobby/Questioning/Voting/Reveal/Scoring)
- FR61: Host display shows player names and connection status
- FR62: Host display shows voting results during reveal phase
- FR63: Host display shows leaderboard between rounds

### Non-Functional Requirements

**Performance (NFR1-NFR5)**
- NFR1: Page Load - Player UI loads in < 2 seconds on 4G
- NFR2: WebSocket Latency - Messages delivered in < 100ms on local network
- NFR3: Concurrent Players - System handles 10 players with no perceptible lag
- NFR4: State Sync - All players see same game state within 500ms of change
- NFR5: Timer Accuracy - Round/voting timers accurate to ±1 second

**Security (NFR6-NFR9)**
- NFR6: Role Unpredictability - Spy assignment cannot be predicted or reverse-engineered from client data
- NFR7: Role Privacy - Player cannot see another player's role via network inspection
- NFR8: Session Isolation - Players in one game session cannot access another session's data
- NFR9: No Persistent Storage - No sensitive data stored on player devices

**Reliability (NFR10-NFR15)**
- NFR10: Session Stability - Complete 5-round game session without crash
- NFR11: Disconnect Detection - Player disconnect detected within 30 seconds
- NFR12: Reconnection Window - Player can reconnect within 5 minutes of disconnect
- NFR13: State Preservation - Game state survives individual player disconnects
- NFR14: Graceful Degradation - Game continues with remaining players if one leaves permanently
- NFR15: Host Resilience - Game pauses (not crashes) if host device sleeps briefly

**Integration (NFR16-NFR20)**
- NFR16: HA Compatibility - Works with Home Assistant 2025.11+
- NFR17: HACS Distribution - Installable via HACS with single click
- NFR18: HA Resource Usage - Minimal CPU/memory impact on HA during idle
- NFR19: Browser Compatibility - Functions on Chrome, Safari, Firefox (last 2 years)
- NFR20: No External Dependencies - Runs entirely on local network, no cloud services required

### Additional Requirements

**From Architecture - Starter Template:**
- ARCH-1: Use Beatify Blueprint pattern for project structure
- ARCH-2: Initialize with: `mkdir -p custom_components/spyster/{game,server,www/{js,css},content,translations}`

**From Architecture - Phase State Machine:**
- ARCH-3: Implement GamePhase enum: LOBBY, ROLES, QUESTIONING, VOTE, REVEAL, SCORING, END, PAUSED
- ARCH-4: Phase transitions must follow defined flow (no skipping phases)
- ARCH-5: Any phase → PAUSED on host disconnect; PAUSED → Previous on host reconnect

**From Architecture - Security:**
- ARCH-6: Spy assignment must use `secrets.choice()` (CSPRNG)
- ARCH-7: Per-player state filtering via `get_state(for_player=player_name)`
- ARCH-8: Never broadcast same state to all players (role privacy)

**From Architecture - Timer System:**
- ARCH-9: Named timer dictionary pattern: `self._timers: dict[str, asyncio.Task]`
- ARCH-10: Timer types: round (configurable), vote (60s), role_display (5s), reveal_delay (3s), disconnect_grace (30s), reconnect_window (5min)
- ARCH-11: Cancel existing timer before starting new one with same name

**From Architecture - WebSocket Protocol:**
- ARCH-12: Message format: `{"type": "...", ...payload}` with snake_case fields
- ARCH-13: Error responses must include `code` + `message`
- ARCH-14: Broadcast state after every state mutation

**From Architecture - Code Organization:**
- ARCH-15: Constants in `const.py` - never hardcode error codes, timeouts, or config values
- ARCH-16: Logging format: `_LOGGER.info("Event: %s (context: %d)", name, value)`
- ARCH-17: Phase guards on all state-mutating methods

**From Architecture - Scoring Module:**
- ARCH-18: Separate `game/scoring.py` with pure functions
- ARCH-19: Return pattern for actions: `(success: bool, error_code: str | None)`

**From UX Design - Visual System:**
- UX-1: Fork Beatify CSS tokens (dark neon theme, #0a0a12 background)
- UX-2: Accent colors: Pink (#ff2d6a) primary, Cyan (#00f5ff) secondary
- UX-3: ALL IN special treatment: Gold (#ffd700) with stronger glow
- UX-4: Minimum touch targets: 44px (48px for primary, 56px for bet buttons)

**From UX Design - Components:**
- UX-5: Player cards with states: default, hover, selected, reveal, disabled
- UX-6: Bet buttons: 1 / 2 / ALL IN with radio group behavior
- UX-7: Submission tracker: "4/7 voted" pattern with real-time updates
- UX-8: Reveal sequence: votes-intro → votes-flip → bets-intro → bets-show → verdict (~8-12s)

**From UX Design - Spy Parity:**
- UX-9: Spy and non-spy screens must have identical layouts (prevent visual tells)
- UX-10: Role display dimensions must be identical for spy vs non-spy

**From UX Design - Accessibility:**
- UX-11: WCAG 2.1 AA compliance (4.5:1 contrast minimum)
- UX-12: ARIA roles on interactive elements (button, radiogroup, timer, progressbar)
- UX-13: Respect `prefers-reduced-motion`
- UX-14: Keyboard navigation support (arrows, Enter/Space, Tab order)

**From UX Design - Responsive:**
- UX-15: Mobile-first player view (320-428px)
- UX-16: Host view tablet/TV optimized (768px+, 2-3x scale)

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Host creates game session |
| FR2 | Epic 3 | Configure round duration |
| FR3 | Epic 3 | Select location pack |
| FR4 | Epic 1 | QR code for joining |
| FR5 | Epic 1 | Lobby view |
| FR6 | Epic 3 | Start game (4-10 players) |
| FR7 | Epic 6 | End game anytime |
| FR8 | Epic 3 | Configure round count |
| FR9 | Epic 2 | Join via QR scan |
| FR10 | Epic 2 | Enter display name |
| FR11 | Epic 2 | Connection status feedback |
| FR12 | Epic 2 | Error message with network requirements |
| FR13 | Epic 2 | Retry connection |
| FR14 | Epic 2 | Auto-reconnect (5 min window) |
| FR15 | Epic 2 | Disconnect detection (30s heartbeat) |
| FR16 | Epic 2 | Host sees connected vs disconnected |
| FR17 | Epic 2 | Host removes disconnected player |
| FR18 | Epic 2 | Prevent duplicate sessions |
| FR19 | Epic 3 | Assign exactly one spy |
| FR20 | Epic 3 | Non-spy sees location + role |
| FR21 | Epic 3 | Spy sees location list |
| FR22 | Epic 3 | Loading state during assignment |
| FR23 | Epic 3 | Random spy each round |
| FR24 | Epic 4 | View assigned role anytime |
| FR25 | Epic 4 | Display questioner |
| FR26 | Epic 4 | Display answerer |
| FR27 | Epic 4 | Host shows Q&A pair |
| FR28 | Epic 4 | Round timer countdown |
| FR29 | Epic 4 | Any player calls vote |
| FR30 | Epic 4 | Auto-vote on timer expiry |
| FR31 | Epic 5 | Vote triggers voting phase |
| FR32 | Epic 5 | Select spy suspect |
| FR33 | Epic 5 | Set confidence bet (1-3) |
| FR34 | Epic 5 | Vote timer (60s) |
| FR35 | Epic 5 | Timeout = abstain |
| FR36 | Epic 5 | Simultaneous reveal |
| FR37 | Epic 5 | See votes and confidence |
| FR38 | Epic 5 | Plurality convicts (ties = no conviction) |
| FR39 | Epic 5 | Spy chooses guess OR vote |
| FR40 | Epic 5 | Spy guesses location |
| FR41 | Epic 5 | Spy sees location list for guess |
| FR42 | Epic 5 | Spy ALL IN = Double Agent |
| FR43 | Epic 5 | Wrong guess = spy revealed |
| FR44 | Epic 6 | Points from vote + bet |
| FR45 | Epic 6 | Confidence 1 = +2 points |
| FR46 | Epic 6 | Confidence 2 = +4 points |
| FR47 | Epic 6 | Confidence 3 = +6 points |
| FR48 | Epic 6 | Wrong vote loses bet |
| FR49 | Epic 6 | Double Agent +10 bonus |
| FR50 | Epic 6 | Spy guess points |
| FR51 | Epic 6 | Leaderboard between rounds |
| FR52 | Epic 6 | Final scores at end |
| FR53 | Epic 6 | Advance to next round |
| FR54 | Epic 6 | Cumulative scores |
| FR55 | Epic 6 | Declare winner |
| FR56 | Epic 8 | Classic pack (10 locations) |
| FR57 | Epic 8 | 6-8 roles per location |
| FR58 | Epic 8 | Random location selection |
| FR59 | Epic 7 | Host display game state |
| FR60 | Epic 7 | Host shows current phase |
| FR61 | Epic 7 | Host shows player status |
| FR62 | Epic 7 | Host shows vote results |
| FR63 | Epic 7 | Host shows leaderboard |

## Epic List

### Epic 1: Project Foundation & Game Session
Host can create a game session in Home Assistant and see a working lobby with QR code.

**FRs covered:** FR1, FR4, FR5
**Additional:** ARCH-1, ARCH-2, ARCH-3 (Beatify pattern, project structure, phase enum)

### Epic 2: Player Join & Connection
Players can join via QR scan and the system handles connections reliably with reconnection support.

**FRs covered:** FR9-FR18
**NFRs:** NFR11-NFR14 (disconnect detection, reconnection, state preservation)
**Additional:** ARCH-9, ARCH-10 (timer system for disconnect grace)

### Epic 3: Game Configuration & Role Assignment
Host can configure and start the game; players receive their roles with spy privacy maintained.

**FRs covered:** FR2, FR3, FR6, FR8, FR19-FR23
**Additional:** ARCH-6, ARCH-7, ARCH-8 (CSPRNG, per-player filtering, role privacy)
**UX:** UX-9, UX-10 (spy parity)

### Epic 4: Questioning Phase
Players engage in the Q&A phase with visible timer and can call votes.

**FRs covered:** FR24-FR30
**Additional:** ARCH-10 (round timer), ARCH-14 (broadcast after state change)

### Epic 5: Voting & Confidence Betting
Players vote with confidence bets, spy can guess location or attempt Double Agent play.

**FRs covered:** FR31-FR43
**UX:** UX-5, UX-6, UX-7, UX-8 (player cards, bet buttons, tracker, reveal sequence)
**Additional:** UX-3 (ALL IN gold treatment)

### Epic 6: Scoring & Game Progression
Points calculated correctly, leaderboard updates, game progresses through rounds to winner.

**FRs covered:** FR7, FR44-FR55
**Additional:** ARCH-18, ARCH-19 (scoring module, pure functions)

### Epic 7: Host Display Experience
TV/tablet shows game state visible to the whole room with phase transitions.

**FRs covered:** FR59-FR63
**UX:** UX-15, UX-16 (responsive, host scale)

### Epic 8: Content & Polish
Complete game with Classic location pack and accessibility compliance.

**FRs covered:** FR56-FR58
**NFRs:** NFR19 (browser compatibility)
**UX:** UX-11, UX-12, UX-13, UX-14 (WCAG AA, ARIA, motion, keyboard)

---

## Epic 1: Project Foundation & Game Session

Host can create a game session in Home Assistant and see a working lobby with QR code.

### Story 1.1: Initialize Project Structure and HA Integration

As a **developer**,
I want **the Spyster custom component initialized with proper structure**,
So that **I have a working foundation following Beatify patterns**.

**Acceptance Criteria:**

**Given** a fresh Home Assistant installation
**When** the Spyster integration is loaded
**Then** the integration registers successfully without errors
**And** `hass.data["spyster"]` is initialized for state storage
**And** the directory structure follows Beatify pattern

**Given** the manifest.json is configured
**When** HACS scans for integrations
**Then** Spyster appears as installable with correct metadata

---

### Story 1.2: Create Game Session with Lobby Phase

As a **host**,
I want **to create a new game session**,
So that **I can start hosting a Spyster game**.

**Acceptance Criteria:**

**Given** Spyster integration is loaded
**When** the host navigates to the Spyster panel
**Then** a new game session is created with phase=LOBBY

**Given** a game session exists in LOBBY phase
**When** the host views the game page
**Then** the lobby is displayed showing "Waiting for players..."
**And** the game phase is clearly indicated

**Given** GameState class is initialized
**When** phase transitions are attempted
**Then** only valid transitions per the phase state machine are allowed

---

### Story 1.3: Generate and Display QR Code

As a **host**,
I want **to see a QR code for players to scan**,
So that **guests can easily join the game on their phones**.

**Acceptance Criteria:**

**Given** a game session is in LOBBY phase
**When** the host display is rendered
**Then** a QR code is prominently displayed encoding the player join URL

**Given** the QR code is scanned
**When** a player's phone camera reads it
**Then** the browser opens to the correct player join URL

**Given** the game is running on local network
**When** the QR URL is generated
**Then** it uses the HA instance's local IP/hostname accessible to guests

---

### Story 1.4: Implement Basic Player and Host Views

As a **user (host or player)**,
I want **dedicated UI views served by the integration**,
So that **hosts see the room display and players see their phone interface**.

**Acceptance Criteria:**

**Given** a user navigates to `/api/spyster/host`
**When** the page loads
**Then** the host display HTML is served with dark neon styling

**Given** a user navigates to `/api/spyster/player`
**When** the page loads
**Then** the player UI HTML is served (mobile-optimized, dark neon)

**Given** static assets exist in `www/`
**When** CSS/JS files are requested
**Then** they are served correctly via `/api/spyster/static/*`

**Given** the views are loaded
**When** inspecting the page
**Then** Beatify-forked CSS tokens are applied (dark bg, proper colors)

---

## Epic 2: Player Join & Connection

Players can join via QR scan and the system handles connections reliably with reconnection support.

### Story 2.1: WebSocket Connection Handler

As a **player**,
I want **a real-time connection to the game server**,
So that **I receive game updates instantly**.

**Acceptance Criteria:**

**Given** a player navigates to the player URL
**When** the page loads
**Then** a WebSocket connection is established to `/api/spyster/ws`

**Given** the WebSocket handler receives a connection
**When** the connection is established
**Then** the connection is tracked in the server's connection pool
**And** the connection receives a welcome message

**Given** a WebSocket message is received
**When** the message is malformed JSON
**Then** an error response is sent with code `ERR_INVALID_MESSAGE`

---

### Story 2.2: Player Join Flow

As a **player**,
I want **to enter my name and join the game**,
So that **I appear in the lobby and can participate**.

**Acceptance Criteria:**

**Given** a player opens the join page
**When** the page loads
**Then** a name entry field is displayed with a "Join" button

**Given** a player enters a valid name (1-20 characters)
**When** they tap "Join"
**Then** a `join` message is sent via WebSocket
**And** their name appears in the lobby on both player and host displays

**Given** a player enters a name already in use
**When** they tap "Join"
**Then** they receive error `ERR_NAME_TAKEN` with message "That name is already taken"

**Given** the lobby already has 10 players
**When** a new player tries to join
**Then** they receive error `ERR_GAME_FULL`

---

### Story 2.3: Player Session Management

As a **system**,
I want **to track player sessions with URL tokens**,
So that **players can reconnect without re-entering their name**.

**Acceptance Criteria:**

**Given** a player successfully joins
**When** the join is confirmed
**Then** a session token is generated and included in the URL
**And** the PlayerSession object is created with `connected=True`

**Given** a player with an existing session token
**When** they reconnect with the same token
**Then** they are restored to their previous session automatically

**Given** a player tries to join with an in-use name
**When** a valid session exists for that name
**Then** the old session is replaced (prevents duplicate sessions per FR18)

---

### Story 2.4: Disconnect Detection

As a **host**,
I want **to see when players disconnect**,
So that **I know who is still active in the game**.

**Acceptance Criteria:**

**Given** a player is connected
**When** no heartbeat is received for 30 seconds
**Then** the player is marked as "disconnected" (not removed)
**And** the host display shows a yellow indicator next to their name

**Given** a WebSocket connection closes
**When** the close event is detected
**Then** a disconnect grace timer starts (30 seconds to mark disconnected)

**Given** the disconnect grace timer fires
**When** the player hasn't reconnected
**Then** their status changes to "disconnected"
**And** all clients receive updated state via broadcast

---

### Story 2.5: Player Reconnection

As a **player**,
I want **to automatically reconnect if my connection drops**,
So that **I don't lose my place in the game**.

**Acceptance Criteria:**

**Given** a player is marked "disconnected"
**When** they reopen the browser with their session token (within 5 minutes)
**Then** they are automatically restored to their session
**And** their status changes back to "connected"
**And** they see the current game state

**Given** a player has been disconnected for over 5 minutes
**When** they try to reconnect
**Then** their session is invalid
**And** they must rejoin as a new player (if in lobby phase)

**Given** a player reconnects during an active round
**When** the session is restored
**Then** they see their role and current phase
**And** game continues without interruption

---

### Story 2.6: Host Lobby Management

As a **host**,
I want **to manage the lobby and remove inactive players**,
So that **I can start the game without waiting for ghosts**.

**Acceptance Criteria:**

**Given** a player has been "disconnected" for 60+ seconds
**When** the host views the lobby
**Then** a "Remove" button appears next to that player

**Given** the host taps "Remove" on a disconnected player
**When** the action is confirmed
**Then** the player is removed from the game
**And** the lobby updates on all connected clients

**Given** the host tries to remove a connected player
**When** they attempt the action
**Then** the action is blocked (only disconnected players can be removed)

**Given** the host display shows the lobby
**When** players join/leave/disconnect
**Then** the player list updates in real-time with status indicators

---

## Epic 3: Game Configuration & Role Assignment

Host can configure and start the game; players receive their roles with spy privacy maintained.

### Story 3.1: Game Configuration UI

As a **host**,
I want **to configure game settings before starting**,
So that **I can customize the game for my group**.

**Acceptance Criteria:**

**Given** the host is viewing the lobby
**When** the configuration options are displayed
**Then** the host can set round duration (default 7 minutes)
**And** the host can set number of rounds (default 5)
**And** the host can select a location pack (Classic by default)

**Given** the host changes a configuration value
**When** the value is updated
**Then** the new value is stored in GameState
**And** the configuration is displayed to confirm the setting

**Given** configuration values are set
**When** the game starts
**Then** the configured values are used for gameplay

---

### Story 3.2: Start Game with Player Validation

As a **host**,
I want **to start the game when enough players have joined**,
So that **we can begin playing**.

**Acceptance Criteria:**

**Given** fewer than 4 players are in the lobby
**When** the host tries to start
**Then** the START button is disabled
**And** a message shows "Need at least 4 players"

**Given** 4-10 players are in the lobby
**When** the host taps START
**Then** an `admin` message with `action: start_game` is sent
**And** the game transitions from LOBBY to ROLES phase

**Given** more than 10 players are in the lobby
**When** this state is reached
**Then** it should not be possible (blocked at join per FR)

**Given** a player disconnects while START is pressed
**When** the player count drops below 4
**Then** the start is aborted with an error message

---

### Story 3.3: Spy Assignment

As a **system**,
I want **to randomly assign exactly one spy per round**,
So that **the game has a fair and unpredictable spy selection**.

**Acceptance Criteria:**

**Given** the game transitions to ROLES phase
**When** spy assignment occurs
**Then** exactly one player is marked as spy using `secrets.choice()` (CSPRNG)
**And** all other players are marked as non-spy

**Given** a new round starts
**When** spy assignment occurs
**Then** a new random player is selected (may be same player as previous round per FR23)

**Given** the spy assignment is complete
**When** the assignment is stored
**Then** the spy identity is stored only in server-side GameState
**And** no client-visible data reveals who the spy is

---

### Story 3.4: Role Distribution with Per-Player Filtering

As a **system**,
I want **to send personalized role information to each player**,
So that **players only see their own role (security requirement)**.

**Acceptance Criteria:**

**Given** roles are assigned
**When** state is broadcast to players
**Then** each player receives a personalized `role` message via `get_state(for_player=name)`

**Given** a non-spy player receives their role
**When** the role message arrives
**Then** they see the location name and their assigned role
**And** they do NOT see other players' roles

**Given** the spy receives their role
**When** the role message arrives
**Then** they see "YOU ARE THE SPY"
**And** they see the list of possible locations (not the actual location)
**And** they do NOT see the actual location

**Given** network traffic is inspected
**When** WebSocket messages are examined
**Then** no player can see another player's role data

---

### Story 3.5: Role Display UI with Spy Parity

As a **player**,
I want **to see my role clearly on my phone**,
So that **I know my role and can play accordingly**.

**Acceptance Criteria:**

**Given** a non-spy player is in ROLES phase
**When** their screen displays the role
**Then** they see: location name prominently, their role, and a list of other possible roles at this location

**Given** the spy is in ROLES phase
**When** their screen displays the role
**Then** they see: "YOU ARE THE SPY" prominently, and the list of possible locations

**Given** spy and non-spy screens are compared
**When** viewed side-by-side
**Then** the layouts have identical dimensions and structure (spy parity per UX-9, UX-10)
**And** a casual glance cannot distinguish spy from non-spy

**Given** all players see "Assigning roles..." loading state
**When** the transition to ROLES phase occurs
**Then** no partial data or flicker is visible (prevents data leak per FR22)

---

## Epic 4: Questioning Phase

Players engage in the Q&A phase with visible timer and can call votes.

### Story 4.1: Transition to Questioning Phase

As a **system**,
I want **to transition from ROLES to QUESTIONING after role display**,
So that **the game proceeds to active gameplay**.

**Acceptance Criteria:**

**Given** all players have received their role information
**When** the role display timer expires (5 seconds)
**Then** the phase transitions from ROLES to QUESTIONING
**And** all players receive updated state via broadcast

**Given** the phase is QUESTIONING
**When** state is broadcast
**Then** all players see the questioning phase UI
**And** the round timer begins counting down

---

### Story 4.2: Round Timer with Countdown

As a **player**,
I want **to see the round timer counting down**,
So that **I know how much time remains before voting**.

**Acceptance Criteria:**

**Given** the game is in QUESTIONING phase
**When** the phase begins
**Then** a named timer `round` starts with the configured duration

**Given** the round timer is running
**When** players view their screens
**Then** the remaining time is displayed prominently (large, visible)
**And** the timer updates in real-time (synced across all clients)

**Given** the round timer reaches zero
**When** the timer expires
**Then** the voting phase is automatically triggered
**And** a `vote` transition occurs without player action (per FR30)

**Given** a timer is displayed
**When** the accuracy is measured
**Then** the timer is accurate to ±1 second across all clients (per NFR5)

---

### Story 4.3: Questioner/Answerer Turn Management

As a **player**,
I want **to know whose turn it is to ask and answer**,
So that **the questioning flows smoothly**.

**Acceptance Criteria:**

**Given** the game is in QUESTIONING phase
**When** a turn begins
**Then** the system designates a questioner and an answerer
**And** both player and host displays show "Player A asks Player B"

**Given** the current questioner
**When** they complete their question verbally (no UI action needed)
**Then** the answerer responds verbally
**And** turns rotate naturally (no enforced turn advancement in MVP)

**Given** the host display
**When** showing Q&A state
**Then** the current questioner and answerer names are prominently visible to the room

---

### Story 4.4: Player Role View During Questioning

As a **player**,
I want **to view my role at any time during the round**,
So that **I can remember my role while asking/answering questions**.

**Acceptance Criteria:**

**Given** a non-spy player is in QUESTIONING phase
**When** they view their screen
**Then** their role and location are visible (or easily accessible)
**And** the round timer is always visible

**Given** the spy is in QUESTIONING phase
**When** they view their screen
**Then** the location list is visible (or easily accessible)
**And** the round timer is always visible
**And** the layout matches non-spy layout (spy parity)

**Given** a player needs to reference their role
**When** during active questioning
**Then** the information is glanceable without disrupting social interaction

---

### Story 4.5: Call Vote Functionality

As a **player**,
I want **to call for a vote at any time during questioning**,
So that **I can accuse someone when I'm suspicious**.

**Acceptance Criteria:**

**Given** the game is in QUESTIONING phase
**When** a player taps "Call Vote"
**Then** a vote message is sent to the server
**And** the game transitions from QUESTIONING to VOTE phase

**Given** any connected player
**When** they call a vote
**Then** the vote triggers for ALL players simultaneously
**And** all players enter the voting phase together

**Given** a vote is called
**When** the transition occurs
**Then** the round timer is cancelled
**And** the vote timer (60 seconds) begins

**Given** multiple players try to call vote simultaneously
**When** the server receives multiple requests
**Then** only the first is processed
**And** subsequent requests are ignored (already in VOTE phase)

---

## Epic 5: Voting & Confidence Betting

Players vote with confidence bets, spy can guess location or attempt Double Agent play.

### Story 5.1: Voting Phase UI with Player Cards

As a **player**,
I want **to select who I think is the spy**,
So that **I can vote against them**.

**Acceptance Criteria:**

**Given** the game transitions to VOTE phase
**When** a player views their screen
**Then** a grid of player cards is displayed (excluding themselves)
**And** each card shows the player's name
**And** cards are tappable with clear touch targets (48px+)

**Given** a player taps a player card
**When** the card is selected
**Then** the card shows a selected state (visual highlight)
**And** only one player can be selected at a time

**Given** a player wants to change their selection
**When** they tap a different card
**Then** the previous selection is cleared
**And** the new card is selected

---

### Story 5.2: Confidence Betting Selection

As a **player**,
I want **to set my confidence level (1, 2, or ALL IN)**,
So that **I can wager points on my vote being correct**.

**Acceptance Criteria:**

**Given** a player is in the voting UI
**When** viewing the bet selection
**Then** three options are displayed: 1, 2, and ALL IN (3)
**And** each option shows risk/reward (+2/-1, +4/-2, +6/-3)

**Given** the ALL IN option
**When** displayed
**Then** it has special gold styling with glow effect (UX-3)
**And** touch target is larger (56px per UX spec)

**Given** a player selects a confidence level
**When** the selection is made
**Then** the button shows selected state
**And** the selection is stored locally until submission

**Given** no confidence is explicitly selected
**When** a player submits their vote
**Then** confidence defaults to 1

---

### Story 5.3: Vote Submission and Tracking

As a **player**,
I want **to lock in my vote and see who else has voted**,
So that **I know when everyone is ready for the reveal**.

**Acceptance Criteria:**

**Given** a player has selected a target and confidence
**When** they tap "Lock It In"
**Then** a `vote` message is sent with `{target, confidence}`
**And** the button transforms to "LOCKED ✓" (disabled)
**And** the player cannot change their vote

**Given** votes are being submitted
**When** the server receives a vote
**Then** all clients receive updated submission count
**And** the tracker shows "4/7 voted" format

**Given** a player has already voted
**When** they try to vote again
**Then** they receive error `ERR_ALREADY_VOTED`

---

### Story 5.4: Spy Location Guess Option

As a **spy**,
I want **to guess the location instead of voting**,
So that **I can win by deduction rather than framing someone**.

**Acceptance Criteria:**

**Given** the spy is in VOTE phase
**When** they view their screen
**Then** they see two options: "Vote" or "Guess Location"

**Given** the spy taps "Guess Location"
**When** the option is selected
**Then** a list of possible locations is displayed
**And** the spy can select one location

**Given** the spy selects a location
**When** they tap "Confirm Guess"
**Then** a `spy_guess` message is sent with `{location_id}`
**And** the spy cannot vote (mutually exclusive per FR39)

**Given** a non-spy player
**When** viewing the vote screen
**Then** the "Guess Location" option is NOT visible

---

### Story 5.5: Vote Timer and Abstain Handling

As a **system**,
I want **to enforce a 60-second voting window**,
So that **the game progresses even if players are slow**.

**Acceptance Criteria:**

**Given** the VOTE phase begins
**When** the timer starts
**Then** a 60-second countdown is displayed prominently

**Given** the vote timer expires
**When** not all players have voted
**Then** non-voters are counted as abstain (no bet placed)
**And** the game transitions to REVEAL phase

**Given** all players have submitted votes
**When** the last vote is received
**Then** the vote timer is cancelled early
**And** the game immediately transitions to REVEAL phase

**Given** a player abstains (timeout)
**When** results are calculated
**Then** they have no vote recorded and lose no points

---

### Story 5.6: Vote and Bet Reveal Sequence

As a **player**,
I want **to experience a dramatic reveal of all votes and bets**,
So that **the game creates memorable tension moments**.

**Acceptance Criteria:**

**Given** the game transitions to REVEAL phase
**When** the reveal sequence begins
**Then** a staged animation plays (8-12 seconds total per UX-8)

**Given** the reveal sequence
**When** step 1 occurs
**Then** "Votes are in..." text displays with 1-second pause

**Given** the reveal sequence
**When** step 2 occurs
**Then** vote targets flip/reveal one by one (staggered ~0.5s each)
**And** players see who voted for whom

**Given** the reveal sequence
**When** step 3 occurs
**Then** "Now the bets..." text displays with 1-second pause (stomach-drop moment)

**Given** the reveal sequence
**When** step 4 occurs
**Then** all confidence bets reveal simultaneously
**And** bet amounts (1/2/3) are visible next to each vote
**And** ALL IN bets have gold highlight

---

### Story 5.7: Conviction Logic

As a **system**,
I want **to determine if the spy is convicted based on votes**,
So that **the round resolves correctly**.

**Acceptance Criteria:**

**Given** all votes are revealed
**When** calculating conviction
**Then** the player with plurality of votes is convicted
**And** the convicted player is highlighted

**Given** a tie occurs (multiple players have equal highest votes)
**When** calculating conviction
**Then** no one is convicted
**And** the round continues with a message "No conviction - tie!"

**Given** the spy is convicted
**When** the verdict is shown
**Then** "SPY CAUGHT!" is displayed
**And** the spy's identity is revealed to all

**Given** an innocent player is convicted
**When** the verdict is shown
**Then** "INNOCENT!" is displayed
**And** the actual spy remains hidden (round ends, spy wins)

**Given** the spy successfully guessed the location
**When** the verdict is shown
**Then** "SPY WINS - Location Guessed!" is displayed

---

## Epic 6: Scoring & Game Progression

Points calculated correctly, leaderboard updates, game progresses through rounds to winner.

### Story 6.1: Scoring Module with Pure Functions

As a **developer**,
I want **a dedicated scoring module with pure functions**,
So that **scoring logic is testable and maintainable**.

**Acceptance Criteria:**

**Given** the project structure
**When** `game/scoring.py` is created
**Then** it contains pure functions for all scoring calculations
**And** functions have no side effects (per ARCH-19)

**Given** a scoring function
**When** called with the same inputs
**Then** it always returns the same output
**And** it does not modify any external state

**Given** the scoring module
**When** imported
**Then** functions are available: `calculate_vote_score()`, `calculate_spy_frame_bonus()`, `calculate_spy_guess_score()`

---

### Story 6.2: Vote Scoring Calculation

As a **player**,
I want **to receive points based on my vote accuracy and confidence**,
So that **I'm rewarded for correct deduction and risk-taking**.

**Acceptance Criteria:**

**Given** a player voted correctly (voted for the actual spy)
**When** confidence was 1
**Then** they receive +2 points (per FR45)

**Given** a player voted correctly
**When** confidence was 2
**Then** they receive +4 points (per FR46)

**Given** a player voted correctly
**When** confidence was 3 (ALL IN)
**Then** they receive +6 points (per FR47)

**Given** a player voted incorrectly
**When** confidence was 1
**Then** they lose -1 point (per FR48)

**Given** a player voted incorrectly
**When** confidence was 2
**Then** they lose -2 points

**Given** a player voted incorrectly
**When** confidence was 3 (ALL IN)
**Then** they lose -3 points

---

### Story 6.3: Double Agent Bonus

As a **spy**,
I want **to earn bonus points for successfully framing an innocent**,
So that **I'm rewarded for bold deceptive plays**.

**Acceptance Criteria:**

**Given** the spy voted for an innocent player
**When** that innocent player was convicted (plurality vote)
**And** the spy's confidence was 3 (ALL IN)
**Then** the spy receives +10 bonus points (per FR49)

**Given** the spy voted for an innocent player
**When** that innocent was NOT convicted (tie or different player convicted)
**Then** no Double Agent bonus is awarded

**Given** the spy voted ALL IN but for the wrong target
**When** someone else was convicted
**Then** the spy loses -3 points (normal incorrect vote penalty)

**Given** the Double Agent bonus is awarded
**When** displayed
**Then** special "DOUBLE AGENT!" celebration shows

---

### Story 6.4: Spy Location Guess Scoring

As a **spy**,
I want **to earn points for correctly guessing the location**,
So that **I have an alternative win condition**.

**Acceptance Criteria:**

**Given** the spy guessed the location
**When** the guess was correct
**Then** the spy receives points (per FR50)
**And** the round ends with spy victory

**Given** the spy guessed the location
**When** the guess was incorrect
**Then** the spy is revealed (per FR43)
**And** the round ends with spy losing
**And** other players don't score vote points (voting cancelled)

---

### Story 6.5: Leaderboard Display

As a **player**,
I want **to see the current standings between rounds**,
So that **I know how I'm doing compared to others**.

**Acceptance Criteria:**

**Given** the SCORING phase begins
**When** points are calculated
**Then** cumulative scores are updated for all players (per FR54)

**Given** the leaderboard is displayed
**When** between rounds
**Then** all players are listed with their total scores
**And** players are sorted by score (highest first)
**And** point changes from last round are highlighted (+X / -Y)

**Given** a player views their phone
**When** in SCORING phase
**Then** they see their personal score change prominently
**And** they see the full leaderboard

---

### Story 6.6: Round Progression

As a **system**,
I want **to advance through rounds until the configured count**,
So that **the game plays multiple rounds as configured**.

**Acceptance Criteria:**

**Given** the SCORING phase completes
**When** rounds remaining > 0
**Then** the game transitions to ROLES phase for next round (per FR53)
**And** new spy is assigned
**And** new location is selected

**Given** round transitions occur
**When** displayed to players
**Then** "ROUND 2 of 5" indicator is visible

**Given** the configured number of rounds is reached
**When** scoring completes
**Then** the game transitions to END phase (not another round)

---

### Story 6.7: Game End and Winner Declaration

As a **player**,
I want **to see final results and the winner**,
So that **the game has a satisfying conclusion**.

**Acceptance Criteria:**

**Given** all rounds are complete
**When** the game transitions to END phase
**Then** final scores are displayed (per FR52)
**And** the winner is declared (highest score per FR55)

**Given** a tie for first place
**When** calculating winner
**Then** all tied players are declared co-winners

**Given** the host
**When** viewing END phase
**Then** they see a "Play Again" button to start a new game
**And** an "End Session" button to return to lobby

**Given** the host taps "End Game" at any time (FR7)
**When** the action is confirmed
**Then** the game immediately transitions to END phase
**And** current scores become final scores

---

## Epic 7: Host Display Experience

TV/tablet shows game state visible to the whole room with phase transitions.

### Story 7.1: Host Display Layout

As a **host**,
I want **a TV-optimized display for the room**,
So that **all players can see the game state from their seats**.

**Acceptance Criteria:**

**Given** the host display is viewed on a large screen
**When** the page loads
**Then** content is scaled 2-3x larger than player displays (per UX-16)
**And** text is readable from across the room

**Given** the host display
**When** in any phase
**Then** the layout uses landscape orientation
**And** key information is centered and prominent

**Given** responsive breakpoints
**When** viewport is 768px+
**Then** host layout activates with larger typography
**And** timer displays at 96-144px font size

---

### Story 7.2: Phase Indicators

As a **viewer (anyone in the room)**,
I want **to clearly see the current game phase**,
So that **I know what's happening in the game**.

**Acceptance Criteria:**

**Given** the host display
**When** in LOBBY phase
**Then** "LOBBY" indicator is visible with player count

**Given** the host display
**When** in QUESTIONING phase
**Then** "QUESTIONING" indicator shows with round number
**And** the timer is prominently displayed

**Given** the host display
**When** in VOTE phase
**Then** "VOTING" indicator shows with submission count

**Given** the host display
**When** in REVEAL phase
**Then** "REVEAL" indicator shows during the sequence

**Given** the host display
**When** in SCORING phase
**Then** "RESULTS" indicator shows with leaderboard

**Given** phase transitions
**When** a phase changes
**Then** a transition marker animation plays (e.g., "ROUND 1", "VOTE CALLED")

---

### Story 7.3: Player Status Display

As a **host**,
I want **to see all players and their connection status**,
So that **I know who's ready to play**.

**Acceptance Criteria:**

**Given** the host display in LOBBY
**When** players are connected
**Then** all player names are visible in a grid/list
**And** connected players show green indicator
**And** disconnected players show yellow indicator

**Given** players join or leave
**When** the state changes
**Then** the player list updates in real-time

**Given** the host display during gameplay
**When** showing player list
**Then** compact view shows names with connection status
**And** list doesn't dominate the screen (secondary to game state)

---

### Story 7.4: Vote Results Visualization

As a **viewer**,
I want **to see voting results on the big screen**,
So that **the whole room experiences the reveal together**.

**Acceptance Criteria:**

**Given** the host display in REVEAL phase
**When** votes are being shown
**Then** each player's vote target is displayed
**And** confidence levels are visible (1/2/ALL IN with gold)

**Given** the reveal sequence on host display
**When** the staged reveal plays
**Then** it matches the timing of player displays
**And** room can watch votes flip one by one

**Given** the conviction result
**When** displayed
**Then** "SPY CAUGHT!" or "INNOCENT!" is shown large
**And** the actual spy is revealed (if caught)

**Given** voting in progress
**When** submission tracker updates
**Then** host display shows "4/7 voted" prominently

---

### Story 7.5: Host Admin Controls

As a **host**,
I want **admin controls to manage the game**,
So that **I can pause, skip, or end as needed**.

**Acceptance Criteria:**

**Given** the host display
**When** viewing the game
**Then** a floating admin bar is visible (fixed position)
**And** controls don't obstruct main game display

**Given** the admin bar in QUESTIONING phase
**When** host wants to speed up
**Then** "SKIP TO VOTE" button is available

**Given** the admin bar in any phase
**When** host needs to pause
**Then** "PAUSE" button transitions game to PAUSED phase
**And** all players see "Game Paused" message

**Given** the admin bar
**When** host wants to end
**Then** "END GAME" button is available with confirmation modal

**Given** the PAUSED phase
**When** host taps "RESUME"
**Then** game returns to previous phase
**And** timers resume from where they paused

---

## Epic 8: Content & Polish

Complete game with Classic location pack and accessibility compliance.

### Story 8.1: Classic Location Pack Content

As a **player**,
I want **a variety of interesting locations to play with**,
So that **the game feels complete and replayable**.

**Acceptance Criteria:**

**Given** the content directory
**When** `content/classic.json` is created
**Then** it contains at least 10 unique locations (per FR56)
**And** follows the enriched schema from Architecture

**Given** each location in the pack
**When** the content is reviewed
**Then** it has 6-8 associated roles (per FR57)
**And** each role has a `hint` for new players
**And** the location has a `flavor` text for atmosphere

**Given** the Classic pack
**When** locations are listed
**Then** they include varied settings (e.g., Beach, Hospital, School, Restaurant, etc.)
**And** roles are thematically appropriate for each location

---

### Story 8.2: Content Loading and Validation

As a **system**,
I want **to load and validate location packs**,
So that **the game uses well-formed content**.

**Acceptance Criteria:**

**Given** the game starts
**When** a location pack is loaded
**Then** the JSON is parsed and validated against schema
**And** errors are logged if content is malformed

**Given** a round begins
**When** a location is selected
**Then** a random location is chosen from the pack (per FR58)
**And** the selection doesn't repeat until all locations used (optional enhancement)

**Given** `game/content.py` module
**When** content is loaded
**Then** functions are available: `load_location_pack()`, `get_random_location()`, `get_roles_for_location()`

---

### Story 8.3: Accessibility Compliance

As a **player with accessibility needs**,
I want **the game to be usable with assistive technology**,
So that **everyone can participate in the fun**.

**Acceptance Criteria:**

**Given** all interactive elements
**When** inspected for accessibility
**Then** proper ARIA roles are applied (per UX-12):
- Player cards: `role="button"`, `aria-pressed`
- Bet buttons: `role="radiogroup"`, `aria-checked`
- Timer: `role="timer"`, `aria-live="polite"`
- Submission tracker: `role="progressbar"`

**Given** color contrast
**When** measured against background
**Then** text contrast meets WCAG AA (4.5:1 minimum, per UX-11)
**And** color is never the sole indicator of state

**Given** keyboard navigation
**When** using Tab/Arrow keys
**Then** all interactive elements are reachable
**And** focus states are clearly visible
**And** Enter/Space activates buttons (per UX-14)

**Given** user has `prefers-reduced-motion` enabled
**When** animations would play
**Then** animations are skipped or minimal (per UX-13)
**And** essential state changes remain visible

---

### Story 8.4: Browser Compatibility and Polish

As a **player**,
I want **the game to work on my phone's browser**,
So that **I can play regardless of device**.

**Acceptance Criteria:**

**Given** the player UI
**When** loaded on Chrome (last 2 years)
**Then** all features work correctly

**Given** the player UI
**When** loaded on Safari (last 2 years)
**Then** all features work correctly (including iOS Safari)

**Given** the player UI
**When** loaded on Firefox (last 2 years)
**Then** all features work correctly

**Given** CSS and JavaScript
**When** browser compatibility is checked
**Then** no unsupported features are used without fallbacks
**And** vendor prefixes are applied where needed

**Given** the overall experience
**When** the game is played end-to-end
**Then** transitions are smooth
**And** touch interactions are responsive
**And** no console errors appear during normal gameplay
