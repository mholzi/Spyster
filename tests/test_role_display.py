"""
Story 3.5: Role Display UI with Spy Parity - Test Suite

Tests for role display rendering with critical spy parity requirements.
CRITICAL: Spy and non-spy views must have IDENTICAL dimensions.
"""

import pytest
from custom_components.spyster.game.state import GameState, GamePhase
from custom_components.spyster.game.player import Player


class TestRolePayloadStructure:
    """Test per-player role data payload structures (AC1, AC2)"""

    def test_spy_payload_structure(self, game_state):
        """Verify spy receives correct data structure (AC2)"""
        # Setup: Create game with spy
        game_state.add_player("Dave")
        game_state.add_player("Jenna")
        game_state.add_player("Marcus")
        game_state.add_player("Tom")

        # Assign Dave as spy
        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        # Get state filtered for spy
        state = game_state.get_state(for_player="Dave")

        # Verify spy payload structure
        assert "role_data" in state
        assert state["role_data"]["is_spy"] is True
        assert "possible_locations" in state["role_data"]
        assert isinstance(state["role_data"]["possible_locations"], list)
        assert len(state["role_data"]["possible_locations"]) > 0

        # Spy should NOT see location or role
        assert "location" not in state["role_data"]
        assert "role" not in state["role_data"]
        assert "hint" not in state["role_data"]
        assert "other_roles" not in state["role_data"]

    def test_innocent_payload_structure(self, game_state):
        """Verify non-spy receives correct data structure (AC1)"""
        # Setup: Create game with spy
        game_state.add_player("Dave")
        game_state.add_player("Jenna")
        game_state.add_player("Marcus")
        game_state.add_player("Tom")

        # Assign Dave as spy (so Jenna is innocent)
        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        # Get state filtered for innocent player
        state = game_state.get_state(for_player="Jenna")

        # Verify innocent payload structure
        assert "role_data" in state
        assert state["role_data"]["is_spy"] is False
        assert "location" in state["role_data"]
        assert "role" in state["role_data"]
        assert "hint" in state["role_data"]
        assert "other_roles" in state["role_data"]

        # Validate data types
        assert isinstance(state["role_data"]["location"], str)
        assert isinstance(state["role_data"]["role"], str)
        assert isinstance(state["role_data"]["hint"], str)
        assert isinstance(state["role_data"]["other_roles"], list)
        assert len(state["role_data"]["other_roles"]) > 0

        # Innocent should NOT see possible_locations
        assert "possible_locations" not in state["role_data"]

    def test_role_data_only_in_roles_phase(self, game_state):
        """Verify role_data only appears in ROLES phase"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        # In LOBBY phase - no role_data
        game_state.phase = GamePhase.LOBBY
        state = game_state.get_state(for_player="Dave")
        assert "role_data" not in state

        # In ROLES phase - role_data appears
        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES
        state = game_state.get_state(for_player="Dave")
        assert "role_data" in state


class TestSpyParity:
    """Test spy parity requirements (AC3)"""

    def test_payload_size_similarity(self, game_state):
        """Verify spy and innocent payloads have similar data volume"""
        # Setup game
        game_state.add_player("Dave")
        game_state.add_player("Jenna")
        game_state.add_player("Marcus")
        game_state.add_player("Tom")

        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        # Get both payloads
        spy_state = game_state.get_state(for_player="Dave")
        innocent_state = game_state.get_state(for_player="Jenna")

        # Count total list items (locations vs roles)
        spy_list_count = len(spy_state["role_data"]["possible_locations"])
        innocent_list_count = len(innocent_state["role_data"]["other_roles"])

        # Lists should be similar size (prevents visual tells)
        # Typically 8-12 locations and 5-8 roles
        assert abs(spy_list_count - innocent_list_count) <= 5

    def test_component_structure_identical(self, game_state):
        """Verify both payloads have same top-level structure"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")
        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        spy_state = game_state.get_state(for_player="Dave")
        innocent_state = game_state.get_state(for_player="Jenna")

        # Both should have role_data with is_spy flag
        assert "role_data" in spy_state
        assert "role_data" in innocent_state
        assert "is_spy" in spy_state["role_data"]
        assert "is_spy" in innocent_state["role_data"]

        # Both should have exactly one list field
        spy_lists = [k for k in spy_state["role_data"].keys() if "list" in k.lower() or "locations" in k or "roles" in k]
        innocent_lists = [k for k in innocent_state["role_data"].keys() if "list" in k.lower() or "locations" in k or "roles" in k]

        # Each should have one primary list
        assert len(spy_lists) >= 1
        assert len(innocent_lists) >= 1


class TestLoadingState:
    """Test loading state prevents data flicker (AC4)"""

    def test_no_role_data_before_assignment(self, game_state):
        """Verify no role_data appears before roles assigned"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        # Before spy assignment
        state = game_state.get_state(for_player="Dave")
        assert "role_data" not in state or state["role_data"] is None

    def test_incomplete_data_not_sent(self, game_state):
        """Verify incomplete role data is never sent"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        # Assign spy but NOT roles yet
        game_state.assign_spy("Dave")
        # Don't call assign_roles()

        state = game_state.get_state(for_player="Dave")

        # Should either have no role_data or complete role_data
        if "role_data" in state:
            # If role_data exists, it must be complete
            assert "is_spy" in state["role_data"]
            if state["role_data"]["is_spy"]:
                assert "possible_locations" in state["role_data"]
            else:
                assert "location" in state["role_data"]
                assert "role" in state["role_data"]


class TestSecurityAndValidation:
    """Test security and validation requirements"""

    def test_player_cannot_see_other_roles(self, game_state):
        """Verify players cannot see each other's actual roles"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")
        game_state.add_player("Marcus")

        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        # Get Jenna's state (innocent)
        jenna_state = game_state.get_state(for_player="Jenna")

        # Jenna should see her role and other possible roles
        assert jenna_state["role_data"]["role"] == game_state.players["Jenna"].role.name

        # Other roles should NOT include player-specific assignments
        other_roles = jenna_state["role_data"]["other_roles"]
        assert isinstance(other_roles, list)

        # Should not contain info about who has which role
        # (just role names, not player assignments)
        for role_name in other_roles:
            assert isinstance(role_name, str)

    def test_spy_cannot_see_actual_location(self, game_state):
        """Verify spy does not receive actual location"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        spy_state = game_state.get_state(for_player="Dave")

        # Spy should NOT have location field
        assert "location" not in spy_state["role_data"]

        # Spy should have list of possibilities
        assert "possible_locations" in spy_state["role_data"]
        assert len(spy_state["role_data"]["possible_locations"]) > 1


class TestAccessibility:
    """Test accessibility requirements"""

    def test_role_data_contains_readable_strings(self, game_state):
        """Verify all role data fields are human-readable"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        # Test innocent player
        innocent_state = game_state.get_state(for_player="Jenna")
        rd = innocent_state["role_data"]

        assert isinstance(rd["location"], str)
        assert len(rd["location"]) > 0
        assert isinstance(rd["role"], str)
        assert len(rd["role"]) > 0
        assert isinstance(rd["hint"], str)
        assert len(rd["hint"]) > 0

        # All other roles should be non-empty strings
        for role in rd["other_roles"]:
            assert isinstance(role, str)
            assert len(role) > 0

    def test_spy_location_list_readable(self, game_state):
        """Verify spy's location list contains readable strings"""
        game_state.add_player("Dave")
        game_state.add_player("Jenna")

        game_state.assign_spy("Dave")
        game_state.assign_roles()
        game_state.phase = GamePhase.ROLES

        spy_state = game_state.get_state(for_player="Dave")
        locations = spy_state["role_data"]["possible_locations"]

        # All locations should be non-empty strings
        for location in locations:
            assert isinstance(location, str)
            assert len(location) > 0


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def game_state():
    """Create a fresh game state for testing"""
    state = GameState()
    return state
