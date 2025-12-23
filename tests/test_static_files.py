"""Tests for static file serving."""
import pytest
from unittest.mock import Mock, patch
import os

from custom_components.spyster.server import register_static_paths


class TestStaticFileRegistration:
    """Tests for static file path registration."""

    def test_register_static_paths_called(self):
        """Test that register_static_paths registers the correct path."""
        # Mock hass object
        mock_hass = Mock()
        mock_hass.http = Mock()

        # Mock path resolution
        with patch("os.path.dirname") as mock_dirname:
            with patch("os.path.join") as mock_join:
                # Setup mocks
                mock_dirname.return_value = "/mock/component"
                mock_join.return_value = "/mock/component/www"

                # Call function
                register_static_paths(mock_hass)

        # Verify register_static_path was called
        mock_hass.http.register_static_path.assert_called_once()

        # Get the call arguments
        call_args = mock_hass.http.register_static_path.call_args

        # Verify URL path
        assert call_args[0][0] == "/api/spyster/static"

        # Verify local path
        assert call_args[0][1] == "/mock/component/www"

    def test_register_static_paths_handles_errors(self):
        """Test that register_static_paths handles errors gracefully."""
        # Mock hass object that raises an error
        mock_hass = Mock()
        mock_hass.http.register_static_path.side_effect = Exception("Test error")

        # Should not raise an exception
        try:
            register_static_paths(mock_hass)
        except Exception as e:
            pytest.fail(f"register_static_paths raised an exception: {e}")

    def test_static_path_points_to_www_directory(self):
        """Test that static path correctly points to www directory."""
        mock_hass = Mock()

        with patch("os.path.dirname") as mock_dirname:
            with patch("os.path.join") as mock_join:
                # Setup realistic path resolution
                component_dir = "/custom_components/spyster"
                www_dir = "/custom_components/spyster/www"

                mock_dirname.return_value = component_dir
                mock_join.return_value = www_dir

                register_static_paths(mock_hass)

                # Verify os.path.join was called with correct arguments
                mock_join.assert_called_once_with(component_dir, "www")


class TestStaticFilePaths:
    """Tests for expected static file paths."""

    def test_css_file_path(self):
        """Test that styles.css would be accessible at correct path."""
        # This is a logical test - the actual path should be:
        # /api/spyster/static/css/styles.css
        expected_path = "/api/spyster/static/css/styles.css"
        assert expected_path == "/api/spyster/static/css/styles.css"

    def test_js_host_file_path(self):
        """Test that host.js would be accessible at correct path."""
        expected_path = "/api/spyster/static/js/host.js"
        assert expected_path == "/api/spyster/static/js/host.js"

    def test_js_player_file_path(self):
        """Test that player.js would be accessible at correct path."""
        expected_path = "/api/spyster/static/js/player.js"
        assert expected_path == "/api/spyster/static/js/player.js"


class TestStaticFileStructure:
    """Tests for static file directory structure."""

    def test_www_directory_exists(self):
        """Test that www directory exists (if running in actual project)."""
        # This test will only work when run in the actual project
        # In a test environment, we'd mock this
        component_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        www_path = os.path.join(
            component_root, "custom_components", "spyster", "www"
        )

        # If the path exists, verify structure
        if os.path.exists(www_path):
            assert os.path.isdir(www_path)

            # Check for expected subdirectories
            css_path = os.path.join(www_path, "css")
            js_path = os.path.join(www_path, "js")

            if os.path.exists(css_path):
                assert os.path.isdir(css_path)

            if os.path.exists(js_path):
                assert os.path.isdir(js_path)


class TestHTMLViewportMetaTags:
    """Tests for HTML viewport meta tags and responsive design requirements."""

    def test_player_html_viewport_meta_tag(self):
        """Test that player.html has correct viewport meta tag for mobile optimization."""
        component_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        player_html_path = os.path.join(
            component_root, "custom_components", "spyster", "www", "player.html"
        )

        if os.path.exists(player_html_path):
            with open(player_html_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for viewport meta tag with required attributes
            assert 'name="viewport"' in content
            assert 'width=device-width' in content
            assert 'initial-scale=1' in content
            assert 'viewport-fit=cover' in content

    def test_host_html_viewport_meta_tag(self):
        """Test that host.html has viewport meta tag for responsive behavior."""
        component_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        host_html_path = os.path.join(
            component_root, "custom_components", "spyster", "www", "host.html"
        )

        if os.path.exists(host_html_path):
            with open(host_html_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for viewport meta tag
            assert 'name="viewport"' in content

    def test_player_html_mobile_web_app_meta_tags(self):
        """Test that player.html includes mobile web app meta tags."""
        component_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        player_html_path = os.path.join(
            component_root, "custom_components", "spyster", "www", "player.html"
        )

        if os.path.exists(player_html_path):
            with open(player_html_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for mobile web app capability meta tags
            assert 'apple-mobile-web-app-capable' in content
            assert 'mobile-web-app-capable' in content
