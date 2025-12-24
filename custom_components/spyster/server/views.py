"""HTTP views for Spyster integration."""
import base64
import io
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import qrcode
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from ..const import ERR_INTERNAL, ERROR_MESSAGES
from .websocket import WebSocketHandler

if TYPE_CHECKING:
    from ..game.state import GameState

_LOGGER = logging.getLogger(__name__)

# Cache the version to avoid reading manifest on every request
_CACHED_VERSION: str | None = None


def _get_version() -> str:
    """Get version from manifest.json for cache busting."""
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION

    try:
        manifest_path = Path(__file__).parent.parent / "manifest.json"
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
            _CACHED_VERSION = manifest.get("version", "0.0.0")
    except Exception as err:
        _LOGGER.warning("Failed to read version from manifest: %s", err)
        _CACHED_VERSION = "0.0.0"

    return _CACHED_VERSION


def _inject_cache_bust(html_content: str) -> str:
    """Inject version query parameter into static file URLs for cache busting.

    Args:
        html_content: The HTML content to process

    Returns:
        HTML content with versioned static file URLs
    """
    version = _get_version()

    # Pattern to match static file URLs (CSS, JS, vendor JS)
    # Matches: /api/spyster/static/css/styles.css, /api/spyster/static/js/host.js,
    # or /api/spyster/static/js/vendor/qrcode.min.js
    pattern = r'(/api/spyster/static/(?:css|js(?:/vendor)?)/[^"\']+\.(css|js))(["\'])'

    def add_version(match: re.Match) -> str:
        url = match.group(1)
        quote = match.group(3)
        # Add version query parameter
        return f'{url}?v={version}{quote}'

    return re.sub(pattern, add_version, html_content)


class HostView(HomeAssistantView):
    """View to serve the host display interface."""

    url = "/api/spyster/host"
    name = "api:spyster:host"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Serve the host display HTML.

        Args:
            request: The HTTP request

        Returns:
            HTML response or error response
        """
        try:
            # Get the path to the www directory using pathlib
            component_dir = Path(__file__).parent.parent
            html_path = component_dir / "www" / "host.html"

            # Check if file exists and return 404 if not
            if not html_path.exists():
                _LOGGER.error("host.html not found at %s", html_path)
                return web.Response(
                    text="Host page not found",
                    status=404,
                    content_type="text/plain",
                )

            # Read the HTML file and inject cache busting
            html_content = html_path.read_text(encoding="utf-8")
            html_content = _inject_cache_bust(html_content)

            return web.Response(text=html_content, content_type="text/html")
        except FileNotFoundError as err:
            _LOGGER.error("host.html not found: %s", err)
            return web.Response(
                text="Host page not found",
                status=404,
                content_type="text/plain",
            )
        except Exception as err:
            _LOGGER.error("Error serving host view: %s", err)
            return web.Response(
                text="Error loading host display",
                status=500,
                content_type="text/plain",
            )


class PlayerView(HomeAssistantView):
    """View to serve the player interface."""

    url = "/api/spyster/player"
    name = "api:spyster:player"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Serve the player UI HTML.

        Args:
            request: The HTTP request

        Returns:
            HTML response or error response
        """
        try:
            # Get the path to the www directory using pathlib
            component_dir = Path(__file__).parent.parent
            html_path = component_dir / "www" / "player.html"

            # Check if file exists and return 404 if not
            if not html_path.exists():
                _LOGGER.error("player.html not found at %s", html_path)
                return web.Response(
                    text="Player page not found",
                    status=404,
                    content_type="text/plain",
                )

            # Read the HTML file and inject cache busting
            html_content = html_path.read_text(encoding="utf-8")
            html_content = _inject_cache_bust(html_content)

            return web.Response(text=html_content, content_type="text/html")
        except FileNotFoundError as err:
            _LOGGER.error("player.html not found: %s", err)
            return web.Response(
                text="Player page not found",
                status=404,
                content_type="text/plain",
            )
        except Exception as err:
            _LOGGER.error("Error serving player view: %s", err)
            return web.Response(
                text="Error loading player interface",
                status=500,
                content_type="text/plain",
            )


class SpysterQRView(HomeAssistantView):
    """View for generating QR codes for game sessions.

    This view provides QR code generation functionality for the host display.
    QR codes encode the player join URL for easy mobile device access.
    """

    url = "/api/spyster/qr"
    name = "api:spyster:qr"
    requires_auth = False

    def __init__(self, game_state: "GameState") -> None:
        """Initialize the QR view.

        Args:
            game_state: Reference to active GameState instance
        """
        self.game_state = game_state

    def generate_qr_code(self, url: str) -> str:
        """Generate QR code data URL for given URL.

        Args:
            url: The URL to encode in the QR code

        Returns:
            Base64-encoded PNG data URL for the QR code image

        Raises:
            ValueError: If URL is empty or invalid
        """
        from ..const import DEFAULT_QR_BOX_SIZE, DEFAULT_QR_BORDER

        if not url:
            raise ValueError("URL cannot be empty")

        # Validate URL length to prevent DoS attacks
        MAX_QR_URL_LENGTH = 2048
        if len(url) > MAX_QR_URL_LENGTH:
            raise ValueError(f"URL too long (max {MAX_QR_URL_LENGTH} characters)")

        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,  # Auto-adjust size
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=DEFAULT_QR_BOX_SIZE,
                border=DEFAULT_QR_BORDER,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Generate PIL image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to PNG bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_bytes = buffer.getvalue()

            # Encode as base64 data URL
            img_str = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:image/png;base64,{img_str}"

            _LOGGER.debug("QR code generated: url=%s, size=%d bytes", url, len(img_bytes))
            return data_url

        except Exception as err:
            _LOGGER.error("QR code generation failed: %s", err, exc_info=True)
            raise

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for QR code.

        Query parameters:
            session: Session ID (optional - uses current game session if not provided)

        Returns:
            JSON response with QR code data URL and join URL
        """
        try:
            # Get base URL from Home Assistant
            hass = request.app["hass"]
            base_url = hass.config.api.base_url

            if not base_url:
                _LOGGER.error("Home Assistant base_url not configured")
                return web.json_response(
                    {
                        "error": True,
                        "code": ERR_INTERNAL,
                        "message": "Server configuration error",
                    },
                    status=500,
                )

            # Get join URL from game state
            try:
                join_url = self.game_state.get_join_url(base_url)
            except ValueError as err:
                _LOGGER.warning("Failed to get join URL: %s", err)
                return web.json_response(
                    {
                        "error": True,
                        "code": ERR_INTERNAL,
                        "message": "No active game session",
                    },
                    status=400,
                )

            # Generate QR code
            try:
                qr_data_url = self.generate_qr_code(join_url)
            except Exception as err:
                _LOGGER.error("QR code generation failed: %s", err)
                return web.json_response(
                    {
                        "error": True,
                        "code": ERR_INTERNAL,
                        "message": ERROR_MESSAGES[ERR_INTERNAL],
                    },
                    status=500,
                )

            _LOGGER.info("QR code requested: session=%s", self.game_state.session_id)

            return web.json_response(
                {
                    "success": True,
                    "qr_code_data": qr_data_url,
                    "join_url": join_url,
                    "session_id": self.game_state.session_id,
                }
            )

        except Exception as err:
            _LOGGER.error("Unexpected error in QR view: %s", err, exc_info=True)
            return web.json_response(
                {
                    "error": True,
                    "code": ERR_INTERNAL,
                    "message": ERROR_MESSAGES[ERR_INTERNAL],
                },
                status=500,
            )


class SpysterWebSocketView(HomeAssistantView):
    """WebSocket endpoint for real-time game communication."""

    url = "/api/spyster/ws"
    name = "api:spyster:websocket"
    requires_auth = False

    def __init__(self, hass, game_state: "GameState"):
        """Initialize the WebSocket view.

        Args:
            hass: Home Assistant instance
            game_state: Reference to active GameState instance
        """
        self.hass = hass
        self.handler = WebSocketHandler(game_state)

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection.

        Args:
            request: The WebSocket upgrade request

        Returns:
            WebSocketResponse object
        """
        return await self.handler.handle_connection(request)
