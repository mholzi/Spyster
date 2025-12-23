"""Game state management for Spyster."""
import asyncio
import logging
from enum import Enum
from typing import Any, Awaitable, Callable

from .config import GameConfig

_LOGGER = logging.getLogger(__name__)


class GamePhase(Enum):
    """Game phase enumeration.

    All phases must be defined here even though this story only uses LOBBY.
    Future stories will implement phase transitions.
    """
    LOBBY = "LOBBY"
    ROLES = "ROLES"
    QUESTIONING = "QUESTIONING"
    VOTE = "VOTE"
    REVEAL = "REVEAL"
    SCORING = "SCORING"
    END = "END"
    PAUSED = "PAUSED"


class GameState:
    """Manages game state and phase transitions.

    Timer Types Used Across Game:
    - 'round': Configurable round timer (default 7min) - triggers QUESTIONING → VOTE
    - 'vote': 60s voting timer - triggers VOTE → REVEAL
    - 'role_display': 5s role reveal - triggers ROLES → QUESTIONING
    - 'reveal_delay': 3s dramatic pause - triggers REVEAL → SCORING
    - 'disconnect_grace:{player}': 30s grace period per player
    - 'reconnect_window:{player}': 5min reconnection window per player
    """

    def __init__(self) -> None:
        """Initialize game state.

        Story 1.1 provides: phase, _timers, players
        Story 1.2 adds: session metadata and game configuration
        Story 2.3 adds: sessions dictionary for token-based lookup
        """
        # Story 1.1 fields (already implemented)
        self.phase: GamePhase = GamePhase.LOBBY
        self._timers: dict[str, asyncio.Task] = {}
        self.players: dict[str, Any] = {}  # PlayerSession objects (populated in Story 2.3)

        # Story 4.2: Timer tracking for accurate remaining time calculation
        self._timer_start_times: dict[str, float] = {}  # timer_name -> start timestamp
        self._timer_durations: dict[str, float] = {}  # timer_name -> duration in seconds

        # Story 2.3 additions
        self.sessions: dict[str, Any] = {}  # token -> PlayerSession mapping

        # Story 1.2 additions
        self.previous_phase: GamePhase | None = None  # For PAUSED resume

        # Session metadata (populated by create_session())
        self.session_id: str | None = None
        self.created_at: float | None = None
        self.host_id: str | None = None

        # Game configuration (defaults from const.py)
        from ..const import DEFAULT_ROUND_DURATION, DEFAULT_ROUND_COUNT, DEFAULT_VOTE_DURATION
        self.round_duration: int = DEFAULT_ROUND_DURATION
        self.round_count: int = DEFAULT_ROUND_COUNT

        # Story 4.5: Vote caller attribution (AC6)
        self.vote_caller: str | None = None
        self.vote_duration: int = DEFAULT_VOTE_DURATION

        # Story 5.3: Vote tracking
        self.votes: dict[str, dict] = {}  # {player_name: {target, confidence, timestamp}}

        # Story 5.4: Spy action tracking
        self.spy_guess: dict | None = None  # {location_id, correct, timestamp}
        self.spy_action_taken: bool = False  # True if spy voted or guessed

        # Story 5.6: Reveal tracking
        self.convicted_player: str | None = None  # Most voted player
        self.vote_results: dict = {}  # Aggregated vote results

        # Story 5.7: Round resolution
        self.round_scores: dict[str, dict] = {}  # Per-player scores for round
        self.spy_caught: bool = False  # Whether spy was convicted

        # Story 3.1: Add GameConfig instance (location_pack stored in config.location_pack)
        self.config = GameConfig()

        # Game state
        self.current_round: int = 0
        self.player_count: int = 0
        self._game_started: bool = False  # Story 3.2: Track if game has started

        # Role assignment fields (Story 3.3 - PRIVATE - never in broadcasts)
        self._spy_name: str | None = None
        self._current_location: dict | None = None
        self._player_roles: dict[str, dict] = {}  # {player_name: role_dict}

        # Turn management fields (Story 4.3)
        self.current_questioner_id: str | None = None
        self.current_answerer_id: str | None = None
        self._turn_order: list[str] = []  # Player IDs in turn order

        _LOGGER.info("GameState initialized: phase=%s", self.phase.value)

    def __del__(self) -> None:
        """Clean up resources when GameState is destroyed."""
        try:
            self.cancel_all_timers()
        except Exception as err:
            _LOGGER.debug("Error cleaning up GameState: %s", err)

    # Story 3.3: Properties for role assignment fields
    @property
    def spy_name(self) -> str | None:
        """Get spy name (read-only access)."""
        return self._spy_name

    @spy_name.setter
    def spy_name(self, value: str) -> None:
        """Set spy name (internal use only)."""
        self._spy_name = value

    @property
    def current_location(self) -> dict | None:
        """Get current location data."""
        return self._current_location

    @current_location.setter
    def current_location(self, value: dict) -> None:
        """Set current location."""
        self._current_location = value

    @property
    def player_roles(self) -> dict[str, dict]:
        """Get player roles dict."""
        return self._player_roles

    @player_roles.setter
    def player_roles(self, value: dict[str, dict]) -> None:
        """Set player roles."""
        self._player_roles = value

    @property
    def location_pack(self) -> str:
        """Get location pack ID from config."""
        return self.config.location_pack

    def start_timer(
        self, name: str, duration: float, callback: Callable[[str], Awaitable[None]]
    ) -> None:
        """Start a named timer, cancelling any existing timer with same name.

        Args:
            name: Timer identifier (e.g., 'round', 'vote', 'disconnect_grace:Alice')
            duration: Timer duration in seconds
            callback: Async function to call when timer expires
        """
        import time

        self.cancel_timer(name)

        # Story 4.2: Track start time and duration for accurate remaining time calculation
        self._timer_start_times[name] = time.time()
        self._timer_durations[name] = duration

        self._timers[name] = asyncio.create_task(
            self._timer_task(name, duration, callback)
        )
        _LOGGER.debug("Timer started: %s (duration: %.1fs)", name, duration)

    def cancel_timer(self, name: str) -> None:
        """Cancel a specific timer by name."""
        timer = self._timers.get(name)
        if timer and not timer.done():
            timer.cancel()
            del self._timers[name]
            # Story 4.2: Clean up tracking dictionaries
            self._timer_start_times.pop(name, None)
            self._timer_durations.pop(name, None)
            _LOGGER.debug("Timer cancelled: %s", name)

    def cancel_all_timers(self) -> None:
        """Cancel all active timers (game end cleanup)."""
        for name, task in list(self._timers.items()):
            if not task.done():
                task.cancel()
        self._timers.clear()
        # Story 4.2: Clean up tracking dictionaries
        self._timer_start_times.clear()
        self._timer_durations.clear()
        _LOGGER.debug("All timers cancelled")

    async def _timer_task(
        self, name: str, duration: float, callback: Callable[[str], Awaitable[None]]
    ) -> None:
        """Internal timer task coroutine."""
        try:
            await asyncio.sleep(duration)
            _LOGGER.info("Timer expired: %s", name)
            try:
                await callback(name)
            except Exception as err:
                _LOGGER.error("Timer callback failed for '%s': %s", name, err, exc_info=True)
        except asyncio.CancelledError:
            _LOGGER.debug("Timer task cancelled: %s", name)
            raise

    def create_session(self, host_id: str) -> str:
        """Create a new game session.

        Args:
            host_id: Identifier for the host player

        Returns:
            session_id: Unique session identifier
        """
        import secrets
        import time

        self.session_id = secrets.token_urlsafe(16)
        self.created_at = time.time()
        self.host_id = host_id
        self.phase = GamePhase.LOBBY

        _LOGGER.info(
            "Game session created: session_id=%s, host=%s, created_at=%.2f, phase=%s",
            self.session_id,
            host_id,
            self.created_at,
            self.phase.value
        )

        return self.session_id

    def initialize_turn_order(self) -> None:
        """Initialize turn order when entering QUESTIONING phase (Story 4.3).

        Creates a shuffled list of connected player IDs and sets initial
        questioner and answerer. Uses CSPRNG for unpredictable shuffle.
        """
        import secrets

        # Get connected player names (we use names as IDs)
        connected_players = [
            player_name for player_name, player in self.players.items()
            if player.connected
        ]

        # Shuffle using CSPRNG for cryptographically secure randomization (ARCH-15)
        secrets.SystemRandom().shuffle(connected_players)

        self._turn_order = connected_players
        _LOGGER.info("Turn order initialized with %d players", len(self._turn_order))

        # Set initial questioner and answerer
        if len(self._turn_order) >= 2:
            self.current_questioner_id = self._turn_order[0]
            self.current_answerer_id = self._turn_order[1]
            _LOGGER.info(
                "Initial turn: %s asks %s",
                self.players[self.current_questioner_id].name,
                self.players[self.current_answerer_id].name
            )

    def advance_turn(self) -> None:
        """Advance to next questioner/answerer pair (Story 4.3).

        MVP Implementation:
        - Sequential rotation through turn order
        - Questioner becomes answerer
        - Next player becomes new questioner
        - Skips disconnected players
        """
        if not self._turn_order or len(self._turn_order) < 2:
            _LOGGER.warning("Cannot advance turn - insufficient players")
            return

        # Find current questioner index
        if self.current_questioner_id not in self._turn_order:
            # Current questioner disconnected, restart from beginning
            _LOGGER.warning("Current questioner not in turn order, restarting")
            self.initialize_turn_order()
            return

        current_idx = self._turn_order.index(self.current_questioner_id)

        # Answerer becomes next questioner
        next_questioner_idx = (current_idx + 1) % len(self._turn_order)
        next_answerer_idx = (current_idx + 2) % len(self._turn_order)

        self.current_questioner_id = self._turn_order[next_questioner_idx]
        self.current_answerer_id = self._turn_order[next_answerer_idx]

        _LOGGER.info(
            "Turn advanced: %s asks %s",
            self.players[self.current_questioner_id].name,
            self.players[self.current_answerer_id].name
        )

    def get_current_turn_info(self) -> dict:
        """Get current turn information for state broadcast (Story 4.3).

        Returns:
            dict with questioner and answerer details, or empty if not applicable
        """
        if self.phase != GamePhase.QUESTIONING:
            return {}

        if not self.current_questioner_id or not self.current_answerer_id:
            return {}

        questioner = self.players.get(self.current_questioner_id)
        answerer = self.players.get(self.current_answerer_id)

        if not questioner or not answerer:
            _LOGGER.warning("Turn info requested but player(s) not found")
            return {}

        return {
            "questioner": {
                "id": self.current_questioner_id,
                "name": questioner.name
            },
            "answerer": {
                "id": self.current_answerer_id,
                "name": answerer.name
            }
        }


    def can_transition(self, to_phase: GamePhase) -> tuple[bool, str | None]:
        """Validate if phase transition is allowed.

        Args:
            to_phase: Target phase to transition to

        Returns:
            (True, None) if valid
            (False, ERR_INVALID_PHASE) if blocked

        Raises:
            TypeError: If to_phase is not a GamePhase enum member
        """
        from ..const import VALID_TRANSITIONS, ERR_INVALID_PHASE

        # Validate that to_phase is a GamePhase enum member
        if not isinstance(to_phase, GamePhase):
            raise TypeError(f"to_phase must be a GamePhase enum, got {type(to_phase)}")

        # VALID_TRANSITIONS uses string keys to avoid circular import
        valid_next_strs = VALID_TRANSITIONS.get(self.phase.value, [])
        if to_phase.value not in valid_next_strs:
            _LOGGER.warning(
                "Invalid phase transition blocked: %s → %s",
                self.phase.value,
                to_phase.value
            )
            return False, ERR_INVALID_PHASE
        return True, None

    def transition_to(self, new_phase: GamePhase) -> tuple[bool, str | None]:
        """Transition to a new phase with validation.

        Args:
            new_phase: Target phase

        Returns:
            (success, error_code): True if successful, False with error code if blocked
        """
        # Validate transition
        can_transition, error = self.can_transition(new_phase)
        if not can_transition:
            return False, error

        # Handle PAUSED special case
        if new_phase == GamePhase.PAUSED:
            self.previous_phase = self.phase
            _LOGGER.info("Game paused: previous_phase=%s", self.previous_phase.value)
        elif self.phase == GamePhase.PAUSED and self.previous_phase:
            # Resuming from pause - log the transition
            _LOGGER.info(
                "Resuming from pause: %s → %s (previous was: %s)",
                self.phase.value,
                new_phase.value,
                self.previous_phase.value
            )
            # Clear previous_phase when resuming
            self.previous_phase = None

        old_phase = self.phase
        self.phase = new_phase

        _LOGGER.info(
            "Phase transition: %s → %s (players: %d)",
            old_phase.value,
            new_phase.value,
            self.player_count
        )

        return True, None

    def get_join_url(self, base_url: str) -> str:
        """Get player join URL for this game session.

        Args:
            base_url: Home Assistant base URL (from hass.config.api.base_url)

        Returns:
            Full URL for players to join this game session

        Raises:
            ValueError: If session_id is not set (session not created yet)

        Note:
            Requires self.session_id to be set during game initialization (Story 1.1)
        """
        if not self.session_id:
            raise ValueError("Session ID not set - call create_session() first")

        return f"{base_url}/api/spyster/player?session={self.session_id}"

    def update_config(self, field: str, value: int | str) -> tuple[bool, str | None]:
        """
        Update a configuration field (Story 3.1).

        Args:
            field: Configuration field name
            value: New value

        Returns:
            (success, error_code)
        """
        from ..const import ERR_CONFIG_GAME_STARTED, ERR_INVALID_MESSAGE

        # Phase guard - can only configure in LOBBY
        if self.phase != GamePhase.LOBBY:
            _LOGGER.warning("Cannot update config: game already started (phase: %s)", self.phase)
            return False, ERR_CONFIG_GAME_STARTED

        # Update field
        if field == "round_duration_minutes":
            self.config.round_duration_minutes = int(value)
        elif field == "num_rounds":
            self.config.num_rounds = int(value)
        elif field == "location_pack":
            self.config.location_pack = str(value)
        else:
            _LOGGER.warning("Unknown config field: %s", field)
            return False, ERR_INVALID_MESSAGE

        # Validate new configuration
        valid, error = self.config.validate()
        if not valid:
            # Revert to defaults if invalid
            self.config = GameConfig()
            _LOGGER.warning("Config validation failed: %s", error)
            return False, error

        _LOGGER.info("Configuration updated: %s = %s", field, value)
        return True, None

    def get_state(self, for_player: str | None = None) -> dict[str, Any]:
        """Get game state, filtered for specific player if provided (Story 3.4).

        Args:
            for_player: Player name to filter state for (None = host/public view)

        Returns:
            dict[str, Any]: Game state with appropriate filtering applied

        Security:
            - Public data: phase, player_count, scores, timer
            - Private data: role, location (only for requesting player)
            - Spy sees: location_list (not actual location)
            - Non-spy sees: location + their role
        """
        from ..const import MIN_PLAYERS, MAX_PLAYERS

        # Public state (visible to all)
        state: dict[str, Any] = {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "player_count": self.player_count,
            "current_round": self.current_round,
            "round_count": self.round_count,
            "created_at": self.created_at,
        }

        # Story 4.2: Timer state with detailed info (if active)
        if "round" in self._timers and not self._timers["round"].done():
            state["timer"] = {
                "name": "round",
                "remaining": self._get_timer_remaining("round"),
                "total": self._timer_durations.get("round", 0),
            }
        elif "vote" in self._timers and not self._timers["vote"].done():
            state["timer"] = {
                "name": "vote",
                "remaining": self._get_timer_remaining("vote"),
                "total": self._timer_durations.get("vote", 0),
            }

        # Phase-specific state
        if self.phase == GamePhase.LOBBY:
            state["waiting_for_players"] = True
            state["min_players"] = MIN_PLAYERS
            state["max_players"] = MAX_PLAYERS
            state["connected_count"] = self.get_connected_player_count()  # Story 3.2
            state["can_start"] = self.can_start_game()  # Story 3.2
            # Story 3.1: Include configuration in lobby state
            state["config"] = self.config.to_dict()
            # Story 2.4 & 2.6: Include player list with connection status
            state["players"] = [
                {
                    "name": p.name,
                    "connected": p.connected,
                    "is_host": p.is_host,
                    "disconnect_duration": p.get_disconnect_duration()
                }
                for p in self.players.values()
            ]

        elif self.phase == GamePhase.ROLES:
            # Story 3.3 & 3.4: Role phase - send personalized role info
            if for_player:
                # SECURITY FIX: Validate player exists before getting role data
                if for_player not in self.players:
                    _LOGGER.warning("get_state called for non-existent player: %s", for_player)
                else:
                    try:
                        from .roles import get_player_role_data
                        role_data = get_player_role_data(self, for_player)
                        # CRITICAL: Field name MUST be "role_data" per Story 3.5 spec
                        # Frontend player.js expects state.role_data (lines 304, 313, 314)
                        state["role_data"] = role_data
                    except ValueError as err:
                        _LOGGER.warning("Failed to get role data for %s: %s", for_player, err)

        elif self.phase == GamePhase.QUESTIONING:
            # Story 4.4: Include role info for quick reference
            if for_player:
                player = self.players.get(for_player)
                if not player:
                    _LOGGER.warning("get_state called for non-existent player: %s", for_player)
                else:
                    # Use get_player_role_data() for consistent filtering
                    try:
                        from .roles import get_player_role_data
                        role_data = get_player_role_data(self, for_player)
                        # Story 4.4: Wrap in role_data key for consistency with ROLES phase
                        state["role_data"] = role_data
                    except ValueError as err:
                        _LOGGER.warning("Failed to get role data for %s: %s", for_player, err)

            # Story 4.3: Add turn info
            turn_info = self.get_current_turn_info()
            if turn_info:
                state["current_turn"] = turn_info

        elif self.phase == GamePhase.VOTE:
            # Similar filtering for vote phase
            if for_player:
                player = self.players.get(for_player)
                if not player:
                    _LOGGER.warning("get_state called for non-existent player: %s", for_player)
                else:
                    # FIX: Use get_player_role_data() for consistent filtering
                    try:
                        from .roles import get_player_role_data
                        role_data = get_player_role_data(self, for_player)
                        # Merge role data into state (no "role_info" wrapper in VOTE phase)
                        state.update(role_data)
                    except ValueError as err:
                        _LOGGER.warning("Failed to get role data for %s: %s", for_player, err)

            # Story 5.1: Include player list for vote UI (excluding role data)
            state["players"] = [
                {
                    "name": p.name,
                    "connected": p.connected,
                }
                for p in self.players.values()
            ]

            state["votes_submitted"] = len(getattr(self, "votes", {}))
            state["total_voters"] = len(self.players)
            # Story 4.5: AC6 - Include vote caller for attribution
            state["vote_caller"] = self.vote_caller

            # Story 5.3: Include if current player has voted (for UI state)
            if for_player:
                state["has_voted"] = for_player in self.votes

            # Story 5.4: Include spy-specific data
            if for_player and for_player == self._spy_name:
                state["is_spy"] = True
                state["can_guess_location"] = not self.spy_action_taken
                state["location_list"] = [
                    {"id": loc.get("id"), "name": loc.get("name")}
                    for loc in self._get_location_list()
                ]
            elif for_player:
                state["is_spy"] = False

            # Track if spy has guessed (for reveal logic)
            state["spy_has_guessed"] = self.spy_guess is not None

        elif self.phase == GamePhase.REVEAL:
            # Story 5.6: REVEAL phase - all votes visible (FR37)
            # Include all votes with full data
            state["votes"] = [
                {
                    "voter": voter_name,
                    "target": vote_data.get("target"),
                    "confidence": vote_data.get("confidence", 0),
                    "abstained": vote_data.get("abstained", False),
                }
                for voter_name, vote_data in self.votes.items()
            ]

            # Vote results summary
            if not self.vote_results:
                self.calculate_vote_results()
            state["vote_results"] = self.vote_results
            state["convicted"] = self.convicted_player

            # Actual spy identity (revealed after voting)
            state["actual_spy"] = self._spy_name

            # Location reveal
            state["location"] = {
                "id": self._current_location.get("id") if self._current_location else None,
                "name": self._current_location.get("name") if self._current_location else "Unknown",
            }

            # Spy guess result (if applicable) - Story 5.4/5.6
            if self.spy_guess:
                state["spy_guess"] = {
                    "guessed": True,
                    "location_id": self.spy_guess.get("location_id"),
                    "correct": self.spy_guess.get("correct"),
                }
            else:
                state["spy_guess"] = {"guessed": False}

            # Story 5.7: Conviction result
            state["spy_caught"] = self.spy_caught
            state["round_scores"] = self.round_scores

        elif self.phase == GamePhase.SCORING:
            # Story 5.7 & 6.5: Scoring phase state with leaderboard
            state["spy_caught"] = self.spy_caught
            state["convicted"] = self.convicted_player
            state["actual_spy"] = self._spy_name
            state["round_scores"] = self.round_scores

            # Current scores
            state["scores"] = {p.name: p.score for p in self.players.values()}

            # Story 6.5: Standings with round changes (sorted by score)
            standings = []
            for p in sorted(
                self.players.values(),
                key=lambda x: x.score,
                reverse=True
            ):
                round_score = self.round_scores.get(p.name, {})
                standings.append({
                    "name": p.name,
                    "score": p.score,
                    "round_change": round_score.get("points", 0),
                    "is_self": p.name == for_player,
                })
            state["standings"] = standings

            # Story 6.5: Round info
            state["round_number"] = self.current_round
            state["total_rounds"] = self.config.num_rounds

            # Story 6.5: Scoring timer
            if "scoring" in self._timers and not self._timers["scoring"].done():
                state["scoring_timer"] = self._get_timer_remaining("scoring")

        elif self.phase == GamePhase.END:
            # Story 6.7: End game state with winner and final standings
            state["round_number"] = self.current_round
            state["total_rounds"] = self.config.num_rounds

            # Determine winner
            winner_info = self._determine_winner()
            state["winner"] = winner_info

            # Final standings with is_self for highlighting
            standings = []
            for p in sorted(
                self.players.values(),
                key=lambda x: x.score,
                reverse=True
            ):
                standings.append({
                    "name": p.name,
                    "score": p.score,
                    "is_self": p.name == for_player,
                })
            state["standings"] = standings
            state["final_standings"] = standings

            # Game statistics
            state["game_stats"] = self._get_game_stats()

        return state

    def _determine_winner(self) -> dict:
        """
        Determine the winner(s) of the game (Story 6.7).

        Returns dict with:
            - name: Winner name (or None if tie)
            - score: Winning score
            - is_tie: True if multiple players tied
            - tied_players: List of tied player names (if tie)
        """
        if not self.players:
            return {"name": None, "score": 0, "is_tie": False}

        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.score,
            reverse=True
        )

        top_score = sorted_players[0].score
        winners = [p for p in sorted_players if p.score == top_score]

        if len(winners) == 1:
            return {
                "name": winners[0].name,
                "score": top_score,
                "is_tie": False,
                "tied_players": [],
            }
        else:
            return {
                "name": None,
                "score": top_score,
                "is_tie": True,
                "tied_players": [w.name for w in winners],
            }

    def _get_game_stats(self) -> dict:
        """
        Get game statistics for end screen (Story 6.7).

        Returns:
            Game statistics dictionary
        """
        stats = {
            "total_rounds": self.current_round,
        }

        # Count spies caught from round history
        if hasattr(self, 'round_history'):
            spies_caught = sum(1 for r in self.round_history if r.get("spy_caught"))
            stats["spies_caught"] = spies_caught

        return stats

    def _get_timer_remaining(self, timer_name: str) -> float:
        """Get remaining seconds for a named timer (Story 4.2).

        Uses start time and duration to calculate accurate remaining time,
        preventing drift from repeated updates (NFR5: ±1 second accuracy).

        Args:
            timer_name: Name of the timer

        Returns:
            Remaining seconds as float (0.0 if timer doesn't exist or is done)
        """
        import time

        if timer_name not in self._timers:
            return 0.0

        task = self._timers[timer_name]
        if task.done():
            return 0.0

        # Story 4.2: Calculate remaining time from start timestamp
        if timer_name not in self._timer_start_times:
            return 0.0

        elapsed = time.time() - self._timer_start_times[timer_name]
        duration = self._timer_durations.get(timer_name, 0.0)
        remaining = max(0.0, duration - elapsed)

        return remaining

    def record_vote(
        self,
        player_name: str,
        target: str,
        confidence: int
    ) -> tuple[bool, str | None]:
        """Record a player's vote (Story 5.3).

        Args:
            player_name: Name of player casting vote
            target: Name of player being voted for
            confidence: Confidence level (1, 2, or 3)

        Returns:
            (success: bool, error_code: str | None)
        """
        import time
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_ALREADY_VOTED,
            ERR_INVALID_TARGET,
            ERR_PLAYER_NOT_FOUND,
        )

        # Phase guard (ARCH-17)
        if self.phase != GamePhase.VOTE:
            _LOGGER.warning(
                "Cannot record vote - invalid phase: %s (player: %s)",
                self.phase,
                player_name
            )
            return False, ERR_INVALID_PHASE

        # Verify voter exists and is connected
        if player_name not in self.players:
            _LOGGER.warning("Vote from unknown player: %s", player_name)
            return False, ERR_PLAYER_NOT_FOUND

        voter = self.players[player_name]
        if not voter.connected:
            _LOGGER.warning("Vote from disconnected player: %s", player_name)
            return False, ERR_PLAYER_NOT_FOUND

        # Check for duplicate vote (AC3)
        if player_name in self.votes:
            _LOGGER.warning("Duplicate vote attempt: %s", player_name)
            return False, ERR_ALREADY_VOTED

        # Validate target exists and is not self
        if target not in self.players:
            _LOGGER.warning("Vote for invalid target: %s -> %s", player_name, target)
            return False, ERR_INVALID_TARGET

        if target == player_name:
            _LOGGER.warning("Player tried to vote for self: %s", player_name)
            return False, ERR_INVALID_TARGET

        # Validate confidence (1, 2, or 3)
        if confidence not in [1, 2, 3]:
            confidence = 1  # Default to 1 if invalid

        # Record vote (AC4)
        self.votes[player_name] = {
            "target": target,
            "confidence": confidence,
            "timestamp": time.time(),
        }

        _LOGGER.info(
            "Vote recorded: %s -> %s (confidence: %d, total: %d/%d)",
            player_name,
            target,
            confidence,
            len(self.votes),
            len([p for p in self.players.values() if p.connected])
        )

        # Check if all votes are in (AC5)
        if self._all_votes_submitted():
            _LOGGER.info("All votes submitted - ready for REVEAL transition")
            # Cancel vote timer
            self.cancel_timer("vote")

        return True, None

    def _all_votes_submitted(self) -> bool:
        """Check if all connected players have voted (Story 5.3)."""
        connected_players = [
            p.name for p in self.players.values() if p.connected
        ]
        return all(name in self.votes for name in connected_players)

    def get_vote_stats(self) -> dict:
        """Get vote submission statistics for tracker (Story 5.3)."""
        connected_count = len([p for p in self.players.values() if p.connected])
        voted_count = len(self.votes)
        return {
            "votes_submitted": voted_count,
            "total_voters": connected_count,
            "all_voted": voted_count >= connected_count,
        }

    def reset_votes(self) -> None:
        """Reset votes for new round (Story 5.3, 5.6, 5.7)."""
        self.votes = {}
        self.spy_guess = None
        self.spy_action_taken = False
        # Story 5.6: Reset reveal data
        self.convicted_player = None
        self.vote_results = {}
        # Story 5.7: Reset conviction data
        self.round_scores = {}
        self.spy_caught = False
        _LOGGER.debug("Votes, reveal, and conviction data reset")

    def record_spy_guess(
        self,
        player_name: str,
        location_id: str
    ) -> tuple[bool, str | None]:
        """Record spy's location guess (Story 5.4).

        Args:
            player_name: Name of player making guess (must be spy)
            location_id: ID of guessed location

        Returns:
            (success: bool, error_code: str | None)
        """
        import time
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_NOT_SPY,
            ERR_SPY_ALREADY_ACTED,
            ERR_INVALID_LOCATION,
        )

        # Phase guard (ARCH-17)
        if self.phase != GamePhase.VOTE:
            _LOGGER.warning(
                "Cannot record spy guess - invalid phase: %s",
                self.phase
            )
            return False, ERR_INVALID_PHASE

        # Verify player is the spy (AC4)
        if player_name != self._spy_name:
            _LOGGER.warning(
                "Non-spy tried to guess location: %s (spy is: %s)",
                player_name,
                self._spy_name
            )
            return False, ERR_NOT_SPY

        # Check if spy already acted (AC5)
        if self.spy_action_taken:
            _LOGGER.warning("Spy already acted: %s", player_name)
            return False, ERR_SPY_ALREADY_ACTED

        if player_name in self.votes:
            _LOGGER.warning("Spy already voted: %s", player_name)
            return False, ERR_SPY_ALREADY_ACTED

        # Validate location exists
        location_list = self._get_location_list()
        if location_id not in [loc.get("id") for loc in location_list]:
            _LOGGER.warning("Invalid location guess: %s", location_id)
            return False, ERR_INVALID_LOCATION

        # Check if guess is correct
        correct = (location_id == self._current_location.get("id"))

        # Record the guess
        self.spy_guess = {
            "location_id": location_id,
            "correct": correct,
            "timestamp": time.time(),
        }
        self.spy_action_taken = True

        _LOGGER.info(
            "Spy guess recorded: %s guessed '%s' (correct: %s)",
            player_name,
            location_id,
            correct
        )

        # Spy guess ends voting immediately - cancel timer
        self.cancel_timer("vote")

        return True, None

    def _get_location_list(self) -> list[dict]:
        """Get list of possible locations for spy (Story 5.4)."""
        try:
            from .content import get_location_pack
            pack = get_location_pack(self.config.location_pack)
            return pack.get("locations", [])
        except Exception as err:
            _LOGGER.warning("Failed to get location pack: %s", err)
            return []

    def calculate_vote_results(self) -> dict:
        """
        Calculate vote results for reveal (Story 5.6).

        Counts votes per target and determines convicted player.
        Ties are broken alphabetically (first alphabetically wins).

        Returns:
            dict with vote_counts, convicted, max_votes, total_votes, abstentions
        """
        # Count votes per target
        vote_counts: dict[str, int] = {}
        for voter_name, vote_data in self.votes.items():
            target = vote_data.get("target")
            if target:  # Ignore abstentions
                vote_counts[target] = vote_counts.get(target, 0) + 1

        # Find most voted (convicted) - ties go to first alphabetically
        convicted = None
        max_votes = 0
        for target, count in sorted(vote_counts.items()):
            if count > max_votes:
                max_votes = count
                convicted = target

        self.convicted_player = convicted
        self.vote_results = {
            "vote_counts": vote_counts,
            "convicted": convicted,
            "max_votes": max_votes,
            "total_votes": len([v for v in self.votes.values() if v.get("target")]),
            "abstentions": len([v for v in self.votes.values() if v.get("abstained")]),
        }

        _LOGGER.info(
            "Vote results calculated: convicted=%s (%d votes), %d abstentions",
            convicted,
            max_votes,
            self.vote_results["abstentions"]
        )

        return self.vote_results

    def process_conviction(self) -> tuple[bool, str | None]:
        """
        Process conviction and calculate scores (Story 5.7).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE
        from .scoring import calculate_round_scores

        # Phase guard
        if self.phase != GamePhase.REVEAL:
            return False, ERR_INVALID_PHASE

        # Calculate vote results if not done
        if not self.vote_results:
            self.calculate_vote_results()

        # Determine if spy was caught (AC2, AC3)
        self.spy_caught = self.convicted_player == self._spy_name

        if self.spy_caught:
            _LOGGER.info("Spy caught! %s was the spy.", self.convicted_player)
        elif self.convicted_player:
            _LOGGER.info("Innocent convicted! %s was NOT the spy.", self.convicted_player)
        else:
            _LOGGER.info("No conviction this round.")

        # Calculate scores
        self.round_scores = calculate_round_scores(self)

        # Apply scores to players
        for player_name, score_data in self.round_scores.items():
            if player_name in self.players:
                player = self.players[player_name]
                player.add_score(score_data["points"])
                _LOGGER.debug(
                    "Score applied: %s %+d (total: %d)",
                    player_name,
                    score_data["points"],
                    player.score
                )

        return True, None

    def transition_to_scoring(self) -> tuple[bool, str | None]:
        """
        Transition from REVEAL to SCORING phase (Story 5.7: AC6, Story 6.5).

        Processes conviction and calculates scores.
        Starts scoring display timer for auto-advance to next round.

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE, SCORING_DISPLAY_SECONDS

        if self.phase != GamePhase.REVEAL:
            return False, ERR_INVALID_PHASE

        # Process conviction and scores
        success, error = self.process_conviction()
        if not success:
            return False, error

        # Transition to SCORING
        self.phase = GamePhase.SCORING

        # Story 6.5: Start scoring display timer (for auto-advance)
        self.start_timer(
            "scoring",
            float(SCORING_DISPLAY_SECONDS),
            self._on_scoring_timer_expired
        )

        _LOGGER.info(
            "Transitioned to SCORING: spy_caught=%s, convicted=%s, timer=%ds",
            self.spy_caught,
            self.convicted_player,
            SCORING_DISPLAY_SECONDS
        )

        return True, None

    async def _on_scoring_timer_expired(self, timer_name: str) -> None:
        """
        Handle scoring display timer expiration (Story 6.5/6.6).

        Advances to next round or ends game.

        Args:
            timer_name: Name of the expired timer (ignored)
        """
        _LOGGER.info("Scoring display timer expired")

        # Story 6.6: Check if game should end
        if self.should_end_game():
            _LOGGER.info("Final round complete - transitioning to END")
            self.phase = GamePhase.END
        else:
            # Story 6.6: Start next round
            success, error = self.start_next_round()
            if not success:
                _LOGGER.error("Failed to start next round: %s", error)

    def should_end_game(self) -> bool:
        """Check if game should end after current round (Story 6.6)."""
        return self.current_round >= self.config.num_rounds

    def start_next_round(self) -> tuple[bool, str | None]:
        """
        Advance to next round (Story 6.6).

        Saves round history, resets state, assigns new spy/location,
        and transitions to ROLES phase.

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE, ERR_GAME_ENDED

        # Phase guard
        if self.phase != GamePhase.SCORING:
            return False, ERR_INVALID_PHASE

        # Check if game should end
        if self.current_round >= self.config.num_rounds:
            return False, ERR_GAME_ENDED

        # Save round history
        self._save_round_history()

        # Reset for new round
        self._reset_for_new_round()

        # Increment round counter
        self.current_round += 1

        # Assign new spy and location
        try:
            from .roles import assign_roles
            assign_roles(self)
        except ValueError as err:
            _LOGGER.error("Failed to assign roles for round %d: %s", self.current_round, err)
            # Continue anyway - shouldn't fail with existing players
            return False, "role_assignment_failed"

        # Transition to ROLES phase
        self.phase = GamePhase.ROLES

        _LOGGER.info(
            "Started round %d of %d",
            self.current_round,
            self.config.num_rounds
        )

        # Start role display timer
        self.start_timer(
            "role_display",
            5.0,
            self._on_role_display_complete
        )

        return True, None

    def _save_round_history(self) -> None:
        """Save current round data to history (Story 6.6)."""
        if not hasattr(self, 'round_history'):
            self.round_history: list[dict] = []

        self.round_history.append({
            "round": self.current_round,
            "spy": self._spy_name,
            "location": self._current_location.get("id") if self._current_location else None,
            "convicted": self.convicted_player,
            "spy_caught": self.spy_caught,
            "scores": dict(self.round_scores),
        })
        _LOGGER.debug("Round %d history saved", self.current_round)

    def _reset_for_new_round(self) -> None:
        """Reset state for new round (Story 6.6)."""
        # Clear votes
        self.votes = {}
        self.vote_results = {}
        self.convicted_player = None

        # Clear spy guess
        self.spy_guess = None
        self.spy_action_taken = False

        # Clear round scores (cumulative stays in player objects)
        self.round_scores = {}
        self.spy_caught = False

        # Reset vote caller
        self.vote_caller = None

        # Reset turn (will be re-initialized)
        self.current_questioner_id = None
        self.current_answerer_id = None
        self._turn_order = []

        # Clear timers (new timers will be started)
        self.cancel_all_timers()

        _LOGGER.debug("State reset for new round")

    def remove_player(self, player_name: str, requester_name: str | None = None) -> tuple[bool, str | None]:
        """Remove a disconnected player from the lobby (Story 2.6).

        Args:
            player_name: Name of player to remove
            requester_name: Name of player requesting removal (must be host)

        Returns:
            (success, error_code) - error_code is None on success

        Validation:
        - Phase must be LOBBY
        - Requester must be the host (if provided)
        - Player must exist
        - Player must not be the requester (cannot remove self)
        - Player must be disconnected for 60+ seconds
        """
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_PLAYER_NOT_FOUND,
            ERR_CANNOT_REMOVE_CONNECTED,
            ERR_NOT_HOST,
            MIN_DISCONNECT_DURATION_FOR_REMOVAL,
        )

        # Phase guard - only in LOBBY
        if self.phase != GamePhase.LOBBY:
            _LOGGER.warning("Cannot remove player: invalid phase %s", self.phase)
            return False, ERR_INVALID_PHASE

        # Host permission check - only host can remove players
        if requester_name is not None:
            if requester_name not in self.players:
                _LOGGER.warning("Cannot remove player: requester not found %s", requester_name)
                return False, ERR_PLAYER_NOT_FOUND

            requester = self.players[requester_name]
            if not requester.is_host:
                _LOGGER.warning(
                    "Cannot remove player: requester %s is not host",
                    requester_name
                )
                return False, ERR_NOT_HOST

            # Cannot remove self
            if requester_name == player_name:
                _LOGGER.warning(
                    "Cannot remove player: host cannot remove themselves %s",
                    requester_name
                )
                return False, ERR_CANNOT_REMOVE_CONNECTED

        # Check player exists
        if player_name not in self.players:
            _LOGGER.warning("Cannot remove player: not found %s", player_name)
            return False, ERR_PLAYER_NOT_FOUND

        player = self.players[player_name]

        # Check player is disconnected
        if player.connected:
            _LOGGER.warning("Cannot remove player: still connected %s", player_name)
            return False, ERR_CANNOT_REMOVE_CONNECTED

        # Check disconnect duration >= 60 seconds
        disconnect_duration = player.get_disconnect_duration()
        if disconnect_duration is None or disconnect_duration < MIN_DISCONNECT_DURATION_FOR_REMOVAL:
            _LOGGER.warning(
                "Cannot remove player: not disconnected long enough %s (duration: %.1fs)",
                player_name,
                disconnect_duration or 0
            )
            return False, ERR_CANNOT_REMOVE_CONNECTED

        # FIX: Race condition prevention - use atomic cancellation
        # Store reference to player before any async operations
        player_token = player.session_token

        # Cancel timers atomically - both must be cancelled before checking player existence
        grace_timer = f"disconnect_grace:{player_name}"
        reconnect_timer = f"reconnect_window:{player_name}"

        # Cancel both timers in quick succession to minimize race window
        self.cancel_timer(grace_timer)
        self.cancel_timer(reconnect_timer)

        # CRITICAL: Re-check player still exists after timer cancellation
        # This handles the edge case where reconnect_window fired during cancellation
        if player_name not in self.players:
            _LOGGER.info("Player already removed during timer cancellation: %s", player_name)
            return True, None  # Consider this a success - player is gone

        # Remove from sessions dict first (prevents token-based re-entry)
        self.sessions.pop(player_token, None)

        # Then remove from players dict
        del self.players[player_name]
        self.player_count = len(self.players)

        _LOGGER.info(
            "Player removed from lobby: %s (was disconnected for %.1fs, remaining: %d)",
            player_name,
            disconnect_duration,
            self.player_count
        )

        return True, None

    def add_player(
        self,
        name: str,
        is_host: bool = False,
        ws: Any = None
    ) -> tuple[bool, str | None, Any]:
        """Add a new player or replace existing session.

        Implements FR18: Duplicate session prevention by replacing old sessions.

        Args:
            name: Player name
            is_host: Whether this player is the host
            ws: WebSocket connection

        Returns:
            (success, error_code, player_session)
        """
        from .player import PlayerSession

        # Check for duplicate name (FR18)
        old_ws = None
        if name in self.players:
            # Replace old session
            old_session = self.players[name]
            _LOGGER.info(
                "Replacing session for %s (old token: %s)",
                name,
                old_session.session_token[:8]
            )
            # Clean up old session - save WebSocket for closing AFTER new player is stored
            del self.sessions[old_session.session_token]
            if old_session.ws and not old_session.ws.closed:
                old_ws = old_session.ws
                old_session.ws = None  # Prevent broadcast to old connection

        # Create new session
        session = PlayerSession.create_new(name, is_host)
        session.ws = ws

        # Store in both dictionaries BEFORE closing old WebSocket
        self.players[name] = session
        self.sessions[session.session_token] = session

        # Now close old WebSocket after new player is fully registered
        if old_ws:
            asyncio.create_task(
                old_ws.close(
                    code=4001,
                    message=b"Session replaced by new connection"
                )
            )
        self.player_count = len(self.players)

        _LOGGER.info(
            "Player added: %s (token: %s, total: %d)",
            name,
            session.session_token[:8],
            len(self.players)
        )

        return True, None, session

    def get_session_by_token(self, token: str) -> Any:
        """Retrieve player session by token.

        Args:
            token: Session token

        Returns:
            PlayerSession if found, None otherwise
        """
        return self.sessions.get(token)

    def restore_session(
        self,
        token: str,
        ws: Any
    ) -> tuple[bool, str | None, Any]:
        """Restore a player session using token.

        Args:
            token: Session token
            ws: WebSocket connection

        Returns:
            (success, error_code, player_session)
        """
        from ..const import ERR_INVALID_TOKEN, ERR_SESSION_EXPIRED

        session = self.get_session_by_token(token)

        if not session:
            return False, ERR_INVALID_TOKEN, None

        # Check if session is still valid (within reconnection window)
        if not session.is_session_valid():
            # Clean up expired session
            del self.sessions[token]
            if session.name in self.players:
                del self.players[session.name]
                self.player_count = len(self.players)
            return False, ERR_SESSION_EXPIRED, None

        # Cancel disconnect_grace timer if still running (Story 2.5)
        self.cancel_timer(f"disconnect_grace:{session.name}")

        # Reconnect session
        session.reconnect(ws)

        _LOGGER.info(
            "Session restored: %s (token: %s)",
            session.name,
            token[:8]
        )

        return True, None, session

    async def _on_player_disconnect(self, player_name: str) -> None:
        """Handle player disconnect after grace period expires (Story 2.4 & 2.5).

        Called by disconnect_grace timer (30 seconds after connection drop).
        Marks player as disconnected and starts 5-minute reconnection window timer.

        Args:
            player_name: Name of disconnected player
        """
        from ..const import RECONNECT_WINDOW_SECONDS

        if player_name not in self.players:
            return  # Player already removed

        player = self.players[player_name]

        if not player.connected:
            # Player still disconnected after grace period
            player.disconnect()  # Sets disconnected_at and connected=False

            # Story 2.5: Start 5-minute reconnection window
            self.start_timer(
                name=f"reconnect_window:{player_name}",
                duration=RECONNECT_WINDOW_SECONDS,
                callback=lambda _: self._on_reconnect_window_expired(player_name)
            )

            _LOGGER.warning(
                "Player disconnected: %s (reconnection window: %d seconds)",
                player_name,
                RECONNECT_WINDOW_SECONDS
            )

            # Broadcast state update showing player as disconnected
            # Note: broadcast_state() will be implemented when WebSocket is ready
            # await self.broadcast_state()

    async def _on_reconnect_window_expired(self, player_name: str) -> None:
        """Remove player after 5-minute reconnection window expires (Story 2.5).

        Called by reconnect_window timer (fires regardless of reconnection status).
        This enforces NFR12: absolute 5-minute limit from first disconnect.

        Args:
            player_name: Name of player whose window expired
        """
        from ..const import RECONNECT_WINDOW_SECONDS

        if player_name not in self.players:
            return  # Player already removed

        player = self.players[player_name]

        # Remove player regardless of connected status - 5 minutes elapsed from first disconnect
        _LOGGER.info(
            "Reconnection window expired: %s (removing from game after %d seconds)",
            player_name,
            RECONNECT_WINDOW_SECONDS
        )

        # Cancel disconnect_grace timer if still running
        self.cancel_timer(f"disconnect_grace:{player_name}")

        # Remove from both dictionaries
        self.sessions.pop(player.session_token, None)
        del self.players[player_name]
        self.player_count = len(self.players)

        # Broadcast state update
        # Note: broadcast_state() will be implemented when WebSocket is ready
        # await self.broadcast_state()

    def start_role_display_timer(self) -> tuple[bool, str | None]:
        """Start the 5-second role display timer after role assignment (Story 4.1).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE, TIMER_ROLE_DISPLAY

        # Phase guard
        if self.phase != GamePhase.ROLES:
            _LOGGER.warning("Cannot start role display timer - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        _LOGGER.info("Starting role display timer (%d seconds)", TIMER_ROLE_DISPLAY)

        # Cancel existing timer if present (ARCH-11)
        self.cancel_timer("role_display")

        # Start timer
        self.start_timer(
            "role_display",
            float(TIMER_ROLE_DISPLAY),
            self._on_role_display_complete
        )

        return True, None

    async def transition_to_questioning(self) -> tuple[bool, str | None]:
        """Transition from ROLES to QUESTIONING phase (Story 4.1).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE_TRANSITION, ERR_NO_ROUND_DURATION

        # Phase guard - must be in ROLES phase
        if self.phase != GamePhase.ROLES:
            _LOGGER.warning(
                "Cannot transition to QUESTIONING - invalid phase: %s",
                self.phase
            )
            return False, ERR_INVALID_PHASE_TRANSITION

        # Verify round duration is configured
        round_duration_minutes = getattr(self.config, 'round_duration_minutes', None)
        if not round_duration_minutes or round_duration_minutes <= 0:
            _LOGGER.error("Round duration not configured")
            return False, ERR_NO_ROUND_DURATION

        # Calculate duration in seconds
        round_duration_seconds = round_duration_minutes * 60

        # Transition to QUESTIONING
        _LOGGER.info(
            "Transitioning to QUESTIONING phase (round duration: %d seconds)",
            round_duration_seconds
        )
        self.phase = GamePhase.QUESTIONING

        # Start round timer
        success, error = await self.start_round_timer()
        if not success:
            _LOGGER.error("Failed to start round timer: %s", error)
            # Revert phase transition on failure
            self.phase = GamePhase.ROLES
            return False, error

        return True, None

    async def start_round_timer(self) -> tuple[bool, str | None]:
        """Start the round timer for QUESTIONING phase (Story 4.1).

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import ERR_INVALID_PHASE

        # Phase guard
        if self.phase != GamePhase.QUESTIONING:
            _LOGGER.warning("Cannot start round timer - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        # Get round duration from config (in minutes, convert to seconds)
        round_duration_minutes = getattr(self.config, 'round_duration_minutes', 7)
        round_duration_seconds = round_duration_minutes * 60

        _LOGGER.info("Starting round timer (%d seconds)", round_duration_seconds)

        # Cancel existing round timer if present (ARCH-11)
        self.cancel_timer("round")

        # Start timer
        self.start_timer(
            "round",
            float(round_duration_seconds),
            self._on_round_timer_expired
        )

        return True, None

    async def _on_role_display_complete(self, timer_name: str) -> None:
        """Timer callback: role display timer expired (Story 3.3, updated for Story 4.1).

        Transitions from ROLES phase to QUESTIONING phase after 5 seconds.

        Args:
            timer_name: Name of the expired timer (ignored)
        """
        _LOGGER.info("Role display timer expired - transitioning to QUESTIONING")

        # Story 4.3: Initialize turn order (before transition)
        if hasattr(self, 'initialize_turn_order'):
            self.initialize_turn_order()

        # Transition to QUESTIONING phase (Story 4.1)
        success, error = await self.transition_to_questioning()
        if not success:
            _LOGGER.error("Failed to transition to QUESTIONING: %s", error)

        # Note: broadcast_state() will be called by WebSocket handler

    def call_vote(self, caller_name: str | None = None) -> tuple[bool, str | None]:
        """
        Transition from QUESTIONING to VOTE phase.

        Any player can call this during questioning (FR29).

        Args:
            caller_name: Name of player who called the vote (AC6), or "[TIMER]" for auto-vote

        Returns:
            (success: bool, error_code: str | None)

        Phase Guard:
            - Only valid in QUESTIONING phase (ARCH-17)

        Side Effects:
            - Cancels round timer (ARCH-11)
            - Starts vote timer (60s per ARCH-10)
            - Transitions to VOTE phase
            - Stores vote_caller for attribution (AC6)
        """
        from ..const import ERR_INVALID_PHASE, VOTE_TIMER_DURATION

        # Phase guard (ARCH-17)
        if self.phase != GamePhase.QUESTIONING:
            return (False, ERR_INVALID_PHASE)

        # Store vote caller for attribution (Story 4.5: AC6)
        self.vote_caller = caller_name

        _LOGGER.info("Vote called by %s - transitioning from QUESTIONING to VOTE", caller_name or "unknown")

        # Cancel round timer (ARCH-11)
        self.cancel_timer("round")

        # Transition to VOTE phase
        self.phase = GamePhase.VOTE

        # Start vote timer (60 seconds per ARCH-10)
        self.start_timer("vote", VOTE_TIMER_DURATION, self._on_vote_timeout)

        return (True, None)

    async def _on_vote_timeout(self, timer_name: str) -> None:
        """
        Handle vote timer expiration (Story 5.5 enhancement).

        Non-voters are automatically marked as abstain (AC3, FR36).
        Transition to REVEAL phase (AC5).

        Args:
            timer_name: Name of the expired timer (ignored)
        """
        import time

        _LOGGER.info("Vote timer expired - processing abstentions")

        # Mark non-voters as abstain (AC3)
        connected_players = [
            name for name, player in self.players.items() if player.connected
        ]

        for player_name in connected_players:
            if player_name not in self.votes:
                # Check if this is the spy who guessed (Story 5.4)
                if self.spy_guess and player_name == self._spy_name:
                    continue  # Spy guessed location, not abstaining

                self.votes[player_name] = {
                    "target": None,
                    "confidence": 0,
                    "abstained": True,
                    "timestamp": time.time(),
                }
                _LOGGER.info("Player %s abstained (timeout)", player_name)

        votes_cast = len([v for v in self.votes.values() if not v.get("abstained")])
        abstentions = len([v for v in self.votes.values() if v.get("abstained")])

        _LOGGER.info(
            "Vote phase complete: %d voted, %d abstained",
            votes_cast,
            abstentions
        )

        # Cancel vote timer
        self.cancel_timer("vote")

        # Transition to REVEAL (AC5)
        self.phase = GamePhase.REVEAL
        _LOGGER.info("Transitioning to REVEAL phase")

    async def _on_round_timer_expired(self, timer_name: str) -> None:
        """Timer callback: round timer expired - auto-transition to VOTE (Story 4.2, FR30).

        When the round timer reaches zero, automatically trigger vote phase
        without requiring player action (FR30).

        Args:
            timer_name: Name of the expired timer (ignored)
        """
        if self.phase != GamePhase.QUESTIONING:
            _LOGGER.warning(
                "Round timer expired but not in QUESTIONING phase: %s",
                self.phase.value
            )
            return

        _LOGGER.info("Round timer expired - auto-transitioning to VOTE phase (FR30)")

        # Use call_vote() for consistent transition logic
        # Pass "[TIMER]" as caller for attribution (Story 4.5: AC6)
        success, error = self.call_vote(caller_name="[TIMER]")
        if not success:
            _LOGGER.error("Auto-transition to VOTE failed: %s", error)

    def get_connected_player_count(self) -> int:
        """Get count of currently connected players (Story 3.2).

        Returns:
            int: Number of connected players
        """
        return sum(1 for p in self.players.values() if p.connected)

    def can_start_game(self) -> bool:
        """Check if game can be started (Story 3.2).

        Used for UI state management to enable/disable START button.

        Returns:
            bool: True if game can be started, False otherwise
        """
        from ..const import MIN_PLAYERS, MAX_PLAYERS

        # Phase must be LOBBY
        if self.phase != GamePhase.LOBBY:
            return False

        # Game must not be already started
        if self._game_started:
            return False

        # Check connected player count
        connected_count = self.get_connected_player_count()
        return MIN_PLAYERS <= connected_count <= MAX_PLAYERS

    def start_game(self) -> tuple[bool, str | None]:
        """Start the game if conditions are met (Story 3.2).

        Validates:
        - Phase is LOBBY
        - Game not already started
        - 4-10 connected players

        Returns:
            (success: bool, error_code: str | None)
        """
        from ..const import (
            ERR_INVALID_PHASE,
            ERR_GAME_ALREADY_STARTED,
            ERR_NOT_ENOUGH_PLAYERS,
            ERR_GAME_FULL,
            ERR_ROLE_ASSIGNMENT_FAILED,
            MIN_PLAYERS,
            MAX_PLAYERS,
        )

        # Phase guard
        if self.phase != GamePhase.LOBBY:
            _LOGGER.warning("Cannot start game - invalid phase: %s", self.phase)
            return False, ERR_INVALID_PHASE

        # Check if game already started
        if self._game_started:
            _LOGGER.warning("Game already started")
            return False, ERR_GAME_ALREADY_STARTED

        # Count connected players only
        connected_count = self.get_connected_player_count()

        # Validate minimum players
        if connected_count < MIN_PLAYERS:
            _LOGGER.info(
                "Cannot start game - not enough players: %d (need %d)",
                connected_count,
                MIN_PLAYERS
            )
            return False, ERR_NOT_ENOUGH_PLAYERS

        # Validate maximum players (should be prevented at join, but double-check)
        if connected_count > MAX_PLAYERS:
            _LOGGER.warning(
                "Too many players: %d (max %d) - this should not happen",
                connected_count,
                MAX_PLAYERS
            )
            return False, ERR_GAME_FULL

        # FIX #3: Update player_count to match connected count
        self.player_count = connected_count

        # FIX #6: Use transition_to() for proper phase management (ARCH-4)
        success, error = self.transition_to(GamePhase.ROLES)
        if not success:
            _LOGGER.error("Failed to transition to ROLES phase: %s", error)
            return False, error

        # FIX #7: Set state fields AFTER phase transition succeeds
        self.current_round = 1
        self._game_started = True

        # Story 3.3: Assign spy and roles
        try:
            from .roles import assign_roles
            assign_roles(self)
        except ValueError as err:
            # FIX #1: Rollback state on role assignment failure
            _LOGGER.error("Failed to assign roles: %s", err)
            self._game_started = False
            self.current_round = 0
            # Transition back to LOBBY
            self.transition_to(GamePhase.LOBBY)
            # FIX #5: Use imported constant (ARCH-19)
            return False, ERR_ROLE_ASSIGNMENT_FAILED

        # FIX #4: Validate config or use safe default
        num_rounds = getattr(self.config, 'num_rounds', 5)
        if num_rounds < 1:
            num_rounds = 5
            _LOGGER.warning("Invalid num_rounds, using default: 5")

        _LOGGER.info(
            "Game started: %d players, round 1/%d",
            connected_count,
            num_rounds
        )

        # FIX #10: Story 3.3: Start role display timer with error handling
        try:
            self.start_timer(
                "role_display",
                5.0,
                self._on_role_display_complete
            )
        except Exception as err:
            _LOGGER.error("Failed to start role display timer: %s", err)
            # Continue anyway - timer is non-critical for initial start

        return True, None
