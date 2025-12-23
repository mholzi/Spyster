"""Server infrastructure for Spyster."""
import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

__all__: list[str] = ["register_static_paths", "StaticCSSView", "StaticJSView", "StaticVendorJSView"]


class StaticCSSView(HomeAssistantView):
    """View to serve CSS files with correct MIME type."""

    url = "/api/spyster/static/css/{filename}"
    name = "api:spyster:static:css"
    requires_auth = False

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Serve CSS file with correct Content-Type."""
        try:
            component_dir = Path(__file__).parent.parent
            css_path = component_dir / "www" / "css" / filename

            if not css_path.exists():
                _LOGGER.error("CSS file not found: %s", css_path)
                return web.Response(text="Not found", status=404)

            # Security: prevent path traversal
            if ".." in filename or filename.startswith("/"):
                return web.Response(text="Forbidden", status=403)

            content = css_path.read_text(encoding="utf-8")
            return web.Response(
                text=content,
                content_type="text/css",
                charset="utf-8"
            )
        except Exception as err:
            _LOGGER.error("Error serving CSS %s: %s", filename, err)
            return web.Response(text="Server error", status=500)


class StaticJSView(HomeAssistantView):
    """View to serve JavaScript files with correct MIME type."""

    url = "/api/spyster/static/js/{filename}"
    name = "api:spyster:static:js"
    requires_auth = False

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Serve JavaScript file with correct Content-Type."""
        try:
            component_dir = Path(__file__).parent.parent
            js_path = component_dir / "www" / "js" / filename

            if not js_path.exists():
                _LOGGER.error("JS file not found: %s", js_path)
                return web.Response(text="Not found", status=404)

            # Security: prevent path traversal
            if ".." in filename or filename.startswith("/"):
                return web.Response(text="Forbidden", status=403)

            content = js_path.read_text(encoding="utf-8")
            return web.Response(
                text=content,
                content_type="application/javascript",
                charset="utf-8"
            )
        except Exception as err:
            _LOGGER.error("Error serving JS %s: %s", filename, err)
            return web.Response(text="Server error", status=500)


class StaticVendorJSView(HomeAssistantView):
    """View to serve vendor JavaScript files with correct MIME type."""

    url = "/api/spyster/static/js/vendor/{filename}"
    name = "api:spyster:static:js:vendor"
    requires_auth = False

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Serve vendor JavaScript file with correct Content-Type."""
        try:
            component_dir = Path(__file__).parent.parent
            js_path = component_dir / "www" / "js" / "vendor" / filename

            if not js_path.exists():
                _LOGGER.error("Vendor JS file not found: %s", js_path)
                return web.Response(text="Not found", status=404)

            # Security: prevent path traversal
            if ".." in filename or filename.startswith("/"):
                return web.Response(text="Forbidden", status=403)

            content = js_path.read_text(encoding="utf-8")
            return web.Response(
                text=content,
                content_type="application/javascript",
                charset="utf-8"
            )
        except Exception as err:
            _LOGGER.error("Error serving vendor JS %s: %s", filename, err)
            return web.Response(text="Server error", status=500)


def register_static_paths(hass: HomeAssistant) -> None:
    """Register static file views for serving CSS/JS assets."""
    try:
        # Register views for static files with proper MIME types
        hass.http.register_view(StaticCSSView())
        hass.http.register_view(StaticJSView())
        hass.http.register_view(StaticVendorJSView())

        _LOGGER.info("Registered static file views for CSS, JS, and vendor JS")
    except Exception as err:
        _LOGGER.error("Failed to register static paths: %s", err)
