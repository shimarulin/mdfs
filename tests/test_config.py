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
            "responses_dir: custom_responses\n"
            "prompt_extensions:\n"
            "  - docs/prompts\n",
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
        # Without .mdfs/rules/ directory, extensions should be empty
        assert config.get_prompt_extensions_dirs(tmp_path) == []


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


class TestPromptExtensions:
    """Test prompt extensions loading."""

    def test_load_extensions_empty(self, tmp_path: Path) -> None:
        """Test loading extensions when none are configured."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("# No extensions\n")

        config = Config(config_file)
        # Without .mdfs/rules/ directory, should return empty
        assert config.load_prompt_extensions(tmp_path) == ""

    def test_load_extensions_multiple_dirs(self, tmp_path: Path) -> None:
        """Test loading extensions from multiple directories."""
        ext_dir1 = tmp_path / "ext1"
        ext_dir2 = tmp_path / "ext2"
        ext_dir1.mkdir()
        ext_dir2.mkdir()

        # Create extension files
        (ext_dir1 / "extension1.md").write_text("Extension 1 content")
        (ext_dir2 / "extension2.md").write_text("Extension 2 content")

        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "prompt_extensions:\n"
            "  - ext1\n"
            "  - ext2\n",
        )

        config = Config(config_file)
        result = config.load_prompt_extensions(tmp_path)
        assert "Extension 1 content" in result
        assert "Extension 2 content" in result

    def test_load_extensions_sorted(self, tmp_path: Path) -> None:
        """Test that extensions are loaded in alphabetical order."""
        ext_dir = tmp_path / "extensions"
        ext_dir.mkdir()

        # Create files in non-alphabetical order
        (ext_dir / "z_last.md").write_text("Last")
        (ext_dir / "a_first.md").write_text("First")
        (ext_dir / "m_middle.md").write_text("Middle")

        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions:\n  - extensions\n")

        config = Config(config_file)
        result = config.load_prompt_extensions(tmp_path)
        
        # Check order
        first_pos = result.find("First")
        middle_pos = result.find("Middle")
        last_pos = result.find("Last")
        assert first_pos < middle_pos < last_pos

    def test_load_extensions_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test loading from non-existent directory (should be skipped)."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text(
            "prompt_extensions:\n"
            "  - /nonexistent/path\n",
        )

        config = Config(config_file)
        # Should not raise error, just return empty
        result = config.load_prompt_extensions(tmp_path)
        assert result == ""


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
        assert "prompt_extensions" in content

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

    def test_override_prompt_extensions_dirs(self, tmp_path: Path) -> None:
        """Override prompt_extensions via override() method."""
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions: []\n")
        config = Config(config_file)
        config.override(prompt_extensions_dirs=[".mdfs/ext1", ".mdfs/ext2"])
        assert config.config_data["prompt_extensions"] == [".mdfs/ext1", ".mdfs/ext2"]

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
            prompt_extensions_dirs=[".ext"],
        )
        assert config.config_data["contexts_dir"] == "/ctx"
        assert config.config_data["responses_dir"] == "/resp"
        assert config.config_data["prompt_extensions"] == [".ext"]

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


class TestDefaultRulesDir:
    """Test built-in .mdfs/rules/ directory handling."""

    def test_rules_dir_loaded_by_default(self, tmp_path: Path) -> None:
        """Test that .mdfs/rules/ is automatically loaded if it exists."""
        # Create .mdfs/rules/ directory
        rules_dir = tmp_path / ".mdfs" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "system_prompt.md").write_text("System prompt content")

        # Config without explicit prompt_extensions
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("# No extensions configured\n")

        config = Config(config_file)
        dirs = config.get_prompt_extensions_dirs(tmp_path)
        
        # Should include .mdfs/rules/
        assert len(dirs) == 1
        assert dirs[0] == rules_dir.resolve()

    def test_rules_dir_cumulative_with_config(self, tmp_path: Path) -> None:
        """Test that .mdfs/rules/ is combined with config extensions."""
        # Create .mdfs/rules/ directory
        rules_dir = tmp_path / ".mdfs" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "builtin.md").write_text("Built-in prompt")

        # Create custom extension directory
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        (custom_dir / "custom.md").write_text("Custom prompt")

        # Config with custom extensions
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions:\n  - custom\n")

        config = Config(config_file)
        dirs = config.get_prompt_extensions_dirs(tmp_path)
        
        # Should include both .mdfs/rules/ first, then custom
        assert len(dirs) == 2
        assert dirs[0] == rules_dir.resolve()
        assert dirs[1] == custom_dir.resolve()

    def test_load_extensions_with_rules_dir(self, tmp_path: Path) -> None:
        """Test loading extensions includes .mdfs/rules/ content."""
        # Create .mdfs/rules/ directory
        rules_dir = tmp_path / ".mdfs" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "builtin1.md").write_text("Built-in content 1")
        (rules_dir / "builtin2.md").write_text("Built-in content 2")

        # Create custom extension directory
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        (custom_dir / "custom.md").write_text("Custom content")

        # Config with custom extensions
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions:\n  - custom\n")

        config = Config(config_file)
        result = config.load_prompt_extensions(tmp_path)
        
        # Should contain content from both built-in and custom
        assert "Built-in content 1" in result
        assert "Built-in content 2" in result
        assert "Custom content" in result

    def test_rules_dir_not_included_if_missing(self, tmp_path: Path) -> None:
        """Test that missing .mdfs/rules/ doesn't cause errors."""
        # Don't create .mdfs/rules/ directory
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions: []\n")

        config = Config(config_file)
        dirs = config.get_prompt_extensions_dirs(tmp_path)
        
        # Should be empty since no config extensions and rules dir doesn't exist
        assert dirs == []

    def test_rules_dir_no_duplicates(self, tmp_path: Path) -> None:
        """Test that .mdfs/rules/ appears only once even if configured."""
        # Create .mdfs/rules/ directory
        rules_dir = tmp_path / ".mdfs" / "rules"
        rules_dir.mkdir(parents=True)

        # Try to configure .mdfs/rules/ explicitly
        config_file = tmp_path / ".mdfsrc.yaml"
        config_file.write_text("prompt_extensions:\n  - .mdfs/rules\n")

        config = Config(config_file)
        dirs = config.get_prompt_extensions_dirs(tmp_path)
        
        # Should appear only once
        rules_resolved = rules_dir.resolve()
        count = sum(1 for d in dirs if d == rules_resolved)
        assert count == 1
