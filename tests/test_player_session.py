"""Unit tests for player session management (Story 2.3)."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import pytest

from custom_components.spyster.const import (
    ERR_INVALID_TOKEN,
    ERR_SESSION_EXPIRED,
    RECONNECT_WINDOW_SECONDS,
)
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.game.state import GameState


class TestPlayerSession:
    """Test PlayerSession class."""

    def test_session_creation(self):
        """Test that new sessions generate unique tokens."""
        session1 = PlayerSession.create_new("Alice")
        session2 = PlayerSession.create_new("Bob")

        assert session1.session_token != session2.session_token
        assert len(session1.session_token) >= 43  # 32 bytes = 256 bits -> ~43 base64 chars
        assert session1.name == "Alice"
        assert session2.name == "Bob"
        assert session1.connected is True
        assert session2.connected is True

    def test_session_token_format(self):
        """Test that session tokens are URL-safe."""
        session = PlayerSession.create_new("TestPlayer")

        # Token should be URL-safe (no special characters that need encoding)
        assert all(c.isalnum() or c in '-_' for c in session.session_token)

    def test_heartbeat_update(self):
        """Test heartbeat timestamp update."""
        session = PlayerSession.create_new("Alice")
        original_heartbeat = session.last_heartbeat

        # Wait a tiny bit
        import time
        time.sleep(0.01)

        session.update_heartbeat()
        assert session.last_heartbeat > original_heartbeat

    def test_disconnect(self):
        """Test player disconnect."""
        mock_ws = Mock()
        session = PlayerSession.create_new("Alice")
        session.ws = mock_ws

        session.disconnect()

        assert session.connected is False
        assert session.ws is None

    def test_reconnect(self):
        """Test player reconnect."""
        session = PlayerSession.create_new("Alice")
        session.disconnect()

        assert session.connected is False

        new_ws = Mock()
        session.reconnect(new_ws)

        assert session.connected is True
        assert session.ws == new_ws

    def test_host_flag(self):
        """Test host flag during session creation."""
        host_session = PlayerSession.create_new("Host", is_host=True)
        player_session = PlayerSession.create_new("Player", is_host=False)

        assert host_session.is_host is True
        assert player_session.is_host is False


class TestGameStateSessionManagement:
    """Test GameState session management methods."""

    def test_add_player_creates_session(self):
        """Test that adding a player creates a session."""
        game_state = GameState()
        mock_ws = Mock()

        success, error, session = game_state.add_player("Alice", is_host=True, ws=mock_ws)

        assert success is True
        assert error is None
        assert session is not None
        assert session.name == "Alice"
        assert session.is_host is True
        assert session.ws == mock_ws
        assert "Alice" in game_state.players
        assert session.session_token in game_state.sessions
        assert game_state.player_count == 1

    def test_duplicate_name_replacement(self):
        """Test FR18: Duplicate session prevention."""
        game_state = GameState()

        # Add first player
        success1, _, session1 = game_state.add_player("Alice")
        assert success1
        token1 = session1.session_token

        # Add player with same name
        success2, _, session2 = game_state.add_player("Alice")
        assert success2
        token2 = session2.session_token

        # Tokens should be different
        assert token1 != token2

        # Only one session should exist
        assert len(game_state.players) == 1
        assert len(game_state.sessions) == 1

        # Old token should be invalid
        assert game_state.get_session_by_token(token1) is None

        # New token should be valid
        assert game_state.get_session_by_token(token2) == session2

    def test_get_session_by_token(self):
        """Test session retrieval by token."""
        game_state = GameState()
        _, _, session = game_state.add_player("Alice")

        retrieved = game_state.get_session_by_token(session.session_token)

        assert retrieved == session
        assert retrieved.name == "Alice"

    def test_get_session_by_invalid_token(self):
        """Test session retrieval with invalid token."""
        game_state = GameState()

        retrieved = game_state.get_session_by_token("invalid_token_xyz")

        assert retrieved is None

    def test_session_restoration(self):
        """Test successful session restoration."""
        game_state = GameState()

        # Create session
        _, _, session = game_state.add_player("Alice")
        token = session.session_token

        # Simulate disconnect
        session.disconnect()

        # Restore session
        mock_ws = Mock()
        success, error, restored = game_state.restore_session(token, mock_ws)

        assert success is True
        assert error is None
        assert restored.name == "Alice"
        assert restored.connected is True
        assert restored.ws == mock_ws

    def test_session_restoration_invalid_token(self):
        """Test session restoration with invalid token."""
        game_state = GameState()

        mock_ws = Mock()
        success, error, restored = game_state.restore_session("invalid_token", mock_ws)

        assert success is False
        assert error == ERR_INVALID_TOKEN
        assert restored is None

    def test_session_expiry(self):
        """Test session expiry after reconnection window."""
        import time
        game_state = GameState()

        # Create and disconnect session
        _, _, session = game_state.add_player("Alice")
        token = session.session_token
        session.disconnect()

        # FIXED: Simulate time passing by manipulating disconnected_at (not last_heartbeat)
        # Set disconnected_at to 6 minutes ago (beyond 5-minute window)
        session.disconnected_at = time.time() - (RECONNECT_WINDOW_SECONDS + 60)

        # Try to restore
        mock_ws = Mock()
        success, error, _ = game_state.restore_session(token, mock_ws)

        assert success is False
        assert error == ERR_SESSION_EXPIRED

        # Session should be cleaned up
        assert token not in game_state.sessions
        assert "Alice" not in game_state.players

    def test_session_valid_within_window(self):
        """Test session is valid within reconnection window."""
        import time
        game_state = GameState()

        # Create and disconnect session
        _, _, session = game_state.add_player("Alice")
        session.disconnect()

        # FIXED: Set disconnected_at to 2 minutes ago (within 5 minute window)
        session.disconnected_at = time.time() - (2 * 60)

        # Session should still be valid
        assert game_state._is_session_valid(session) is True

    def test_session_valid_while_connected(self):
        """Test session is always valid while connected (never disconnected)."""
        game_state = GameState()

        _, _, session = game_state.add_player("Alice")

        # Connected sessions (never disconnected) are always valid
        # disconnected_at should be None
        assert session.disconnected_at is None
        assert game_state._is_session_valid(session) is True

    def test_multiple_players_sessions(self):
        """Test managing multiple player sessions."""
        game_state = GameState()

        # Add multiple players
        _, _, alice = game_state.add_player("Alice")
        _, _, bob = game_state.add_player("Bob")
        _, _, carol = game_state.add_player("Carol")

        # All sessions should be stored
        assert len(game_state.players) == 3
        assert len(game_state.sessions) == 3

        # All tokens should be unique
        tokens = {alice.session_token, bob.session_token, carol.session_token}
        assert len(tokens) == 3

        # All should be retrievable
        assert game_state.get_session_by_token(alice.session_token) == alice
        assert game_state.get_session_by_token(bob.session_token) == bob
        assert game_state.get_session_by_token(carol.session_token) == carol

    @pytest.mark.asyncio
    async def test_websocket_close_on_duplicate(self):
        """Test that old WebSocket is closed when duplicate name joins."""
        game_state = GameState()

        # Create mock WebSocket
        old_ws = AsyncMock()
        old_ws.closed = False

        # Add first player
        _, _, session1 = game_state.add_player("Alice", ws=old_ws)

        # Add duplicate name with new WebSocket
        new_ws = Mock()
        _, _, session2 = game_state.add_player("Alice", ws=new_ws)

        # Give asyncio time to process the close task
        await asyncio.sleep(0.1)

        # Old WebSocket should have been closed
        old_ws.close.assert_called_once_with(
            code=4001,
            message=b"Session replaced by new connection"
        )

    def test_player_count_updates(self):
        """Test that player_count is updated correctly."""
        game_state = GameState()

        assert game_state.player_count == 0

        game_state.add_player("Alice")
        assert game_state.player_count == 1

        game_state.add_player("Bob")
        assert game_state.player_count == 2

        # Duplicate name doesn't increase count
        game_state.add_player("Alice")
        assert game_state.player_count == 2

    def test_reconnection_resets_disconnect_timer(self):
        """Test that reconnection resets disconnected_at and gives fresh 5-minute window."""
        import time
        from unittest.mock import Mock
        game_state = GameState()

        # Create and disconnect session
        _, _, session = game_state.add_player("Alice")
        session.disconnect()

        # Verify disconnected_at is set
        assert session.disconnected_at is not None
        first_disconnect_time = session.disconnected_at

        # Wait a moment
        time.sleep(0.1)

        # Reconnect
        mock_ws = Mock()
        session.reconnect(mock_ws)

        # CRITICAL FIX: disconnected_at should be reset to None
        assert session.disconnected_at is None, "disconnected_at should be reset on reconnect"
        assert session.connected is True
        assert session.ws == mock_ws

        # Disconnect again
        session.disconnect()

        # Should get new disconnected_at timestamp (not the old one)
        assert session.disconnected_at is not None
        assert session.disconnected_at != first_disconnect_time

    def test_disconnect_timer_cleared_on_reconnect(self):
        """Test that disconnect_timer is cleared when player reconnects."""
        from unittest.mock import Mock, AsyncMock
        import asyncio
        game_state = GameState()

        _, _, session = game_state.add_player("Alice")

        # Simulate having a disconnect timer
        mock_timer = AsyncMock()
        mock_timer.done.return_value = False
        session.disconnect_timer = mock_timer

        # Reconnect
        mock_ws = Mock()
        session.reconnect(mock_ws)

        # Timer reference should be cleared
        assert session.disconnect_timer is None
