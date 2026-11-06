"""MDFS rules loading — .mdfs/rules/ directory with minimal frontmatter.

Rules are plain Markdown files in .mdfs/rules/. Their order is controlled
by the filesystem (file names) and can be overridden by a single
`priority` field in a minimal YAML frontmatter:

    ---
    priority: 100        # higher = earlier in the bundle (default: 0)
    alwaysApply: false   # include only with `bundle --all` (default: true)
    ---

No other frontmatter fields are defined; the rest of the file body is
included verbatim in the bundle. Files without frontmatter are always
included and keep filesystem order (backward compatible).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils import rules_dir


@dataclass
class Rule:
    """A single rule file loaded from .mdfs/rules/."""

    name: str           # file name relative to the rules directory
    priority: int       # sort priority: higher goes first
    always_apply: bool  # whether the rule is included without `--all`
    body: str           # Markdown content without frontmatter


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a minimal `key: value` YAML frontmatter from Markdown text.

    Only flat scalar `key: value` pairs are supported (no nested
    structures), which is all MDFS rules need. Inline comments
    (` # ...`) and surrounding quotes are stripped from values.

    Args:
        text: Raw file content

    Returns:
        Tuple (metadata dict, body without frontmatter)
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.split("#", 1)[0].strip().strip("'\"")
        meta[key.strip()] = value
    return meta, text[end + 4:].lstrip("\n")


def _load_rule_file(path: Path) -> Rule | None:
    """Load a single rule file.

    Args:
        path: Path to the rule file

    Returns:
        Rule instance, or None if the file is empty or unreadable
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not content.strip():
        return None
    meta, body = parse_frontmatter(content)
    if not body.strip():
        return None
    try:
        priority = int(meta.get("priority", "0").strip() or "0")
    except ValueError:
        priority = 0
    always_apply = meta.get("alwaysApply", "true").strip().lower() not in (
        "false", "no", "0", "off",
    )
    return Rule(
        name=path.name,
        priority=priority,
        always_apply=always_apply,
        body=body.strip(),
    )


def load_rules(root: str | Path, include_all: bool = False) -> list[Rule]:
    """Load rule files from <root>/.mdfs/rules/.

    Rules are sorted by descending frontmatter `priority`, ties broken
    by file name (filesystem order). Files without frontmatter get
    priority 0 and alwaysApply=true, so they are always included.

    Args:
        root: Project root directory
        include_all: Also include rules with `alwaysApply: false`
            (the `bundle --all` flag)

    Returns:
        List of Rule objects in bundle order
    """
    rdir = rules_dir(Path(root))
    if not rdir.is_dir():
        return []
    loaded: list[Rule] = []
    for path in sorted(rdir.glob("*.md")):
        if not path.is_file():
            continue
        rule = _load_rule_file(path)
        if rule is None:
            continue
        if not include_all and not rule.always_apply:
            continue
        loaded.append(rule)
    loaded.sort(key=lambda r: (-r.priority, r.name))
    return loaded


def render_rules(root: str | Path, include_all: bool = False) -> str:
    """Render .mdfs/rules/ content for inclusion into a bundle.

    Rule bodies are joined with blank lines; frontmatter is stripped.

    Args:
        root: Project root directory
        include_all: Also include rules with `alwaysApply: false`

    Returns:
        Concatenated rule bodies (empty string if no rules found)
    """
    return "\n\n".join(r.body for r in load_rules(root, include_all=include_all))
