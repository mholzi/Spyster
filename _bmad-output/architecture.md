---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - 'prd.md'
  - 'analysis/brainstorming-session-2025-12-22.md'
  - 'external-blueprint: /Volumes/My Passport/Beatify/custom_components'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2025-12-22'
project_name: 'Spyster'
user_name: 'Markusholzhaeuser'
date: '2025-12-22'
hasProjectContext: false
blueprintReference: 'Beatify custom_components'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

63 requirements spanning game session management, player connections, role assignment, game flow phases, voting/betting mechanics, scoring, content management, and host display. The requirements define a complete 6-phase game loop:

1. **LOBBY** - Host creates game, players join via QR code
2. **ROLES** - Server assigns spy (exactly one), distributes role/location info
3. **QUESTIONING** - Turn-based Q&A with countdown timer
4. **VOTE** - 60-second voting phase with Confidence Betting (1-3 points)
5. **REVEAL** - Simultaneous vote/bet reveal, scoring calculation
6. **END** - Leaderboard, winner declaration, game cleanup

Key mechanics requiring architectural support:
- Confidence Betting: Server must track bets secretly until reveal
- Double Agent: +10 bonus calculation for spy frame success
- Spy location guess: Alternative win condition with dedicated flow

**Non-Functional Requirements:**

| Category | Key Constraints |
|----------|-----------------|
| **Performance** | <2s page load, <100ms WS latency, 10 concurrent players |
| **Security** | Unpredictable spy assignment, role privacy, session isolation |
| **Reliability** | 5-round sessions without crash, 5-min reconnection window |
| **Integration** | HA 2025.11+, HACS distribution, no cloud dependencies |

**Scale & Complexity:**

- Primary domain: Full-stack (Python/aiohttp backend + vanilla JS frontend)
- Complexity level: Medium
- Estimated architectural components: 8-10 core modules

### Technical Constraints & Dependencies

**Platform Constraints:**
- Must run as Home Assistant custom component (Python, aiohttp)
- Browser support: Chrome, Safari, Firefox (last 2 years) - mobile-first
- Local network only - no external API calls or cloud services

**Blueprint Constraint:**
- Architecture follows Beatify integration patterns per user requirement
- Reuse proven patterns: HomeAssistantView, WebSocket handler, GameState class

**Security Constraints:**
- Spy assignment via `secrets.token_urlsafe()` or equivalent CSPRNG
- No role information in client-visible network payloads until reveal phase
- URL tokens for session recovery (not cookies - phone browser limitations)

### Cross-Cutting Concerns Identified

1. **Real-Time State Sync** - All 63 FRs ultimately require broadcasting state changes to connected clients via WebSocket

2. **Session Lifecycle** - Spans FR9-FR18, NFR10-15: join, heartbeat, disconnect detection, reconnection, cleanup

3. **Timer Orchestration** - Round timers, vote timers, grace periods all need coordinated server-side management with asyncio tasks

4. **Error Recovery** - Game must continue with remaining players if someone disconnects permanently; host disconnect pauses (not crashes) game

5. **Phase Guards** - Many actions only valid in specific phases (can't vote in LOBBY, can't submit guess in REVEAL) - state machine enforcement required

## Starter Template Evaluation

### Primary Technology Domain

**Home Assistant Custom Component** - Python backend with aiohttp, browser-based frontend with vanilla JavaScript.

### Starter Options Considered

| Option | Assessment |
|--------|------------|
| **Beatify Blueprint** | ✅ Selected - Production-proven HA integration with real-time multiplayer |
| **HA Integration Blueprint** | Generic, lacks real-time multiplayer patterns |
| **Custom from Scratch** | Unnecessary - Beatify solves identical technical challenges |

### Selected Starter: Beatify Integration Pattern

**Rationale for Selection:**
1. User explicitly requested using Beatify as architectural blueprint
2. Beatify solves identical technical challenges (real-time multiplayer party game in HA)
3. Proven production patterns for WebSocket, session management, reconnection handling
4. Reduces architectural risk by following working implementation

**Initialization Approach:**
```bash
# No CLI - manual structure creation following Beatify patterns
mkdir -p custom_components/spyster/{game,server,www/{js,css},content,translations}
```

### Architectural Decisions Provided by Blueprint

**Language & Runtime:**
- Python 3.12+ (HA 2025.11 requirement)
- Async/await throughout using asyncio
- Type hints with TYPE_CHECKING guards

**HTTP Layer:**
- aiohttp via HomeAssistantView subclasses
- `requires_auth=False` for frictionless player access
- JSON API endpoints for game operations

**Real-time Communication:**
- WebSocket via aiohttp's `WebSocketResponse`
- Server-authoritative state broadcasting
- Connection tracking with disconnect detection

**Frontend:**
- Vanilla HTML/JS/CSS (no build step)
- Mobile-first responsive design
- Served as static files from `www/` directory

**State Management:**
- Centralized `GameState` class with phase enum
- `PlayerSession` objects tracking individual connections
- `hass.data[DOMAIN]` for integration-wide state storage

**Development Experience:**
- Standard HA custom component development workflow
- Logs via `_LOGGER = logging.getLogger(__name__)`
- Hot reload via HA's integration reload

**Note:** First implementation story should establish the base directory structure following this pattern.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Phase State Machine - Defines game flow
2. Role Privacy Architecture - Security requirement
3. Timer Architecture - Enables core game mechanics

**Important Decisions (Shape Architecture):**
4. WebSocket Message Protocol - Client-server contract
5. Content Pack Format - Content authoring experience
6. Scoring Engine Location - Code organization

**Deferred Decisions (Post-MVP):**
- Image support for locations (Growth feature)
- 2-spy mode state handling (Growth feature)
- Custom content editor (Vision feature)

### Game State Architecture

**Phase State Machine: Flat Phases**

```python
class GamePhase(Enum):
    LOBBY = "LOBBY"           # Players joining, host configuring
    ROLES = "ROLES"           # Brief role assignment display
    QUESTIONING = "QUESTIONING"  # Active Q&A with round timer
    VOTE = "VOTE"             # 60-second voting + betting
    REVEAL = "REVEAL"         # Results shown, scores calculated
    SCORING = "SCORING"       # Leaderboard update display
    END = "END"               # Game complete, final standings
    PAUSED = "PAUSED"         # Host disconnected
```

**Rationale:** Maps 1:1 to PRD phases, simple to debug and test, clear phase guards.

**Phase Transitions:**
```
LOBBY → ROLES (host starts game)
ROLES → QUESTIONING (after role display timeout)
QUESTIONING → VOTE (player calls vote OR round timer expires)
VOTE → REVEAL (vote timer expires OR all players submitted)
REVEAL → SCORING (brief delay for dramatic reveal)
SCORING → QUESTIONING (next round) OR END (final round)
Any → PAUSED (host disconnect)
PAUSED → Previous (host reconnect)
```

### Security Architecture

**Role Privacy: Per-Player State Payloads**

The `get_state()` method accepts an optional `for_player` parameter to filter sensitive data:

```python
def get_state(self, for_player: str | None = None) -> dict:
    """
    Get game state, filtered for specific player if provided.

    - Public data: phase, player_count, scores, timer
    - Private data: role, location (only for requesting player)
    - Spy sees: location_list (not actual location)
    - Non-spy sees: location + their role
    """
```

**Security Guarantees:**
- Spy assignment uses `secrets.choice()` (CSPRNG)
- Role data never in broadcast payloads
- Each WebSocket connection receives personalized state
- Network inspection reveals only own role

**Implementation Pattern:**
```python
# In WebSocket handler
async def broadcast_state(self):
    for player_name, player in game_state.players.items():
        if player.connected:
            state = game_state.get_state(for_player=player_name)
            await player.ws.send_json({"type": "state", **state})
```

### API & Communication Patterns

**WebSocket Message Protocol: Flat Types**

| Type | Direction | Payload | Phase |
|------|-----------|---------|-------|
| `join` | C→S | `{name, is_host}` | LOBBY |
| `vote` | C→S | `{target, confidence}` | VOTE |
| `spy_guess` | C→S | `{location_id}` | VOTE |
| `admin` | C→S | `{action, ...params}` | Any |
| `state` | S→C | `{phase, ...phase_data}` | Any |
| `role` | S→C | `{role, location?, locations?}` | ROLES |
| `error` | S→C | `{code, message}` | Any |

**Admin Actions:**
- `start_game` - Transition LOBBY → ROLES
- `pause_game` - Manual pause
- `resume_game` - Resume from PAUSED
- `end_game` - Force end current game
- `kick_player` - Remove player from lobby

**Error Codes:**
```python
ERR_NAME_TAKEN = "NAME_TAKEN"
ERR_NAME_INVALID = "NAME_INVALID"
ERR_GAME_FULL = "GAME_FULL"
ERR_GAME_NOT_STARTED = "GAME_NOT_STARTED"
ERR_GAME_ALREADY_STARTED = "GAME_ALREADY_STARTED"
ERR_NOT_HOST = "NOT_HOST"
ERR_INVALID_PHASE = "INVALID_PHASE"
ERR_ALREADY_VOTED = "ALREADY_VOTED"
ERR_VOTE_EXPIRED = "VOTE_EXPIRED"
ERR_INVALID_LOCATION = "INVALID_LOCATION"
ERR_NOT_SPY = "NOT_SPY"
```

### Content Architecture

**Location Pack Format: Enriched Schema**

```json
{
  "id": "classic",
  "name": "Classic",
  "description": "The original Spyfall locations",
  "version": "1.0.0",
  "locations": [
    {
      "id": "beach",
      "name": "The Beach",
      "flavor": "Sandy shores, crashing waves, and sun-soaked relaxation",
      "roles": [
        {"id": "lifeguard", "name": "Lifeguard", "hint": "You watch over swimmers from your elevated chair"},
        {"id": "tourist", "name": "Tourist", "hint": "You're here on vacation, camera in hand"},
        {"id": "vendor", "name": "Ice Cream Vendor", "hint": "You sell frozen treats from your cart"},
        {"id": "surfer", "name": "Surfer", "hint": "You ride the waves and live for the perfect swell"},
        {"id": "photographer", "name": "Photographer", "hint": "You capture beach moments professionally"},
        {"id": "sunbather", "name": "Sunbather", "hint": "You're here to relax and work on your tan"}
      ]
    }
  ]
}
```

**Schema Notes:**
- `hint` helps new players understand their role context
- `flavor` displayed on host screen for atmosphere
- `id` fields enable future features (stats tracking, favorites)
- All text fields support localization keys (future)

### Timer Architecture

**Named Timer Dictionary**

```python
class GameState:
    def __init__(self):
        self._timers: dict[str, asyncio.Task] = {}

    def start_timer(self, name: str, duration: float, callback: Callable) -> None:
        """Start a named timer, cancelling any existing timer with same name."""
        self.cancel_timer(name)
        self._timers[name] = asyncio.create_task(
            self._timer_task(name, duration, callback)
        )

    def cancel_timer(self, name: str) -> None:
        """Cancel a specific timer by name."""
        if name in self._timers and not self._timers[name].done():
            self._timers[name].cancel()
            del self._timers[name]

    def cancel_all_timers(self) -> None:
        """Cancel all active timers (game end cleanup)."""
        for task in self._timers.values():
            if not task.done():
                task.cancel()
        self._timers.clear()
```

**Timer Types:**
| Timer Name | Duration | Trigger |
|------------|----------|---------|
| `round` | Configurable (default 7min) | Phase → VOTE |
| `vote` | 60 seconds fixed | Phase → REVEAL |
| `role_display` | 5 seconds | Phase → QUESTIONING |
| `reveal_delay` | 3 seconds | Phase → SCORING |
| `disconnect_grace:{player}` | 30 seconds | Mark disconnected |
| `reconnect_window:{player}` | 5 minutes | Remove player |

**Rationale:** Named timers allow disconnect grace periods to run independently of game phase timers. Multiple players can have independent reconnection windows.

### Scoring Architecture

**Separate Scoring Module: `game/scoring.py`**

```python
# game/scoring.py

def calculate_vote_score(
    voted_for: str,
    actual_spy: str,
    confidence: int,  # 1, 2, or 3
) -> tuple[int, str]:
    """
    Calculate points for a vote.

    Returns: (points, outcome)
    - Correct vote: +2/+4/+6 based on confidence
    - Incorrect vote: -1/-2/-3 based on confidence
    """

def calculate_spy_frame_bonus(
    spy_vote_target: str,
    convicted_player: str,
    spy_confidence: int,
) -> int:
    """
    Calculate Double Agent bonus.

    Returns: +10 if spy went ALL IN (confidence=3) and
             successfully framed an innocent player.
    """

def calculate_spy_guess_score(
    guessed_location: str,
    actual_location: str,
) -> int:
    """
    Calculate spy's location guess score.

    Returns: Points for correct guess (TBD based on playtesting)
    """
```

**Rationale:** Isolated scoring logic enables:
- Unit testing without game state setup
- Easy tuning of point values
- Clear separation of concerns
- Future scoring variants (casual mode, tournament mode)

### Decision Impact Analysis

**Implementation Sequence:**
1. `const.py` - Error codes, game constants, phase enum
2. `game/state.py` - GameState with timer architecture
3. `game/scoring.py` - Scoring calculations
4. `server/websocket.py` - Message protocol handlers
5. `server/views.py` - HTTP endpoints
6. `www/` - Frontend implementation
7. `content/classic.json` - First location pack

**Cross-Component Dependencies:**
- WebSocket handler depends on GameState phase guards
- Scoring module called by GameState during REVEAL → SCORING transition
- Frontend state rendering depends on message protocol contract
- Timer callbacks trigger phase transitions and broadcasts

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 7 areas where AI agents could make different choices, all now standardized.

### Naming Patterns

**Python Naming (HA/Beatify Standard):**

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case | `game_state.py`, `websocket_handler.py` |
| Classes | PascalCase | `GameState`, `PlayerSession` |
| Functions | snake_case | `get_state()`, `broadcast_state()` |
| Constants | UPPER_SNAKE | `DOMAIN`, `ERR_NAME_TAKEN` |
| Private | underscore prefix | `_timers`, `_handle_message()` |

**JavaScript Naming:**

| Element | Convention | Example |
|---------|------------|---------|
| Variables | camelCase | `playerName`, `gameState` |
| Functions | camelCase | `handleVote()`, `renderPlayers()` |
| Constants | UPPER_SNAKE | `WS_RECONNECT_DELAY` |
| DOM IDs | kebab-case | `player-list`, `vote-button` |
| CSS classes | kebab-case | `.player-card`, `.vote-confidence` |
| Event handlers | `on` prefix | `onMessage`, `onVoteClick` |

**JSON/API Field Naming:**

All WebSocket and HTTP API payloads use `snake_case` for field names:

```json
// CORRECT
{"type": "state", "player_count": 5, "current_phase": "VOTE", "is_spy": false}

// WRONG - never use camelCase in API payloads
{"type": "state", "playerCount": 5, "currentPhase": "VOTE", "isSpy": false}
```

**Rationale:** Python naturally serializes dicts with snake_case. No conversion layer needed.

### Structure Patterns

**Project Organization:**

```
custom_components/spyster/
├── __init__.py           # Entry point only - no business logic
├── manifest.json         # HACS metadata
├── const.py              # ALL constants, error codes, config values
├── config_flow.py        # HA configuration UI
├── translations/
│   └── en.json           # UI strings for config flow
├── game/
│   ├── __init__.py       # Empty or minimal exports
│   ├── state.py          # GameState class - phase management
│   ├── player.py         # PlayerSession class
│   ├── roles.py          # Spy assignment, role distribution
│   └── scoring.py        # Score calculation functions
├── server/
│   ├── __init__.py       # Static path registration
│   ├── views.py          # HTTP endpoints (HomeAssistantView)
│   └── websocket.py      # WebSocket handler
├── content/
│   └── classic.json      # Location pack data
└── www/
    ├── player.html       # Player phone UI
    ├── host.html         # Host/TV display
    ├── css/
    │   └── styles.css    # All styles in one file
    └── js/
        ├── player.js     # Player UI logic
        └── host.js       # Host display logic

tests/
├── __init__.py
├── test_state.py         # GameState unit tests
├── test_scoring.py       # Scoring function tests
├── test_roles.py         # Role assignment tests
└── conftest.py           # Pytest fixtures
```

**File Placement Rules:**
- Constants go in `const.py`, never inline
- Each class gets its own file in appropriate module
- Tests mirror source structure in `tests/` folder
- All CSS in single `styles.css` (no build step)
- All static assets under `www/`

### Format Patterns

**WebSocket Message Format:**

All messages follow this structure:

```python
# Server → Client
{"type": "state", ...payload}   # Game state update
{"type": "role", ...payload}    # Private role assignment
{"type": "error", ...payload}   # Error feedback
{"type": "timer", ...payload}   # Timer sync (optional)

# Client → Server
{"type": "join", ...payload}    # Join game
{"type": "vote", ...payload}    # Submit vote + confidence
{"type": "spy_guess", ...payload}  # Spy guesses location
{"type": "admin", ...payload}   # Host control actions
```

**Error Response Format:**

```json
{
  "type": "error",
  "code": "ERR_NAME_TAKEN",
  "message": "That name is already taken. Please choose another."
}
```

- `code`: Machine-readable, matches constant in `const.py`
- `message`: Human-readable, can display directly to user

**User-Friendly Error Messages:**

| Code | Message |
|------|---------|
| `ERR_NAME_TAKEN` | "That name is already taken. Please choose another." |
| `ERR_NAME_INVALID` | "Please enter a name between 1-20 characters." |
| `ERR_GAME_FULL` | "Sorry, this game is full (max 10 players)." |
| `ERR_GAME_NOT_STARTED` | "No game is currently active." |
| `ERR_INVALID_PHASE` | "You can't do that right now." |
| `ERR_ALREADY_VOTED` | "You've already submitted your vote." |
| `ERR_VOTE_EXPIRED` | "Time's up! Voting has ended." |
| `ERR_NOT_HOST` | "Only the host can do that." |
| `ERR_NOT_SPY` | "Only the spy can guess the location." |

### Communication Patterns

**State Broadcast Pattern:**

```python
# Always broadcast after state changes
async def some_action(self):
    # 1. Validate action is allowed
    if not self._can_perform_action():
        return error

    # 2. Update state
    self._update_state()

    # 3. Broadcast to all players (personalized)
    await self.broadcast_state()
```

**Per-Player State Filtering:**

```python
# In WebSocket handler - NEVER broadcast same state to all
async def broadcast_state(self):
    for player_name, player in game_state.players.items():
        if player.connected:
            # Each player gets personalized state
            state = game_state.get_state(for_player=player_name)
            await player.ws.send_json({"type": "state", **state})
```

### Process Patterns

**Error Handling:**

```python
# WebSocket message handling - always catch and respond
try:
    await self._handle_message(ws, msg.json())
except Exception as err:
    _LOGGER.warning("Failed to handle message: %s", err)
    await ws.send_json({
        "type": "error",
        "code": "ERR_INTERNAL",
        "message": "Something went wrong. Please try again."
    })
```

**Phase Guards:**

```python
# Always validate phase before action
def vote(self, player_name: str, target: str, confidence: int) -> tuple[bool, str | None]:
    if self.phase != GamePhase.VOTE:
        return False, ERR_INVALID_PHASE
    # ... continue with action
```

**Logging Levels:**

| Level | Use For | Example |
|-------|---------|---------|
| DEBUG | Development flow details | `"WebSocket connected, total: %d"` |
| INFO | Significant game events | `"Game started: %d players"` |
| WARNING | Handled unexpected situations | `"Failed to send to WebSocket: %s"` |
| ERROR | Failures affecting functionality | `"Config file not found: %s"` |

**Logging Format:**

```python
_LOGGER = logging.getLogger(__name__)

# Good - includes context
_LOGGER.info("Player joined: %s (total: %d)", name, len(self.players))

# Bad - missing context
_LOGGER.info("Player joined")
```

### Enforcement Guidelines

**All AI Agents MUST:**

1. **Use constants from `const.py`** - Never hardcode error codes, timeouts, or config values
2. **Follow naming conventions exactly** - snake_case Python, camelCase JS, snake_case JSON
3. **Validate phase before actions** - Every player action must check current phase
4. **Broadcast after state changes** - No state mutation without subsequent broadcast
5. **Use per-player state filtering** - Never send other players' private data
6. **Log with context** - Always include relevant counts, names, phases in log messages
7. **Handle WebSocket errors gracefully** - Catch exceptions, send error response, continue

**Pattern Verification:**

- Code review should check naming conventions
- Test coverage should verify phase guards
- Integration tests should verify state broadcast after actions

### Pattern Examples

**Good Example - Vote Handling:**

```python
async def _handle_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
    player = self._get_player_by_ws(ws)
    if not player:
        await ws.send_json({"type": "error", "code": ERR_NOT_IN_GAME, "message": "You're not in this game."})
        return

    if self.game_state.phase != GamePhase.VOTE:
        await ws.send_json({"type": "error", "code": ERR_INVALID_PHASE, "message": "You can't vote right now."})
        return

    target = data.get("target")
    confidence = data.get("confidence", 1)

    success, error = self.game_state.record_vote(player.name, target, confidence)
    if not success:
        await ws.send_json({"type": "error", "code": error, "message": ERROR_MESSAGES[error]})
        return

    _LOGGER.info("Vote recorded: %s voted for %s (confidence: %d)", player.name, target, confidence)
    await self.broadcast_state()
```

**Anti-Patterns to Avoid:**

```python
# BAD: Hardcoded error string
await ws.send_json({"type": "error", "message": "Name taken"})

# BAD: No phase check
def vote(self, target):
    self.votes[player] = target  # Could be called in wrong phase!

# BAD: Broadcasting same state to all
for ws in self.connections:
    await ws.send_json(game_state.get_state())  # Leaks role data!

# BAD: camelCase in JSON
{"playerCount": 5, "currentPhase": "VOTE"}

# BAD: Logging without context
_LOGGER.info("Vote recorded")
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
Spyster/
├── custom_components/
│   └── spyster/
│       ├── __init__.py              # Integration entry point
│       ├── manifest.json            # HACS metadata, dependencies
│       ├── const.py                 # ALL constants, config, error codes
│       ├── config_flow.py           # HA configuration UI flow
│       │
│       ├── translations/
│       │   └── en.json              # Config flow strings
│       │
│       ├── game/
│       │   ├── __init__.py          # Package exports
│       │   ├── state.py             # GameState class (phase machine, timers)
│       │   ├── player.py            # PlayerSession class
│       │   ├── roles.py             # Spy assignment, role distribution
│       │   ├── scoring.py           # Vote scores, Double Agent, spy guess
│       │   └── content.py           # Location pack loading/validation
│       │
│       ├── server/
│       │   ├── __init__.py          # Static path registration
│       │   ├── views.py             # HTTP endpoints (player, host pages)
│       │   └── websocket.py         # WebSocket handler, message routing
│       │
│       ├── content/
│       │   ├── classic.json         # Default location pack (25 locations)
│       │   └── schema.json          # JSON schema for validation
│       │
│       └── www/
│           ├── player.html          # Player phone UI
│           ├── host.html            # TV/host display
│           ├── css/
│           │   └── styles.css       # All styles (mobile-first)
│           └── js/
│               ├── player.js        # Player WebSocket client
│               ├── host.js          # Host display WebSocket client
│               └── shared.js        # Common utilities
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_state.py                # GameState unit tests
│   ├── test_scoring.py              # Scoring calculation tests
│   ├── test_roles.py                # Role assignment tests
│   ├── test_player.py               # PlayerSession tests
│   ├── test_content.py              # Content loading tests
│   └── test_websocket.py            # Message handling tests
│
├── hacs.json                        # HACS repository metadata
├── README.md                        # Installation, usage docs
├── LICENSE                          # MIT license
└── .gitignore
```

### Architectural Boundaries

**API Boundaries:**

| Endpoint | Type | Auth | Purpose |
|----------|------|------|---------|
| `/api/spyster/player` | HTTP GET | None | Serve player.html |
| `/api/spyster/host` | HTTP GET | None | Serve host.html |
| `/api/spyster/ws` | WebSocket | None | Real-time game |
| `/api/spyster/static/*` | HTTP GET | None | CSS/JS/assets |

**Component Communication:**

| From | To | Method | Data |
|------|----|--------|------|
| WebSocket Handler | GameState | Direct method call | Player actions |
| GameState | WebSocket Handler | Callback/async | State changes |
| GameState | Scoring | Function call | Vote data → points |
| GameState | Roles | Function call | Players → role assignments |
| Frontend | WebSocket Handler | WS message | JSON payloads |

**Data Boundaries:**

| Data | Storage | Lifetime | Access |
|------|---------|----------|--------|
| Game state | `hass.data["spyster"]` | Game session | `GameState` only |
| Player sessions | `GameState.players` | Game session | `GameState`, `WebSocketHandler` |
| Content packs | JSON files | Integration lifetime | Read-only |
| Config | HA config entries | Persistent | `config_flow.py` |

### Requirements to Structure Mapping

**FR Categories → Files:**

| Requirements | Primary File | Supporting Files |
|--------------|--------------|------------------|
| FR1-8 (Session) | `game/state.py` | `server/websocket.py` |
| FR9-18 (Connection) | `game/player.py` | `server/websocket.py` |
| FR19-23 (Roles) | `game/roles.py` | `game/state.py` |
| FR24-30 (Questioning) | `game/state.py` | `www/js/player.js` |
| FR31-43 (Voting) | `game/state.py`, `game/scoring.py` | `www/js/player.js` |
| FR44-55 (Scoring) | `game/scoring.py` | `game/state.py` |
| FR56-58 (Content) | `game/content.py` | `content/*.json` |
| FR59-63 (Host Display) | `www/host.html`, `www/js/host.js` | `server/views.py` |

**Cross-Cutting Concerns → Files:**

| Concern | Files |
|---------|-------|
| Error handling | `const.py` (codes), `server/websocket.py` (WS errors) |
| Timer management | `game/state.py` (timer dict) |
| State broadcast | `server/websocket.py` (broadcast_state) |
| Logging | All files (`_LOGGER`) |
| Phase guards | `game/state.py` (phase checks) |

### Integration Points

**Internal Data Flow:**

```
Player Vote:
phone → {"type":"vote"} → websocket.py → state.record_vote()
→ scoring.calculate_vote_score() → state update → broadcast_state() → all clients

Host Start Game:
host → {"type":"admin","action":"start_game"} → websocket.py
→ state.start_game() → roles.assign_roles() → phase ROLES → broadcast_state()

Timer Expiry:
state._timers["vote"] expires → _on_timer_expired("vote")
→ transition VOTE→REVEAL → broadcast_state()
```

**External Integration Points:**

| System | File | Integration |
|--------|------|-------------|
| Home Assistant core | `__init__.py` | `async_setup_entry()` |
| HA config flow | `config_flow.py` | `ConfigFlow` class |
| HA sidebar | `__init__.py` | `async_register_panel()` |
| HACS | `manifest.json`, `hacs.json` | Metadata files |

### Development & Deployment

**Development:**
- Edit files directly in `custom_components/spyster/`
- Reload integration via HA Developer Tools
- Test with `pytest tests/ -v`

**Deployment:**
- HACS: Add custom repository, install via UI
- Manual: Copy `custom_components/spyster/` to HA config

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices (Python 3.12+, aiohttp, vanilla JS) work together without conflicts. The phase state machine, timer architecture, and per-player payloads are mutually consistent.

**Pattern Consistency:**
Naming conventions (snake_case Python, camelCase JS, snake_case JSON) are applied uniformly. Error handling, logging, and phase guard patterns are consistent across all components.

**Structure Alignment:**
Project structure directly supports all architectural decisions. Boundaries between game/, server/, and www/ are clear and respected.

### Requirements Coverage Validation ✅

**Functional Requirements:**
All 63 FRs mapped to specific architectural components:
- Game session (FR1-8): GameState class
- Player connection (FR9-18): PlayerSession + timer architecture
- Role assignment (FR19-23): roles.py with CSPRNG
- Game phases (FR24-30): Phase enum + timer callbacks
- Voting mechanics (FR31-43): state.py + scoring.py
- Scoring system (FR44-55): scoring.py functions
- Content management (FR56-58): content.py + JSON schema
- Host display (FR59-63): host.html + host.js

**Non-Functional Requirements:**
All 20 NFRs architecturally addressed:
- Performance: Local network, minimal payloads, no build step
- Security: Per-player state filtering, secrets.choice()
- Reliability: Named timer dict, phase guards, reconnection windows
- Integration: Standard HA patterns, HACS metadata

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with code examples
- Technology versions specified (Python 3.12+, HA 2025.11+)
- Integration patterns fully defined

**Structure Completeness:**
- Complete directory tree with all files
- Each file has defined responsibility
- Tests organized in separate folder

**Pattern Completeness:**
- Naming conventions for all languages
- Error handling with code + message pattern
- State broadcast with per-player filtering
- Phase guards on all state-mutating methods

### Gap Analysis Results

**Critical Gaps:** None

**Important Gaps (Low Priority):**
1. QR code generation: Use `qrcode` Python library in views.py
2. Host heartbeat: Use 30s interval (same as player disconnect)

**Deferred to Post-MVP:**
- CI/CD pipeline setup
- Performance profiling
- Location pack editor

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (Medium)
- [x] Technical constraints identified (HA, HACS, local network)
- [x] Cross-cutting concerns mapped (5 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented (6 decisions)
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established (Python, JS, JSON)
- [x] Structure patterns defined
- [x] Communication patterns specified (WebSocket protocol)
- [x] Process patterns documented (error handling, logging)

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. Proven blueprint (Beatify) reduces architectural risk
2. Clear phase state machine simplifies game logic
3. Per-player payloads ensure role privacy
4. Named timer architecture handles complex timing requirements
5. Comprehensive patterns prevent AI agent conflicts

**Areas for Future Enhancement:**
1. Image support for locations (Growth feature)
2. 2-spy mode architecture (Growth feature)
3. Analytics/stats tracking (Vision feature)
4. Multi-language content packs (Vision feature)

### Implementation Handoff

**AI Agent Guidelines:**
1. Follow all architectural decisions exactly as documented
2. Use implementation patterns consistently across all components
3. Respect project structure and boundaries
4. Refer to this document for all architectural questions
5. Constants go in const.py - never hardcode values
6. Always validate phase before state-mutating actions
7. Always broadcast after state changes

**First Implementation Priority:**
```bash
mkdir -p custom_components/spyster/{game,server,www/{js,css},content,translations}
```

Create files in this order:
1. `const.py` - Error codes, phases, config values
2. `manifest.json` - HACS metadata
3. `game/state.py` - GameState skeleton with phase enum
4. `game/player.py` - PlayerSession class
5. Continue per Implementation Sequence in Core Decisions

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2025-12-22
**Document Location:** `_bmad-output/architecture.md`

### Final Architecture Deliverables

**Complete Architecture Document**
- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**
- 6 core architectural decisions made
- 7 implementation pattern categories defined
- 15+ architectural components specified
- 63 FRs + 20 NFRs fully supported

**AI Agent Implementation Guide**
- Technology stack: Python 3.12+, aiohttp, vanilla JS
- Consistency rules preventing implementation conflicts
- Project structure with clear boundaries
- WebSocket protocol and communication standards

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing Spyster. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**
```bash
mkdir -p custom_components/spyster/{game,server,www/{js,css},content,translations}
```

**Development Sequence:**
1. Initialize project structure
2. Create `const.py` with all constants
3. Create `manifest.json` for HACS
4. Implement `game/state.py` with GameState class
5. Implement `game/player.py` with PlayerSession
6. Implement `game/roles.py` for spy assignment
7. Implement `game/scoring.py` for point calculations
8. Implement `server/websocket.py` for real-time communication
9. Implement `server/views.py` for HTTP endpoints
10. Create frontend files in `www/`
11. Create `content/classic.json` location pack

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**
- [x] All 63 functional requirements supported
- [x] All 20 non-functional requirements addressed
- [x] Cross-cutting concerns handled
- [x] Integration points defined

**✅ Implementation Readiness**
- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Code examples provided for clarity

### Project Success Factors

**Clear Decision Framework:**
Every technology choice was made collaboratively with clear rationale, ensuring consistent architectural direction.

**Consistency Guarantee:**
Implementation patterns ensure multiple AI agents produce compatible, consistent code.

**Complete Coverage:**
All project requirements architecturally supported with clear mapping.

**Solid Foundation:**
Beatify blueprint provides production-proven patterns for real-time multiplayer.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

