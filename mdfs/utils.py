"""MDFS utility functions for CLI operations."""

from __future__ import annotations

import datetime
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def timestamp() -> str:
    """Generate a timestamp string in format YYYY-MM-DD_HHMMSS."""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def sanitize_label(label: str) -> str:
    """Sanitize a label for use in filenames.
    
    Converts to lowercase, replaces spaces with underscores,
    removes invalid characters, and collapses multiple underscores.
    """
    label = label.strip().lower()
    label = label.replace(" ", "_")
    label = re.sub(r"[^\w\-]", "", label)
    label = re.sub(r"_+", "_", label)
    label = label.strip("_")
    return label


def make_filename(label: str | None) -> str:
    """Generate a filename with timestamp and optional label.
    
    Args:
        label: Optional human-readable label for the filename
        
    Returns:
        Filename in format TIMESTAMP__LABEL.md or TIMESTAMP.md
    """
    ts = timestamp()
    if label:
        safe = sanitize_label(label)
        if safe:
            return f"{ts}__{safe}.md"
    return f"{ts}.md"


def get_clipboard() -> str:
    """Get clipboard content from the system.
    
    Supports macOS (pbpaste), Linux (wl-paste, xclip, xsel), and more.
    
    Returns:
        Clipboard content as string
        
    Raises:
        SystemExit: If clipboard is not available on the system
    """
    system = platform.system()

    if system == "Darwin":
        if shutil.which("pbpaste"):
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, check=True,
            )
            return result.stdout if result.stdout else ""
        print("Error: pbpaste not found on macOS.", file=sys.stderr)
        sys.exit(1)

    if system == "Linux":
        # Try Wayland first (wl-paste), then X11 tools (xclip, xsel)
        commands = [
            ("wl-paste", ["wl-paste", "--no-newline"]),
            ("xclip", ["xclip", "-selection", "clipboard", "-o"]),
            ("xsel", ["xsel", "--clipboard", "--output"]),
        ]

        for name, cmd in commands:
            if shutil.which(name):
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0:
                        return result.stdout if result.stdout else ""
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue

        print(
            "Error: install wl-paste (Wayland) or xclip/xsel (X11) for clipboard support.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Error: clipboard not supported on {system}.", file=sys.stderr)
    sys.exit(1)


def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard.
    
    Supports macOS (pbcopy), Linux (wl-copy, xclip, xsel), and more.
    
    Args:
        text: Text to copy to clipboard
        
    Raises:
        SystemExit: If clipboard is not available on the system
    """
    system = platform.system()

    if system == "Darwin":
        if shutil.which("pbcopy"):
            subprocess.run(
                ["pbcopy"], input=text, text=True, check=True,
            )
            return
        print("Error: pbcopy not found on macOS.", file=sys.stderr)
        sys.exit(1)

    if system == "Linux":
        # Try Wayland first (wl-copy), then X11 tools (xclip, xsel)
        commands = [
            ("wl-copy", ["wl-copy"]),
            ("xclip", ["xclip", "-selection", "clipboard"]),
            ("xsel", ["xsel", "--clipboard", "--input"]),
        ]

        for name, cmd in commands:
            if shutil.which(name):
                try:
                    subprocess.run(
                        cmd, input=text, text=True, timeout=5, check=True,
                    )
                    return
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue

        print(
            "Error: install wl-copy (Wayland) or xclip/xsel (X11) for clipboard support.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Error: clipboard not supported on {system}.", file=sys.stderr)
    sys.exit(1)


def find_mdfs_root(start: str | Path | None = None) -> Path:
    """Find the root directory containing .mdfs folder.
    
    Searches upward from the starting directory until .mdfs is found.
    
    Args:
        start: Starting directory (default: current working directory)
        
    Returns:
        Path to the project root containing .mdfs
        
    Raises:
        SystemExit: If .mdfs directory is not found
    """
    current = Path(start) if start else Path.cwd()
    current = current.resolve()
    while True:
        if (current / ".mdfs").is_dir():
            return current
        parent = current.parent
        if parent == current:
            print(
                "Error: .mdfs directory not found. Run `mdfs init` first.",
                file=sys.stderr,
            )
            sys.exit(1)
        current = parent


def mdfs_dir(root: Path) -> Path:
    """Get the .mdfs directory path."""
    return root / ".mdfs"


def rules_dir(root: Path) -> Path:
    """Get the rules directory path (.mdfs/rules)."""
    return mdfs_dir(root) / "rules"


def contexts_dir(root: Path) -> Path:
    """Get the contexts directory path (.mdfs/contexts)."""
    return mdfs_dir(root) / "contexts"


def responses_dir(root: Path) -> Path:
    """Get the responses directory path (.mdfs/responses)."""
    return mdfs_dir(root) / "responses"


def print_actions(actions: list) -> None:
    """Print extraction actions in a formatted way.
    
    Args:
        actions: List of Action objects with action type and path
    """
    for action in actions:
        icon = {"write": "📄", "patch": "🩹", "error": "❌"}.get(
            action.action, "?",
        )
        detail = f" — {action.detail}" if action.detail else ""
        print(f"  {icon} {action.action:6s} {action.path}{detail}")
