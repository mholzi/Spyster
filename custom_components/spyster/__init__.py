"""Spyster integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .server import register_static_paths
from .server.views import HostView, PlayerView, SpysterQRView, SpysterWebSocketView
from .game.state import GameState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spyster from a config entry."""
    try:
        _LOGGER.info("Setting up Spyster integration")

        # Initialize integration data storage
        hass.data.setdefault(DOMAIN, {})

        # Store config entry data
        hass.data[DOMAIN]["config"] = entry.data

        # Initialize game state (Story 1.2)
        game_state = GameState()
        hass.data[DOMAIN]["game_state"] = game_state

        # Create a session for testing (Story 1.3)
        # This will be moved to proper game initialization in future stories
        game_state.create_session("default_host")

        # Register HTTP views
        hass.http.register_view(HostView())
        hass.http.register_view(PlayerView())
        hass.http.register_view(SpysterQRView(game_state))
        hass.http.register_view(SpysterWebSocketView(hass, game_state))
        _LOGGER.info(
            "Registered HTTP views: /api/spyster/host, /api/spyster/player, /api/spyster/qr, /api/spyster/ws"
        )

        # Register static file paths
        register_static_paths(hass)

        # Story 3.3: Preload location packs at startup
        from .game.content import preload_location_packs
        await preload_location_packs(hass)

        _LOGGER.info("Spyster integration setup complete")
        return True
    except Exception as err:
        _LOGGER.error("Failed to set up Spyster integration: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Spyster integration")

    # Cancel all timers (Story 1.2)
    if DOMAIN in hass.data and "game_state" in hass.data[DOMAIN]:
        game_state = hass.data[DOMAIN]["game_state"]
        game_state.cancel_all_timers()

    # Clean up integration data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True
