"""Player session management for Spyster."""
import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from time import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aiohttp import web

_LOGGER = logging.getLogger(__name__)


@dataclass
class PlayerSession:
    """Represents a player's session in the game.

    Attributes:
        name: Player's display name
        token: Session token for reconnection
        connected: Whether player is currently connected
        is_host: Whether this player created the game
        ws: WebSocket connection (None if disconnected)
        role: Assigned role during ROLES phase (e.g., "Astronaut", "Spy")
        is_spy: Whether this player is the spy
        vote_target: Name of player being voted for
        vote_confidence: Confidence level (1-3)
        score: Current score
        joined_at: Timestamp when player joined
        last_heartbeat: Last activity timestamp
    """

    name: str
    session_token: str  # Story 2.2: Session token for reconnection (renamed from 'token' for clarity)
    connected: bool = True
    is_host: bool = False
    ws: Optional["web.WebSocketResponse"] = None
    role: Optional[str] = None
    is_spy: bool = False
    vote_target: Optional[str] = None
    vote_confidence: int = 1
    score: int = 0
    joined_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    disconnect_timer: Optional[asyncio.Task] = None  # Story 2.4: Grace timer reference
    disconnected_at: Optional[float] = None  # Story 2.6: Timestamp when player disconnected (time.time())

    @classmethod
    def create_new(cls, name: str, is_host: bool = False) -> "PlayerSession":
        """Create a new player session with generated token.

        Args:
            name: Player's display name
            is_host: Whether this player is the host

        Returns:
            New PlayerSession instance with cryptographically secure token

        Security:
            Uses 32 bytes (256 bits) for token entropy per security best practices.
            Base64-encoded string length will be ~43 characters.
        """
        session_token = secrets.token_urlsafe(32)  # 256 bits of entropy
        return cls(name=name, session_token=session_token, is_host=is_host)

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now()

    def disconnect(self) -> None:
        """Mark player as disconnected and record timestamp (Story 2.4/2.6).

        Called by disconnect_grace timer after 30 seconds of inactivity.
        Sets disconnected_at ONLY on first disconnect (not updated on subsequent disconnects).
        This ensures the 5-minute reconnection window is calculated from the first disconnect.
        """
        if self.connected:
            self.connected = False
            self.ws = None
            self.disconnected_at = time()
            _LOGGER.info("Player marked disconnected: %s (at: %.2f)", self.name, self.disconnected_at)
        else:
            _LOGGER.debug(
                "Player already disconnected: %s (disconnected_at preserved: %.2f)",
                self.name,
                self.disconnected_at if self.disconnected_at else 0
            )

    def reconnect(self, ws: "web.WebSocketResponse") -> None:
        """Reconnect player with new WebSocket connection (Story 2.5).

        FIXED: Now resets disconnected_at to allow fresh 5-minute window on each disconnect.
        This prevents unfair kicks after multiple brief disconnects.

        Args:
            ws: New WebSocket connection
        """
        self.connected = True
        self.ws = ws
        # FIXED: Reset disconnected_at to give fresh 5-minute window on next disconnect
        self.disconnected_at = None
        # Clear disconnect timer reference
        if self.disconnect_timer:
            self.disconnect_timer = None
        self.update_heartbeat()
        _LOGGER.info(
            "Player reconnected: %s (disconnected_at reset for fresh window)",
            self.name
        )

    def get_disconnect_duration(self) -> float | None:
        """Get seconds since disconnection, or None if connected (Story 2.6).

        Returns:
            Seconds since disconnection, or None if player is connected
        """
        if self.connected or self.disconnected_at is None:
            return None
        return time() - self.disconnected_at

    def is_session_valid(self) -> bool:
        """Check if session is still within reconnection window (Story 2.5).

        Returns:
            True if session is valid (never disconnected OR within 5-minute window)
            False if session expired (disconnected for over 5 minutes)
        """
        from ..const import RECONNECT_WINDOW_SECONDS

        if self.disconnected_at is None:
            return True  # Never disconnected

        elapsed = time() - self.disconnected_at
        is_valid = elapsed < RECONNECT_WINDOW_SECONDS

        _LOGGER.debug(
            "Session validation: %s disconnected for %.1fs (valid: %s)",
            self.name,
            elapsed,
            is_valid
        )

        return is_valid

    def add_score(self, points: int) -> None:
        """Add points to player's score (Story 5.7).

        Args:
            points: Points to add (can be negative)
        """
        self.score += points
        _LOGGER.debug("Player %s score updated: %+d (total: %d)", self.name, points, self.score)

    def reset_score(self) -> None:
        """Reset player's score to 0 (for new game)."""
        self.score = 0

    def to_dict(self) -> dict:
        """Return public player info (no sensitive data).

        Returns:
            dict: Public player information safe to broadcast

        Note:
            Never includes session_token, ws connection, or role info (in lobby).
            Role information is added in later stories with proper filtering.
        """
        return {
            "name": self.name,
            "connected": self.connected,
            "is_host": self.is_host,
            "score": self.score,
        }
