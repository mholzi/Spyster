"""Unit tests for player join flow (Story 2.2)."""
import asyncio
import secrets
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.spyster.const import (
    ERR_GAME_ALREADY_STARTED,
    ERR_GAME_FULL,
    ERR_NAME_INVALID,
    ERROR_MESSAGES,
    MAX_PLAYERS,
)
from custom_components.spyster.game.player import PlayerSession
from custom_components.spyster.game.state import GamePhase, GameState
from custom_components.spyster.server.websocket import WebSocketHandler


@pytest.fixture
def game_state():
    """Create a fresh game state in LOBBY phase."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    state.session_id = "test_session_123"
    return state


@pytest.fixture
def ws_handler(game_state):
    """Create WebSocket handler with game state."""
    return WebSocketHandler(game_state)


@pytest.fixture
def mock_ws():
    """Create mock WebSocket response."""
    ws = AsyncMock()
    ws.closed = False
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_valid_join(ws_handler, game_state, mock_ws):
    """Test successful player join."""
    player_name = "Alice"
    data = {"name": player_name}

    # Execute join
    await ws_handler._handle_join(mock_ws, data)

    # Verify player added to game state
    assert player_name in game_state.players
    assert game_state.players[player_name].connected
    assert len(game_state.players) == 1
    assert game_state.player_count == 1

    # Verify success response sent with correct field names
    mock_ws.send_json.assert_any_call({
        "type": "join_success",
        "player_name": player_name,
        "session_token": game_state.players[player_name].session_token,
        "is_host": False
    })

    # Verify session token is cryptographically secure (16 bytes URL-safe)
    token = game_state.players[player_name].session_token
    assert len(token) > 0
    assert isinstance(token, str)


@pytest.mark.asyncio
async def test_invalid_name_empty(ws_handler, mock_ws):
    """Test join with empty name."""
    data = {"name": ""}

    await ws_handler._handle_join(mock_ws, data)

    # Verify error response
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_NAME_INVALID
    assert call_args["message"] == ERROR_MESSAGES[ERR_NAME_INVALID]


@pytest.mark.asyncio
async def test_invalid_name_too_long(ws_handler, mock_ws):
    """Test join with name > 20 characters."""
    long_name = "A" * 21
    data = {"name": long_name}

    await ws_handler._handle_join(mock_ws, data)

    # Verify error response
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_NAME_INVALID


@pytest.mark.asyncio
async def test_invalid_name_whitespace_only(ws_handler, mock_ws):
    """Test join with whitespace-only name."""
    data = {"name": "   "}

    await ws_handler._handle_join(mock_ws, data)

    # Verify error response
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_NAME_INVALID


@pytest.mark.asyncio
async def test_duplicate_name_replaces_old_session(ws_handler, game_state):
    """Test FR18: duplicate name removes old session."""
    player_name = "Alice"

    # Create first session
    ws1 = AsyncMock()
    ws1.closed = False
    ws1.close = AsyncMock()
    ws1.send_json = AsyncMock()

    data1 = {"name": player_name}
    await ws_handler._handle_join(ws1, data1)

    # Verify first player added
    assert len(game_state.players) == 1
    assert game_state.players[player_name].ws == ws1
    old_token = game_state.players[player_name].session_token

    # Create second session with same name
    ws2 = AsyncMock()
    ws2.closed = False
    ws2.close = AsyncMock()
    ws2.send_json = AsyncMock()

    data2 = {"name": player_name}
    await ws_handler._handle_join(ws2, data2)

    # Verify old WebSocket was closed
    ws1.close.assert_called_once()

    # Verify only one player in game (old removed, new added)
    assert len(game_state.players) == 1
    assert game_state.players[player_name].ws == ws2

    # Verify new session has different token
    new_token = game_state.players[player_name].session_token
    assert new_token != old_token


@pytest.mark.asyncio
async def test_game_full(ws_handler, game_state, mock_ws):
    """Test join when game has 10 players."""
    # Add MAX_PLAYERS players
    for i in range(MAX_PLAYERS):
        ws = AsyncMock()
        ws.closed = False
        player = PlayerSession(
            name=f"Player{i}",
            session_token=secrets.token_urlsafe(16),
            ws=ws,
            connected=True,
        )
        game_state.players[player.name] = player

    game_state.player_count = len(game_state.players)

    # Try to add 11th player
    data = {"name": "NewPlayer"}
    await ws_handler._handle_join(mock_ws, data)

    # Verify error response
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_GAME_FULL
    assert call_args["message"] == ERROR_MESSAGES[ERR_GAME_FULL]

    # Verify player count unchanged
    assert len(game_state.players) == MAX_PLAYERS


@pytest.mark.asyncio
async def test_join_after_game_started(ws_handler, game_state, mock_ws):
    """Test join when game is no longer in LOBBY phase."""
    game_state.phase = GamePhase.ROLES

    data = {"name": "LatePlayer"}
    await ws_handler._handle_join(mock_ws, data)

    # Verify error response
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_GAME_ALREADY_STARTED
    assert call_args["message"] == ERROR_MESSAGES[ERR_GAME_ALREADY_STARTED]

    # Verify no player added
    assert len(game_state.players) == 0


@pytest.mark.asyncio
async def test_multiple_players_join(ws_handler, game_state):
    """Test multiple players joining in sequence."""
    player_names = ["Alice", "Bob", "Charlie"]

    for name in player_names:
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()

        data = {"name": name}
        await ws_handler._handle_join(ws, data)

        # Verify player added
        assert name in game_state.players

    # Verify all players in game
    assert len(game_state.players) == len(player_names)
    assert game_state.player_count == len(player_names)


@pytest.mark.asyncio
async def test_name_trimming(ws_handler, game_state, mock_ws):
    """Test that player names are trimmed of whitespace."""
    data = {"name": "  Alice  "}

    await ws_handler._handle_join(mock_ws, data)

    # Verify player added with trimmed name
    assert "Alice" in game_state.players
    assert "  Alice  " not in game_state.players


@pytest.mark.asyncio
async def test_broadcast_state_after_join(ws_handler, game_state):
    """Test that state is broadcast after successful join."""
    # Add first player
    ws1 = AsyncMock()
    ws1.closed = False
    ws1.send_json = AsyncMock()

    data1 = {"name": "Alice"}
    await ws_handler._handle_join(ws1, data1)

    # Clear previous calls
    ws1.send_json.reset_mock()

    # Add second player
    ws2 = AsyncMock()
    ws2.closed = False
    ws2.send_json = AsyncMock()

    data2 = {"name": "Bob"}
    await ws_handler._handle_join(ws2, data2)

    # Verify both players received state broadcast
    # Alice should receive state update (via broadcast_state)
    assert ws1.send_json.called
    # Bob receives join_success and state via broadcast
    assert ws2.send_json.call_count >= 2


@pytest.mark.asyncio
async def test_player_session_fields(ws_handler, game_state, mock_ws):
    """Test that PlayerSession has all required fields."""
    data = {"name": "Alice"}

    await ws_handler._handle_join(mock_ws, data)

    player = game_state.players["Alice"]

    # Verify core fields
    assert player.name == "Alice"
    assert player.session_token is not None
    assert player.connected is True
    assert player.ws == mock_ws

    # Verify default fields
    assert player.is_host is False
    assert player.is_spy is False
    assert player.role is None
    assert player.score == 0


@pytest.mark.asyncio
async def test_ws_to_player_mapping(ws_handler, game_state, mock_ws):
    """Test that WebSocket to player mapping is maintained."""
    data = {"name": "Alice"}

    await ws_handler._handle_join(mock_ws, data)

    # Verify mapping exists
    assert mock_ws in ws_handler._ws_to_player
    assert ws_handler._ws_to_player[mock_ws].name == "Alice"

@pytest.mark.asyncio
async def test_xss_attack_in_name(ws_handler, mock_ws):
    """Test join with XSS attack attempt in name."""
    malicious_names = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "Alice<script>",
        "Bob';DROP TABLE players;--",
        'Name"onclick="alert(1)"',
    ]

    for mal_name in malicious_names:
        data = {"name": mal_name}
        await ws_handler._handle_join(mock_ws, data)

        # Verify error response
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["code"] == ERR_NAME_INVALID
        mock_ws.send_json.reset_mock()


@pytest.mark.asyncio
async def test_special_characters_rejected(ws_handler, mock_ws):
    """Test that special characters are rejected."""
    invalid_names = ["Alice&Bob", "Test;Name", "User<Name", "Name>Test", "Test'Name", 'Test"Name']

    for invalid_name in invalid_names:
        data = {"name": invalid_name}
        await ws_handler._handle_join(mock_ws, data)

        # Verify error response
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["code"] == ERR_NAME_INVALID
        mock_ws.send_json.reset_mock()


@pytest.mark.asyncio
async def test_missing_name_field(ws_handler, mock_ws):
    """Test join with missing 'name' field in message."""
    data = {"type": "join"}  # No 'name' field

    await ws_handler._handle_join(mock_ws, data)

    # Verify error response for invalid name
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["code"] == ERR_NAME_INVALID


@pytest.mark.asyncio
async def test_name_exactly_20_characters(ws_handler, game_state, mock_ws):
    """Test join with name exactly at maximum length (20 chars)."""
    name_20_chars = "A" * 20
    data = {"name": name_20_chars}

    await ws_handler._handle_join(mock_ws, data)

    # Verify player added successfully
    assert name_20_chars in game_state.players
    assert len(game_state.players) == 1

    # Verify success response
    mock_ws.send_json.assert_any_call({
        "type": "join_success",
        "player_name": name_20_chars,
        "session_token": game_state.players[name_20_chars].session_token,
        "is_host": False
    })


@pytest.mark.asyncio
async def test_duplicate_name_closes_old_ws_after_registration(ws_handler, game_state):
    """Test that old WebSocket is closed AFTER new player is registered (race condition fix)."""
    player_name = "Alice"

    # Create first session
    ws1 = AsyncMock()
    ws1.closed = False
    ws1.close = AsyncMock()
    ws1.send_json = AsyncMock()

    data1 = {"name": player_name}
    await ws_handler._handle_join(ws1, data1)

    # Verify first player added
    assert len(game_state.players) == 1
    old_token = game_state.players[player_name].session_token

    # Create second session with same name
    ws2 = AsyncMock()
    ws2.closed = False
    ws2.close = AsyncMock()
    ws2.send_json = AsyncMock()

    data2 = {"name": player_name}
    await ws_handler._handle_join(ws2, data2)

    # Verify new player is in state BEFORE old ws.close is called
    assert len(game_state.players) == 1
    assert game_state.players[player_name].ws == ws2
    new_token = game_state.players[player_name].session_token
    assert new_token != old_token

    # Verify old token removed from sessions dict
    assert old_token not in game_state.sessions
    assert new_token in game_state.sessions

    # Give async task time to close old WebSocket
    await asyncio.sleep(0.1)
    ws1.close.assert_called_once_with(
        code=4001,
        message=b"Session replaced by new connection"
    )


@pytest.mark.asyncio
async def test_name_with_leading_trailing_spaces_trimmed(ws_handler, game_state, mock_ws):
    """Test that names with leading/trailing spaces are trimmed correctly."""
    data = {"name": "  Bob  "}

    await ws_handler._handle_join(mock_ws, data)

    # Verify player added with trimmed name
    assert "Bob" in game_state.players
    assert "  Bob  " not in game_state.players

    # Verify success response uses trimmed name
    mock_ws.send_json.assert_any_call({
        "type": "join_success",
        "player_name": "Bob",
        "session_token": game_state.players["Bob"].session_token,
        "is_host": False
    })


@pytest.mark.asyncio
async def test_session_token_cryptographically_secure(ws_handler, game_state, mock_ws):
    """Test that session token has sufficient entropy for security."""
    data = {"name": "Alice"}

    await ws_handler._handle_join(mock_ws, data)

    player = game_state.players["Alice"]
    token = player.session_token

    # Verify token is URL-safe base64 string
    assert isinstance(token, str)
    # 32 bytes = 256 bits encoded in base64 should be ~43 chars
    assert len(token) >= 40
    # Verify no invalid base64 characters
    import re
    assert re.match(r'^[A-Za-z0-9_-]+$', token)


@pytest.mark.asyncio
async def test_host_flag_propagated(ws_handler, game_state, mock_ws):
    """Test that is_host flag is correctly propagated to player session."""
    data = {"name": "Alice", "is_host": True}

    await ws_handler._handle_join(mock_ws, data)

    player = game_state.players["Alice"]
    assert player.is_host is True

    # Verify response includes is_host
    mock_ws.send_json.assert_any_call({
        "type": "join_success",
        "player_name": "Alice",
        "session_token": player.session_token,
        "is_host": True
    })

