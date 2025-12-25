"""WebSocket handler for real-time game communication."""
import asyncio
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict

from aiohttp import WSMsgType, web

from ..const import (
    DISCONNECT_GRACE_SECONDS,
    ERR_CONNECTION_LIMIT,
    ERR_GAME_ALREADY_STARTED,
    ERR_GAME_FULL,
    ERR_INVALID_MESSAGE,
    ERR_MESSAGE_PARSE_FAILED,
    ERR_NAME_INVALID,
    ERR_NOT_HOST,
    ERR_NOT_IN_GAME,
    ERROR_MESSAGES,
    MAX_CONNECTIONS,
    MAX_NAME_LENGTH,
    MAX_PLAYERS,
    MIN_NAME_LENGTH,
    WS_HEARTBEAT_TIMEOUT,
)
from ..game.player import PlayerSession
from ..game.state import GamePhase

if TYPE_CHECKING:
    from ..game.state import GameState

_LOGGER = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections for real-time game communication."""

    def __init__(self, game_state: "GameState"):
        """Initialize WebSocket handler.

        Args:
            game_state: Reference to active GameState instance
        """
        self.game_state = game_state
        self._connections: Dict[str, web.WebSocketResponse] = {}  # connection_id → ws
        self._ws_to_player: Dict[web.WebSocketResponse, "PlayerSession"] = {}  # ws → PlayerSession
        self._connection_counter = 0
        # Story 4.2: Periodic timer broadcast task
        self._timer_broadcast_task: asyncio.Task | None = None

    async def handle_connection(self, request: web.Request) -> web.WebSocketResponse:
        """Handle new WebSocket connection with session management (Story 2.3).

        Args:
            request: The WebSocket request

        Returns:
            WebSocketResponse object
        """
        from ..const import ERR_INVALID_TOKEN, ERR_SESSION_EXPIRED

        # Check connection pool limit (ARCH-12)
        if len(self._connections) >= MAX_CONNECTIONS:
            _LOGGER.warning("Connection limit reached: %d/%d", len(self._connections), MAX_CONNECTIONS)
            ws = web.WebSocketResponse(heartbeat=WS_HEARTBEAT_TIMEOUT)
            await ws.prepare(request)
            await ws.send_json({
                "type": "error",
                "code": ERR_CONNECTION_LIMIT,
                "message": ERROR_MESSAGES[ERR_CONNECTION_LIMIT]
            })
            await ws.close(code=1008, message=b"Connection limit reached")
            return ws

        ws = web.WebSocketResponse(heartbeat=WS_HEARTBEAT_TIMEOUT)
        prepared = await ws.prepare(request)

        # Verify WebSocket was prepared successfully (ARCH-12)
        if not prepared or ws.closed:
            _LOGGER.error("WebSocket preparation failed")
            return ws

        # Generate unique connection ID
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}"
        self._connections[connection_id] = ws

        _LOGGER.info(
            "WebSocket connected: %s (total connections: %d)",
            connection_id,
            len(self._connections),
        )

        # Story 2.3: Check for existing session token
        token = request.rel_url.query.get('token')

        if token:
            # Attempt session restoration
            success, error, session = self.game_state.restore_session(token, ws)

            if success:
                # Map WebSocket to player session
                self._ws_to_player[ws] = session

                # Send restored session state
                # FIXED: Use correct attribute name
                await ws.send_json({
                    "type": "session_restored",
                    "name": session.name,
                    "token": session.session_token,
                    "is_host": session.is_host
                })

                # Send current game state
                state = self.game_state.get_state(for_player=session.name)
                await ws.send_json({"type": "state", **state})

                # Broadcast to others that player reconnected
                await self.broadcast_state()

                _LOGGER.info("Player reconnected: %s", session.name)
            else:
                # Session invalid or expired - use consistent error format
                await self._send_error(ws, error)
                await ws.close(code=1008, message=b"Session invalid")
                return ws
        else:
            # No token - send welcome message for new connection
            await self._send_welcome(ws, connection_id)

        # Handle messages
        try:
            await self._message_loop(ws, connection_id)
        finally:
            # Cleanup on disconnect - fix race condition (ARCH-12)
            # Store player session reference before removing from connection pool
            player_session = self._ws_to_player.get(ws)

            # Remove connection from pool atomically
            if connection_id in self._connections:
                del self._connections[connection_id]

            # Remove WebSocket to player mapping
            if ws in self._ws_to_player:
                del self._ws_to_player[ws]

            # Story 2.4: Handle player disconnect after cleanup
            if player_session:
                await self._on_disconnect(player_session)

            _LOGGER.info(
                "WebSocket disconnected: %s (remaining: %d)",
                connection_id,
                len(self._connections),
            )

        return ws

    async def _send_welcome(
        self, ws: web.WebSocketResponse, connection_id: str
    ) -> None:
        """Send welcome message to newly connected client.

        Args:
            ws: WebSocket connection
            connection_id: Unique connection identifier
        """
        await ws.send_json(
            {
                "type": "welcome",
                "connection_id": connection_id,
                "server_version": "1.0.0",
                "game_active": self.game_state is not None,
            }
        )

    async def _message_loop(
        self, ws: web.WebSocketResponse, connection_id: str
    ) -> None:
        """Process incoming messages from WebSocket.

        Args:
            ws: WebSocket connection
            connection_id: Unique connection identifier
        """
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
        """Handle text message from client.

        Args:
            ws: WebSocket connection
            connection_id: Unique connection identifier
            data: Raw message data
        """
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

        # Story 2.4: Handle heartbeat messages
        if message_type == "heartbeat":
            await self._handle_heartbeat(connection_id, ws)
            return

        # Story 2.2: Handle player join
        if message_type == "join":
            await self._handle_join(ws, message)
            return

        # Story 2.6: Handle admin actions (host-only)
        if message_type == "admin":
            await self._handle_admin(ws, message)
            return

        # Story 3.1: Handle configuration updates (host-only)
        if message_type == "configure":
            await self._handle_configure(ws, message)
            return

        # Story 4.5: Handle call vote from any player
        if message_type == "call_vote":
            await self._handle_call_vote(ws, message)
            return

        # Story 5.3: Handle vote submission
        if message_type == "vote":
            await self._handle_vote(ws, message)
            return

        # Story 5.4: Handle spy location guess
        if message_type == "spy_guess":
            await self._handle_spy_guess(ws, message)
            return

        # Host join as player (allows host to participate in the game)
        if message_type == "host_join_as_player":
            await self._handle_host_join_as_player(ws, message)
            return

        # TODO: Route to other specific handlers based on message_type
        # For now, just acknowledge receipt
        await ws.send_json({"type": "ack", "received": message_type})

    async def _send_error(self, ws: web.WebSocketResponse, error_code: str) -> None:
        """Send error message to client.

        Args:
            ws: WebSocket connection
            error_code: Error code constant
        """
        await ws.send_json(
            {
                "type": "error",
                "code": error_code,
                "message": ERROR_MESSAGES.get(error_code, "Unknown error"),
            }
        )

    async def _handle_heartbeat(self, connection_id: str, ws: web.WebSocketResponse) -> None:
        """Handle heartbeat message from client (Story 2.4).

        Updates player's last heartbeat timestamp and cancels disconnect timer if active.

        Args:
            connection_id: Unique connection identifier
            ws: WebSocket connection (for authentication validation)
        """
        # SECURITY FIX: Validate WebSocket connection belongs to authenticated session
        player_session = self._ws_to_player.get(ws)

        if not player_session:
            # Heartbeat from unauthenticated connection - ignore silently
            return

        # Update last heartbeat timestamp
        player_session.last_heartbeat = datetime.now()

        # Cancel existing disconnect timer if reconnecting (ARCH-9)
        timer_name = f"disconnect_grace:{player_session.name}"
        if player_session.disconnect_timer and not player_session.disconnect_timer.done():
            player_session.disconnect_timer.cancel()
            player_session.disconnect_timer = None
            self.game_state.cancel_timer(timer_name)

        # If player was marked disconnected, restore to connected
        if not player_session.connected:
            player_session.connected = True
            # Restore WebSocket mapping (Story 2.5 fix)
            player_session.ws = ws
            self._ws_to_player[ws] = player_session
            _LOGGER.info("Player reconnected via heartbeat: %s", player_session.name)
            await self.broadcast_state()

    async def _on_disconnect(self, player_session) -> None:
        """Handle WebSocket close event - start disconnect grace timer (Story 2.4).

        Args:
            player_session: PlayerSession that disconnected
        """
        if not player_session:
            return

        _LOGGER.info("WebSocket closed for player: %s, starting grace timer", player_session.name)

        # ARCH-9 FIX: Use GameState.start_timer() for consistent timer management
        timer_name = f"disconnect_grace:{player_session.name}"

        # Create timer callback that calls _disconnect_grace_completion
        async def timer_callback(name: str) -> None:
            await self._disconnect_grace_completion(player_session)

        # Use GameState timer management (ARCH-9 requirement)
        self.game_state.start_timer(
            name=timer_name,
            duration=DISCONNECT_GRACE_SECONDS,  # NFR11: Use correct constant
            callback=timer_callback
        )

        # Store timer reference in player session for cancellation
        player_session.disconnect_timer = self.game_state._timers[timer_name]

    async def _disconnect_grace_completion(self, player_session) -> None:
        """Called when disconnect grace timer completes (Story 2.4).

        Timer cleanup is handled by GameState.start_timer() per ARCH-9.

        Args:
            player_session: PlayerSession to mark as disconnected
        """
        # Grace period expired without reconnection
        # Story 2.5: Call state's _on_player_disconnect to start reconnection window
        await self.game_state._on_player_disconnect(player_session.name)
        _LOGGER.info("Player disconnected: %s (grace period expired)", player_session.name)

        # Clear player session reference (timer cleanup handled by GameState)
        player_session.disconnect_timer = None

        # Broadcast updated state to all clients (NFR11 requirement)
        await self.broadcast_state()

    async def _handle_join(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle player join request (Story 2.2 + 2.3).

        Validates name, phase, capacity, and handles FR18 duplicate name replacement.
        Creates session token for reconnection (Story 2.3).

        Args:
            ws: WebSocket connection
            data: Join message data containing 'name' and optional 'is_host' fields
        """
        name = data.get("name", "").strip()
        is_host = data.get("is_host", False)

        # Validate name length
        if not name or len(name) < MIN_NAME_LENGTH or len(name) > MAX_NAME_LENGTH:
            await self._send_error(ws, ERR_NAME_INVALID)
            return

        # SECURITY FIX: Sanitize name to prevent XSS attacks
        # Reject names containing HTML/script tags or special characters
        import re as regex_module
        if regex_module.search(r'[<>"\'&;]', name):
            await self._send_error(ws, ERR_NAME_INVALID)
            return

        # Check game phase - must be in LOBBY
        if self.game_state.phase != GamePhase.LOBBY:
            await self._send_error(ws, ERR_GAME_ALREADY_STARTED)
            return

        # Check game capacity (before adding player)
        if len(self.game_state.players) >= MAX_PLAYERS and name not in self.game_state.players:
            await self._send_error(ws, ERR_GAME_FULL)
            return

        # Story 2.3: Add player (handles FR18 duplicate name replacement)
        success, error, session = self.game_state.add_player(name, is_host, ws)

        if success:
            # Map WebSocket to player session
            self._ws_to_player[ws] = session

            # Update host_id when the actual host joins
            if is_host:
                self.game_state.host_id = name
                _LOGGER.info("Host registered: %s", name)

            # FIXED: Use correct message type "join_success" and field names per spec
            await ws.send_json({
                "type": "join_success",
                "player_name": session.name,
                "session_token": session.session_token,
                "is_host": session.is_host
            })

            # Send initial state
            state = self.game_state.get_state(for_player=session.name)
            await ws.send_json({"type": "state", **state})

            # Broadcast to all players
            await self.broadcast_state()

            _LOGGER.info(
                "Player joined: %s (total: %d)",
                name,
                len(self.game_state.players)
            )
        else:
            await self._send_error(ws, error)

    async def _handle_host_join_as_player(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle host joining the game as a player.

        This allows the host display to also participate as a player in the game.

        Args:
            ws: WebSocket connection (must be the host)
            data: Message data containing 'name' field
        """
        import re as regex_module

        # Verify this is the host connection
        player_session = self._ws_to_player.get(ws)
        if not player_session or not player_session.is_host:
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "Only the host can use this feature"
            })
            return

        name = data.get("name", "").strip()

        # Validate name length
        if not name or len(name) < MIN_NAME_LENGTH or len(name) > MAX_NAME_LENGTH:
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "Please enter a name (1-20 characters)"
            })
            return

        # SECURITY: Sanitize name to prevent XSS
        if regex_module.search(r'[<>"\'&;]', name):
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "Name contains invalid characters"
            })
            return

        # Check game phase - must be in LOBBY
        if self.game_state.phase != GamePhase.LOBBY:
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "Game has already started"
            })
            return

        # Check if name is already taken (by someone other than HostDisplay)
        if name in self.game_state.players and name != "HostDisplay":
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "That name is already taken"
            })
            return

        # Check game capacity
        current_player_count = sum(1 for p in self.game_state.players.values() if p.name != "HostDisplay")
        if current_player_count >= MAX_PLAYERS:
            await ws.send_json({
                "type": "host_join_response",
                "success": False,
                "error": "Game is full"
            })
            return

        # Update the host's name from "HostDisplay" to the chosen name
        old_name = player_session.name
        if old_name in self.game_state.players:
            # Remove the old HostDisplay entry
            del self.game_state.players[old_name]

        # Update session with new name
        player_session.name = name

        # Add as player with the new name
        self.game_state.players[name] = player_session

        # Update host_id to match the new name
        self.game_state.host_id = name

        _LOGGER.info("Host joined as player: %s", name)

        # Send success response
        await ws.send_json({
            "type": "host_join_response",
            "success": True,
            "player_name": name
        })

        # Broadcast updated state to all players
        await self.broadcast_state()

    async def broadcast_state(self) -> None:
        """Broadcast personalized state to all players (Story 3.4).

        CRITICAL: Each player receives a personalized payload.
        NEVER broadcast the same state to all players (security violation).

        SECURITY: Cross-validates WebSocket ownership before sending.
        """
        failed_broadcasts = []

        # Each player gets personalized state (Story 3.4)
        for player_name, player in self.game_state.players.items():
            if player.ws and not player.ws.closed:
                # SECURITY FIX: Validate WebSocket actually belongs to this player
                mapped_player = self._ws_to_player.get(player.ws)
                if mapped_player and mapped_player.name != player_name:
                    _LOGGER.error(
                        "WebSocket ownership mismatch: expected %s, got %s",
                        player_name,
                        mapped_player.name
                    )
                    failed_broadcasts.append(player_name)
                    continue

                try:
                    # Per-player filtering happens here (Story 3.4)
                    state = self.game_state.get_state(for_player=player_name)
                    await player.ws.send_json({"type": "state", **state})
                except Exception as err:
                    _LOGGER.warning("Failed to send state to %s: %s", player_name, err)
                    failed_broadcasts.append(player_name)

        # Log aggregate broadcast failures for monitoring
        if failed_broadcasts:
            _LOGGER.error("Broadcast failed for %d players: %s", len(failed_broadcasts), failed_broadcasts)

    async def start_timer_broadcasts(self) -> None:
        """Start periodic timer broadcasts for real-time countdown (Story 4.2, NFR5).

        Broadcasts game state every 1 second during QUESTIONING and VOTE phases
        to ensure all clients see synchronized timer countdown (±1 second accuracy).
        """
        if self._timer_broadcast_task and not self._timer_broadcast_task.done():
            # Already running
            return

        async def broadcast_loop():
            """Background task that broadcasts state every second during timed phases."""
            try:
                while True:
                    await asyncio.sleep(1.0)  # Broadcast every 1 second (NFR5)

                    # Only broadcast if in a timed phase
                    if self.game_state.phase in [GamePhase.QUESTIONING, GamePhase.VOTE]:
                        await self.broadcast_state()
            except asyncio.CancelledError:
                _LOGGER.debug("Timer broadcast task cancelled")
                raise
            except Exception as err:
                _LOGGER.error("Timer broadcast loop error: %s", err, exc_info=True)

        self._timer_broadcast_task = asyncio.create_task(broadcast_loop())
        _LOGGER.info("Timer broadcasts started")

    async def stop_timer_broadcasts(self) -> None:
        """Stop periodic timer broadcasts (Story 4.2)."""
        if self._timer_broadcast_task and not self._timer_broadcast_task.done():
            self._timer_broadcast_task.cancel()
            try:
                await self._timer_broadcast_task
            except asyncio.CancelledError:
                pass
            self._timer_broadcast_task = None
            _LOGGER.info("Timer broadcasts stopped")

    def _get_player_by_ws(self, ws: web.WebSocketResponse) -> 'PlayerSession | None':
        """Get player session by WebSocket connection (Story 2.6).

        Args:
            ws: WebSocket connection

        Returns:
            PlayerSession if found, None otherwise
        """
        return self._ws_to_player.get(ws)

    async def _handle_admin(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle admin actions from host (Story 2.6).

        Args:
            ws: WebSocket connection
            data: Admin message data
        """
        player = self._get_player_by_ws(ws)
        if not player:
            await self._send_error(ws, ERR_NOT_IN_GAME)
            return

        # FIX: Cross-validate host status with game_state.host_id for security
        if not player.is_host:
            await self._send_error(ws, ERR_NOT_HOST)
            return

        # Additional security check: verify against game_state host_id
        if self.game_state.host_id and self.game_state.host_id != player.name:
            _LOGGER.warning(
                "Host validation mismatch: player.is_host=%s but host_id=%s (player=%s)",
                player.is_host,
                self.game_state.host_id,
                player.name
            )
            await self._send_error(ws, ERR_NOT_HOST)
            return

        action = data.get('action')

        if action == 'remove_player':
            await self._handle_remove_player(ws, data)
        elif action == 'start_game':
            await self._handle_start_game(ws)
        elif action == 'advance_turn':
            await self._handle_advance_turn(ws)
        # Future admin actions: pause_game, etc.
        else:
            _LOGGER.warning("Unknown admin action: %s", action)
            await self._send_error(ws, ERR_INVALID_MESSAGE)

    async def _handle_remove_player(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle player removal admin action (Story 2.6).

        Args:
            ws: WebSocket connection
            data: Message data containing player_name
        """
        player = self._get_player_by_ws(ws)
        if not player:
            await self._send_error(ws, ERR_NOT_IN_GAME)
            return

        target_player = data.get('player_name')
        if not target_player:
            await self._send_error(ws, ERR_INVALID_MESSAGE)
            return

        # Pass requester name to business logic for permission check
        success, error = self.game_state.remove_player(target_player, requester_name=player.name)
        if not success:
            await self._send_error(ws, error)
            return

        _LOGGER.info('Admin removed player: %s by %s', target_player, player.name)
        await self.broadcast_state()

    async def _handle_start_game(self, ws: web.WebSocketResponse) -> None:
        """Handle game start request from host (Story 3.2 + 4.2).

        Args:
            ws: WebSocket connection
        """
        success, error_code = self.game_state.start_game()

        if not success:
            _LOGGER.info("Game start failed: %s", error_code)
            await self._send_error(ws, error_code)
            return

        # Story 4.2: Start periodic timer broadcasts for real-time countdown (NFR5)
        await self.start_timer_broadcasts()

        # Game started successfully - broadcast to all players
        _LOGGER.info("Game started - transitioning to ROLES phase")
        await self.broadcast_state()

    async def _handle_advance_turn(self, ws: web.WebSocketResponse) -> None:
        """Handle turn advancement request from host (Story 4.3: AC5).

        Args:
            ws: WebSocket connection
        """
        self.game_state.advance_turn()

        _LOGGER.info("Turn advanced by host")
        await self.broadcast_state()

    async def _handle_configure(self, ws: web.WebSocketResponse, data: dict) -> None:
        """
        Handle configuration update from host (Story 3.1).

        Message format:
            {"type": "configure", "field": "round_duration_minutes", "value": 10}

        Args:
            ws: WebSocket connection
            data: Configuration message data
        """
        player = self._get_player_by_ws(ws)
        if not player:
            await self._send_error(ws, ERR_NOT_IN_GAME)
            return

        # Only host can configure
        if not player.is_host:
            await self._send_error(ws, ERR_NOT_HOST)
            return

        field = data.get("field")
        value = data.get("value")

        if not field or value is None:
            await ws.send_json({
                "type": "error",
                "code": ERR_INVALID_MESSAGE,
                "message": "Missing field or value in configure message."
            })
            return

        # Update configuration
        success, error = self.game_state.update_config(field, value)

        if not success:
            await ws.send_json({
                "type": "error",
                "code": error,
                "message": ERROR_MESSAGES.get(error, "Configuration update failed.")
            })
            return

        _LOGGER.info("Configuration updated by host %s: %s = %s", player.name, field, value)

        # Broadcast updated state to all players
        await self.broadcast_state()

    async def _handle_call_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
        """
        Handle call_vote message from player.

        FR29: Any player can call for a vote during questioning.

        Args:
            ws: Player's WebSocket connection
            data: Message payload (empty for call_vote)
        """
        from ..const import ERR_NOT_CONNECTED, ERROR_MESSAGES

        # Verify player is connected
        if ws not in self._ws_to_player:
            await ws.send_json({
                "type": "error",
                "code": ERR_NOT_CONNECTED,
                "message": ERROR_MESSAGES[ERR_NOT_CONNECTED]
            })
            return

        player = self._ws_to_player[ws]

        _LOGGER.info("Player %s called vote", player.name)

        # Call vote on game state (Story 4.5: AC6 - pass caller name for attribution)
        success, error_code = self.game_state.call_vote(caller_name=player.name)

        if not success:
            await ws.send_json({
                "type": "error",
                "code": error_code,
                "message": ERROR_MESSAGES.get(error_code, "Unknown error")
            })
            return

        # Broadcast updated state to all clients (ARCH-14)
        await self.broadcast_state()

    async def _handle_vote(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle vote submission (Story 5.3).

        Args:
            ws: Player's WebSocket connection
            data: Message payload {target, confidence}
        """
        from ..const import (
            ERR_NOT_IN_GAME,
            ERR_NO_TARGET_SELECTED,
            ERROR_MESSAGES,
        )
        from ..game.state import GamePhase

        # Verify player is in game
        if ws not in self._ws_to_player:
            await ws.send_json({
                "type": "error",
                "code": ERR_NOT_IN_GAME,
                "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
            })
            return

        player = self._ws_to_player[ws]

        # Extract vote data
        target = data.get("target")
        confidence = data.get("confidence", 1)

        # Validate target provided
        if not target:
            await ws.send_json({
                "type": "error",
                "code": ERR_NO_TARGET_SELECTED,
                "message": ERROR_MESSAGES[ERR_NO_TARGET_SELECTED]
            })
            return

        # Record vote
        success, error_code = self.game_state.record_vote(player.name, target, confidence)

        if not success:
            await ws.send_json({
                "type": "error",
                "code": error_code,
                "message": ERROR_MESSAGES.get(error_code, "Could not record vote.")
            })
            return

        _LOGGER.info("Vote submitted: %s -> %s (confidence: %d)", player.name, target, confidence)

        # Broadcast updated state (includes vote count)
        await self.broadcast_state()

        # Check if all votes submitted - trigger reveal
        if self.game_state._all_votes_submitted():
            await self._trigger_reveal()

    async def _trigger_reveal(self) -> None:
        """Trigger transition to REVEAL phase (Story 5.3)."""
        from ..game.state import GamePhase

        if self.game_state.phase != GamePhase.VOTE:
            return

        _LOGGER.info("Transitioning to REVEAL phase (all votes in)")
        self.game_state.phase = GamePhase.REVEAL

        # Broadcast the phase change
        await self.broadcast_state()

    async def _handle_spy_guess(self, ws: web.WebSocketResponse, data: dict) -> None:
        """Handle spy location guess (Story 5.4).

        Args:
            ws: Player's WebSocket connection
            data: Message payload {location_id}
        """
        from ..const import (
            ERR_NOT_IN_GAME,
            ERR_INVALID_LOCATION,
            ERROR_MESSAGES,
        )
        from ..game.state import GamePhase

        # Verify player is in game
        if ws not in self._ws_to_player:
            await ws.send_json({
                "type": "error",
                "code": ERR_NOT_IN_GAME,
                "message": ERROR_MESSAGES[ERR_NOT_IN_GAME]
            })
            return

        player = self._ws_to_player[ws]
        location_id = data.get("location_id")

        if not location_id:
            await ws.send_json({
                "type": "error",
                "code": ERR_INVALID_LOCATION,
                "message": ERROR_MESSAGES[ERR_INVALID_LOCATION]
            })
            return

        # Record spy guess
        success, error_code = self.game_state.record_spy_guess(player.name, location_id)

        if not success:
            await ws.send_json({
                "type": "error",
                "code": error_code,
                "message": ERROR_MESSAGES.get(error_code, "Could not record guess.")
            })
            return

        _LOGGER.info("Spy guess submitted: %s -> %s", player.name, location_id)

        # Spy guess triggers immediate transition to REVEAL
        self.game_state.phase = GamePhase.REVEAL

        # Broadcast state (spy guess ends voting)
        await self.broadcast_state()

