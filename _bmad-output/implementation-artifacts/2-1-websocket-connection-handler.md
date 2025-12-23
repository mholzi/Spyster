---
story_id: '2.1'
epic: 'Epic 2: Player Join & Connection'
title: 'WebSocket Connection Handler'
status: 'ready-for-dev'
priority: 'high'
estimated_effort: '4 hours'
dependencies: ['1.1', '1.2']
created: '2025-12-23'
---

# Story 2.1: WebSocket Connection Handler

## User Story

As a **player**,
I want **a real-time connection to the game server**,
So that **I receive game updates instantly**.

## Business Context

This story establishes the foundational real-time communication layer for Spyster. All game interactions (joining, voting, role assignment, state sync) depend on reliable WebSocket connections. This is the core infrastructure that enables the multiplayer party game experience.

**Why this matters:**
- Without WebSocket, the game cannot sync state between players in real-time
- Connection handling must be robust for smooth gameplay (FR9-FR18)
- This foundation supports all subsequent player interaction stories

## Acceptance Criteria

### AC1: WebSocket Connection Establishment

**Given** a player navigates to the player URL (`/api/spyster/player`)
**When** the page loads
**Then** a WebSocket connection is established to `/api/spyster/ws`
**And** the connection state is tracked in the browser (connecting → connected → error)
**And** the player sees visual feedback of connection status

**Frontend Implementation:**
```javascript
// www/js/player.js
class PlayerClient {
    constructor() {
        this.ws = null;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2 seconds, exponential backoff
    }

    connect() {
        this.connectionState = 'connecting';
        this.updateConnectionUI();

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/spyster/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => this.onOpen();
        this.ws.onmessage = (event) => this.onMessage(event);
        this.ws.onerror = (error) => this.onError(error);
        this.ws.onclose = () => this.onClose();
    }

    onOpen() {
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.updateConnectionUI();
        console.log('WebSocket connected');
    }

    updateConnectionUI() {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;

        const stateMap = {
            'disconnected': { text: 'Disconnected', class: 'status-error' },
            'connecting': { text: 'Connecting...', class: 'status-connecting' },
            'connected': { text: 'Connected', class: 'status-connected' },
            'error': { text: 'Connection Error', class: 'status-error' }
        };

        const state = stateMap[this.connectionState];
        statusElement.textContent = state.text;
        statusElement.className = `connection-status ${state.class}`;
    }
}
```

**Validation:**
- Open `/api/spyster/player` in browser
- Check browser DevTools Network tab → WS section
- Verify WebSocket connection to `/api/spyster/ws` is established
- Status indicator shows "Connected"

---

### AC2: Server Connection Tracking and Welcome Message

**Given** the WebSocket handler receives a connection
**When** the connection is established
**Then** the connection is tracked in the server's connection pool
**And** the connection receives a welcome message with server info
**And** the connection is logged with connection count

**Backend Implementation:**
```python
# server/websocket.py
import asyncio
import json
import logging
from typing import Dict, Optional
from aiohttp import web, WSMsgType

from ..const import (
    WS_HEARTBEAT_TIMEOUT,
    ERR_INVALID_MESSAGE,
    ERR_MESSAGE_PARSE_FAILED,
    ERROR_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections for real-time game communication."""

    def __init__(self, game_state):
        self.game_state = game_state
        self._connections: Dict[str, web.WebSocketResponse] = {}  # connection_id → ws
        self._connection_counter = 0

    async def handle_connection(self, request: web.Request) -> web.WebSocketResponse:
        """Handle new WebSocket connection."""
        ws = web.WebSocketResponse(heartbeat=WS_HEARTBEAT_TIMEOUT)
        await ws.prepare(request)

        # Generate unique connection ID
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}"
        self._connections[connection_id] = ws

        _LOGGER.info(
            "WebSocket connected: %s (total connections: %d)",
            connection_id,
            len(self._connections),
        )

        # Send welcome message
        await self._send_welcome(ws, connection_id)

        # Handle messages
        try:
            await self._message_loop(ws, connection_id)
        finally:
            # Cleanup on disconnect
            if connection_id in self._connections:
                del self._connections[connection_id]
            _LOGGER.info(
                "WebSocket disconnected: %s (remaining: %d)",
                connection_id,
                len(self._connections),
            )

        return ws

    async def _send_welcome(self, ws: web.WebSocketResponse, connection_id: str) -> None:
        """Send welcome message to newly connected client."""
        await ws.send_json({
            "type": "welcome",
            "connection_id": connection_id,
            "server_version": "1.0.0",
            "game_active": self.game_state is not None,
        })

    async def _message_loop(self, ws: web.WebSocketResponse, connection_id: str) -> None:
        """Process incoming messages from WebSocket."""
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await self._handle_text_message(ws, connection_id, msg.data)
            elif msg.type == WSMsgType.ERROR:
                _LOGGER.warning(
                    "WebSocket error on %s: %s",
                    connection_id,
                    ws.exception(),
                )
            # BINARY and other types ignored for now

    async def _handle_text_message(
        self, ws: web.WebSocketResponse, connection_id: str, data: str
    ) -> None:
        """Handle text message from client."""
        try:
            message = json.loads(data)
        except json.JSONDecodeError as err:
            _LOGGER.warning(
                "Failed to parse JSON from %s: %s",
                connection_id,
                err,
            )
            await self._send_error(ws, ERR_MESSAGE_PARSE_FAILED)
            return

        # Validate message structure
        if not isinstance(message, dict) or "type" not in message:
            _LOGGER.warning(
                "Invalid message structure from %s: %s",
                connection_id,
                message,
            )
            await self._send_error(ws, ERR_INVALID_MESSAGE)
            return

        # Route message to appropriate handler
        message_type = message.get("type")
        _LOGGER.debug(
            "Received message from %s: type=%s",
            connection_id,
            message_type,
        )

        # TODO: Route to specific handlers based on message_type
        # For now, just acknowledge receipt
        await ws.send_json({"type": "ack", "received": message_type})

    async def _send_error(
        self, ws: web.WebSocketResponse, error_code: str
    ) -> None:
        """Send error message to client."""
        await ws.send_json({
            "type": "error",
            "code": error_code,
            "message": ERROR_MESSAGES.get(error_code, "Unknown error"),
        })
```

**Constants to add to const.py:**
```python
# const.py additions

# WebSocket configuration (ARCH-15)
WS_HEARTBEAT_TIMEOUT = 30  # seconds - aiohttp keepalive

# Error codes (ARCH-13)
ERR_INVALID_MESSAGE = "INVALID_MESSAGE"
ERR_MESSAGE_PARSE_FAILED = "MESSAGE_PARSE_FAILED"

# Error messages (ARCH-13)
ERROR_MESSAGES = {
    ERR_INVALID_MESSAGE: "Message must be JSON with a 'type' field.",
    ERR_MESSAGE_PARSE_FAILED: "Could not parse message as JSON.",
}
```

**Validation:**
- Connection is added to `_connections` dict
- Welcome message contains `connection_id` and `server_version`
- Server logs show "WebSocket connected" with connection count
- Disconnect properly removes connection and logs event

---

### AC3: Malformed Message Error Handling

**Given** a WebSocket message is received
**When** the message is malformed JSON
**Then** an error response is sent with code `ERR_INVALID_MESSAGE`
**And** the connection remains open (non-fatal error)
**And** the error is logged for debugging

**Test Cases:**

**Test 1: Invalid JSON syntax**
```javascript
// Client sends
ws.send('{"type": "join", invalid}'); // Missing quotes, invalid JSON

// Server responds
{
    "type": "error",
    "code": "MESSAGE_PARSE_FAILED",
    "message": "Could not parse message as JSON."
}
```

**Test 2: Valid JSON but missing 'type' field**
```javascript
// Client sends
ws.send('{"name": "Alice"}'); // No 'type' field

// Server responds
{
    "type": "error",
    "code": "INVALID_MESSAGE",
    "message": "Message must be JSON with a 'type' field."
}
```

**Test 3: Valid JSON with wrong 'type' structure**
```javascript
// Client sends
ws.send('{"type": ["array", "not", "string"]}'); // Type is not a string

// Server responds
{
    "type": "error",
    "code": "INVALID_MESSAGE",
    "message": "Message must be JSON with a 'type' field."
}
```

**Frontend Error Handling:**
```javascript
// www/js/player.js additions

class PlayerClient {
    onMessage(event) {
        let message;
        try {
            message = JSON.parse(event.data);
        } catch (err) {
            console.error('Failed to parse server message:', err);
            return;
        }

        const messageType = message.type;

        if (messageType === 'error') {
            this.handleError(message);
            return;
        }

        // Route to specific handlers
        switch (messageType) {
            case 'welcome':
                this.handleWelcome(message);
                break;
            case 'ack':
                console.log('Server acknowledged:', message.received);
                break;
            default:
                console.warn('Unknown message type:', messageType);
        }
    }

    handleError(message) {
        console.error('Server error:', message.code, message.message);

        // Display error to user
        const errorElement = document.getElementById('error-display');
        if (errorElement) {
            errorElement.textContent = message.message;
            errorElement.classList.add('visible');

            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorElement.classList.remove('visible');
            }, 5000);
        }
    }

    handleWelcome(message) {
        console.log('Connected to server:', message.connection_id);
        this.connectionId = message.connection_id;
        this.serverVersion = message.server_version;
    }
}
```

**Validation:**
- Send malformed JSON → server responds with error, connection stays open
- Send valid JSON without 'type' → server responds with ERR_INVALID_MESSAGE
- Error appears in browser console and UI
- Server logs warning with connection_id and error details

---

## Technical Implementation Details

### File Structure
```
custom_components/spyster/
├── const.py                 # Add WS constants and error codes
├── server/
│   ├── __init__.py          # Export WebSocketHandler
│   ├── websocket.py         # NEW: WebSocket handler implementation
│   └── views.py             # Register WS endpoint
└── www/
    ├── player.html          # Add connection status UI
    └── js/
        └── player.js        # NEW: PlayerClient class
```

### Integration with Existing Code

**1. Register WebSocket endpoint in views.py:**
```python
# server/views.py additions

from .websocket import WebSocketHandler

class SpysterWebSocketView(HomeAssistantView):
    """WebSocket endpoint for real-time game communication."""

    url = "/api/spyster/ws"
    name = "api:spyster:websocket"
    requires_auth = False

    def __init__(self, hass, game_state):
        self.hass = hass
        self.handler = WebSocketHandler(game_state)

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        return await self.handler.handle_connection(request)
```

**2. Initialize in __init__.py:**
```python
# __init__.py additions

from .server.views import SpysterWebSocketView
from .game.state import GameState

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spyster from a config entry."""

    # Initialize game state (from Story 1.1)
    game_state = GameState()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["game_state"] = game_state

    # Register WebSocket view
    hass.http.register_view(SpysterWebSocketView(hass, game_state))

    return True
```

**3. Player HTML additions:**
```html
<!-- www/player.html additions -->

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spyster - Player</title>
    <link rel="stylesheet" href="/api/spyster/static/css/styles.css">
</head>
<body>
    <div class="player-container">
        <!-- Connection Status -->
        <div id="connection-status" class="connection-status status-disconnected">
            Disconnected
        </div>

        <!-- Error Display -->
        <div id="error-display" class="error-display"></div>

        <!-- Main Content (join form, game UI, etc.) -->
        <div id="main-content">
            <!-- Story 2.2 will add join form here -->
        </div>
    </div>

    <script src="/api/spyster/static/js/player.js"></script>
    <script>
        // Initialize player client
        const playerClient = new PlayerClient();
        playerClient.connect();
    </script>
</body>
</html>
```

**4. CSS for connection status:**
```css
/* www/css/styles.css additions */

.connection-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    z-index: 1000;
    transition: all 0.3s ease;
}

.status-disconnected,
.status-error {
    background-color: #ff2d6a;
    color: #fff;
}

.status-connecting {
    background-color: #ffd700;
    color: #0a0a12;
}

.status-connected {
    background-color: #00f5ff;
    color: #0a0a12;
}

.error-display {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #ff2d6a;
    color: #fff;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(255, 45, 106, 0.3);
    max-width: 90%;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
    z-index: 1000;
}

.error-display.visible {
    opacity: 1;
    pointer-events: auto;
}
```

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_websocket.py`

```python
import pytest
import json
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from custom_components.spyster.server.websocket import WebSocketHandler
from custom_components.spyster.const import (
    ERR_INVALID_MESSAGE,
    ERR_MESSAGE_PARSE_FAILED,
)


class TestWebSocketHandler(AioHTTPTestCase):
    async def get_application(self):
        """Create test application."""
        from custom_components.spyster.game.state import GameState

        self.game_state = GameState()
        self.handler = WebSocketHandler(self.game_state)

        app = web.Application()
        app.router.add_get('/ws', self.handler.handle_connection)
        return app

    @unittest_run_loop
    async def test_connection_establishment(self):
        """Test WebSocket connection is established and tracked."""
        async with self.client.ws_connect('/ws') as ws:
            # Verify welcome message
            msg = await ws.receive_json()
            assert msg['type'] == 'welcome'
            assert 'connection_id' in msg
            assert 'server_version' in msg
            assert msg['server_version'] == '1.0.0'

            # Verify connection is tracked
            assert len(self.handler._connections) == 1

    @unittest_run_loop
    async def test_connection_cleanup(self):
        """Test connection is removed from pool on disconnect."""
        async with self.client.ws_connect('/ws') as ws:
            await ws.receive_json()  # Welcome message
            assert len(self.handler._connections) == 1

        # After context exit, connection should be cleaned up
        assert len(self.handler._connections) == 0

    @unittest_run_loop
    async def test_invalid_json(self):
        """Test malformed JSON triggers error response."""
        async with self.client.ws_connect('/ws') as ws:
            await ws.receive_json()  # Welcome message

            # Send invalid JSON
            await ws.send_str('{"type": "join", invalid}')

            # Expect error response
            msg = await ws.receive_json()
            assert msg['type'] == 'error'
            assert msg['code'] == ERR_MESSAGE_PARSE_FAILED
            assert 'message' in msg

    @unittest_run_loop
    async def test_missing_type_field(self):
        """Test message without 'type' field triggers error."""
        async with self.client.ws_connect('/ws') as ws:
            await ws.receive_json()  # Welcome message

            # Send valid JSON but no 'type'
            await ws.send_json({"name": "Alice"})

            # Expect error response
            msg = await ws.receive_json()
            assert msg['type'] == 'error'
            assert msg['code'] == ERR_INVALID_MESSAGE

    @unittest_run_loop
    async def test_multiple_connections(self):
        """Test multiple simultaneous connections are tracked."""
        async with self.client.ws_connect('/ws') as ws1:
            await ws1.receive_json()  # Welcome
            assert len(self.handler._connections) == 1

            async with self.client.ws_connect('/ws') as ws2:
                await ws2.receive_json()  # Welcome
                assert len(self.handler._connections) == 2

            assert len(self.handler._connections) == 1

        assert len(self.handler._connections) == 0
```

### Integration Tests

**Manual Testing Steps:**

1. **Connection Establishment**
   - Start Home Assistant with Spyster integration
   - Navigate to `/api/spyster/player`
   - Open DevTools → Network → WS
   - Verify WebSocket connection to `/api/spyster/ws`
   - Verify welcome message received
   - Verify connection status shows "Connected"

2. **Error Handling**
   - Open browser console
   - Send malformed message: `ws.send('invalid json')`
   - Verify error message appears in UI
   - Verify connection remains open
   - Send valid message after error works normally

3. **Multiple Connections**
   - Open `/api/spyster/player` in 3 different browser tabs
   - Verify all tabs connect successfully
   - Check server logs for connection count (should increment)
   - Close one tab
   - Verify server logs show disconnect and decremented count

### Performance Validation

**NFR2: WebSocket Latency < 100ms on local network**

```javascript
// Performance test script (run in browser console)
const measureLatency = async () => {
    const results = [];

    for (let i = 0; i < 10; i++) {
        const start = performance.now();
        ws.send(JSON.stringify({ type: 'ping' }));

        // Wait for ack response
        await new Promise(resolve => {
            const handler = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'ack') {
                    ws.removeEventListener('message', handler);
                    resolve();
                }
            };
            ws.addEventListener('message', handler);
        });

        const latency = performance.now() - start;
        results.push(latency);
    }

    const avg = results.reduce((a, b) => a + b) / results.length;
    const max = Math.max(...results);
    const min = Math.min(...results);

    console.log(`Average latency: ${avg.toFixed(2)}ms`);
    console.log(`Min: ${min.toFixed(2)}ms, Max: ${max.toFixed(2)}ms`);
    console.log(`Results:`, results.map(r => r.toFixed(2)));

    // Validate NFR2 compliance
    if (avg < 100) {
        console.log('✅ NFR2 PASSED: Average latency < 100ms');
    } else {
        console.warn('⚠️ NFR2 FAILED: Average latency >= 100ms');
    }
};

measureLatency();
```

**Expected Results:**
- Average latency < 100ms on local network (NFR2)
- Typical local network latency: 5-20ms
- Most latency from JavaScript execution, not network

---

## Definition of Done

- [ ] WebSocket endpoint registered at `/api/spyster/ws`
- [ ] Server tracks all active connections in connection pool
- [ ] Welcome message sent on connection establishment
- [ ] Malformed JSON triggers `ERR_MESSAGE_PARSE_FAILED` error
- [ ] Missing 'type' field triggers `ERR_INVALID_MESSAGE` error
- [ ] Connection cleanup on disconnect (remove from pool)
- [ ] Player UI shows real-time connection status indicator
- [ ] Error messages display in browser UI
- [ ] All unit tests pass (connection, cleanup, error handling)
- [ ] Manual testing confirms WebSocket connectivity
- [ ] Server logs show connection/disconnection events with counts
- [ ] Multiple simultaneous connections work correctly
- [ ] Code follows architecture patterns (snake_case, logging, error handling)
- [ ] Constants defined in `const.py` (no hardcoded values)

---

## Dependencies

### Blocked By
- **Story 1.1 (Integration Foundation)**: Requires `GameState` class to exist and be initialized in `hass.data[DOMAIN]` for WebSocketHandler constructor
- **Story 1.2 (Player/Host HTML Pages)**: Requires `player.html` to exist as the page where WebSocket connection is initiated

### Blocks
- **Story 2.2**: Player join flow needs WebSocket connection
- **Story 2.3**: Session management requires connection tracking
- **Story 2.4**: Disconnect detection needs connection pool

---

## Architecture Compliance

### Patterns Applied

**WebSocket Protocol (ARCH-12, ARCH-13):**
- Message format: `{"type": "...", ...payload}`
- Error format: `{"type": "error", "code": "...", "message": "..."}`
- All fields use snake_case
- **Note**: Welcome message (`type: "welcome"`) is a connection-level message, not part of game protocol. Used for connection handshake and debugging.

**Constants in const.py (ARCH-15):**
```python
WS_HEARTBEAT_TIMEOUT = 30  # WebSocket keepalive
ERR_INVALID_MESSAGE = "INVALID_MESSAGE"
ERR_MESSAGE_PARSE_FAILED = "MESSAGE_PARSE_FAILED"
ERROR_MESSAGES = {...}  # User-friendly error messages
```

**Logging Format (ARCH-16):**
```python
_LOGGER.info("WebSocket connected: %s (total connections: %d)", connection_id, len(self._connections))
_LOGGER.warning("Failed to parse JSON from %s: %s", connection_id, err)
```

**Code Organization (ARCH-14):**
- WebSocket handler in `server/websocket.py`
- Constants in `const.py` (no hardcoded values)
- Frontend in `www/js/player.js`
- Static assets in `www/css/styles.css`

---

## Notes for Developers

### Why aiohttp WebSocketResponse?

Home Assistant uses aiohttp for all HTTP/WebSocket handling. We leverage `aiohttp.web.WebSocketResponse` because:
- Native HA integration (no extra dependencies)
- Built-in heartbeat support (connection health checks)
- Async/await compatible with HA's event loop
- Proven in production HA integrations

### Connection Pool Design

The connection pool (`_connections` dict) uses `connection_id` keys rather than player names because:
- Connections exist before players join (before they have a name)
- Same player might reconnect with new connection (need to track both temporarily)
- Story 2.3 will link `PlayerSession.ws` to specific connections

### Error Recovery Philosophy

**Non-fatal errors (malformed messages):**
- Send error response
- Log warning
- Keep connection open
- Allow client to retry

**Fatal errors (authentication failures, rate limits - future):**
- Send error response
- Log error
- Close connection
- Client must reconnect

This story implements only non-fatal error handling. Fatal errors will be added in security hardening phase.

---

## Related Documentation

- **Architecture:** `/Volumes/My Passport/Spyster/_bmad-output/architecture.md` - Section: "WebSocket Message Protocol"
- **Project Context:** `/Volumes/My Passport/Spyster/_bmad-output/project-context.md` - Section: "WebSocket Rules"
- **Epic 2:** `/Volumes/My Passport/Spyster/_bmad-output/epics.md` - Lines 416-569
- **FR9-FR18:** Player connection requirements (disconnect detection, reconnection)
- **NFR2:** WebSocket latency < 100ms on local network

---

**Story Ready for Implementation** ✅
