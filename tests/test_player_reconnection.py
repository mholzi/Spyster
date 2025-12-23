"""Unit tests for player reconnection functionality (Story 2.5)."""
import pytest
from time import time, sleep
from unittest.mock import Mock
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.const import RECONNECT_WINDOW_SECONDS


class TestPlayerSessionReconnection:
    """Test player session reconnection logic."""

    def test_session_valid_when_never_disconnected(self):
        """Test session is valid for player who never disconnected."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Alice", session_token="test_token_123", ws=ws)

        # Act
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is True
        assert player.disconnected_at is None

    def test_session_valid_within_window(self):
        """Test session is valid within 5-minute window."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Bob", session_token="test_token_456", ws=ws)
        player.disconnect()  # Mark as disconnected

        # Act (immediately check, should be valid)
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is True
        assert player.disconnected_at is not None
        assert player.connected is False

    def test_session_invalid_after_window(self):
        """Test session is invalid after 5-minute window expires."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Charlie", session_token="test_token_789", ws=ws)

        # Simulate disconnect 6 minutes ago
        player.disconnected_at = time() - (RECONNECT_WINDOW_SECONDS + 60)
        player.connected = False

        # Act
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is False

    def test_mark_disconnected_sets_timestamp(self):
        """Test disconnect() sets timestamp only on first call."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Dave", session_token="test_token_abc", ws=ws)

        # Act - first disconnect
        player.disconnect()
        first_timestamp = player.disconnected_at

        # Wait a tiny bit
        sleep(0.1)

        # Act - second disconnect (should not update timestamp)
        player.disconnect()
        second_timestamp = player.disconnected_at

        # Assert
        assert first_timestamp is not None
        assert first_timestamp == second_timestamp
        assert player.connected is False

    def test_reconnect_preserves_disconnect_time(self):
        """Test reconnect() does NOT reset disconnect_time."""
        # Arrange
        ws_original = Mock()
        ws_new = Mock()
        player = PlayerSession(name="Eve", session_token="test_token_def", ws=ws_original)

        # Disconnect player
        player.disconnect()
        original_disconnect_time = player.disconnected_at

        # Wait a bit
        sleep(0.1)

        # Act - reconnect
        player.reconnect(ws_new)

        # Assert
        assert player.connected is True
        assert player.ws == ws_new
        assert player.disconnected_at == original_disconnect_time  # Preserved!

    def test_session_valid_after_reconnection(self):
        """Test session remains valid after reconnection."""
        # Arrange
        ws_original = Mock()
        ws_new = Mock()
        player = PlayerSession(name="Frank", session_token="test_token_ghi", ws=ws_original)

        # Disconnect and reconnect
        player.disconnect()
        player.reconnect(ws_new)

        # Act
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is True
        assert player.connected is True

    def test_multiple_reconnections_preserve_first_disconnect_time(self):
        """Test multiple disconnects/reconnects preserve first disconnect time."""
        # Arrange
        ws1 = Mock()
        ws2 = Mock()
        ws3 = Mock()
        player = PlayerSession(name="Grace", session_token="test_token_jkl", ws=ws1)

        # First disconnect
        player.disconnect()
        first_disconnect_time = player.disconnected_at

        sleep(0.1)

        # Reconnect
        player.reconnect(ws2)

        sleep(0.1)

        # Second disconnect (should not update timestamp)
        player.disconnect()

        sleep(0.1)

        # Second reconnect
        player.reconnect(ws3)

        # Assert
        assert player.disconnected_at == first_disconnect_time
        assert player.connected is True

    def test_get_disconnect_duration_returns_none_when_connected(self):
        """Test get_disconnect_duration() returns None for connected players."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Hank", session_token="test_token_mno", ws=ws)

        # Act
        duration = player.get_disconnect_duration()

        # Assert
        assert duration is None

    def test_get_disconnect_duration_returns_elapsed_time(self):
        """Test get_disconnect_duration() returns elapsed time since disconnect."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Ivy", session_token="test_token_pqr", ws=ws)

        # Disconnect player
        player.disconnect()

        # Wait a bit
        sleep(0.2)

        # Act
        duration = player.get_disconnect_duration()

        # Assert
        assert duration is not None
        assert duration >= 0.2  # At least 200ms
        assert duration < 1.0  # But less than 1 second

    def test_session_expiry_edge_case_exact_300_seconds(self):
        """Test session expires at exactly 300 seconds."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Jack", session_token="test_token_stu", ws=ws)

        # Simulate disconnect exactly 300 seconds ago
        player.disconnected_at = time() - RECONNECT_WINDOW_SECONDS
        player.connected = False

        # Act
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is False  # Expired at exactly 300 seconds

    def test_session_valid_at_299_seconds(self):
        """Test session is still valid at 299 seconds."""
        # Arrange
        ws = Mock()
        player = PlayerSession(name="Kate", session_token="test_token_vwx", ws=ws)

        # Simulate disconnect 299 seconds ago
        player.disconnected_at = time() - (RECONNECT_WINDOW_SECONDS - 1)
        player.connected = False

        # Act
        is_valid = player.is_session_valid()

        # Assert
        assert is_valid is True  # Still valid at 299 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
