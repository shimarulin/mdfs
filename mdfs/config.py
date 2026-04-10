"""MDFS configuration management — loads and manages .mdfsrc.yaml settings."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


class ConfigError(Exception):
    """Raised when configuration loading or parsing fails."""

    pass


class Config:
    """Manages MDFS configuration from .mdfsrc.yaml files.
    
    Searches for .mdfsrc.yaml starting from current directory and moving up
    to the filesystem root. Configuration can override default paths for
    contexts, responses, and define directories for system prompt extensions.
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize Config.
        
        Args:
            config_path: Explicit path to .mdfsrc.yaml file. If not provided,
                        searches from current directory up to root.
                        
        Raises:
            ConfigError: If YAML parsing fails or required dependencies missing
        """
        if yaml is None:
            raise ConfigError(
                "PyYAML is required for configuration support. "
                "Install with: pip install pyyaml"
            )

        self.config_path: Path | None = None
        self.config_data: dict = {}

        if config_path:
            self.config_path = Path(config_path).resolve()
            if self.config_path.exists():
                self._load_yaml(self.config_path)
        else:
            # Search for .mdfsrc.yaml from current directory up to root
            self.config_path = self._find_config()
            if self.config_path:
                self._load_yaml(self.config_path)

    def _find_config(self) -> Path | None:
        """Find .mdfsrc.yaml by searching upward from current directory.
        
        Returns:
            Path to .mdfsrc.yaml if found, None otherwise
        """
        current = Path.cwd().resolve()
        while True:
            config_file = current / ".mdfsrc.yaml"
            if config_file.exists():
                return config_file
            
            parent = current.parent
            if parent == current:
                # Reached filesystem root
                return None
            current = parent

    def _load_yaml(self, path: Path) -> None:
        """Load and parse YAML configuration file.
        
        Args:
            path: Path to .mdfsrc.yaml file
            
        Raises:
            ConfigError: If file cannot be read or YAML is invalid
        """
        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise ConfigError(
                    f"Configuration file must contain a YAML dictionary, "
                    f"got {type(data).__name__}"
                )
            self.config_data = data
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse {path}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read {path}: {e}") from e

    def get_contexts_dir(self, base_dir: Path | None = None) -> Path:
        """Get the contexts directory path.
        
        Args:
            base_dir: Base directory for relative paths (defaults to config directory)
            
        Returns:
            Path to contexts directory
        """
        if base_dir is None:
            base_dir = self.config_path.parent if self.config_path else Path.cwd()

        dir_path = self.config_data.get("contexts_dir", ".mdfs/contexts")
        path = Path(dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path.resolve()

    def get_responses_dir(self, base_dir: Path | None = None) -> Path:
        """Get the responses directory path.
        
        Args:
            base_dir: Base directory for relative paths (defaults to config directory)
            
        Returns:
            Path to responses directory
        """
        if base_dir is None:
            base_dir = self.config_path.parent if self.config_path else Path.cwd()

        dir_path = self.config_data.get("responses_dir", ".mdfs/responses")
        path = Path(dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path.resolve()

    def get_prompt_extensions_dirs(
        self, base_dir: Path | None = None,
    ) -> list[Path]:
        """Get directories containing system prompt extensions.
        
        Returns list of directory paths that contain markdown files to be
        appended to the system prompt. Directories are resolved relative to
        the configuration file directory.
        
        By default, includes .mdfs/rules/ if it exists (built-in extensions).
        Configuration and command-line overrides are appended (cumulative).
        
        Args:
            base_dir: Base directory for relative paths (defaults to config directory)
            
        Returns:
            List of Path objects for prompt extension directories
        """
        if base_dir is None:
            base_dir = self.config_path.parent if self.config_path else Path.cwd()

        result: list[Path] = []
        seen: set[Path] = set()

        # Step 1: Add built-in .mdfs/rules/ directory (always first)
        default_rules_dir = base_dir / ".mdfs" / "rules"
        if default_rules_dir.exists():
            resolved = default_rules_dir.resolve()
            if resolved not in seen:
                result.append(resolved)
                seen.add(resolved)

        # Step 2: Add extensions from configuration file
        extensions_config = self.config_data.get("prompt_extensions", [])
        if extensions_config:
            if not isinstance(extensions_config, list):
                extensions_config = [extensions_config]

            for ext_dir in extensions_config:
                path = Path(ext_dir)
                if not path.is_absolute():
                    path = base_dir / path
                resolved = path.resolve()
                if resolved not in seen:
                    result.append(resolved)
                    seen.add(resolved)

        return result

    def load_prompt_extensions(
        self, base_dir: Path | None = None,
    ) -> str:
        """Load and concatenate all markdown files from extension directories.
        
        Reads all .md files from directories specified in prompt_extensions config,
        sorted alphabetically within each directory. Files are joined with blank lines.
        
        Args:
            base_dir: Base directory for relative paths
            
        Returns:
            Concatenated content of all extension files (empty string if none found)
        """
        dirs = self.get_prompt_extensions_dirs(base_dir)
        if not dirs:
            return ""

        extensions: list[str] = []

        for ext_dir in dirs:
            if not ext_dir.exists():
                continue

            # Collect all .md files in this directory
            md_files = sorted(ext_dir.glob("*.md"))
            for md_file in md_files:
                if md_file.is_file():
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        if content.strip():
                            extensions.append(content)
                    except OSError:
                        # Skip files that can't be read
                        continue

        return "\n\n".join(extensions) if extensions else ""

    def is_configured(self) -> bool:
        """Check if a configuration file was found.
        
        Returns:
            True if .mdfsrc.yaml exists and was loaded
        """
        return self.config_path is not None and self.config_path.exists()

    def override(
        self,
        contexts_dir: str | None = None,
        responses_dir: str | None = None,
        prompt_extensions_dirs: list[str] | None = None,
    ) -> None:
        """Override configuration with command-line arguments.
        
        Command-line arguments take precedence over config file values.
        
        Args:
            contexts_dir: Override contexts directory path
            responses_dir: Override responses directory path
            prompt_extensions_dirs: Additional or replacement extension directories
        """
        if contexts_dir is not None:
            self.config_data["contexts_dir"] = contexts_dir
        if responses_dir is not None:
            self.config_data["responses_dir"] = responses_dir
        if prompt_extensions_dirs is not None:
            self.config_data["prompt_extensions"] = prompt_extensions_dirs

    @staticmethod
    def create_default_config(path: Path) -> None:
        """Create a default .mdfsrc.yaml file.
        
        Args:
            path: Path where to create the config file
        """
        content = """# MDFS Configuration
# This file configures the MDFS tool

# Directory for bundled context files
contexts_dir: ".mdfs/contexts"

# Directory for LLM response files
responses_dir: ".mdfs/responses"

# Directories containing markdown files to append to system prompt
# Files are loaded in order, sorted alphabetically within each directory
prompt_extensions: []
  # Example:
  # - ".mdfs/extensions"
  # - "docs/mdfs-prompts"
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
