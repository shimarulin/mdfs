"""Utilities for working with .gitignore files."""

from __future__ import annotations

import mimetypes
from pathlib import Path

try:
    import pathspec
except ImportError:
    pathspec = None


class GitignoreFilter:
    """Filter for checking if paths should be ignored based on .gitignore rules."""

    def __init__(self, base_dir: str | Path):
        """Initialize GitignoreFilter.

        Args:
            base_dir: Base directory to search for .gitignore files
        """
        self.base_dir = Path(base_dir)
        self.spec = None
        self._load_gitignore()

    def _load_gitignore(self) -> None:
        """Load and compile .gitignore patterns."""
        gitignore_path = self.base_dir / ".gitignore"

        if not gitignore_path.exists():
            return

        if pathspec is None:
            # Fallback: simple string matching if pathspec not available
            self.patterns = set()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.patterns.add(line)
            return

        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                patterns = [line.rstrip("\n\r") for line in f if line.strip() and not line.startswith("#")]
            self.spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception:
            # If pathspec fails to parse, ignore
            self.spec = None

    def should_ignore(self, path: str | Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check (relative to base_dir)

        Returns:
            True if path should be ignored, False otherwise
        """
        path = Path(path)

        # Make relative to base_dir if absolute
        try:
            if path.is_absolute():
                path = path.relative_to(self.base_dir)
        except ValueError:
            pass

        if self.spec is not None:
            return self.spec.match_file(str(path))

        # Fallback: simple string matching
        if not hasattr(self, "patterns"):
            return False

        path_str = str(path).replace("\\", "/")
        for pattern in self.patterns:
            if "*" in pattern:
                # Simple wildcard matching
                import fnmatch

                if fnmatch.fnmatch(path_str, pattern):
                    return True
            else:
                if path_str == pattern or path_str.startswith(pattern + "/"):
                    return True

        return False


def is_binary_file(path: str | Path) -> bool:
    """Check if a file is binary.

    Args:
        path: Path to file

    Returns:
        True if file is binary, False if text
    """
    path = Path(path)

    # Check by extension first
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type and mime_type.startswith("text"):
        return False

    # Common text extensions
    text_extensions = {
        ".txt",
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".markdown",
        ".html",
        ".css",
        ".xml",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".go",
        ".rs",
        ".rb",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".sql",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".lock",
        ".gitignore",
        ".dockerfile",
        ".mk",
    }

    if path.suffix.lower() in text_extensions:
        return False

    # Check by reading file header (magic bytes)
    try:
        with open(path, "rb") as f:
            header = f.read(512)

        # Check for null bytes (binary indicator)
        if b"\x00" in header:
            return True

        # Try to decode as UTF-8
        try:
            header.decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True
    except Exception:
        # If we can't determine, assume binary
        return True
