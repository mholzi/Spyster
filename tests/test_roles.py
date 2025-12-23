"""Tests for role assignment logic (Story 3.3)."""
import pytest
import secrets

from custom_components.spyster.game.roles import (
    assign_spy,
    get_player_role_data,
    assign_roles
)
from custom_components.spyster.game.state import GameState


@pytest.fixture
def game_state():
    """Create a GameState with 5 connected players."""
    state = GameState()

    # Add 5 players
    for i in range(1, 6):
        success, error, player = state.add_player(f"Player{i}", is_host=(i == 1))
        assert success
        player.connected = True

    return state


@pytest.fixture
def mock_location_pack(monkeypatch):
    """Mock location pack data."""
    mock_pack = {
        "id": "test",
        "name": "Test Pack",
        "locations": [
            {
                "id": "beach",
                "name": "Beach",
                "flavor": "Sun and sand",
                "roles": [
                    {"name": "Lifeguard", "hint": "You watch swimmers"},
                    {"name": "Tourist", "hint": "You're on vacation"},
                    {"name": "Vendor", "hint": "You sell snacks"}
                ]
            },
            {
                "id": "airplane",
                "name": "Airplane",
                "flavor": "Flying high",
                "roles": [
                    {"name": "Pilot", "hint": "You fly the plane"},
                    {"name": "Attendant", "hint": "You serve passengers"}
                ]
            }
        ]
    }

    # Mock the content module
    import custom_components.spyster.game.content as content_module
    content_module._LOADED_PACKS["classic"] = mock_pack

    return mock_pack


def test_assign_spy_selects_one_player(game_state):
    """Test that exactly one spy is selected (AC1)."""
    spy_name = assign_spy(game_state)

    assert spy_name in game_state.players
    assert game_state.players[spy_name].connected


def test_assign_spy_fails_with_no_players():
    """Test spy assignment fails with no connected players."""
    state = GameState()

    with pytest.raises(ValueError, match="no connected players"):
        assign_spy(state)


def test_assign_spy_fails_with_too_few_players(game_state):
    """Test spy assignment fails with < 4 players."""
    # Disconnect all but 3 players
    connected_count = 0
    for player in game_state.players.values():
        if connected_count >= 3:
            player.connected = False
        else:
            connected_count += 1

    with pytest.raises(ValueError, match="need 4\\+ players"):
        assign_spy(game_state)


def test_assign_spy_uses_csprng(game_state, monkeypatch):
    """Test that secrets.choice() is used (not random.choice) - NFR6, ARCH-6."""
    called = []

    def mock_choice(seq):
        called.append(True)
        return seq[0]

    monkeypatch.setattr(secrets, "choice", mock_choice)

    assign_spy(game_state)

    assert len(called) == 1, "secrets.choice() must be called"


def test_assign_spy_never_logs_identity(game_state, caplog):
    """Test that spy identity is never logged - SECURITY requirement."""
    spy_name = assign_spy(game_state)

    # Check that spy_name does NOT appear in log messages
    for record in caplog.records:
        assert spy_name not in record.message, "Spy identity must never be logged"


def test_get_player_role_data_spy(game_state, mock_location_pack):
    """Test spy receives location list (not actual location) - AC3."""
    game_state.spy_name = "Player1"
    game_state.current_location = mock_location_pack["locations"][0]
    game_state.location_pack = "classic"

    role_data = get_player_role_data(game_state, "Player1")

    assert role_data["is_spy"] is True
    assert "locations" in role_data
    assert isinstance(role_data["locations"], list)
    assert len(role_data["locations"]) == 2  # Beach and Airplane
    assert "Beach" in role_data["locations"]
    assert "Airplane" in role_data["locations"]

    # SECURITY: Spy must NOT see actual location
    assert "location" not in role_data
    assert "role" not in role_data


def test_get_player_role_data_non_spy(game_state, mock_location_pack):
    """Test non-spy receives location and role - AC3."""
    game_state.spy_name = "Player1"
    game_state.current_location = mock_location_pack["locations"][0]
    game_state.player_roles = {
        "Player2": {"name": "Lifeguard", "hint": "You watch swimmers"}
    }

    role_data = get_player_role_data(game_state, "Player2")

    assert role_data["is_spy"] is False
    assert role_data["location"] == "Beach"
    assert role_data["role"] == "Lifeguard"

    # SECURITY: Non-spy must NOT see location list
    assert "locations" not in role_data


def test_get_player_role_data_no_location(game_state):
    """Test error when location not assigned."""
    game_state.spy_name = "Player1"
    game_state.current_location = None

    with pytest.raises(ValueError, match="No location assigned"):
        get_player_role_data(game_state, "Player1")


def test_assign_roles_complete_flow(game_state, mock_location_pack):
    """Test full role assignment flow - AC1, AC2."""
    game_state.current_round = 1
    game_state.location_pack = "classic"

    assign_roles(game_state)

    # Verify spy assigned
    assert game_state.spy_name is not None
    assert game_state.spy_name in game_state.players

    # Verify location selected
    assert game_state.current_location is not None
    assert game_state.current_location["name"] in ["Beach", "Airplane"]

    # Verify roles assigned to non-spy players
    expected_non_spy_count = 4  # 5 players - 1 spy
    assert len(game_state.player_roles) == expected_non_spy_count

    # Verify spy does NOT have a role assigned
    assert game_state.spy_name not in game_state.player_roles


def test_assign_roles_uses_csprng_for_location(game_state, mock_location_pack, monkeypatch):
    """Test that location selection, spy selection, AND role assignments all use CSPRNG - NFR6."""
    called = []
    original_choice = secrets.choice

    def mock_choice(seq):
        called.append(len(seq))
        return original_choice(seq)

    monkeypatch.setattr(secrets, "choice", mock_choice)

    game_state.current_round = 1
    game_state.location_pack = "classic"
    assign_roles(game_state)

    # CRITICAL: Should be called for:
    # 1. Location selection (2 locations in mock pack)
    # 2. Spy selection (5 connected players)
    # 3. Role assignments (4 non-spy players, each gets a role via secrets.choice)
    # Expected calls: 1 (location) + 1 (spy) + 4 (roles) = 6 calls minimum
    assert len(called) >= 6, f"secrets.choice() must be called for location, spy, AND each role assignment (got {len(called)} calls)"

    # Verify we have the expected call patterns
    # - Location selection: 2 locations
    # - Spy selection: 5 players
    # - Role assignments: should see calls with 3 items (Beach has 3 roles)
    assert 2 in called, "Location selection should call with 2 locations"
    assert 5 in called, "Spy selection should call with 5 players"
    # Count role assignment calls (should have 3-item sequences for Beach roles)
    role_calls = [c for c in called if c == 3]
    assert len(role_calls) == 4, f"Should have 4 role assignment calls (got {len(role_calls)})"


def test_role_privacy_network_inspection(game_state, mock_location_pack):
    """Test that network inspection cannot reveal spy identity - NFR7."""
    import json

    game_state.spy_name = "Player1"
    game_state.current_location = mock_location_pack["locations"][0]
    game_state.player_roles = {
        "Player2": {"name": "Lifeguard", "hint": "You watch swimmers"}
    }

    # Get state for two different players
    spy_state = game_state.get_state(for_player="Player1")
    non_spy_state = game_state.get_state(for_player="Player2")

    # Convert to JSON (simulating network transmission)
    spy_json = json.dumps(spy_state)
    non_spy_json = json.dumps(non_spy_state)

    # SECURITY: Neither state should contain spy_name field
    assert "spy_name" not in spy_json
    assert "_spy_name" not in spy_json
    assert "spy_name" not in non_spy_json

    # SECURITY: Verify spy sees location list but NOT actual location dict
    assert "possible_locations" in spy_json or "locations" in spy_json
    # Ensure spy does NOT see the actual location name
    assert "Beach" not in spy_state.get("role_info", {}).get("location", "")

    # Verify non-spy sees actual location
    assert "Beach" in non_spy_json

    # CRITICAL: Verify current_location dict is never in broadcast
    assert '"roles"' not in spy_json  # roles array should not be in spy's state
    assert '"roles"' not in non_spy_json  # roles array should not be in non-spy's state


def test_random_spy_per_round(game_state, mock_location_pack):
    """Test that spy can change between rounds - AC2, FR23."""
    game_state.location_pack = "classic"

    spies = set()

    # Run 10 rounds to verify randomness
    for round_num in range(1, 11):
        game_state.current_round = round_num
        assign_roles(game_state)
        spies.add(game_state.spy_name)

    # With 5 players over 10 rounds, we should see multiple different spies
    # (extremely unlikely to get same player 10 times in a row)
    assert len(spies) > 1, "Spy selection should be random across rounds"


def test_assign_roles_with_more_players_than_roles(mock_location_pack):
    """Test role assignment when more players than available roles."""
    state = GameState()

    # Add 8 players (more than the 3 roles in Beach location)
    for i in range(1, 9):
        success, error, player = state.add_player(f"Player{i}", is_host=(i == 1))
        assert success
        player.connected = True

    state.current_round = 1
    state.location_pack = "classic"

    # Force selection of Beach location (which has only 3 roles)
    import custom_components.spyster.game.content as content_module
    original_choice = secrets.choice

    def mock_choice_beach(seq):
        if isinstance(seq, list) and len(seq) > 0 and isinstance(seq[0], dict):
            if "name" in seq[0]:
                # This is location selection
                return mock_location_pack["locations"][0]  # Beach
        return original_choice(seq)

    import unittest.mock
    with unittest.mock.patch('secrets.choice', side_effect=mock_choice_beach):
        assign_roles(state)

    # Should assign roles with repetition (7 non-spy players, 3 available roles)
    assert len(state.player_roles) == 7  # 8 players - 1 spy

    # All non-spy players should have roles from Beach location
    beach_role_names = ["Lifeguard", "Tourist", "Vendor"]
    for role in state.player_roles.values():
        assert role["name"] in beach_role_names


def test_player_role_fallback_for_missing_role(game_state, mock_location_pack):
    """Test fallback when player has no role assigned."""
    game_state.spy_name = "Player1"
    game_state.current_location = mock_location_pack["locations"][0]
    game_state.player_roles = {}  # No roles assigned

    # Should not raise error, should provide fallback
    role_data = get_player_role_data(game_state, "Player2")

    assert role_data["is_spy"] is False
    assert role_data["role"] == "Visitor"


def test_assign_roles_fails_with_empty_roles_list(game_state, mock_location_pack):
    """Test that assign_roles fails gracefully when location has no roles."""
    game_state.current_round = 1
    game_state.location_pack = "classic"

    # Create a malformed location with no roles
    import custom_components.spyster.game.content as content_module
    content_module._LOADED_PACKS["classic"]["locations"].append({
        "id": "empty",
        "name": "Empty Location",
        "flavor": "Nothing here",
        "roles": []  # Empty roles list
    })

    # Force selection of empty location
    original_choice = secrets.choice

    def mock_choice_empty(seq):
        if isinstance(seq, list) and len(seq) > 0 and isinstance(seq[0], dict):
            if "name" in seq[0]:
                # Return the empty location
                return {"id": "empty", "name": "Empty Location", "flavor": "Nothing here", "roles": []}
        return original_choice(seq)

    import unittest.mock
    with unittest.mock.patch('secrets.choice', side_effect=mock_choice_empty):
        # Should raise ValueError about no roles
        with pytest.raises(ValueError, match="has no roles defined"):
            assign_roles(game_state)
