"""Tests for game configuration (Story 3.1)."""
import pytest

from custom_components.spyster.game.config import GameConfig
from custom_components.spyster.const import (
    CONFIG_DEFAULT_ROUND_DURATION,
    CONFIG_DEFAULT_ROUNDS,
    CONFIG_DEFAULT_LOCATION_PACK,
    ERR_CONFIG_INVALID_DURATION,
    ERR_CONFIG_INVALID_ROUNDS,
    ERR_CONFIG_INVALID_PACK,
)


def test_default_config():
    """Test default configuration values."""
    config = GameConfig()
    assert config.round_duration_minutes == CONFIG_DEFAULT_ROUND_DURATION
    assert config.num_rounds == CONFIG_DEFAULT_ROUNDS
    assert config.location_pack == CONFIG_DEFAULT_LOCATION_PACK


def test_valid_config():
    """Test validation of valid config."""
    config = GameConfig(round_duration_minutes=10, num_rounds=3)
    valid, error = config.validate()
    assert valid is True
    assert error is None


def test_invalid_round_duration_too_low():
    """Test validation rejects round duration below minimum."""
    config = GameConfig(round_duration_minutes=0)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_DURATION


def test_invalid_round_duration_too_high():
    """Test validation rejects round duration above maximum."""
    config = GameConfig(round_duration_minutes=31)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_DURATION


def test_invalid_num_rounds_too_low():
    """Test validation rejects invalid number of rounds (too low)."""
    config = GameConfig(num_rounds=0)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_ROUNDS


def test_invalid_num_rounds_too_high():
    """Test validation rejects invalid number of rounds (too high)."""
    config = GameConfig(num_rounds=21)
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_ROUNDS


def test_invalid_location_pack():
    """Test validation rejects non-existent location pack."""
    config = GameConfig(location_pack="nonexistent_pack")
    valid, error = config.validate()
    assert valid is False
    assert error == ERR_CONFIG_INVALID_PACK


def test_valid_location_pack():
    """Test validation accepts valid location pack."""
    config = GameConfig(location_pack="classic")
    valid, error = config.validate()
    assert valid is True
    assert error is None


def test_to_dict():
    """Test serialization to dictionary."""
    config = GameConfig(round_duration_minutes=10, num_rounds=3, location_pack="classic")
    data = config.to_dict()
    assert data["round_duration_minutes"] == 10
    assert data["num_rounds"] == 3
    assert data["location_pack"] == "classic"


def test_from_dict():
    """Test deserialization from dictionary."""
    data = {"round_duration_minutes": 15, "num_rounds": 7, "location_pack": "classic"}
    config = GameConfig.from_dict(data)
    assert config.round_duration_minutes == 15
    assert config.num_rounds == 7
    assert config.location_pack == "classic"


def test_from_dict_defaults():
    """Test deserialization uses defaults for missing fields."""
    data = {}
    config = GameConfig.from_dict(data)
    assert config.round_duration_minutes == CONFIG_DEFAULT_ROUND_DURATION
    assert config.num_rounds == CONFIG_DEFAULT_ROUNDS
    assert config.location_pack == CONFIG_DEFAULT_LOCATION_PACK


def test_boundary_values():
    """Test boundary values for configuration."""
    # Test minimum valid values
    config_min = GameConfig(round_duration_minutes=1, num_rounds=1)
    valid, error = config_min.validate()
    assert valid is True
    assert error is None

    # Test maximum valid values
    config_max = GameConfig(round_duration_minutes=30, num_rounds=20)
    valid, error = config_max.validate()
    assert valid is True
    assert error is None


# Integration tests for GameState.update_config (Story 3.1 AC2)
def test_gamestate_config_update_in_lobby():
    """Test GameState.update_config() updates configuration in LOBBY phase."""
    from custom_components.spyster.game.state import GameState, GamePhase

    state = GameState()
    state.phase = GamePhase.LOBBY

    # Test round_duration_minutes update
    success, error = state.update_config("round_duration_minutes", 10)
    assert success is True
    assert error is None
    assert state.config.round_duration_minutes == 10

    # Test num_rounds update
    success, error = state.update_config("num_rounds", 3)
    assert success is True
    assert error is None
    assert state.config.num_rounds == 3

    # Test location_pack update
    success, error = state.update_config("location_pack", "classic")
    assert success is True
    assert error is None
    assert state.config.location_pack == "classic"


def test_gamestate_config_update_phase_guard():
    """Test GameState.update_config() rejects updates after game starts."""
    from custom_components.spyster.game.state import GameState, GamePhase
    from custom_components.spyster.const import ERR_CONFIG_GAME_STARTED

    state = GameState()
    state.phase = GamePhase.ROLES  # Game started

    success, error = state.update_config("round_duration_minutes", 10)
    assert success is False
    assert error == ERR_CONFIG_GAME_STARTED


def test_gamestate_config_update_invalid_value_reverts():
    """Test GameState.update_config() reverts to defaults on validation failure."""
    from custom_components.spyster.game.state import GameState, GamePhase
    from custom_components.spyster.const import ERR_CONFIG_INVALID_DURATION

    state = GameState()
    state.phase = GamePhase.LOBBY

    # Set valid value first
    state.update_config("round_duration_minutes", 10)
    assert state.config.round_duration_minutes == 10

    # Try invalid value - should revert to defaults
    success, error = state.update_config("round_duration_minutes", 999)
    assert success is False
    assert error == ERR_CONFIG_INVALID_DURATION
    # Config reverted to defaults
    assert state.config.round_duration_minutes == CONFIG_DEFAULT_ROUND_DURATION


def test_gamestate_config_in_lobby_state():
    """Test GameState.get_state() includes config in LOBBY phase."""
    from custom_components.spyster.game.state import GameState, GamePhase

    state = GameState()
    state.phase = GamePhase.LOBBY
    state.update_config("round_duration_minutes", 15)
    state.update_config("num_rounds", 7)

    game_state = state.get_state()

    assert "config" in game_state
    assert game_state["config"]["round_duration_minutes"] == 15
    assert game_state["config"]["num_rounds"] == 7
    assert game_state["config"]["location_pack"] == "classic"


def test_gamestate_config_unknown_field():
    """Test GameState.update_config() rejects unknown fields."""
    from custom_components.spyster.game.state import GameState, GamePhase
    from custom_components.spyster.const import ERR_INVALID_MESSAGE

    state = GameState()
    state.phase = GamePhase.LOBBY

    success, error = state.update_config("invalid_field", 123)
    assert success is False
    assert error == ERR_INVALID_MESSAGE
