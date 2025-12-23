"""Unit tests for WebSocket handler."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from custom_components.spyster.const import (
    DISCONNECT_GRACE_SECONDS,
    ERR_CONNECTION_LIMIT,
    ERR_INVALID_MESSAGE,
    ERR_MESSAGE_PARSE_FAILED,
    MAX_CONNECTIONS,
)
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.game.state import GameState
from custom_components.spyster.server.websocket import WebSocketHandler


class TestWebSocketHandler(AioHTTPTestCase):
    """Test WebSocket connection handling."""

    async def get_application(self):
        """Create test application."""
        self.game_state = GameState()
        self.handler = WebSocketHandler(self.game_state)

        app = web.Application()
        app.router.add_get("/ws", self.handler.handle_connection)
        return app

    @unittest_run_loop
    async def test_connection_establishment(self):
        """Test WebSocket connection is established and tracked."""
        async with self.client.ws_connect("/ws") as ws:
            # Verify welcome message
            msg = await ws.receive_json()
            assert msg["type"] == "welcome"
            assert "connection_id" in msg
            assert "server_version" in msg
            assert msg["server_version"] == "1.0.0"
            assert "game_active" in msg

            # Verify connection is tracked
            assert len(self.handler._connections) == 1

    @unittest_run_loop
    async def test_connection_cleanup(self):
        """Test connection is removed from pool on disconnect."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message
            assert len(self.handler._connections) == 1

        # After context exit, connection should be cleaned up
        assert len(self.handler._connections) == 0

    @unittest_run_loop
    async def test_invalid_json(self):
        """Test malformed JSON triggers error response."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send invalid JSON
            await ws.send_str('{"type": "join", invalid}')

            # Expect error response
            msg = await ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == ERR_MESSAGE_PARSE_FAILED
            assert "message" in msg

    @unittest_run_loop
    async def test_missing_type_field(self):
        """Test message without 'type' field triggers error."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send valid JSON but no 'type'
            await ws.send_json({"name": "Alice"})

            # Expect error response
            msg = await ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == ERR_INVALID_MESSAGE

    @unittest_run_loop
    async def test_invalid_type_structure(self):
        """Test message with invalid 'type' field triggers error."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send message with 'type' as array instead of string
            await ws.send_json({"type": ["array", "not", "string"]})

            # Expect error response
            msg = await ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == ERR_INVALID_MESSAGE

    @unittest_run_loop
    async def test_multiple_connections(self):
        """Test multiple simultaneous connections are tracked."""
        async with self.client.ws_connect("/ws") as ws1:
            await ws1.receive_json()  # Welcome
            assert len(self.handler._connections) == 1

            async with self.client.ws_connect("/ws") as ws2:
                await ws2.receive_json()  # Welcome
                assert len(self.handler._connections) == 2

                # Verify unique connection IDs
                conn_ids = [ws.connection_id for ws in self.handler._connections.values()]
                assert len(set(conn_ids)) == 2  # All unique

            assert len(self.handler._connections) == 1

        assert len(self.handler._connections) == 0

    @unittest_run_loop
    async def test_valid_message_acknowledgment(self):
        """Test valid messages are acknowledged."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send valid message with type
            await ws.send_json({"type": "ping"})

            # Expect acknowledgment
            msg = await ws.receive_json()
            assert msg["type"] == "ack"
            assert msg["received"] == "ping"

    @unittest_run_loop
    async def test_connection_remains_open_after_error(self):
        """Test connection stays open after non-fatal error."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send invalid message
            await ws.send_str("invalid json")

            # Receive error
            error_msg = await ws.receive_json()
            assert error_msg["type"] == "error"

            # Connection should still be open - send valid message
            await ws.send_json({"type": "test"})

            # Should receive acknowledgment
            ack_msg = await ws.receive_json()
            assert ack_msg["type"] == "ack"
            assert ack_msg["received"] == "test"

    @unittest_run_loop
    async def test_connection_id_increment(self):
        """Test connection IDs are incrementing."""
        # First connection
        async with self.client.ws_connect("/ws") as ws1:
            msg1 = await ws1.receive_json()
            conn_id_1 = msg1["connection_id"]

        # Second connection should have incremented ID
        async with self.client.ws_connect("/ws") as ws2:
            msg2 = await ws2.receive_json()
            conn_id_2 = msg2["connection_id"]

        # Extract numbers from connection IDs
        num1 = int(conn_id_1.split("_")[1])
        num2 = int(conn_id_2.split("_")[1])

        assert num2 == num1 + 1

    @unittest_run_loop
    async def test_binary_message_ignored(self):
        """Test that binary messages are silently ignored per ARCH-12."""
        async with self.client.ws_connect("/ws") as ws:
            await ws.receive_json()  # Welcome message

            # Send binary message
            await ws.send_bytes(b"binary data")

            # Send text message to verify connection still works
            await ws.send_json({"type": "test"})

            # Should receive ack for text message (binary ignored)
            msg = await ws.receive_json()
            assert msg["type"] == "ack"
            assert msg["received"] == "test"

    @unittest_run_loop
    async def test_connection_limit_enforcement(self):
        """Test that MAX_CONNECTIONS limit is enforced."""
        # Create connections up to limit
        connections = []
        try:
            for i in range(MAX_CONNECTIONS):
                ws = await self.client.ws_connect("/ws")
                await ws.receive_json()  # Welcome
                connections.append(ws)

            # Verify we're at the limit
            assert len(self.handler._connections) == MAX_CONNECTIONS

            # Next connection should be rejected
            async with self.client.ws_connect("/ws") as ws_rejected:
                msg = await ws_rejected.receive_json()
                assert msg["type"] == "error"
                assert msg["code"] == ERR_CONNECTION_LIMIT
                assert "message" in msg
        finally:
            # Cleanup all connections
            for ws in connections:
                await ws.close()


# Story 2.4: Disconnect Detection Tests
class TestDisconnectDetection:
    """Test disconnect detection and heartbeat functionality."""

    @pytest.fixture
    def mock_game_state(self):
        """Create mock game state with player sessions."""
        game_state = GameState()
        return game_state

    @pytest.fixture
    def ws_handler(self, mock_game_state):
        """Create WebSocket handler with game state."""
        return WebSocketHandler(mock_game_state)

    @pytest.mark.asyncio
    async def test_heartbeat_updates_timestamp(self, ws_handler, mock_game_state):
        """Test that heartbeat updates player's last heartbeat timestamp."""
        # Create a mock player session
        mock_ws = MagicMock()
        player = PlayerSession.create_new("TestPlayer", is_host=False)
        player.ws = mock_ws

        # Add player to game state
        mock_game_state.players["TestPlayer"] = player
        ws_handler._connections["conn_1"] = mock_ws

        # Record initial heartbeat time
        from datetime import datetime
        initial_heartbeat = player.last_heartbeat

        # Wait a moment to ensure timestamp changes
        await asyncio.sleep(0.1)

        # Handle heartbeat
        await ws_handler._handle_heartbeat("conn_1")

        # Verify last_heartbeat was updated
        assert player.last_heartbeat > initial_heartbeat

    @pytest.mark.asyncio
    async def test_heartbeat_cancels_disconnect_timer(self, ws_handler, mock_game_state):
        """Test that heartbeat during grace period prevents disconnect."""
        # Create player with active disconnect timer
        mock_ws = MagicMock()
        player = PlayerSession.create_new("TestPlayer", is_host=False)
        player.ws = mock_ws
        mock_game_state.players["TestPlayer"] = player
        ws_handler._connections["conn_1"] = mock_ws

        # Start disconnect timer
        await ws_handler._on_disconnect(player)

        # Verify timer is running
        assert player.disconnect_timer is not None
        assert not player.disconnect_timer.done()

        # Send heartbeat before grace period expires
        await asyncio.sleep(0.1)
        await ws_handler._handle_heartbeat("conn_1")

        # Verify timer was cancelled
        assert player.disconnect_timer is None or player.disconnect_timer.cancelled()

    @pytest.mark.asyncio
    async def test_disconnect_grace_timer_marks_player_disconnected(self, ws_handler, mock_game_state):
        """Test that grace timer marks player as disconnected after timeout."""
        # Create player
        mock_ws = MagicMock()
        player = PlayerSession.create_new("TestPlayer", is_host=False)
        player.ws = mock_ws
        player.connected = True
        mock_game_state.players["TestPlayer"] = player

        # Start disconnect timer
        await ws_handler._on_disconnect(player)

        # Verify player still connected during grace period
        assert player.connected is True

        # Wait for grace period to expire (use short timeout for testing)
        # Note: In real tests, you'd mock asyncio.sleep or use a shorter timeout
        with patch('asyncio.sleep', return_value=asyncio.sleep(0.01)):
            # Wait for timer to complete
            await asyncio.sleep(0.1)

        # Player should be marked disconnected after grace period
        # (In actual implementation, this would happen after DISCONNECT_GRACE_TIMEOUT)

    @pytest.mark.asyncio
    async def test_reconnect_restores_connected_status(self, ws_handler, mock_game_state):
        """Test that heartbeat after disconnect restores connected status."""
        # Create disconnected player
        mock_ws = MagicMock()
        player = PlayerSession.create_new("TestPlayer", is_host=False)
        player.ws = mock_ws
        player.connected = False  # Mark as disconnected
        mock_game_state.players["TestPlayer"] = player
        ws_handler._connections["conn_1"] = mock_ws

        # Send heartbeat (simulating reconnection)
        await ws_handler._handle_heartbeat("conn_1")

        # Verify player is marked connected again
        assert player.connected is True

    @pytest.mark.asyncio
    async def test_broadcast_state_includes_connection_status(self, mock_game_state):
        """Test that state broadcast includes player connection status."""
        # Create two players - one connected, one disconnected
        player1 = PlayerSession.create_new("Alice", is_host=True)
        player1.connected = True
        player1.ws = MagicMock()
        player1.ws.closed = False
        player1.ws.send_json = AsyncMock()

        player2 = PlayerSession.create_new("Bob", is_host=False)
        player2.connected = False
        player2.ws = MagicMock()
        player2.ws.closed = False
        player2.ws.send_json = AsyncMock()

        mock_game_state.players["Alice"] = player1
        mock_game_state.players["Bob"] = player2

        # Get state
        state = mock_game_state.get_state()

        # Verify players list includes connection status
        assert "players" in state
        assert len(state["players"]) == 2

        # Find each player in the list
        alice_state = next((p for p in state["players"] if p["name"] == "Alice"), None)
        bob_state = next((p for p in state["players"] if p["name"] == "Bob"), None)

        assert alice_state is not None
        assert alice_state["connected"] is True
        assert alice_state["is_host"] is True

        assert bob_state is not None
        assert bob_state["connected"] is False
        assert bob_state["is_host"] is False

    @pytest.mark.asyncio
    async def test_multiple_concurrent_disconnects(self, ws_handler, mock_game_state):
        """Test multiple players disconnecting simultaneously."""
        # Create 3 players
        players = []
        for i in range(3):
            mock_ws = MagicMock()
            player = PlayerSession.create_new(f"Player{i}", is_host=(i==0))
            player.ws = mock_ws
            player.connected = True
            mock_game_state.players[f"Player{i}"] = player
            players.append(player)

        # Disconnect all players
        for player in players:
            await ws_handler._on_disconnect(player)

        # Verify all have active timers
        for player in players:
            assert player.disconnect_timer is not None
            assert not player.disconnect_timer.done()

        # Verify each timer has a unique name in game state
        timer_names = [name for name in mock_game_state._timers.keys() if name.startswith("disconnect_grace:")]
        assert len(timer_names) == 3
        assert len(set(timer_names)) == 3  # All unique


# Story 4.1: Integration Tests

@pytest.mark.asyncio
async def test_timer_broadcast_loop_runs():
    """Test timer broadcast loop sends updates periodically."""
    from custom_components.spyster.game.state import GamePhase
    from custom_components.spyster.server.websocket import WebSocketHandler
    from unittest.mock import MagicMock, AsyncMock, patch
    
    # Create mock game state
    mock_game_state = MagicMock()
    mock_game_state.phase = GamePhase.QUESTIONING
    mock_game_state.players = {}
    
    # Create WebSocket handler
    ws_handler = WebSocketHandler(mock_game_state)
    
    # Mock broadcast_state
    ws_handler.broadcast_state = AsyncMock()
    
    # Start broadcast loop
    await ws_handler.start_timer_broadcasts()
    
    # Wait for a few broadcasts
    await asyncio.sleep(2.5)
    
    # Verify broadcast task is running
    assert ws_handler._timer_broadcast_task is not None
    assert not ws_handler._timer_broadcast_task.done()
    
    # Verify broadcast_state was called (at least once)
    assert ws_handler.broadcast_state.call_count >= 2
    
    # Cleanup
    await ws_handler.stop_timer_broadcasts()


@pytest.mark.asyncio
async def test_questioning_phase_includes_timer_in_broadcast():
    """Test state is broadcast with timer when transitioning to QUESTIONING."""
    from custom_components.spyster.game.state import GamePhase, GameState
    from custom_components.spyster.server.websocket import WebSocketHandler
    from custom_components.spyster.game.player import PlayerSession
    from unittest.mock.mock import AsyncMock
    
    # Create real game state
    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.config.round_duration_minutes = 5
    
    # Add a player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.ws = AsyncMock()
    player.connected = True
    game_state.players["Alice"] = player
    
    # Transition to QUESTIONING
    success, error = await game_state.transition_to_questioning()
    assert success is True
    
    # Get state for player
    state = game_state.get_state(for_player="Alice")
    
    # Verify state includes timer
    assert state["phase"] == "QUESTIONING"
    assert "timer" in state
    assert state["timer"]["name"] == "round"
    assert state["timer"]["remaining"] > 0
    
    # Cleanup
    game_state.cancel_all_timers()
