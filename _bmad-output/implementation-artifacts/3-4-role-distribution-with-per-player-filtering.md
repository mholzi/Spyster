# Story 3.4: Role Distribution with Per-Player Filtering

**Epic:** Epic 3 - Game Configuration & Role Assignment
**Status:** ready-for-dev
**Priority:** Critical (Security Requirement)
**Estimated Effort:** 6 story points
**Dependencies:** Story 3.3 (Spy Assignment)

---

## User Story

As a **system**,
I want **to send personalized role information to each player**,
So that **players only see their own role (security requirement)**.

---

## Business Context

This story implements the critical security requirement NFR7: "Player cannot see another player's role via network inspection." Role privacy is fundamental to the game's integrity - if players can see who the spy is through network traffic, the entire game breaks.

The per-player state filtering architecture (ARCH-7, ARCH-8) ensures that:
- Each WebSocket connection receives a personalized payload
- Spy sees location list (not the actual location)
- Non-spy players see actual location + their role
- No player can intercept another player's role data

This is a **BLOCKER** for game implementation - without this, the game is unplayable.

---

## Acceptance Criteria

### AC1: Personalized State Broadcasting
**Given** roles are assigned
**When** state is broadcast to players
**Then** each player receives a personalized `role` message via `get_state(for_player=name)`

**Verification:**
- WebSocket handler calls `get_state(for_player=player_name)` for each connected player
- Each player receives a different payload based on their role
- No two players receive identical role data unless both are non-spy (even then, roles differ)

---

### AC2: Non-Spy Role Information
**Given** a non-spy player receives their role
**When** the role message arrives
**Then** they see the location name and their assigned role
**And** they do NOT see other players' roles

**Verification:**
- Payload contains: `{"type": "role", "location": "Beach", "role": "Lifeguard", "is_spy": false}`
- Payload does NOT contain: other players' roles, spy identity, location_list
- Frontend displays location prominently with assigned role

---

### AC3: Spy Role Information
**Given** the spy receives their role
**When** the role message arrives
**Then** they see "YOU ARE THE SPY"
**And** they see the list of possible locations (not the actual location)
**And** they do NOT see the actual location

**Verification:**
- Payload contains: `{"type": "role", "is_spy": true, "locations": ["Beach", "Hospital", ...]}`
- Payload does NOT contain: `location`, `role`, actual location name
- Frontend displays spy indicator with location list

---

### AC4: Network Traffic Security
**Given** network traffic is inspected
**When** WebSocket messages are examined
**Then** no player can see another player's role data

**Verification:**
- Use browser dev tools to inspect WebSocket frames
- Each connection receives different payload
- Spy identity not revealed in any broadcast message
- Test with multiple browser windows (different players)

---

## Technical Implementation

### Files to Create
None - all modifications to existing files

### Files to Modify

#### 1. `custom_components/spyster/game/state.py`
**Add `get_state()` method with per-player filtering:**

```python
def get_state(self, for_player: str | None = None) -> dict:
    """
    Get game state, filtered for specific player if provided.

    Args:
        for_player: Player name to filter state for (None = host/public view)

    Returns:
        dict: Game state with appropriate filtering applied

    Security:
        - Public data: phase, player_count, scores, timer
        - Private data: role, location (only for requesting player)
        - Spy sees: location_list (not actual location)
        - Non-spy sees: location + their role
    """
    # Public state (visible to all)
    state = {
        "phase": self.phase.value,
        "player_count": len(self.players),
        "round_number": self.current_round,
        "total_rounds": self.config.get("rounds", 5),
    }

    # Timer state (if active)
    if "round" in self._timers and not self._timers["round"].done():
        state["timer"] = self._get_timer_remaining("round")
    elif "vote" in self._timers and not self._timers["vote"].done():
        state["timer"] = self._get_timer_remaining("vote")

    # Phase-specific state
    if self.phase == GamePhase.LOBBY:
        state["players"] = [
            {"name": p.name, "connected": p.connected, "is_host": p.is_host}
            for p in self.players.values()
        ]

    elif self.phase == GamePhase.ROLES:
        # Role phase - send personalized role info
        if for_player:
            player = self.players.get(for_player)
            if player:
                if player.name == self.spy_name:
                    # Spy sees location list (NOT actual location)
                    state["role_info"] = {
                        "is_spy": True,
                        "locations": [loc["name"] for loc in self.location_pack["locations"]]
                    }
                else:
                    # Non-spy sees actual location + their role
                    state["role_info"] = {
                        "is_spy": False,
                        "location": self.current_location["name"],
                        "role": player.role
                    }

    elif self.phase == GamePhase.QUESTIONING:
        # Include role info for quick reference
        if for_player:
            player = self.players.get(for_player)
            if player and player.name == self.spy_name:
                state["is_spy"] = True
                state["locations"] = [loc["name"] for loc in self.location_pack["locations"]]
            elif player:
                state["is_spy"] = False
                state["location"] = self.current_location["name"]
                state["role"] = player.role

        state["questioner"] = self.current_questioner
        state["answerer"] = self.current_answerer

    elif self.phase == GamePhase.VOTE:
        # Similar filtering for vote phase
        if for_player:
            player = self.players.get(for_player)
            if player:
                state["is_spy"] = (player.name == self.spy_name)
                if not state["is_spy"]:
                    state["location"] = self.current_location["name"]
                    state["role"] = player.role
                else:
                    state["locations"] = [loc["name"] for loc in self.location_pack["locations"]]

        state["votes_submitted"] = len(self.votes)
        state["total_players"] = len(self.players)

    elif self.phase == GamePhase.REVEAL:
        # Reveal phase - all votes visible
        state["votes"] = [
            {"player": p, "target": v["target"], "confidence": v["confidence"]}
            for p, v in self.votes.items()
        ]
        state["convicted"] = self.convicted_player
        state["actual_spy"] = self.spy_name
        state["location"] = self.current_location["name"]

    elif self.phase == GamePhase.SCORING:
        state["scores"] = {p.name: p.score for p in self.players.values()}
        state["actual_spy"] = self.spy_name
        state["convicted"] = self.convicted_player

    return state
```

**Add helper method:**

```python
def _get_timer_remaining(self, timer_name: str) -> int:
    """Get remaining seconds for a named timer."""
    if timer_name not in self._timers:
        return 0

    task = self._timers[timer_name]
    if task.done():
        return 0

    # Timer tasks store start_time and duration
    # This is simplified - actual implementation may need more state
    return max(0, int(task.get_name().split(":")[-1]) if ":" in task.get_name() else 0)
```

---

#### 2. `custom_components/spyster/server/websocket.py`
**Modify `broadcast_state()` to use per-player filtering:**

```python
async def broadcast_state(self) -> None:
    """
    Broadcast current game state to all connected players.

    CRITICAL: Each player receives a personalized payload.
    NEVER broadcast the same state to all players (security violation).
    """
    game_state = self.hass.data[DOMAIN]["game_state"]

    # Host display gets unfiltered public view
    if self.host_ws and not self.host_ws.closed:
        try:
            host_state = game_state.get_state(for_player=None)
            await self.host_ws.send_json({"type": "state", **host_state})
        except Exception as err:
            _LOGGER.warning("Failed to send state to host: %s", err)

    # Each player gets personalized state
    for player_name, player in game_state.players.items():
        if player.connected and player.ws and not player.ws.closed:
            try:
                # Per-player filtering happens here
                player_state = game_state.get_state(for_player=player_name)
                await player.ws.send_json({"type": "state", **player_state})
            except Exception as err:
                _LOGGER.warning(
                    "Failed to send state to %s: %s",
                    player_name,
                    err
                )
```

---

#### 3. `custom_components/spyster/www/js/player.js`
**Add role display handling:**

```javascript
function handleState(state) {
    currentState = state;

    // Update phase display
    updatePhaseDisplay(state.phase);

    // Phase-specific rendering
    if (state.phase === 'ROLES') {
        renderRoleDisplay(state.role_info);
    } else if (state.phase === 'QUESTIONING') {
        renderQuestioningPhase(state);
    } else if (state.phase === 'VOTE') {
        renderVotingPhase(state);
    } else if (state.phase === 'REVEAL') {
        renderRevealPhase(state);
    } else if (state.phase === 'SCORING') {
        renderScoringPhase(state);
    }
}

function renderRoleDisplay(roleInfo) {
    const container = document.getElementById('role-display');

    if (!roleInfo) {
        container.innerHTML = '<div class="loading">Assigning roles...</div>';
        return;
    }

    if (roleInfo.is_spy) {
        // Spy view: "YOU ARE THE SPY" + location list
        container.innerHTML = `
            <div class="role-card spy">
                <div class="role-title">YOU ARE THE SPY</div>
                <div class="role-subtitle">One of these locations:</div>
                <ul class="location-list">
                    ${roleInfo.locations.map(loc => `<li>${escapeHtml(loc)}</li>`).join('')}
                </ul>
                <div class="role-hint">Ask questions to figure out the location!</div>
            </div>
        `;
    } else {
        // Non-spy view: Location + Role
        container.innerHTML = `
            <div class="role-card non-spy">
                <div class="location-name">${escapeHtml(roleInfo.location)}</div>
                <div class="role-name">You are: ${escapeHtml(roleInfo.role)}</div>
                <div class="role-hint">Answer questions naturally based on your role!</div>
            </div>
        `;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

---

#### 4. `custom_components/spyster/www/css/styles.css`
**Add spy parity styling (UX-9, UX-10):**

```css
/* CRITICAL: Spy and non-spy layouts MUST be identical dimensions */
/* This prevents visual tells - no one can tell who's spy by glancing at phones */

.role-card {
    min-height: 400px; /* Fixed height for parity */
    padding: var(--spacing-xl);
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
}

.role-card.spy,
.role-card.non-spy {
    /* Both have identical outer structure */
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
}

/* Spy-specific (red accent) */
.role-card.spy .role-title {
    font-size: 48px;
    font-weight: 700;
    color: var(--accent-primary); /* Pink */
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: var(--spacing-lg);
}

.role-card.spy .location-list {
    list-style: none;
    padding: 0;
    margin: var(--spacing-lg) 0;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-sm);
}

.role-card.spy .location-list li {
    padding: var(--spacing-sm);
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
    font-size: 16px;
}

/* Non-spy specific (cyan accent) */
.role-card.non-spy .location-name {
    font-size: 48px;
    font-weight: 700;
    color: var(--accent-secondary); /* Cyan */
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: var(--spacing-lg);
}

.role-card.non-spy .role-name {
    font-size: 32px;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: var(--spacing-lg);
}

/* Shared elements (identical sizing) */
.role-subtitle,
.role-hint {
    font-size: 18px;
    color: var(--text-secondary);
    margin-top: var(--spacing-md);
}

.loading {
    font-size: 24px;
    color: var(--text-secondary);
    text-align: center;
    padding: var(--spacing-xl);
}
```

---

## Testing Requirements

### Unit Tests (`tests/test_state.py`)

```python
def test_get_state_spy_filtering():
    """Spy should see location list, NOT actual location."""
    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"},
            {"name": "School", "id": "school"}
        ]
    }

    spy_state = game_state.get_state(for_player="Alice")

    assert spy_state["role_info"]["is_spy"] is True
    assert "locations" in spy_state["role_info"]
    assert "Beach" in spy_state["role_info"]["locations"]
    assert "location" not in spy_state["role_info"]  # MUST NOT reveal actual location
    assert "role" not in spy_state["role_info"]


def test_get_state_non_spy_filtering():
    """Non-spy should see location and role, NOT location list."""
    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}

    player = PlayerSession("Bob", False)
    player.role = "Lifeguard"
    game_state.players["Bob"] = player

    bob_state = game_state.get_state(for_player="Bob")

    assert bob_state["role_info"]["is_spy"] is False
    assert bob_state["role_info"]["location"] == "Beach"
    assert bob_state["role_info"]["role"] == "Lifeguard"
    assert "locations" not in bob_state["role_info"]  # MUST NOT reveal location list


def test_get_state_no_cross_contamination():
    """Each player gets different state - no leakage."""
    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }

    alice = PlayerSession("Alice", False)
    bob = PlayerSession("Bob", False)
    bob.role = "Lifeguard"
    game_state.players["Alice"] = alice
    game_state.players["Bob"] = bob

    alice_state = game_state.get_state(for_player="Alice")
    bob_state = game_state.get_state(for_player="Bob")

    # Alice (spy) should NOT know Bob's role
    assert "role" not in alice_state.get("role_info", {})

    # Bob (non-spy) should NOT see location list
    assert "locations" not in bob_state.get("role_info", {})

    # States must be different
    assert alice_state != bob_state
```

---

### Integration Tests

**Manual Test: Network Inspection**
1. Start game with 4 players on different devices/browsers
2. Open browser DevTools → Network → WS tab
3. Assign roles and observe WebSocket frames
4. **VERIFY:** Each connection receives different payload
5. **VERIFY:** Spy payload has `locations`, NOT `location`
6. **VERIFY:** Non-spy payload has `location` + `role`, NOT `locations`
7. **VERIFY:** No player can see another player's role in any message

**Test Scenario: Spy Parity Visual Check**
1. Display spy and non-spy role screens side-by-side
2. **VERIFY:** Both have identical outer dimensions (400px min-height)
3. **VERIFY:** Casual glance cannot distinguish spy from non-spy
4. **VERIFY:** Both displays are visually balanced (no obvious tells)

---

## Security Considerations

**CRITICAL SECURITY REQUIREMENTS:**

1. **Never broadcast same state to all players**
   - VIOLATION: `for ws in connections: ws.send(state)`
   - CORRECT: `ws.send(get_state(for_player=name))`

2. **Spy must NEVER see actual location**
   - Payload validation: `assert "location" not in spy_state`
   - Only `locations` array permitted

3. **Non-spy must NEVER see location list**
   - Payload validation: `assert "locations" not in non_spy_state`
   - Only `location` + `role` permitted

4. **Network inspection test is MANDATORY**
   - Must verify with browser DevTools before marking story complete
   - Document findings in story completion notes

---

## Definition of Done

- [ ] `get_state(for_player)` method implemented in `game/state.py`
- [ ] Per-player filtering in `broadcast_state()` in `server/websocket.py`
- [ ] Role display rendering in `www/js/player.js`
- [ ] Spy parity CSS in `www/css/styles.css`
- [ ] Unit tests pass (spy filtering, non-spy filtering, no cross-contamination)
- [ ] Integration test: Network inspection confirms no role leakage
- [ ] Visual test: Spy and non-spy displays have identical dimensions
- [ ] Code review completed with ADVERSARIAL mindset
- [ ] Security validation: Manual WebSocket frame inspection documented
- [ ] Story marked as `done` in `sprint-status.yaml`

---

## Dependencies

**Upstream Dependencies:**
- Story 3.3 (Spy Assignment) - MUST be complete before starting
- `GameState.spy_name` must be assigned
- `GameState.current_location` must be selected
- `PlayerSession.role` must be assigned for non-spy players

**Downstream Dependencies:**
- Story 3.5 (Role Display UI) - consumes role data from this story
- Story 4.1 (Questioning Phase) - uses per-player filtering pattern
- Story 5.1 (Voting Phase) - requires role privacy maintained

---

## Notes

**Implementation Order:**
1. Implement `get_state()` method first (pure function, testable)
2. Add unit tests (red-green-refactor)
3. Modify `broadcast_state()` to use per-player filtering
4. Update frontend to handle role info
5. Add CSS for spy parity
6. Manual security validation with browser DevTools

**Common Pitfalls:**
- Broadcasting same state to all players (security violation)
- Spy seeing actual location (game-breaking bug)
- Non-spy seeing location list (unfair advantage)
- Forgetting to update host display (host should see all public data)

**Related Architecture Decisions:**
- ARCH-7: Per-player state filtering via `get_state(for_player=name)`
- ARCH-8: Never broadcast same state to all players
- ARCH-6: Spy assignment must use `secrets.choice()` (CSPRNG)
- NFR7: Role privacy - player cannot see another's role via network inspection

---

## Story Completion Checklist

When completing this story, developer MUST:

1. Run all unit tests: `pytest tests/test_state.py -v`
2. Start local game with 4+ players
3. Open DevTools on all devices → Network → WS
4. Assign roles and inspect WebSocket frames
5. Screenshot spy payload (verify `locations`, NO `location`)
6. Screenshot non-spy payload (verify `location` + `role`, NO `locations`)
7. Document findings in completion notes
8. Request ADVERSARIAL code review with security focus
9. Fix all issues found in review
10. Update `sprint-status.yaml` to `done`

---

**Story Ready for Implementation** ✅
**Security Level:** CRITICAL
**Architectural Impact:** HIGH (establishes per-player filtering pattern)
