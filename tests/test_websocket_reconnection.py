"""Integration tests for WebSocket reconnection (Story 2.5)."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from time import time
from custom_components.spyster.game.state import GameState, GamePhase
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.server.websocket import WebSocketHandler
from custom_components.spyster.const import (
    RECONNECT_WINDOW_SECONDS,
    ERR_SESSION_EXPIRED,
    ERR_INVALID_TOKEN,
)


@pytest.fixture
def game_state():
    """Create a game state instance for testing."""
    state = GameState()
    state.create_session("host_id")
    return state


@pytest.fixture
def ws_handler(game_state):
    """Create WebSocket handler instance."""
    return WebSocketHandler(game_state)


@pytest.mark.asyncio
async def test_reconnect_with_valid_token(game_state):
    """Test successful reconnection with valid token."""
    # Arrange - Create player session
    ws_original = Mock()
    success, error, session = game_state.add_player("Alice", is_host=False, ws=ws_original)
    assert success
    token = session.session_token

    # Disconnect player
    session.disconnect()

    # Act - Reconnect with valid token
    ws_new = Mock()
    success, error, restored_session = game_state.restore_session(token, ws_new)

    # Assert
    assert success is True
    assert error is None
    assert restored_session.name == "Alice"
    assert restored_session.connected is True
    assert restored_session.ws == ws_new
    assert restored_session.disconnected_at is not None  # Preserved!


@pytest.mark.asyncio
async def test_reconnect_with_expired_token(game_state):
    """Test reconnection fails with expired token."""
    # Arrange - Create player session
    ws_original = Mock()
    success, error, session = game_state.add_player("Bob", is_host=False, ws=ws_original)
    assert success
    token = session.session_token

    # Simulate session expiry (disconnect 6 minutes ago)
    session.disconnected_at = time() - (RECONNECT_WINDOW_SECONDS + 60)
    session.connected = False

    # Act - Attempt reconnection with expired token
    ws_new = Mock()
    success, error, restored_session = game_state.restore_session(token, ws_new)

    # Assert
    assert success is False
    assert error == ERR_SESSION_EXPIRED
    assert restored_session is None
    # Session should be cleaned up
    assert "Bob" not in game_state.players
    assert token not in game_state.sessions


@pytest.mark.asyncio
async def test_reconnect_with_invalid_token(game_state):
    """Test reconnection fails with invalid token."""
    # Arrange - Invalid token that doesn't exist
    invalid_token = "nonexistent_token_123"

    # Act
    ws_new = Mock()
    success, error, session = game_state.restore_session(invalid_token, ws_new)

    # Assert
    assert success is False
    assert error == ERR_INVALID_TOKEN
    assert session is None


@pytest.mark.asyncio
async def test_reconnect_preserves_window_timer(game_state):
    """Test that reconnection doesn't cancel the window timer."""
    # Arrange - Create player and disconnect
    ws_original = Mock()
    success, error, session = game_state.add_player("Charlie", is_host=False, ws=ws_original)
    assert success
    token = session.session_token

    # Simulate disconnect and start reconnection window
    await game_state._on_player_disconnect("Charlie")

    # Verify timer exists
    assert f"reconnect_window:Charlie" in game_state._timers

    # Act - Reconnect
    ws_new = Mock()
    success, error, restored_session = game_state.restore_session(token, ws_new)

    # Assert
    assert success is True
    # Timer should STILL be running (not cancelled by reconnection)
    assert f"reconnect_window:Charlie" in game_state._timers


@pytest.mark.asyncio
async def test_reconnection_window_expires_after_5_minutes(game_state):
    """Test player is removed when reconnection window expires."""
    # Arrange - Create player
    ws_original = Mock()
    success, error, session = game_state.add_player("Dave", is_host=False, ws=ws_original)
    assert success
    token = session.session_token

    # Disconnect player (starts window timer)
    await game_state._on_player_disconnect("Dave")

    # Verify player exists and timer is running
    assert "Dave" in game_state.players
    assert f"reconnect_window:Dave" in game_state._timers

    # Act - Simulate timer expiration
    await game_state._on_reconnect_window_expired("Dave")

    # Assert - Player removed
    assert "Dave" not in game_state.players
    assert token not in game_state.sessions


@pytest.mark.asyncio
async def test_multiple_reconnections_within_window(game_state):
    """Test player can reconnect multiple times within window."""
    # Arrange
    ws1 = Mock()
    success, error, session = game_state.add_player("Eve", is_host=False, ws=ws1)
    assert success
    token = session.session_token
    first_disconnect_time = session.disconnected_at

    # First disconnect
    session.disconnect()

    # First reconnection
    ws2 = Mock()
    success, error, _ = game_state.restore_session(token, ws2)
    assert success is True

    # Second disconnect
    session.disconnect()

    # Second reconnection
    ws3 = Mock()
    success, error, final_session = game_state.restore_session(token, ws3)

    # Assert
    assert success is True
    assert final_session.connected is True
    assert final_session.ws == ws3
    # Disconnect time preserved from FIRST disconnect
    assert final_session.disconnected_at == session.disconnected_at


@pytest.mark.asyncio
async def test_reconnect_during_vote_phase(game_state):
    """Test reconnection during active round (VOTE phase)."""
    # Arrange - Create player and transition to VOTE phase
    ws_original = Mock()
    success, error, session = game_state.add_player("Frank", is_host=False, ws=ws_original)
    assert success
    token = session.session_token

    # Transition to VOTE phase (simplified - would normally go through full flow)
    game_state.phase = GamePhase.VOTE

    # Disconnect player
    session.disconnect()

    # Act - Reconnect during VOTE phase
    ws_new = Mock()
    success, error, restored_session = game_state.restore_session(token, ws_new)

    # Assert
    assert success is True
    assert restored_session.connected is True
    # Phase should still be VOTE
    assert game_state.phase == GamePhase.VOTE


@pytest.mark.asyncio
async def test_absolute_5min_limit_enforced(game_state):
    """Test player removed at 5min mark even if reconnected."""
    # Arrange
    ws1 = Mock()
    success, error, session = game_state.add_player("Grace", is_host=False, ws=ws1)
    assert success
    token = session.session_token

    # Disconnect
    await game_state._on_player_disconnect("Grace")

    # Reconnect at 4:59
    ws2 = Mock()
    success, error, _ = game_state.restore_session(token, ws2)
    assert success is True
    assert session.connected is True

    # Act - Timer fires at 5:00 (regardless of reconnection status)
    await game_state._on_reconnect_window_expired("Grace")

    # Assert - Player removed even though currently connected
    assert "Grace" not in game_state.players
    assert token not in game_state.sessions


@pytest.mark.asyncio
async def test_disconnect_grace_starts_reconnection_window(game_state):
    """Test disconnect_grace timer starts reconnection window."""
    # Arrange
    ws = Mock()
    success, error, session = game_state.add_player("Hank", is_host=False, ws=ws)
    assert success

    # Mark as not connected (simulating WebSocket close)
    session.connected = False

    # Act - Call disconnect handler (called by disconnect_grace timer)
    await game_state._on_player_disconnect("Hank")

    # Assert
    assert session.disconnected_at is not None
    assert f"reconnect_window:Hank" in game_state._timers


@pytest.mark.asyncio
async def test_session_cleanup_on_removal(game_state):
    """Test session is cleaned up from both dictionaries on removal."""
    # Arrange
    ws = Mock()
    success, error, session = game_state.add_player("Ivy", is_host=False, ws=ws)
    assert success
    token = session.session_token

    # Verify player exists in both dictionaries
    assert "Ivy" in game_state.players
    assert token in game_state.sessions

    # Act - Remove player (via reconnection window expiry)
    await game_state._on_reconnect_window_expired("Ivy")

    # Assert - Cleaned up from both dictionaries
    assert "Ivy" not in game_state.players
    assert token not in game_state.sessions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
