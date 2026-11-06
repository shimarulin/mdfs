"""MDFS rules loading — .mdfs/rules/ directory with minimal frontmatter.

Rules are plain Markdown files in .mdfs/rules/. Their order is fully
controlled by the filesystem (file names) — use numeric prefixes
(`00-system.md`, `10-style.md`) to pin the sequence.

The only frontmatter field defined is:

    ---
    alwaysApply: false   # include only with `bundle --all` (default: true)
    ---

No other frontmatter fields are defined; the rest of the file body is
included verbatim in the bundle. Files without frontmatter are always
included (backward compatible).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils import rules_dir


@dataclass
class Rule:
    """A single rule file loaded from .mdfs/rules/."""

    name: str           # file name relative to the rules directory
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
    always_apply = meta.get("alwaysApply", "true").strip().lower() not in (
        "false", "no", "0", "off",
    )
    return Rule(
        name=path.name,
        always_apply=always_apply,
        body=body.strip(),
    )


def load_rules(root: str | Path, include_all: bool = False) -> list[Rule]:
    """Load rule files from <root>/.mdfs/rules/ in filename order.

    Use numeric file-name prefixes (`00-system.md`, `10-style.md`) to
    control bundle order. Files without frontmatter get alwaysApply=true,
    so they are always included.

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
    return loaded


def render_rule(rule: Rule) -> str:
    """Render a single rule wrapped in HTML-comment markers.

    Args:
        rule: Rule to render

    Returns:
        Rule body framed by `<!-- mdfs:rule:start name="..." -->` and
        `<!-- mdfs:rule:end name="..." -->` markers
    """
    return (
        f'<!-- mdfs:rule:start name="{rule.name}" -->\n'
        f"{rule.body}\n"
        f'<!-- mdfs:rule:end name="{rule.name}" -->'
    )


def render_rules(root: str | Path, include_all: bool = False) -> str:
    """Render .mdfs/rules/ content for inclusion into a bundle.

    Each rule is framed by `mdfs:rule` start/end HTML-comment markers
    (same idiom as the `<!-- file: ... -->` markers); rules are joined
    with blank lines and frontmatter is stripped.

    Args:
        root: Project root directory
        include_all: Also include rules with `alwaysApply: false`

    Returns:
        Concatenated rule blocks (empty string if no rules found)
    """
    return "\n\n".join(
        render_rule(r) for r in load_rules(root, include_all=include_all)
    )
