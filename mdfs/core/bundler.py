"""MDFS bundler — collects project files into a single Markdown document."""

from __future__ import annotations

import re
from pathlib import Path

from ..default_system_prompt import (
    DEFAULT_SYSTEM_PROMPT,
    PREAMBLE_TEXT,
    QUICK_REMINDER_TEXT,
)


def _detect_max_fence(content: str) -> int:
    max_len = 0
    for match in re.finditer(r"^(`{3,})", content, re.MULTILINE):
        max_len = max(max_len, len(match.group(1)))
    return max_len


def _lang_for_ext(path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".sh": "bash", ".bash": "bash", ".zsh": "zsh",
        ".rb": "ruby", ".rs": "rust", ".go": "go",
        ".java": "java", ".c": "c", ".cpp": "cpp",
        ".h": "c", ".hpp": "cpp", ".css": "css",
        ".html": "html", ".xml": "xml", ".json": "json",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".ini": "ini", ".cfg": "ini", ".sql": "sql",
        ".md": "markdown", ".txt": "text",
        ".dockerfile": "dockerfile", ".mk": "makefile",
    }
    name = Path(path).name.lower()
    if name == "makefile":
        return "makefile"
    if name == "dockerfile":
        return "dockerfile"
    return ext_map.get(Path(path).suffix.lower(), "text")


def _generate_table_of_contents(file_paths: list[str]) -> str:
    """Generate a table of contents from file paths."""
    if not file_paths:
        return ""
    
    lines = ["## Содержание\n"]
    for rel_path in file_paths:
        # Create anchor from filename (remove extension, replace special chars)
        filename = Path(rel_path).name
        anchor = filename.lower().replace(".", "")
        lines.append(f"- [{rel_path}](#{anchor})")
    lines.append("")
    return "\n".join(lines)


def bundle(
    base_dir: str | Path,
    file_paths: list[str],
    system_prompt: str | None = None,
    heading_level: int = 3,
    include_preamble: bool = True,
) -> str:
    base = Path(base_dir)
    parts: list[str] = []

    # Add preamble if requested
    if include_preamble:
        parts.append(PREAMBLE_TEXT.rstrip())
        parts.append("")
        parts.append("--- START OF RULES ---")
        parts.append("")
        parts.append(DEFAULT_SYSTEM_PROMPT.rstrip())
        parts.append("")
        parts.append("--- END OF RULES ---")
        parts.append("")
        parts.append("**Now process the following document. Remember: do not echo the rules. Start directly with the requested output (e.g., file contents or confirmations).**")
        parts.append("")
        parts.append("---")
        parts.append("")
        # Add table of contents
        toc = _generate_table_of_contents(file_paths)
        if toc:
            parts.append(toc)
    elif system_prompt:
        # Legacy behavior: if system_prompt is provided and preamble is disabled
        parts.append(system_prompt.rstrip())
        parts.append("")
        parts.append("---")
        parts.append("")

    heading_prefix = "#" * heading_level

    for rel_path in file_paths:
        full_path = base / rel_path
        
        # Add quick reminder before each file
        if include_preamble:
            parts.append(QUICK_REMINDER_TEXT.rstrip())
            parts.append("")
        
        if not full_path.is_file():
            parts.append(f"{heading_prefix} `{rel_path}`")
            parts.append("")
            parts.append(f"⚠️ File not found: {rel_path}")
            parts.append("")
            continue

        content = full_path.read_text(encoding="utf-8")
        lang = _lang_for_ext(rel_path)

        inner_max = _detect_max_fence(content)
        fence_len = max(3, inner_max + 1)
        fence = "`" * fence_len

        parts.append(f"{heading_prefix} `{rel_path}`")
        parts.append("")
        parts.append(f"<!-- file: \"{rel_path}\" -->")
        parts.append(f"{fence}{lang}")
        if content.endswith("\n"):
            content = content[:-1]
        parts.append(content)
        parts.append(fence)
        parts.append("")

    return "\n".join(parts)
