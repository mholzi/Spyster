"""Game configuration management."""
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ..const import (
    CONFIG_MIN_ROUND_DURATION,
    CONFIG_MAX_ROUND_DURATION,
    CONFIG_DEFAULT_ROUND_DURATION,
    CONFIG_MIN_ROUNDS,
    CONFIG_MAX_ROUNDS,
    CONFIG_DEFAULT_ROUNDS,
    CONFIG_DEFAULT_LOCATION_PACK,
    ERR_CONFIG_INVALID_DURATION,
    ERR_CONFIG_INVALID_ROUNDS,
    ERR_CONFIG_INVALID_PACK,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Game configuration settings."""

    round_duration_minutes: int = CONFIG_DEFAULT_ROUND_DURATION
    num_rounds: int = CONFIG_DEFAULT_ROUNDS
    location_pack: str = CONFIG_DEFAULT_LOCATION_PACK

    def validate(self) -> tuple[bool, str | None]:
        """
        Validate all configuration values.

        Returns:
            (valid, error_code) - True if valid, otherwise False with error code
        """
        # Validate round duration
        if not (CONFIG_MIN_ROUND_DURATION <= self.round_duration_minutes <= CONFIG_MAX_ROUND_DURATION):
            _LOGGER.warning(
                "Invalid round duration: %d (min: %d, max: %d)",
                self.round_duration_minutes,
                CONFIG_MIN_ROUND_DURATION,
                CONFIG_MAX_ROUND_DURATION
            )
            return False, ERR_CONFIG_INVALID_DURATION

        # Validate number of rounds
        if not (CONFIG_MIN_ROUNDS <= self.num_rounds <= CONFIG_MAX_ROUNDS):
            _LOGGER.warning(
                "Invalid number of rounds: %d (min: %d, max: %d)",
                self.num_rounds,
                CONFIG_MIN_ROUNDS,
                CONFIG_MAX_ROUNDS
            )
            return False, ERR_CONFIG_INVALID_ROUNDS

        # Validate location pack exists
        if not self._pack_exists(self.location_pack):
            _LOGGER.warning("Location pack not found: %s", self.location_pack)
            return False, ERR_CONFIG_INVALID_PACK

        return True, None

    def _pack_exists(self, pack_id: str) -> bool:
        """Check if location pack file exists."""
        pack_file = Path(__file__).parent.parent / "content" / f"{pack_id}.json"
        exists = pack_file.exists()
        _LOGGER.debug("Location pack check: %s - %s", pack_id, "exists" if exists else "not found")
        return exists

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'GameConfig':
        """Create from dictionary."""
        return cls(
            round_duration_minutes=data.get("round_duration_minutes", CONFIG_DEFAULT_ROUND_DURATION),
            num_rounds=data.get("num_rounds", CONFIG_DEFAULT_ROUNDS),
            location_pack=data.get("location_pack", CONFIG_DEFAULT_LOCATION_PACK),
        )
