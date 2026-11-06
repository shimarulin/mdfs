"""MDFS configuration management — loads and manages .mdfsrc.yaml settings."""

from __future__ import annotations

import sys
from pathlib import Path

from .core.rules import DEFAULT_RULE_GLOB

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
    contexts, responses and rules, and select which rules are always
    included in bundles (see mdfs/core/rules.py).
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

    def get_rules_dir(self, base_dir: Path | None = None) -> Path:
        """Get the rules directory path.

        Args:
            base_dir: Base directory for relative paths (defaults to config directory)

        Returns:
            Path to rules directory (default: ``.mdfs/rules``)
        """
        if base_dir is None:
            base_dir = self.config_path.parent if self.config_path else Path.cwd()

        dir_path = self.config_data.get("rules_dir", ".mdfs/rules")
        path = Path(dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path.resolve()

    def get_rules_always(self) -> list[str]:
        """Get the glob patterns of rules included in every bundle.

        Returns:
            List of filename glob patterns. Default: ``["00-*"]`` — only
            the file output format rule (see mdfs/core/rules.py)
        """
        value = self.config_data.get("rules_always", [DEFAULT_RULE_GLOB])
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value]
        raise ConfigError(
            "'rules_always' must be a glob string or a list of glob strings, "
            f"got {type(value).__name__}"
        )

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
        rules_dir: str | None = None,
        rules_always: list[str] | None = None,
    ) -> None:
        """Override configuration with command-line arguments.
        
        Command-line arguments take precedence over config file values.
        
        Args:
            contexts_dir: Override contexts directory path
            responses_dir: Override responses directory path
            rules_dir: Override rules directory path
            rules_always: Override rules-always glob patterns
        """
        if contexts_dir is not None:
            self.config_data["contexts_dir"] = contexts_dir
        if responses_dir is not None:
            self.config_data["responses_dir"] = responses_dir
        if rules_dir is not None:
            self.config_data["rules_dir"] = rules_dir
        if rules_always is not None:
            self.config_data["rules_always"] = rules_always

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

# Directory with rule files (*.md)
rules_dir: ".mdfs/rules"

# Rules included in every bundle (filename globs, e.g. "00-*", "1*").
# Default: only the file output format rule. Use ["*"] for all rules.
rules_always:
  - "00-*"
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
