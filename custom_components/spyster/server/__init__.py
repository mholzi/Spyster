"""Server infrastructure for Spyster."""
import logging
import os

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

__all__: list[str] = ["register_static_paths"]


def register_static_paths(hass: HomeAssistant) -> None:
    """Register static file paths for serving CSS/JS assets."""
    try:
        # Get the path to the www directory
        component_dir = os.path.dirname(os.path.dirname(__file__))
        www_path = os.path.join(component_dir, "www")

        # Register the static path
        hass.http.register_static_path(
            "/api/spyster/static",
            www_path,
            cache_headers=False,  # Disable caching for development
        )

        _LOGGER.info("Registered static paths: /api/spyster/static -> %s", www_path)
    except Exception as err:
        _LOGGER.error("Failed to register static paths: %s", err)
