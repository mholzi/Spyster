---
project_name: 'Spyster'
user_name: 'Markusholzhaeuser'
date: '2025-12-22'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'critical_rules']
status: 'complete'
---

# Project Context for AI Agents

_Critical rules and patterns for implementing Spyster - a real-time multiplayer social deduction game as a Home Assistant custom component._

---

## Technology Stack & Versions

| Technology | Version | Notes |
|------------|---------|-------|
| Python | 3.12+ | HA 2025.11 requirement |
| Home Assistant | 2025.11+ | Target platform |
| aiohttp | HA bundled | WebSocket + HTTP |
| JavaScript | ES6+ vanilla | No framework, no build step |
| HTML/CSS | Modern | Mobile-first |

**No external dependencies.** Runs entirely on local network.

---

## Critical Implementation Rules

### Python Rules

- **Async everywhere**: All I/O operations use `async/await`
- **Type hints**: Use `TYPE_CHECKING` guards for imports
- **Logging**: Always `_LOGGER = logging.getLogger(__name__)`
- **Constants in const.py**: Never hardcode error codes, timeouts, or config values
- **File I/O**: Use `hass.async_add_executor_job()` for blocking operations

### Home Assistant Integration Rules

- **Entry point**: `async_setup_entry()` in `__init__.py`
- **State storage**: `hass.data[DOMAIN]` for integration-wide state
- **Views**: Subclass `HomeAssistantView` with `requires_auth = False`
- **Static files**: Register via `async_register_static_paths()`
- **Cleanup**: Implement `async_unload_entry()` properly

### WebSocket Rules

- **Per-player payloads**: NEVER broadcast same state to all players
- **Role privacy**: Spy sees location_list, others see actual location
- **Message format**: `{"type": "...", ...payload}` with snake_case fields
- **Error responses**: Always include `code` + `message`
- **Broadcast after changes**: Every state mutation triggers `broadcast_state()`

### Phase State Machine Rules

- **Phase guards**: ALWAYS validate phase before state-mutating actions
- **Return pattern**: `(success: bool, error_code: str | None)`
- **Transitions**: Only valid transitions per documented flow
- **PAUSED handling**: Any phase → PAUSED on host disconnect

### Timer Rules

- **Named timers**: Use `self._timers: dict[str, asyncio.Task]`
- **Cancel before start**: Always cancel existing timer with same name
- **Player-specific timers**: `disconnect_grace:{player_name}` pattern
- **Cleanup**: `cancel_all_timers()` on game end

---

## Naming Conventions

### Python
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### JavaScript
- Variables: `camelCase`
- Functions: `camelCase()`
- Constants: `UPPER_SNAKE_CASE`
- DOM IDs: `kebab-case`
- CSS classes: `.kebab-case`

### JSON (WebSocket/API)
- All fields: `snake_case`
- NEVER use camelCase in payloads

---

## Testing Rules

- **Location**: Separate `tests/` folder at project root
- **Fixtures**: Use `conftest.py` for shared fixtures
- **Mock HA**: Create mock `hass` object for unit tests
- **Test scoring**: Pure function tests, no state setup needed
- **Test phases**: Verify phase guards reject invalid actions

---

## Anti-Patterns to Avoid

```python
# BAD: Hardcoded error string
await ws.send_json({"type": "error", "message": "Name taken"})

# GOOD: Use constant
await ws.send_json({"type": "error", "code": ERR_NAME_TAKEN, "message": ERROR_MESSAGES[ERR_NAME_TAKEN]})
```

```python
# BAD: Broadcasting same state to all (LEAKS ROLES!)
for ws in connections:
    await ws.send_json(game_state.get_state())

# GOOD: Per-player filtering
for player_name, player in players.items():
    state = game_state.get_state(for_player=player_name)
    await player.ws.send_json({"type": "state", **state})
```

```python
# BAD: No phase check
def vote(self, target):
    self.votes[player] = target

# GOOD: Phase guard
def vote(self, player_name, target, confidence):
    if self.phase != GamePhase.VOTE:
        return False, ERR_INVALID_PHASE
    # ... continue
```

```python
# BAD: Logging without context
_LOGGER.info("Player joined")

# GOOD: Include context
_LOGGER.info("Player joined: %s (total: %d)", name, len(self.players))
```

---

## Security Rules

- **Spy assignment**: Use `secrets.choice()` (CSPRNG)
- **Role privacy**: Never include other players' roles in any payload
- **Session tokens**: URL-based tokens, not cookies
- **No sensitive persistence**: Don't store role data on client

---

## File Organization

```
custom_components/spyster/
├── __init__.py        # Entry point ONLY - no business logic
├── const.py           # ALL constants live here
├── game/              # Domain logic (state, players, scoring)
├── server/            # Infrastructure (views, websocket)
├── www/               # Frontend (HTML, JS, CSS)
└── content/           # Location packs (JSON)
```

---

**Remember:** This is a real-time multiplayer game. Every action affects other players. Always broadcast state changes, always validate phases, always filter per-player.
