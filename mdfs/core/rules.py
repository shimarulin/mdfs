"""MDFS rules loading — .mdfs/rules/ directory, selected by filename globs.

Rules are plain Markdown files in .mdfs/rules/. There is no frontmatter:
selection is fully controlled by filename globs, and order is the
filename order — use numeric prefixes (`00-system.md`, `10-style.md`)
to pin the sequence.

Two glob sources are combined (union):
- config `rules_always` (default: `00-*` — only the file output format
  rule) — included in every bundle;
- CLI `bundle --rules` (repeatable/comma-separated, `*` = everything) —
  extra rules for a single bundle.

The file output format rule (`00-file-output-format.md`) ships with the
package: `mdfs init` writes it into the project, and if it is absent
from the rules directory, the built-in copy is used in the bundle.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

# The built-in file output format rule: written into a project by
# `mdfs init`, used as a fallback when absent from the rules directory.
DEFAULT_RULE_NAME = "00-file-output-format.md"

# Packaged copy of the rule — the single source of truth (a real file
# inside the package, shipped via package-data; no duplicate constant).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Default config selection (`rules_always`): only the file output
# format rule — i.e. everything with the reserved `00-` prefix.
DEFAULT_RULE_GLOB = "00-*"

# Name of the built-in rule inside the bundle when the file is absent
# from the rules directory (no .md suffix — it is not a file on disk).
BUILTIN_RULE_NAME = "default-file-output-format"


@dataclass
class Rule:
    """A single rule file loaded from the rules directory."""

    name: str  # file name (or the built-in rule name)
    body: str  # Markdown content


def built_in_rule() -> Rule:
    """The packaged file output format rule (fallback / `mdfs init` template)."""
    body = (DATA_DIR / DEFAULT_RULE_NAME).read_text(encoding="utf-8")
    return Rule(name=BUILTIN_RULE_NAME, body=body.rstrip())


def load_rules(rules_path: str | Path, patterns: list[str]) -> list[Rule]:
    """Load rule files from a rules directory, selected by filename globs.

    Files are loaded in filename order; a file is included when its name
    matches ANY of the glob `patterns` (fnmatch syntax, e.g. `00-*`,
    `1*`, `*`). Non-markdown files and empty files are skipped.

    Args:
        rules_path: Rules directory (typically `Config.get_rules_dir()`)
        patterns: Filename glob patterns (empty list selects nothing)

    Returns:
        List of Rule objects in bundle order
    """
    rdir = Path(rules_path)
    if not rdir.is_dir() or not patterns:
        return []
    loaded: list[Rule] = []
    for path in sorted(rdir.glob("*.md")):
        if not path.is_file():
            continue
        if not any(fnmatch(path.name, pat) for pat in patterns):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not body.strip():
            continue
        loaded.append(Rule(name=path.name, body=body.strip()))
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


def render_rules(rules: list[Rule]) -> str:
    """Render rule blocks for inclusion into a bundle.

    Each rule is framed by `mdfs:rule` start/end HTML-comment markers
    (same idiom as the `<!-- file: ... -->` markers); rules are joined
    with blank lines.

    Args:
        rules: Rules in bundle order

    Returns:
        Concatenated rule blocks (empty string if the list is empty)
    """
    return "\n\n".join(render_rule(r) for r in rules)


def resolve_rules(rules_path: str | Path, patterns: list[str]) -> str:
    """Resolve the rules text for a bundle.

    Loads the rules selected by `patterns` from the rules directory and
    guarantees the file output format rule is present: when
    `00-file-output-format.md` is absent from the directory, the built-in
    packaged copy is prepended (first position, like the reserved `00-`
    prefix).

    Args:
        rules_path: Rules directory (typically `Config.get_rules_dir()`)
        patterns: Combined glob patterns (config `rules_always` + CLI)

    Returns:
        Rendered rules text (empty string if nothing is selected)
    """
    rules = load_rules(rules_path, patterns)
    if not Path(rules_path, DEFAULT_RULE_NAME).is_file():
        rules.insert(0, built_in_rule())
    return render_rules(rules)
