"""Tests for version detection."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from mdfs.__main__ import _get_version


class TestGetVersionDev(unittest.TestCase):
    """Test version reading in development mode (from pyproject.toml)."""

    def test_read_from_pyproject_toml(self):
        """Test reading version from pyproject.toml when importlib fails."""
        # Mock importlib.metadata.version to raise exception
        with patch("importlib.metadata.version", side_effect=Exception("Not found")):
            version = _get_version()
            # Should read from actual pyproject.toml
            self.assertNotEqual(version, "unknown")
            # Version should be in format X.Y.Z or similar
            self.assertRegex(version, r"\d+\.\d+\.\d+")

    def test_dev_mode_fallback(self):
        """Test fallback to pyproject.toml works correctly."""
        with patch("importlib.metadata.version", side_effect=ImportError()):
            version = _get_version()
            self.assertNotEqual(version, "unknown")
            self.assertRegex(version, r"\d+\.\d+\.\d+")


class TestGetVersionProd(unittest.TestCase):
    """Test version reading in production mode (from importlib.metadata)."""

    def test_read_from_importlib_metadata(self):
        """Test reading version from importlib.metadata (installed package)."""
        # Mock importlib.metadata.version to return a version
        with patch("importlib.metadata.version", return_value="0.2.0"):
            version = _get_version()
            self.assertEqual(version, "0.2.0")

    def test_importlib_takes_precedence(self):
        """Test that importlib.metadata is tried first."""
        # Even if pyproject.toml exists, importlib should be used first
        with patch("importlib.metadata.version", return_value="1.0.0"):
            version = _get_version()
            self.assertEqual(version, "1.0.0")


class TestGetVersionFallback(unittest.TestCase):
    """Test fallback behavior when version cannot be determined."""

    def test_returns_unknown_on_all_failures(self):
        """Test that 'unknown' is returned when all methods fail."""
        with patch("importlib.metadata.version", side_effect=Exception("Not installed")):
            with patch.object(Path, "exists", return_value=False):
                version = _get_version()
                self.assertEqual(version, "unknown")

    def test_handles_invalid_toml_format(self):
        """Test graceful handling of malformed pyproject.toml."""
        with patch("importlib.metadata.version", side_effect=Exception("Not found")):
            # Create a mock for Path.read_text that returns invalid content
            with patch("pathlib.Path.read_text", return_value="invalid toml content"):
                with patch("pathlib.Path.exists", return_value=True):
                    version = _get_version()
                    # Should return unknown if regex doesn't match
                    self.assertEqual(version, "unknown")


class TestGetVersionIntegration(unittest.TestCase):
    """Integration tests for version detection."""

    def test_version_is_not_empty(self):
        """Test that some version is always returned."""
        version = _get_version()
        self.assertTrue(len(version) > 0)
        self.assertNotEqual(version, "")

    def test_version_format_is_valid(self):
        """Test that returned version has valid format."""
        version = _get_version()
        # Either should be "unknown" or match semantic versioning
        if version != "unknown":
            self.assertRegex(version, r"\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
