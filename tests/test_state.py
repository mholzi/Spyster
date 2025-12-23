"""Tests for GameState and GamePhase."""
import pytest
import asyncio
from unittest.mock import AsyncMock

from custom_components.spyster.game.state import GameState, GamePhase
from custom_components.spyster.const import ERR_INVALID_PHASE, MIN_PLAYERS, MAX_PLAYERS


def test_game_phase_enum_has_all_phases():
    """Test that GamePhase enum has all required phases."""
    assert hasattr(GamePhase, "LOBBY")
    assert hasattr(GamePhase, "ROLES")
    assert hasattr(GamePhase, "QUESTIONING")
    assert hasattr(GamePhase, "VOTE")
    assert hasattr(GamePhase, "REVEAL")
    assert hasattr(GamePhase, "SCORING")
    assert hasattr(GamePhase, "END")
    assert hasattr(GamePhase, "PAUSED")


def test_game_phase_enum_values():
    """Test that GamePhase enum values are correct."""
    assert GamePhase.LOBBY.value == "LOBBY"
    assert GamePhase.ROLES.value == "ROLES"
    assert GamePhase.QUESTIONING.value == "QUESTIONING"
    assert GamePhase.VOTE.value == "VOTE"
    assert GamePhase.REVEAL.value == "REVEAL"
    assert GamePhase.SCORING.value == "SCORING"
    assert GamePhase.END.value == "END"
    assert GamePhase.PAUSED.value == "PAUSED"


def test_game_state_initializes_with_lobby_phase():
    """Test that GameState initializes with LOBBY phase."""
    state = GameState()
    assert state.phase == GamePhase.LOBBY


def test_game_state_timer_dict_starts_empty():
    """Test that timer dictionary starts empty."""
    state = GameState()
    assert state._timers == {}


def test_game_state_players_dict_starts_empty():
    """Test that players dictionary starts empty."""
    state = GameState()
    assert state.players == {}


@pytest.mark.asyncio
async def test_start_timer_creates_timer():
    """Test that start_timer creates a timer task."""
    state = GameState()
    callback = AsyncMock()

    # Start a very short timer
    state.start_timer("test", 0.01, callback)

    # Verify timer exists
    assert "test" in state._timers
    assert not state._timers["test"].done()

    # Wait for timer to complete
    await asyncio.sleep(0.02)

    # Verify callback was called
    callback.assert_called_once()


@pytest.mark.asyncio
async def test_start_timer_cancels_existing_timer():
    """Test that start_timer cancels existing timer with same name."""
    state = GameState()
    callback1 = AsyncMock()
    callback2 = AsyncMock()

    # Start first timer
    state.start_timer("test", 10.0, callback1)
    first_task = state._timers["test"]

    # Start second timer with same name
    state.start_timer("test", 0.01, callback2)

    # Verify first timer was cancelled
    assert first_task.cancelled()

    # Wait for second timer to complete
    await asyncio.sleep(0.02)

    # Verify only second callback was called
    callback1.assert_not_called()
    callback2.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_timer_cancels_active_timer():
    """Test that cancel_timer cancels an active timer."""
    state = GameState()
    callback = AsyncMock()

    # Start a long timer
    state.start_timer("test", 10.0, callback)

    # Cancel it
    state.cancel_timer("test")

    # Verify timer is cancelled and removed
    assert "test" not in state._timers

    # Wait a bit
    await asyncio.sleep(0.01)

    # Verify callback was not called
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_timer_handles_nonexistent_timer():
    """Test that cancel_timer handles nonexistent timer gracefully."""
    state = GameState()

    # Should not raise an error
    state.cancel_timer("nonexistent")


@pytest.mark.asyncio
async def test_cancel_all_timers_cancels_multiple_timers():
    """Test that cancel_all_timers cancels all active timers."""
    state = GameState()
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    callback3 = AsyncMock()

    # Start multiple timers
    state.start_timer("timer1", 10.0, callback1)
    state.start_timer("timer2", 10.0, callback2)
    state.start_timer("timer3", 10.0, callback3)

    # Verify all timers exist
    assert len(state._timers) == 3

    # Cancel all timers
    state.cancel_all_timers()

    # Verify all timers are cancelled and removed
    assert len(state._timers) == 0

    # Wait a bit
    await asyncio.sleep(0.01)

    # Verify no callbacks were called
    callback1.assert_not_called()
    callback2.assert_not_called()
    callback3.assert_not_called()


@pytest.mark.asyncio
async def test_timer_with_player_specific_name():
    """Test timer with player-specific naming pattern."""
    state = GameState()
    callback = AsyncMock()

    # Start timer with player-specific name
    state.start_timer("disconnect_grace:Alice", 0.01, callback)

    # Verify timer exists with correct name
    assert "disconnect_grace:Alice" in state._timers

    # Wait for timer to complete
    await asyncio.sleep(0.02)

    # Verify callback was called
    callback.assert_called_once_with("disconnect_grace:Alice")


@pytest.mark.asyncio
async def test_timer_callback_error_handling():
    """Test that timer callback errors are caught and logged."""
    state = GameState()

    # Create callback that raises an exception
    async def failing_callback(name: str) -> None:
        raise RuntimeError(f"Callback error for {name}")

    # Start timer with failing callback
    state.start_timer("test", 0.01, failing_callback)

    # Wait for timer to complete
    await asyncio.sleep(0.02)

    # Verify timer task completed (didn't crash)
    assert "test" not in state._timers or state._timers["test"].done()


@pytest.mark.asyncio
async def test_gamestate_cleanup_on_deletion():
    """Test that GameState cleans up timers when deleted."""
    state = GameState()
    callback = AsyncMock()

    # Start multiple timers
    state.start_timer("timer1", 10.0, callback)
    state.start_timer("timer2", 10.0, callback)

    # Verify timers exist
    assert len(state._timers) == 2

    # Delete the state object
    del state

    # Wait a bit to allow cleanup
    await asyncio.sleep(0.01)

    # Verify callbacks were not called (timers were cancelled)
    callback.assert_not_called()


# Story 1.2: Session creation and phase transition tests

def test_session_creation():
    """Test session initialization."""
    state = GameState()
    session_id = state.create_session("host_player")

    assert state.session_id is not None
    assert len(state.session_id) > 0
    assert state.host_id == "host_player"
    assert state.phase == GamePhase.LOBBY
    assert state.created_at is not None
    assert isinstance(state.created_at, float)


def test_session_id_is_unique():
    """Test that multiple sessions get unique IDs."""
    state1 = GameState()
    state2 = GameState()

    id1 = state1.create_session("host1")
    id2 = state2.create_session("host2")

    assert id1 != id2


def test_lobby_to_roles_transition():
    """Test valid transition from LOBBY to ROLES."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    success, error = state.transition_to(GamePhase.ROLES)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.ROLES


def test_lobby_to_vote_blocked():
    """Test invalid transition from LOBBY to VOTE is blocked."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    success, error = state.transition_to(GamePhase.VOTE)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.LOBBY  # Phase unchanged


def test_roles_to_questioning_transition():
    """Test valid transition from ROLES to QUESTIONING."""
    state = GameState()
    state.phase = GamePhase.ROLES
    success, error = state.transition_to(GamePhase.QUESTIONING)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.QUESTIONING


def test_questioning_to_vote_transition():
    """Test valid transition from QUESTIONING to VOTE."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    success, error = state.transition_to(GamePhase.VOTE)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.VOTE


def test_vote_to_reveal_transition():
    """Test valid transition from VOTE to REVEAL."""
    state = GameState()
    state.phase = GamePhase.VOTE
    success, error = state.transition_to(GamePhase.REVEAL)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.REVEAL


def test_reveal_to_scoring_transition():
    """Test valid transition from REVEAL to SCORING."""
    state = GameState()
    state.phase = GamePhase.REVEAL
    success, error = state.transition_to(GamePhase.SCORING)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.SCORING


def test_scoring_to_roles_transition():
    """Test valid transition from SCORING to ROLES (next round)."""
    state = GameState()
    state.phase = GamePhase.SCORING
    success, error = state.transition_to(GamePhase.ROLES)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.ROLES


def test_scoring_to_end_transition():
    """Test valid transition from SCORING to END (final round)."""
    state = GameState()
    state.phase = GamePhase.SCORING
    success, error = state.transition_to(GamePhase.END)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.END


def test_end_to_lobby_transition():
    """Test valid transition from END to LOBBY (new game)."""
    state = GameState()
    state.phase = GamePhase.END
    success, error = state.transition_to(GamePhase.LOBBY)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.LOBBY


def test_pause_from_lobby():
    """Test PAUSED can be entered from LOBBY."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert error is None
    assert state.phase == GamePhase.PAUSED
    assert state.previous_phase == GamePhase.LOBBY


def test_pause_from_roles():
    """Test PAUSED can be entered from ROLES."""
    state = GameState()
    state.phase = GamePhase.ROLES
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert state.previous_phase == GamePhase.ROLES


def test_pause_from_questioning():
    """Test PAUSED can be entered from QUESTIONING."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert state.previous_phase == GamePhase.QUESTIONING


def test_pause_from_vote():
    """Test PAUSED can be entered from VOTE."""
    state = GameState()
    state.phase = GamePhase.VOTE
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert state.previous_phase == GamePhase.VOTE


def test_pause_from_reveal():
    """Test PAUSED can be entered from REVEAL."""
    state = GameState()
    state.phase = GamePhase.REVEAL
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert state.previous_phase == GamePhase.REVEAL


def test_pause_from_scoring():
    """Test PAUSED can be entered from SCORING."""
    state = GameState()
    state.phase = GamePhase.SCORING
    success, error = state.transition_to(GamePhase.PAUSED)

    assert success is True
    assert state.previous_phase == GamePhase.SCORING


def test_resume_from_pause():
    """Test resume from PAUSED returns to previous phase."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    state.transition_to(GamePhase.PAUSED)

    success, error = state.transition_to(GamePhase.QUESTIONING)
    assert success is True
    assert state.phase == GamePhase.QUESTIONING


def test_can_transition_validates_correctly():
    """Test can_transition validates without changing state."""
    state = GameState()
    state.phase = GamePhase.LOBBY

    # Valid transition
    can, error = state.can_transition(GamePhase.ROLES)
    assert can is True
    assert error is None
    assert state.phase == GamePhase.LOBBY  # State unchanged

    # Invalid transition
    can, error = state.can_transition(GamePhase.VOTE)
    assert can is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.LOBBY  # State unchanged


def test_get_state_lobby():
    """Test get_state returns lobby-specific fields."""
    state = GameState()
    state.create_session("host")
    game_state = state.get_state()

    assert game_state["phase"] == "LOBBY"
    assert game_state["waiting_for_players"] is True
    assert game_state["min_players"] == MIN_PLAYERS
    assert game_state["max_players"] == MAX_PLAYERS
    assert game_state["session_id"] is not None
    assert game_state["player_count"] == 0
    assert game_state["current_round"] == 0


def test_get_state_non_lobby():
    """Test get_state does not include lobby fields for other phases."""
    state = GameState()
    state.create_session("host")
    state.transition_to(GamePhase.ROLES)
    game_state = state.get_state()

    assert game_state["phase"] == "ROLES"
    assert "waiting_for_players" not in game_state


def test_get_state_for_player_parameter():
    """Test get_state accepts for_player parameter (for future use)."""
    state = GameState()
    state.create_session("host")

    # Should not raise an error
    game_state = state.get_state(for_player="Alice")
    assert game_state is not None


def test_game_state_initialization_includes_session_fields():
    """Test that GameState __init__ includes all Story 1.2 session fields."""
    state = GameState()

    # Session metadata fields
    assert hasattr(state, "session_id")
    assert hasattr(state, "created_at")
    assert hasattr(state, "host_id")
    assert hasattr(state, "previous_phase")

    # Game configuration fields
    assert hasattr(state, "round_duration")
    assert hasattr(state, "round_count")
    assert hasattr(state, "vote_duration")
    assert hasattr(state, "location_pack")

    # Game state fields
    assert hasattr(state, "current_round")
    assert hasattr(state, "player_count")

    # Initial values
    assert state.session_id is None
    assert state.created_at is None
    assert state.host_id is None
    assert state.previous_phase is None
    assert state.current_round == 0
    assert state.player_count == 0


# Additional comprehensive invalid transition tests (Issue #8)


def test_roles_to_lobby_blocked():
    """Test invalid transition from ROLES to LOBBY is blocked."""
    state = GameState()
    state.phase = GamePhase.ROLES
    success, error = state.transition_to(GamePhase.LOBBY)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.ROLES  # Phase unchanged


def test_questioning_to_roles_blocked():
    """Test invalid transition from QUESTIONING to ROLES is blocked."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    success, error = state.transition_to(GamePhase.ROLES)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.QUESTIONING  # Phase unchanged


def test_vote_to_questioning_blocked():
    """Test invalid transition from VOTE to QUESTIONING is blocked."""
    state = GameState()
    state.phase = GamePhase.VOTE
    success, error = state.transition_to(GamePhase.QUESTIONING)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.VOTE  # Phase unchanged


def test_reveal_to_vote_blocked():
    """Test invalid transition from REVEAL to VOTE is blocked."""
    state = GameState()
    state.phase = GamePhase.REVEAL
    success, error = state.transition_to(GamePhase.VOTE)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.REVEAL  # Phase unchanged


def test_scoring_to_questioning_blocked():
    """Test invalid transition from SCORING to QUESTIONING is blocked."""
    state = GameState()
    state.phase = GamePhase.SCORING
    success, error = state.transition_to(GamePhase.QUESTIONING)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.SCORING  # Phase unchanged


def test_end_to_roles_blocked():
    """Test invalid transition from END to ROLES is blocked."""
    state = GameState()
    state.phase = GamePhase.END
    success, error = state.transition_to(GamePhase.ROLES)

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert state.phase == GamePhase.END  # Phase unchanged


def test_can_transition_type_validation():
    """Test can_transition validates type of to_phase parameter."""
    state = GameState()
    state.phase = GamePhase.LOBBY

    # Should raise TypeError for non-GamePhase argument
    import pytest
    with pytest.raises(TypeError, match="to_phase must be a GamePhase enum"):
        state.can_transition("ROLES")  # String instead of enum


def test_previous_phase_cleared_on_resume():
    """Test that previous_phase is cleared when resuming from PAUSED."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING

    # Pause the game
    state.transition_to(GamePhase.PAUSED)
    assert state.previous_phase == GamePhase.QUESTIONING

    # Resume to the previous phase
    state.transition_to(GamePhase.QUESTIONING)
    assert state.previous_phase is None  # Should be cleared


# Story 2.6: Player removal tests

def test_remove_player_success():
    """Test successful removal of disconnected player."""
    from custom_components.spyster.game.player import PlayerSession
    from time import time, sleep

    state = GameState()
    state.create_session("host")

    # Add a player
    player = PlayerSession.create_new("Alice", is_host=False)
    state.players["Alice"] = player
    state.player_count = 1

    # Mark player as disconnected for 61 seconds
    player.disconnect()
    player.disconnected_at = time() - 61

    # Attempt removal
    success, error = state.remove_player("Alice")

    assert success is True
    assert error is None
    assert "Alice" not in state.players
    assert state.player_count == 0


def test_remove_player_not_found():
    """Test removal fails when player doesn't exist."""
    from custom_components.spyster.const import ERR_PLAYER_NOT_FOUND

    state = GameState()
    state.create_session("host")

    success, error = state.remove_player("NonExistent")

    assert success is False
    assert error == ERR_PLAYER_NOT_FOUND


def test_remove_player_still_connected():
    """Test removal fails when player is still connected."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_CANNOT_REMOVE_CONNECTED

    state = GameState()
    state.create_session("host")

    # Add a connected player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.connected = True
    state.players["Alice"] = player

    success, error = state.remove_player("Alice")

    assert success is False
    assert error == ERR_CANNOT_REMOVE_CONNECTED
    assert "Alice" in state.players  # Player not removed


def test_remove_player_not_disconnected_long_enough():
    """Test removal fails when player hasn't been disconnected for 60 seconds."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_CANNOT_REMOVE_CONNECTED
    from time import time

    state = GameState()
    state.create_session("host")

    # Add a player
    player = PlayerSession.create_new("Alice", is_host=False)
    state.players["Alice"] = player

    # Mark as disconnected for only 30 seconds
    player.disconnect()
    player.disconnected_at = time() - 30

    success, error = state.remove_player("Alice")

    assert success is False
    assert error == ERR_CANNOT_REMOVE_CONNECTED
    assert "Alice" in state.players  # Player not removed


def test_remove_player_invalid_phase():
    """Test removal fails when not in LOBBY phase."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_INVALID_PHASE
    from time import time

    state = GameState()
    state.create_session("host")
    state.transition_to(GamePhase.ROLES)  # Move out of LOBBY

    # Add a disconnected player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.disconnect()
    player.disconnected_at = time() - 61
    state.players["Alice"] = player

    success, error = state.remove_player("Alice")

    assert success is False
    assert error == ERR_INVALID_PHASE
    assert "Alice" in state.players  # Player not removed


@pytest.mark.asyncio
async def test_remove_player_cancels_timers():
    """Test that removing a player cancels their disconnect timers."""
    from custom_components.spyster.game.player import PlayerSession
    from time import time
    from unittest.mock import AsyncMock

    state = GameState()
    state.create_session("host")

    # Add a player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.disconnect()
    player.disconnected_at = time() - 61
    state.players["Alice"] = player

    # Add mock timers for the player
    callback = AsyncMock()
    state.start_timer("disconnect_grace:Alice", 10.0, callback)
    state.start_timer("reconnect_window:Alice", 10.0, callback)

    # Verify timers exist
    assert "disconnect_grace:Alice" in state._timers
    assert "reconnect_window:Alice" in state._timers

    # Remove player
    success, error = state.remove_player("Alice")

    assert success is True
    assert "disconnect_grace:Alice" not in state._timers
    assert "reconnect_window:Alice" not in state._timers


def test_get_state_includes_disconnect_duration():
    """Test that get_state includes disconnect_duration for players."""
    from custom_components.spyster.game.player import PlayerSession
    from time import time

    state = GameState()
    state.create_session("host")

    # Add a connected player
    connected_player = PlayerSession.create_new("Bob", is_host=True)
    connected_player.connected = True
    state.players["Bob"] = connected_player

    # Add a disconnected player
    disconnected_player = PlayerSession.create_new("Alice", is_host=False)
    disconnected_player.disconnect()
    disconnected_player.disconnected_at = time() - 45
    state.players["Alice"] = disconnected_player

    state.player_count = 2

    game_state = state.get_state()

    # Check players list
    assert "players" in game_state
    assert len(game_state["players"]) == 2

    # Find Alice's entry
    alice_data = next((p for p in game_state["players"] if p["name"] == "Alice"), None)
    assert alice_data is not None
    assert alice_data["connected"] is False
    assert alice_data["disconnect_duration"] is not None
    assert alice_data["disconnect_duration"] >= 44  # Should be close to 45

    # Find Bob's entry
    bob_data = next((p for p in game_state["players"] if p["name"] == "Bob"), None)
    assert bob_data is not None
    assert bob_data["connected"] is True
    assert bob_data["disconnect_duration"] is None


def test_remove_player_requires_host_permission():
    """Test that only host can remove players (Story 2.6)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_NOT_HOST
    from time import time

    state = GameState()
    state.create_session("host")

    # Add host
    host = PlayerSession.create_new("Host", is_host=True)
    state.players["Host"] = host

    # Add non-host player
    non_host = PlayerSession.create_new("Bob", is_host=False)
    state.players["Bob"] = non_host

    # Add disconnected player
    disconnected = PlayerSession.create_new("Alice", is_host=False)
    disconnected.disconnect()
    disconnected.disconnected_at = time() - 61
    state.players["Alice"] = disconnected

    state.player_count = 3

    # Non-host should NOT be able to remove players
    success, error = state.remove_player("Alice", requester_name="Bob")
    assert success is False
    assert error == ERR_NOT_HOST
    assert "Alice" in state.players  # Player not removed

    # Host SHOULD be able to remove players
    success, error = state.remove_player("Alice", requester_name="Host")
    assert success is True
    assert error is None
    assert "Alice" not in state.players  # Player removed


def test_remove_player_cannot_remove_self():
    """Test that host cannot remove themselves (Story 2.6)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_CANNOT_REMOVE_CONNECTED
    from time import time

    state = GameState()
    state.create_session("host")

    # Add host and mark as disconnected (edge case)
    host = PlayerSession.create_new("Host", is_host=True)
    host.disconnect()
    host.disconnected_at = time() - 61
    state.players["Host"] = host
    state.player_count = 1

    # Host should NOT be able to remove themselves
    success, error = state.remove_player("Host", requester_name="Host")
    assert success is False
    assert error == ERR_CANNOT_REMOVE_CONNECTED
    assert "Host" in state.players  # Host not removed


def test_remove_player_requester_not_found():
    """Test removal fails when requester doesn't exist (Story 2.6)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_PLAYER_NOT_FOUND
    from time import time

    state = GameState()
    state.create_session("host")

    # Add disconnected player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.disconnect()
    player.disconnected_at = time() - 61
    state.players["Alice"] = player

    # Non-existent requester
    success, error = state.remove_player("Alice", requester_name="NonExistent")
    assert success is False
    assert error == ERR_PLAYER_NOT_FOUND
    assert "Alice" in state.players  # Player not removed


def test_remove_player_without_requester_name():
    """Test removal works when requester_name is None (backward compatibility)."""
    from custom_components.spyster.game.player import PlayerSession
    from time import time

    state = GameState()
    state.create_session("host")

    # Add disconnected player
    player = PlayerSession.create_new("Alice", is_host=False)
    player.disconnect()
    player.disconnected_at = time() - 61
    state.players["Alice"] = player
    state.player_count = 1

    # Call without requester_name (backward compatibility - skips permission check)
    success, error = state.remove_player("Alice", requester_name=None)
    assert success is True
    assert error is None
    assert "Alice" not in state.players  # Player removed


# Story 3.2: Start Game with Player Validation tests

def test_get_connected_player_count_all_connected():
    """Test get_connected_player_count with all players connected."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    assert state.get_connected_player_count() == 4


def test_get_connected_player_count_mixed():
    """Test get_connected_player_count with mixed connection status."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")

    # Add 3 connected players
    for i in range(3):
        player = PlayerSession.create_new(f"Connected{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Connected{i}"] = player

    # Add 2 disconnected players
    for i in range(2):
        player = PlayerSession.create_new(f"Disconnected{i}", is_host=False)
        player.connected = False
        state.players[f"Disconnected{i}"] = player

    assert state.get_connected_player_count() == 3


def test_get_connected_player_count_none_connected():
    """Test get_connected_player_count with no connected players."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")

    # Add 2 disconnected players
    for i in range(2):
        player = PlayerSession.create_new(f"Player{i}", is_host=False)
        player.connected = False
        state.players[f"Player{i}"] = player

    assert state.get_connected_player_count() == 0


def test_can_start_game_success():
    """Test can_start_game returns True with 4-10 connected players."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    assert state.can_start_game() is True


def test_can_start_game_not_enough_players():
    """Test can_start_game returns False with < 4 connected players."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add only 3 connected players
    for i in range(3):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    assert state.can_start_game() is False


def test_can_start_game_wrong_phase():
    """Test can_start_game returns False when not in LOBBY phase."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.ROLES  # Not LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    assert state.can_start_game() is False


def test_can_start_game_already_started():
    """Test can_start_game returns False if game already started."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY
    state._game_started = True  # Already started

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    assert state.can_start_game() is False


def test_start_game_success():
    """Test successful game start with 4-10 players."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    success, error = state.start_game()

    assert success is True
    assert error is None
    assert state.phase == GamePhase.ROLES
    assert state.current_round == 1
    assert state._game_started is True


def test_start_game_not_enough_players():
    """Test game start fails with < 4 players."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_NOT_ENOUGH_PLAYERS

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add only 3 connected players
    for i in range(3):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    success, error = state.start_game()

    assert success is False
    assert error == ERR_NOT_ENOUGH_PLAYERS
    assert state.phase == GamePhase.LOBBY  # Phase unchanged
    assert state._game_started is False


def test_start_game_invalid_phase():
    """Test game start fails from non-LOBBY phase."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_INVALID_PHASE

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.ROLES  # Not LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    success, error = state.start_game()

    assert success is False
    assert error == ERR_INVALID_PHASE


def test_start_game_already_started():
    """Test game start fails if already started."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_GAME_ALREADY_STARTED

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY
    state._game_started = True

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    success, error = state.start_game()

    assert success is False
    assert error == ERR_GAME_ALREADY_STARTED


def test_start_game_too_many_players():
    """Test game start fails with > 10 players (edge case)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_GAME_FULL

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 11 connected players (should be prevented at join, but test the validation)
    for i in range(11):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    success, error = state.start_game()

    assert success is False
    assert error == ERR_GAME_FULL
    assert state.phase == GamePhase.LOBBY  # Phase unchanged


def test_start_game_counts_only_connected_players():
    """Test start_game only counts connected players."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_NOT_ENOUGH_PLAYERS

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 2 connected players
    for i in range(2):
        player = PlayerSession.create_new(f"Connected{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Connected{i}"] = player

    # Add 3 disconnected players (total 5, but only 2 connected)
    for i in range(3):
        player = PlayerSession.create_new(f"Disconnected{i}", is_host=False)
        player.connected = False
        state.players[f"Disconnected{i}"] = player

    success, error = state.start_game()

    assert success is False
    assert error == ERR_NOT_ENOUGH_PLAYERS


def test_get_state_includes_connected_count_and_can_start():
    """Test get_state includes connected_count and can_start for LOBBY phase."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    state.player_count = 4

    game_state = state.get_state()

    assert "connected_count" in game_state
    assert game_state["connected_count"] == 4
    assert "can_start" in game_state
    assert game_state["can_start"] is True


def test_game_state_initialization_includes_game_started():
    """Test that GameState __init__ includes _game_started field."""
    state = GameState()

    assert hasattr(state, "_game_started")
    assert state._game_started is False


def test_start_game_role_assignment_fails():
    """Test game start rollback when role assignment fails (FIX #8)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_ROLE_ASSIGNMENT_FAILED
    from unittest.mock import patch

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    # Mock assign_roles to raise ValueError
    with patch('custom_components.spyster.game.state.assign_roles', side_effect=ValueError("Test error")):
        success, error = state.start_game()

    # Verify rollback occurred
    assert success is False
    assert error == ERR_ROLE_ASSIGNMENT_FAILED
    assert state.phase == GamePhase.LOBBY  # Rolled back to LOBBY
    assert state.current_round == 0  # Reset
    assert state._game_started is False  # Reset


@pytest.mark.asyncio
async def test_start_game_player_disconnect_race_condition():
    """Test start_game handles player disconnect during start (FIX #9)."""
    from custom_components.spyster.game.player import PlayerSession
    from custom_components.spyster.const import ERR_NOT_ENOUGH_PLAYERS

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY

    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Player{i}"] = player

    # Simulate player disconnecting right before start_game is called
    state.players["Player1"].connected = False
    state.players["Player2"].connected = False

    # Now only 2 players connected - should fail
    success, error = state.start_game()

    assert success is False
    assert error == ERR_NOT_ENOUGH_PLAYERS
    assert state.phase == GamePhase.LOBBY
    assert state._game_started is False


def test_start_game_updates_player_count():
    """Test start_game updates player_count to match connected count (FIX #3)."""
    from custom_components.spyster.game.player import PlayerSession

    state = GameState()
    state.create_session("host")
    state.phase = GamePhase.LOBBY
    state.player_count = 10  # Incorrect value

    # Add 4 connected players + 2 disconnected
    for i in range(4):
        player = PlayerSession.create_new(f"Connected{i}", is_host=(i == 0))
        player.connected = True
        state.players[f"Connected{i}"] = player

    for i in range(2):
        player = PlayerSession.create_new(f"Disconnected{i}", is_host=False)
        player.connected = False
        state.players[f"Disconnected{i}"] = player

    success, error = state.start_game()

    assert success is True
    assert state.player_count == 4  # Updated to connected count only


# Story 3.4: Role Distribution with Per-Player Filtering Tests


def test_get_state_spy_filtering():
    """Spy should see location list, NOT actual location."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"},
            {"name": "School", "id": "school"}
        ]
    }

    # Add spy player
    alice = PlayerSession.create_new("Alice", is_host=False)
    game_state.players["Alice"] = alice
    game_state.player_count = 1

    spy_state = game_state.get_state(for_player="Alice")

    assert "role_info" in spy_state
    assert spy_state["role_info"]["is_spy"] is True
    assert "locations" in spy_state["role_info"]
    assert "Beach" in spy_state["role_info"]["locations"]
    assert "Hospital" in spy_state["role_info"]["locations"]
    assert "School" in spy_state["role_info"]["locations"]
    assert "location" not in spy_state["role_info"]  # MUST NOT reveal actual location
    assert "role" not in spy_state["role_info"]


def test_get_state_non_spy_filtering():
    """Non-spy should see location and role, NOT location list."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }

    # Add non-spy player
    bob = PlayerSession.create_new("Bob", is_host=False)
    bob.role = "Lifeguard"
    game_state.players["Bob"] = bob
    game_state.player_count = 1

    bob_state = game_state.get_state(for_player="Bob")

    assert "role_info" in bob_state
    assert bob_state["role_info"]["is_spy"] is False
    assert bob_state["role_info"]["location"] == "Beach"
    assert bob_state["role_info"]["role"] == "Lifeguard"
    assert "locations" not in bob_state["role_info"]  # MUST NOT reveal location list


def test_get_state_no_cross_contamination():
    """Each player gets different state - no leakage."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }

    alice = PlayerSession.create_new("Alice", is_host=False)
    bob = PlayerSession.create_new("Bob", is_host=False)
    bob.role = "Lifeguard"
    game_state.players["Alice"] = alice
    game_state.players["Bob"] = bob
    game_state.player_count = 2

    alice_state = game_state.get_state(for_player="Alice")
    bob_state = game_state.get_state(for_player="Bob")

    # Alice (spy) should NOT know Bob's role
    assert "role" not in alice_state.get("role_info", {})

    # Bob (non-spy) should NOT see location list
    assert "locations" not in bob_state.get("role_info", {})

    # States must be different
    assert alice_state != bob_state


def test_get_state_questioning_phase_spy():
    """Test spy filtering in QUESTIONING phase."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }

    alice = PlayerSession.create_new("Alice", is_host=False)
    game_state.players["Alice"] = alice

    spy_state = game_state.get_state(for_player="Alice")

    assert spy_state["is_spy"] is True
    assert "locations" in spy_state
    assert "location" not in spy_state
    assert "role" not in spy_state


def test_get_state_questioning_phase_non_spy():
    """Test non-spy filtering in QUESTIONING phase."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }

    bob = PlayerSession.create_new("Bob", is_host=False)
    bob.role = "Lifeguard"
    game_state.players["Bob"] = bob

    non_spy_state = game_state.get_state(for_player="Bob")

    assert non_spy_state["is_spy"] is False
    assert non_spy_state["location"] == "Beach"
    assert non_spy_state["role"] == "Lifeguard"
    assert "locations" not in non_spy_state


def test_get_state_vote_phase_filtering():
    """Test role filtering in VOTE phase."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.VOTE
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.location_pack = {
        "locations": [
            {"name": "Beach", "id": "beach"},
            {"name": "Hospital", "id": "hospital"}
        ]
    }
    game_state.votes = {}

    alice = PlayerSession.create_new("Alice", is_host=False)
    bob = PlayerSession.create_new("Bob", is_host=False)
    bob.role = "Lifeguard"
    game_state.players["Alice"] = alice
    game_state.players["Bob"] = bob

    # Test spy
    spy_state = game_state.get_state(for_player="Alice")
    assert spy_state["is_spy"] is True
    assert "locations" in spy_state
    assert "location" not in spy_state

    # Test non-spy
    non_spy_state = game_state.get_state(for_player="Bob")
    assert non_spy_state["is_spy"] is False
    assert non_spy_state["location"] == "Beach"
    assert non_spy_state["role"] == "Lifeguard"


def test_get_state_reveal_phase_shows_all():
    """Test REVEAL phase shows all information."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.REVEAL
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}
    game_state.convicted_player = "Alice"
    game_state.votes = {
        "Bob": {"target": "Alice", "confidence": 2},
        "Carol": {"target": "Alice", "confidence": 1}
    }

    state = game_state.get_state(for_player="Bob")

    assert state["actual_spy"] == "Alice"
    assert state["convicted"] == "Alice"
    assert state["location"] == "Beach"
    assert len(state["votes"]) == 2


def test_get_state_scoring_phase():
    """Test SCORING phase shows scores and results."""
    from custom_components.spyster.game.player import PlayerSession

    game_state = GameState()
    game_state.phase = GamePhase.SCORING
    game_state.spy_name = "Alice"
    game_state.convicted_player = "Alice"

    alice = PlayerSession.create_new("Alice", is_host=False)
    alice.score = 0
    bob = PlayerSession.create_new("Bob", is_host=False)
    bob.score = 2
    game_state.players["Alice"] = alice
    game_state.players["Bob"] = bob

    state = game_state.get_state(for_player="Bob")

    assert "scores" in state
    assert state["scores"]["Alice"] == 0
    assert state["scores"]["Bob"] == 2
    assert state["actual_spy"] == "Alice"
    assert state["convicted"] == "Alice"


def test_get_state_no_player_name_returns_host_view():
    """Test get_state without for_player returns host/public view."""
    game_state = GameState()
    game_state.phase = GamePhase.ROLES
    game_state.spy_name = "Alice"
    game_state.current_location = {"name": "Beach", "id": "beach"}

    state = game_state.get_state(for_player=None)

    # Host view should not have role_info
    assert "role_info" not in state
    assert "is_spy" not in state
    assert "location" not in state


# ============================================================================
# Story 4.2: Round Timer with Countdown Tests
# ============================================================================

@pytest.mark.asyncio
async def test_round_timer_starts_with_tracking():
    """AC1: Timer starts with tracking for accurate remaining time calculation."""
    import time
    
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    start_time = time.time()
    game.start_timer("round", 420.0, dummy_callback)
    
    assert "round" in game._timers
    assert "round" in game._timer_start_times
    assert "round" in game._timer_durations
    assert game._timer_durations["round"] == 420.0
    # Start time should be very recent (within 1 second)
    assert abs(game._timer_start_times["round"] - start_time) < 1.0


@pytest.mark.asyncio
async def test_round_timer_cancels_existing():
    """AC1: Existing timer is cancelled before starting new one (ARCH-11)."""
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    # Start first timer
    game.start_timer("round", 420.0, dummy_callback)
    first_timer = game._timers["round"]
    first_start_time = game._timer_start_times["round"]
    
    # Wait a moment then start second timer
    await asyncio.sleep(0.1)
    game.start_timer("round", 300.0, dummy_callback)
    
    assert first_timer.cancelled()
    assert "round" in game._timers
    assert game._timers["round"] != first_timer
    assert game._timer_durations["round"] == 300.0
    # Start time should be updated
    assert game._timer_start_times["round"] > first_start_time


@pytest.mark.asyncio
async def test_timer_remaining_accuracy():
    """AC4: Timer remaining calculation is accurate (NFR5)."""
    import time
    
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    # Start timer with 60 seconds
    game.start_timer("round", 60.0, dummy_callback)
    
    # Wait 2 seconds
    await asyncio.sleep(2.0)
    
    remaining = game._get_timer_remaining("round")
    
    # Should be ~58 seconds remaining (60 - 2)
    # Allow ±1 second tolerance per NFR5
    assert 57.0 <= remaining <= 59.0


@pytest.mark.asyncio
async def test_timer_auto_transitions_to_vote():
    """AC3: Timer expiry triggers vote transition (FR30)."""
    game = GameState()
    
    # Setup game state for QUESTIONING phase
    game.phase = GamePhase.QUESTIONING
    game.players = {}  # Empty players for test
    
    # Mock call_vote to track if it was called
    call_vote_called = False
    original_call_vote = game.call_vote
    
    def mock_call_vote():
        nonlocal call_vote_called
        call_vote_called = True
        return True, None
    
    game.call_vote = mock_call_vote
    
    # Start very short timer (100ms)
    game.start_timer("round", 0.1, game._on_round_timer_expired)
    
    # Wait for timer to expire
    await asyncio.sleep(0.2)
    
    # Verify call_vote was triggered
    assert call_vote_called


def test_get_state_includes_timer_in_questioning():
    """AC2: get_state() includes timer data during QUESTIONING."""
    import time
    
    game = GameState()
    game.phase = GamePhase.QUESTIONING
    
    async def dummy_callback(name: str):
        pass
    
    # Start timer
    game.start_timer("round", 420.0, dummy_callback)
    
    state = game.get_state()
    
    assert "timer" in state
    assert state["timer"]["name"] == "round"
    assert state["timer"]["total"] == 420.0
    assert 0 <= state["timer"]["remaining"] <= 420.0


@pytest.mark.asyncio
async def test_cancel_timer_cleans_up_tracking():
    """Verify cancel_timer removes tracking dictionaries."""
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    game.start_timer("round", 420.0, dummy_callback)
    
    assert "round" in game._timers
    assert "round" in game._timer_start_times
    assert "round" in game._timer_durations
    
    game.cancel_timer("round")
    
    assert "round" not in game._timers
    assert "round" not in game._timer_start_times
    assert "round" not in game._timer_durations


@pytest.mark.asyncio
async def test_cancel_all_timers_cleans_up_tracking():
    """Verify cancel_all_timers clears all tracking dictionaries."""
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    game.start_timer("round", 420.0, dummy_callback)
    game.start_timer("vote", 60.0, dummy_callback)
    
    assert len(game._timers) == 2
    assert len(game._timer_start_times) == 2
    assert len(game._timer_durations) == 2
    
    game.cancel_all_timers()
    
    assert len(game._timers) == 0
    assert len(game._timer_start_times) == 0
    assert len(game._timer_durations) == 0


def test_get_timer_remaining_returns_zero_for_nonexistent():
    """_get_timer_remaining returns 0.0 for non-existent timer."""
    game = GameState()
    
    remaining = game._get_timer_remaining("nonexistent")
    
    assert remaining == 0.0


@pytest.mark.asyncio
async def test_get_timer_remaining_returns_zero_for_done_timer():
    """_get_timer_remaining returns 0.0 for completed timer."""
    game = GameState()
    
    async def dummy_callback(name: str):
        pass
    
    # Start very short timer
    game.start_timer("round", 0.01, dummy_callback)
    
    # Wait for it to complete
    await asyncio.sleep(0.05)
    
    remaining = game._get_timer_remaining("round")
    
    assert remaining == 0.0


# Story 4.5: Call Vote Functionality Tests


def test_call_vote_success():
    """Call vote transitions from QUESTIONING to VOTE."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    success, error = game_state.call_vote()

    assert success is True
    assert error is None
    assert game_state.phase == GamePhase.VOTE
    assert "vote" in game_state._timers  # Vote timer started


def test_call_vote_invalid_phase():
    """Call vote fails in non-QUESTIONING phase."""
    from custom_components.spyster.const import ERR_INVALID_PHASE

    game_state = GameState()

    # Test in LOBBY
    game_state.phase = GamePhase.LOBBY
    success, error = game_state.call_vote()
    assert success is False
    assert error == ERR_INVALID_PHASE

    # Test in VOTE
    game_state.phase = GamePhase.VOTE
    success, error = game_state.call_vote()
    assert success is False
    assert error == ERR_INVALID_PHASE

    # Test in REVEAL
    game_state.phase = GamePhase.REVEAL
    success, error = game_state.call_vote()
    assert success is False
    assert error == ERR_INVALID_PHASE


def test_call_vote_cancels_round_timer():
    """Call vote cancels active round timer (ARCH-11)."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # Start a round timer
    async def dummy_callback(name):
        pass

    game_state.start_timer("round", 420, dummy_callback)
    assert "round" in game_state._timers
    round_task = game_state._timers["round"]
    assert not round_task.done()

    # Call vote
    success, _ = game_state.call_vote()

    assert success is True
    assert round_task.cancelled()  # Round timer cancelled
    assert "round" not in game_state._timers


def test_call_vote_starts_vote_timer():
    """Call vote starts 60-second vote timer (ARCH-10)."""
    from custom_components.spyster.const import VOTE_TIMER_DURATION

    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    success, _ = game_state.call_vote()

    assert success is True
    assert "vote" in game_state._timers
    assert game_state._timers["vote"] is not None
    # Timer duration is tracked
    assert game_state._timer_durations.get("vote") == VOTE_TIMER_DURATION


def test_call_vote_race_condition():
    """Multiple simultaneous call_vote requests handled correctly."""
    from custom_components.spyster.const import ERR_INVALID_PHASE

    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # First call succeeds
    success1, error1 = game_state.call_vote()
    assert success1 is True
    assert game_state.phase == GamePhase.VOTE

    # Second call (immediate) fails - already in VOTE
    success2, error2 = game_state.call_vote()
    assert success2 is False
    assert error2 == ERR_INVALID_PHASE
    assert game_state.phase == GamePhase.VOTE  # Still in VOTE


def test_call_vote_stores_caller_name():
    """Call vote stores caller name for attribution (Story 4.5: AC6)."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    success, _ = game_state.call_vote(caller_name="Alice")

    assert success is True
    assert game_state.vote_caller == "Alice"


def test_call_vote_timer_attribution():
    """Round timer expiry sets vote_caller to [TIMER] (Story 4.5: AC6)."""
    game_state = GameState()
    game_state.phase = GamePhase.QUESTIONING

    # Simulate timer-triggered call_vote
    success, _ = game_state.call_vote(caller_name="[TIMER]")

    assert success is True
    assert game_state.vote_caller == "[TIMER]"


def test_get_state_includes_vote_caller():
    """VOTE phase state includes vote_caller (Story 4.5: AC6)."""
    game_state = GameState()
    game_state.phase = GamePhase.VOTE
    game_state.vote_caller = "Bob"

    state = game_state.get_state()

    assert state["vote_caller"] == "Bob"


async def test_on_vote_timeout():
    """Vote timer expiration transitions to REVEAL phase."""
    game_state = GameState()
    game_state.phase = GamePhase.VOTE
    game_state.players = {"Alice": type('obj', (object,), {"name": "Alice"})}

    # Call the timer callback
    await game_state._on_vote_timeout("vote")

    assert game_state.phase == GamePhase.REVEAL
    assert "vote" not in game_state._timers  # Vote timer cancelled


# ============================================================================
# Story 4.3: Questioner/Answerer Turn Management Tests
# ============================================================================

def test_initialize_turn_order():
    """Test turn order initialization (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
        player.connected = True
        state.players[player.name] = player
    
    state.initialize_turn_order()
    
    assert len(state._turn_order) == 4
    assert state.current_questioner_id is not None
    assert state.current_answerer_id is not None
    assert state.current_questioner_id != state.current_answerer_id
    assert state.current_questioner_id in state._turn_order
    assert state.current_answerer_id in state._turn_order


def test_initialize_turn_order_shuffled():
    """Test turn order is shuffled (probabilistic - Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    orders = []
    for _ in range(10):
        state = GameState()
        state.phase = GamePhase.QUESTIONING
        
        # Add 4 players with deterministic names
        for i in range(4):
            player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
            player.connected = True
            state.players[player.name] = player
        
        state.initialize_turn_order()
        orders.append(tuple(state._turn_order))
    
    # At least some variation in 10 runs (not all identical)
    unique_orders = len(set(orders))
    assert unique_orders > 1, "Turn order should be shuffled"


def test_advance_turn():
    """Test turn advancement (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
        player.connected = True
        state.players[player.name] = player
    
    state.initialize_turn_order()
    
    initial_questioner = state.current_questioner_id
    initial_answerer = state.current_answerer_id
    
    state.advance_turn()
    
    # Answerer should become questioner
    assert state.current_questioner_id == initial_answerer
    # New answerer should be different
    assert state.current_answerer_id != initial_answerer
    assert state.current_answerer_id in state._turn_order


def test_advance_turn_insufficient_players():
    """Test advance_turn handles insufficient players (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add only 1 player
    player = PlayerSession.create_new("Player1", is_host=True)
    player.connected = True
    state.players[player.name] = player
    
    state.initialize_turn_order()
    
    # Should not crash with insufficient players
    state.advance_turn()
    # Turn order should remain empty or incomplete
    assert len(state._turn_order) < 2


def test_get_current_turn_info():
    """Test turn info retrieval (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
        player.connected = True
        state.players[player.name] = player
    
    state.initialize_turn_order()
    
    turn_info = state.get_current_turn_info()
    
    assert "questioner" in turn_info
    assert "answerer" in turn_info
    assert "id" in turn_info["questioner"]
    assert "name" in turn_info["questioner"]
    assert "id" in turn_info["answerer"]
    assert "name" in turn_info["answerer"]
    assert turn_info["questioner"]["name"] in state.players
    assert turn_info["answerer"]["name"] in state.players


def test_get_current_turn_info_wrong_phase():
    """Test turn info empty in non-QUESTIONING phase (Story 4.3)."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    
    turn_info = state.get_current_turn_info()
    
    assert turn_info == {}


def test_get_current_turn_info_no_turns_initialized():
    """Test turn info empty when turns not initialized (Story 4.3)."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    # Don't initialize turns
    
    turn_info = state.get_current_turn_info()
    
    assert turn_info == {}


def test_get_state_includes_turn_info():
    """Test state includes turn info in QUESTIONING phase (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add 4 connected players
    for i in range(4):
        player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
        player.connected = True
        state.players[player.name] = player
    
    state.initialize_turn_order()
    
    game_state = state.get_state()
    
    assert "current_turn" in game_state
    assert game_state["current_turn"]["questioner"]["name"] is not None
    assert game_state["current_turn"]["answerer"]["name"] is not None


def test_get_state_no_turn_info_in_lobby():
    """Test state does not include turn info in LOBBY phase (Story 4.3)."""
    state = GameState()
    state.phase = GamePhase.LOBBY
    
    game_state = state.get_state()
    
    assert "current_turn" not in game_state


def test_advance_turn_wraps_around():
    """Test turn advancement wraps around to beginning (Story 4.3)."""
    from custom_components.spyster.game.player import PlayerSession
    
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    
    # Add 3 players for easier wrap-around testing
    for i in range(3):
        player = PlayerSession.create_new(f"Player{i+1}", is_host=(i == 0))
        player.connected = True
        state.players[player.name] = player
    
    state.initialize_turn_order()
    
    # Advance through all players and verify wrap-around
    seen_questioners = set()
    for _ in range(6):  # More than number of players
        seen_questioners.add(state.current_questioner_id)
        state.advance_turn()
    
    # Should have seen all players as questioners
    assert len(seen_questioners) == 3
    assert seen_questioners == set(state._turn_order)

# Story 4.1: Phase Transition Tests

@pytest.mark.asyncio
async def test_transition_to_questioning_success():
    """Test successful transition from ROLES to QUESTIONING."""
    state = GameState()
    state.phase = GamePhase.ROLES
    state.config.round_duration_minutes = 5
    
    success, error = await state.transition_to_questioning()
    
    assert success is True
    assert error is None
    assert state.phase == GamePhase.QUESTIONING
    assert "round" in state._timers
    assert not state._timers["round"].done()


@pytest.mark.asyncio
async def test_transition_to_questioning_invalid_phase():
    """Test transition fails from non-ROLES phase."""
    from custom_components.spyster.const import ERR_INVALID_PHASE_TRANSITION
    
    state = GameState()
    state.phase = GamePhase.LOBBY
    
    success, error = await state.transition_to_questioning()
    
    assert success is False
    assert error == ERR_INVALID_PHASE_TRANSITION
    assert state.phase == GamePhase.LOBBY


@pytest.mark.asyncio
async def test_role_display_timer_triggers_transition():
    """Test role display timer automatically transitions to QUESTIONING."""
    from custom_components.spyster.const import TIMER_ROLE_DISPLAY
    
    state = GameState()
    state.phase = GamePhase.ROLES
    state.config.round_duration_minutes = 5
    
    success, error = state.start_role_display_timer()
    assert success is True
    assert "role_display" in state._timers
    
    # Wait for timer to expire (5 seconds + tolerance)
    await asyncio.sleep(TIMER_ROLE_DISPLAY + 0.5)
    
    # Verify phase transitioned
    assert state.phase == GamePhase.QUESTIONING
    assert "round" in state._timers


@pytest.mark.asyncio
async def test_start_round_timer():
    """Test round timer starts correctly."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    state.config.round_duration_minutes = 5
    
    success, error = await state.start_round_timer()
    
    assert success is True
    assert error is None
    assert "round" in state._timers
    assert not state._timers["round"].done()


@pytest.mark.asyncio
async def test_start_role_display_timer_invalid_phase():
    """Test role display timer fails in non-ROLES phase."""
    from custom_components.spyster.const import ERR_INVALID_PHASE
    
    state = GameState()
    state.phase = GamePhase.LOBBY
    
    success, error = state.start_role_display_timer()
    
    assert success is False
    assert error == ERR_INVALID_PHASE


@pytest.mark.asyncio
async def test_cancel_timer_before_starting_new():
    """Test timer cancellation works correctly (ARCH-11)."""
    state = GameState()
    state.phase = GamePhase.ROLES
    state.config.round_duration_minutes = 5
    
    # Start first timer
    state.start_role_display_timer()
    assert "role_display" in state._timers
    first_task = state._timers["role_display"]
    
    # Start second timer (should cancel first)
    state.start_role_display_timer()
    assert "role_display" in state._timers
    second_task = state._timers["role_display"]
    
    # First task should be cancelled
    assert first_task.cancelled() or first_task.done()
    # Second task should be running
    assert not second_task.done()
    
    # Cleanup
    state.cancel_timer("role_display")


@pytest.mark.asyncio
async def test_get_state_includes_questioning_timer():
    """Test get_state includes timer data in QUESTIONING phase."""
    state = GameState()
    state.phase = GamePhase.QUESTIONING
    state.config.round_duration_minutes = 5
    
    # Start round timer
    await state.start_round_timer()
    
    # Get state
    game_state = state.get_state()
    
    assert game_state["phase"] == "QUESTIONING"
    assert "timer" in game_state
    assert game_state["timer"]["name"] == "round"
    assert game_state["timer"]["remaining"] > 0
    
    # Cleanup
    state.cancel_timer("round")
