"""Unit tests for QR code generation (Story 1.3)."""
import base64
import io
import pytest
from unittest.mock import Mock, patch

from custom_components.spyster.const import ERR_INTERNAL
from custom_components.spyster.game.state import GameState
from custom_components.spyster.server.views import SpysterQRView


class TestGameStateJoinURL:
    """Test GameState.get_join_url() method."""

    def test_get_join_url_with_valid_session(self):
        """Test get_join_url returns correct URL format."""
        state = GameState()
        state.create_session("host_123")

        base_url = "http://homeassistant.local:8123"
        join_url = state.get_join_url(base_url)

        # Verify URL format
        assert join_url.startswith(base_url)
        assert "/api/spyster/player?session=" in join_url
        assert state.session_id in join_url

    def test_get_join_url_without_session_raises_error(self):
        """Test get_join_url raises ValueError when session_id is None."""
        state = GameState()

        with pytest.raises(ValueError, match="Session ID not set"):
            state.get_join_url("http://homeassistant.local:8123")

    def test_get_join_url_with_ip_address(self):
        """Test get_join_url works with IP address base URL."""
        state = GameState()
        state.create_session("host_123")

        base_url = "http://192.168.1.100:8123"
        join_url = state.get_join_url(base_url)

        assert join_url.startswith(base_url)
        assert "/api/spyster/player?session=" in join_url


class TestQRCodeGeneration:
    """Test SpysterQRView.generate_qr_code() method."""

    def test_generate_qr_code_returns_data_url(self):
        """Test QR code generation returns valid base64 data URL."""
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        url = "http://homeassistant.local:8123/api/spyster/player?session=test123"
        qr_data_url = view.generate_qr_code(url)

        # Verify data URL format
        assert qr_data_url.startswith("data:image/png;base64,")

        # Verify base64 encoding is valid
        base64_data = qr_data_url.split(",")[1]
        try:
            base64.b64decode(base64_data)
        except Exception as err:
            pytest.fail(f"Invalid base64 encoding: {err}")

    def test_generate_qr_code_with_empty_url_raises_error(self):
        """Test QR code generation raises ValueError for empty URL."""
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        with pytest.raises(ValueError, match="URL cannot be empty"):
            view.generate_qr_code("")

    def test_generate_qr_code_with_long_url_raises_error(self):
        """Test QR code generation raises ValueError for URLs over 2048 chars."""
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        # Create a URL longer than 2048 characters
        long_url = "http://homeassistant.local:8123/api/spyster/player?session=" + ("x" * 2100)

        with pytest.raises(ValueError, match="URL too long"):
            view.generate_qr_code(long_url)

    def test_generate_qr_code_contains_png_data(self):
        """Test QR code data URL contains valid PNG data."""
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        url = "http://homeassistant.local:8123/api/spyster/player?session=test123"
        qr_data_url = view.generate_qr_code(url)

        # Decode base64 data
        base64_data = qr_data_url.split(",")[1]
        png_data = base64.b64decode(base64_data)

        # Verify PNG signature (first 8 bytes)
        png_signature = b"\x89PNG\r\n\x1a\n"
        assert png_data[:8] == png_signature

    def test_generate_qr_code_uses_constants(self):
        """Test QR code generation uses constants from const.py."""
        from custom_components.spyster.const import DEFAULT_QR_BOX_SIZE, DEFAULT_QR_BORDER

        # Verify constants are defined and reasonable
        assert DEFAULT_QR_BOX_SIZE > 0
        assert DEFAULT_QR_BORDER >= 0

        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        # QR code should generate without errors using these constants
        url = "http://homeassistant.local:8123/api/spyster/player?session=test123"
        qr_data_url = view.generate_qr_code(url)

        assert qr_data_url.startswith("data:image/png;base64,")


class TestQRViewEndpoint:
    """Test SpysterQRView HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_qr_view_get_returns_qr_data(self):
        """Test GET /api/spyster/qr returns QR code data."""
        # Create game state with session
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        # Mock request
        mock_request = Mock()
        mock_hass = Mock()
        mock_hass.config.api.base_url = "http://homeassistant.local:8123"
        mock_request.app = {"hass": mock_hass}

        # Call endpoint
        with patch("custom_components.spyster.server.views.web.json_response") as mock_response:
            await view.get(mock_request)

            # Verify response was called
            assert mock_response.called

            # Get response data
            call_args = mock_response.call_args[0][0]
            assert call_args["success"] is True
            assert "qr_code_data" in call_args
            assert "join_url" in call_args
            assert call_args["session_id"] == state.session_id

    @pytest.mark.asyncio
    async def test_qr_view_get_without_session_returns_error(self):
        """Test GET /api/spyster/qr returns error when no session exists."""
        # Create game state WITHOUT creating session
        state = GameState()
        view = SpysterQRView(state)

        # Mock request
        mock_request = Mock()
        mock_hass = Mock()
        mock_hass.config.api.base_url = "http://homeassistant.local:8123"
        mock_request.app = {"hass": mock_hass}

        # Call endpoint
        with patch("custom_components.spyster.server.views.web.json_response") as mock_response:
            await view.get(mock_request)

            # Verify error response
            assert mock_response.called
            call_args = mock_response.call_args[0][0]
            assert call_args["error"] is True
            assert "code" in call_args

    @pytest.mark.asyncio
    async def test_qr_view_get_without_base_url_returns_error(self):
        """Test GET /api/spyster/qr returns error when base_url not configured."""
        state = GameState()
        state.create_session("host_123")
        view = SpysterQRView(state)

        # Mock request with no base_url
        mock_request = Mock()
        mock_hass = Mock()
        mock_hass.config.api.base_url = None
        mock_request.app = {"hass": mock_hass}

        # Call endpoint
        with patch("custom_components.spyster.server.views.web.json_response") as mock_response:
            await view.get(mock_request)

            # Verify error response
            assert mock_response.called
            call_args = mock_response.call_args[0][0]
            assert call_args["error"] is True
            assert call_args["code"] == ERR_INTERNAL
