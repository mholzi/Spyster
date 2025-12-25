"""Role assignment logic for Spyster game."""
from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState

_LOGGER = logging.getLogger(__name__)


def assign_spy(game_state: GameState) -> str:
    """Assign exactly one player as the spy using CSPRNG.

    Args:
        game_state: Current game state with active players

    Returns:
        Name of the player selected as spy

    Raises:
        ValueError: If no connected players available or insufficient players
    """
    from ..const import MIN_PLAYERS

    connected_players = [
        name for name, player in game_state.players.items()
        if player.connected
    ]

    if not connected_players:
        raise ValueError("Cannot assign spy: no connected players")

    if len(connected_players) < MIN_PLAYERS:
        raise ValueError(f"Cannot assign spy: need {MIN_PLAYERS}+ players, have {len(connected_players)}")

    # CRITICAL: Use secrets.choice() for cryptographic randomness (NFR6, ARCH-6)
    spy_name = secrets.choice(connected_players)

    _LOGGER.info(
        "Spy assigned for round %d: player count %d",
        game_state.current_round,
        len(connected_players)
    )
    # SECURITY: Never log spy identity to avoid data leaks

    return spy_name


def get_player_role_data(
    game_state: GameState,
    player_name: str
) -> dict:
    """Get role information for a specific player (filtered).

    SECURITY-CRITICAL: Implements per-player filtering per ARCH-7, ARCH-8.
    This function ensures spy NEVER sees actual location and non-spy NEVER sees location list.

    Args:
        game_state: Current game state
        player_name: Name of player requesting role data

    Returns:
        Role data dict appropriate for this player (Story 3.5 spec compliance):
        - Spy: {"is_spy": True, "possible_locations": ["Beach", "Hospital", ...]}
        - Non-spy: {"is_spy": False, "location": "Beach", "role": "Lifeguard",
                    "hint": "...", "other_roles": [...]}

    Security Guarantees (ARCH-7, ARCH-8):
        - Spy payload has NO "location" or "role" keys
        - Non-spy payload has NO "possible_locations" key
        - Field names MUST match Story 3.5 spec for frontend compatibility
    """
    if not game_state.current_location:
        raise ValueError("No location assigned for current round")

    is_spy = (player_name == game_state.spy_name)

    if is_spy:
        # Spy sees ALL possible locations (not the actual one)
        from .content import get_location_list

        location_list = get_location_list(game_state.location_pack)

        # SECURITY: ONLY is_spy and possible_locations - NO location, NO role
        # Story 3.5 AC2: Field name MUST be "possible_locations" per spec line 346
        return {
            "is_spy": True,
            "possible_locations": location_list,
        }
    else:
        # Non-spy sees actual location and their assigned role
        role = game_state.player_roles.get(player_name)

        if not role:
            _LOGGER.warning("Player %s has no role assigned", player_name)
            role = {"name": "Visitor", "hint": "You're just passing through"}

        # Story 3.5 AC1: Non-spy MUST have location, role, hint, and other_roles
        # Field names MUST match spec lines 316-321
        return {
            "is_spy": False,
            "location": game_state.current_location["name"],
            "role": role["name"],
            "hint": role.get("hint", ""),  # AC1: Required field
            "other_roles": [
                r["name"] for r in game_state.current_location["roles"]
                if r["name"] != role["name"]
            ]  # AC1: Other roles at this location
        }


def assign_roles(game_state: GameState) -> None:
    """Assign spy and distribute roles to all players.

    Updates game_state with:
    - spy_name (private)
    - current_location (from selected pack)
    - player_roles dict (role assigned to each non-spy)

    Raises:
        ValueError: If prerequisites not met (location not selected, etc.)
    """
    from .content import get_random_location

    # Select location for this round
    game_state.current_location = get_random_location(game_state.location_pack)

    if not game_state.current_location:
        raise ValueError(f"Failed to load location from pack: {game_state.location_pack}")

    _LOGGER.info(
        "Location selected for round %d: %s (%d roles available)",
        game_state.current_round,
        game_state.current_location["name"],
        len(game_state.current_location["roles"])
    )

    # Assign spy using CSPRNG
    game_state.spy_name = assign_spy(game_state)

    # Assign roles to non-spy players
    connected_players = [
        name for name, player in game_state.players.items()
        if player.connected and name != game_state.spy_name
    ]

    available_roles = list(game_state.current_location["roles"])

    # Validate that location has roles
    if not available_roles:
        raise ValueError(f"Location '{game_state.current_location['name']}' has no roles defined")

    game_state.player_roles = {}

    for player_name in connected_players:
        # Assign random role (with repetition if more players than roles)
        role = secrets.choice(available_roles)
        game_state.player_roles[player_name] = role

    _LOGGER.info(
        "Roles assigned: %d non-spy players",
        len(connected_players)
    )
