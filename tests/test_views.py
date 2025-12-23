"""Tests for HTTP views."""
import pytest
from aiohttp import web
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from custom_components.spyster.server.views import HostView, PlayerView


@pytest.mark.asyncio
async def test_host_view_returns_html():
    """Test HostView serves host.html."""
    view = HostView()
    request = Mock(spec=web.Request)

    # Mock the file reading
    html_content = """<!DOCTYPE html>
<html>
<head><title>Spyster - Host Display</title></head>
<body>
    <div id="phase-indicator">LOBBY</div>
    <div id="lobby-message">Waiting for players...</div>
</body>
</html>"""

    with patch("builtins.open", mock_open(read_data=html_content)):
        with patch("pathlib.Path.exists", return_value=True):
            response = await view.get(request)

    assert response.status == 200
    assert response.content_type == "text/html"
    assert "LOBBY" in response.text
    assert "Waiting for players..." in response.text


@pytest.mark.asyncio
async def test_host_view_handles_missing_file():
    """Test HostView handles missing host.html gracefully."""
    view = HostView()
    request = Mock(spec=web.Request)

    with patch("pathlib.Path.exists", return_value=False):
        response = await view.get(request)

    assert response.status == 404
    assert "Host page not found" in response.text


@pytest.mark.asyncio
async def test_player_view_returns_html():
    """Test PlayerView serves player.html."""
    view = PlayerView()
    request = Mock(spec=web.Request)

    # Mock the file reading
    html_content = """<!DOCTYPE html>
<html>
<head><title>Spyster - Player</title></head>
<body>
    <div id="player-ui">Player Interface</div>
</body>
</html>"""

    with patch("builtins.open", mock_open(read_data=html_content)):
        with patch("pathlib.Path.exists", return_value=True):
            response = await view.get(request)

    assert response.status == 200
    assert response.content_type == "text/html"


@pytest.mark.asyncio
async def test_player_view_handles_missing_file():
    """Test PlayerView handles missing player.html gracefully."""
    view = PlayerView()
    request = Mock(spec=web.Request)

    with patch("pathlib.Path.exists", return_value=False):
        response = await view.get(request)

    assert response.status == 404
    assert "Player page not found" in response.text


def test_host_view_configuration():
    """Test HostView has correct configuration."""
    view = HostView()

    assert view.url == "/api/spyster/host"
    assert view.name == "api:spyster:host"
    assert view.requires_auth is False


def test_player_view_configuration():
    """Test PlayerView has correct configuration."""
    view = PlayerView()

    assert view.url == "/api/spyster/player"
    assert view.name == "api:spyster:player"
    assert view.requires_auth is False
