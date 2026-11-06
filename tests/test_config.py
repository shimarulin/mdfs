"""Tests for MDFS configuration management."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mdfs.config import Config, ConfigError


class TestConfigBasics:
    """Test basic Config functionality."""

    def test_config_no_file(self, tmp_path: Path) -> None:
        """Test Config with no .mdfsrc.yaml file."""
        import os

        # Change to temporary directory with no config
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = Config()
            assert not config.is_configured()
            assert config.config_path is None
        finally:
            os.chdir(old_cwd)

    def test_config_with_file(self, tmp_path: Path) -> None:
        """Test Config loading from .mdfsrc.yaml."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "contexts_dir: custom_contexts\n"
            "responses_dir: custom_responses\n",
        )

        config = Config(config_file)
        assert config.is_configured()
        assert config.config_path == config_file
        assert config.get_contexts_dir(tmp_path).name == "custom_contexts"
        assert config.get_responses_dir(tmp_path).name == "custom_responses"

    def test_config_defaults(self, tmp_path: Path) -> None:
        """Test Config with default values."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("# Empty config\n")

        config = Config(config_file)
        assert config.is_configured()
        assert config.get_contexts_dir(tmp_path).name == "contexts"
        assert config.get_responses_dir(tmp_path).name == "responses"


class TestConfigPaths:
    """Test path resolution in Config."""

    def test_relative_paths(self, tmp_path: Path) -> None:
        """Test relative path resolution."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "contexts_dir: .mdfs/contexts\n"
            "responses_dir: .mdfs/responses\n",
        )

        config = Config(config_file)
        contexts = config.get_contexts_dir(tmp_path)
        assert contexts.parent.name == ".mdfs"
        assert contexts.name == "contexts"

    def test_absolute_paths(self, tmp_path: Path) -> None:
        """Test absolute path handling."""
        abs_path = tmp_path / "absolute_dir"
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(f"contexts_dir: {abs_path}\n")

        config = Config(config_file)
        contexts = config.get_contexts_dir(tmp_path)
        assert contexts == abs_path.resolve()


class TestConfigCreation:
    """Test config file creation."""

    def test_create_default_config(self, tmp_path: Path) -> None:
        """Test creating default .mdfsrc.yaml."""
        config_file = tmp_path / ".mdfsrc.yaml"
        Config.create_default_config(config_file)

        assert config_file.exists()
        content = config_file.read_text()
        assert "contexts_dir" in content
        assert "responses_dir" in content

    def test_create_default_config_creates_parent(self, tmp_path: Path) -> None:
        """Test that create_default_config creates parent directories."""
        config_file = tmp_path / "subdir" / ".mdfsrc.yaml"
        Config.create_default_config(config_file)

        assert config_file.exists()
        assert config_file.parent.exists()


class TestConfigYAMLErrors:
    """Test error handling for invalid YAML."""

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test error handling for invalid YAML syntax."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("invalid: yaml: content:\n  - bad")

        with pytest.raises(ConfigError):
            Config(config_file)

    def test_invalid_config_type(self, tmp_path: Path) -> None:
        """Test error handling when config is not a dict."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ConfigError):
            Config(config_file)

    def test_missing_pyyaml(self, tmp_path: Path, monkeypatch) -> None:
        """Test error when PyYAML is not available."""
        monkeypatch.setattr("mdfs.config.yaml", None)
        
        with pytest.raises(ConfigError, match="PyYAML"):
            Config()


class TestConfigOverrides:
    """Test command-line config overrides."""

    def test_override_contexts_dir(self, tmp_path: Path) -> None:
        """Override contexts_dir via override() method."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("contexts_dir: '.mdfs/contexts'\n")
        config = Config(config_file)
        config.override(contexts_dir="/custom/contexts")
        assert config.config_data["contexts_dir"] == "/custom/contexts"

    def test_override_responses_dir(self, tmp_path: Path) -> None:
        """Override responses_dir via override() method."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("responses_dir: '.mdfs/responses'\n")
        config = Config(config_file)
        config.override(responses_dir="/custom/responses")
        assert config.config_data["responses_dir"] == "/custom/responses"

    def test_override_multiple_params(self, tmp_path: Path) -> None:
        """Override multiple parameters at once."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "contexts_dir: '.mdfs/contexts'\nresponses_dir: '.mdfs/responses'\n"
        )
        config = Config(config_file)
        config.override(
            contexts_dir="/ctx",
            responses_dir="/resp",
        )
        assert config.config_data["contexts_dir"] == "/ctx"
        assert config.config_data["responses_dir"] == "/resp"

    def test_override_partial(self, tmp_path: Path) -> None:
        """Override only specified parameters."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "contexts_dir: '.mdfs/contexts'\nresponses_dir: '.mdfs/responses'\n"
        )
        config = Config(config_file)
        config.override(contexts_dir="/custom")
        assert config.config_data["contexts_dir"] == "/custom"
        assert config.config_data["responses_dir"] == ".mdfs/responses"

    def test_override_nonexistent_params(self) -> None:
        """Override nonexistent parameters (should add them)."""
        config = Config.__new__(Config)
        config.config_path = None
        config.config_data = {}
        config.override(contexts_dir="/ctx")
        assert config.config_data["contexts_dir"] == "/ctx"
