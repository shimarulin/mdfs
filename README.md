# MDFS — Markdown FileSystem

Bundle project files into a single Markdown document for LLM chat,
then extract files and apply patches from the LLM response.

```
┌──────────────┐     bundle      ┌──────────────┐
│  Project     │ ──────────────→ │  context.md  │──→ LLM chat
│  files       │                 │  (single     │    (attach as file)
│              │                 │   document)  │
│  src/app.py  │     extract     │              │
│  src/lib.py  │ ←────────────── │  response.md │←── LLM output
│  docs/api.md │                 │  (from       │    (copy-paste)
└──────────────┘                 │   clipboard) │
                                 └──────────────┘
```

## Why

LLM chat interfaces often limit file attachments (e.g. 2 files).
MDFS solves this by packing multiple files into one Markdown document
with special markers, so the LLM can read and produce them correctly.

**Key features:**

- **Bundle** any number of project files into a single `.md`
- **Extract** files from LLM responses back to disk
- **Fuzzy patch** — apply unified diffs even when line numbers are wrong
  (LLMs are notoriously bad at counting lines)
- **Clipboard integration** — paste LLM response directly from clipboard
- **Chronological history** — contexts and responses are timestamped
- **Zero dependencies** — Python 3.10+ stdlib only
- **Shell completions** — zsh and bash

## Installation

### Option A: pip install (recommended)

```bash
pip install git+https://github.com/YOUR_USER/mdfs.git
```

This gives you the `mdfs` command globally.

### Option B: git submodule (for project-local tools)

```bash
cd your-project
git submodule add https://github.com/YOUR_USER/mdfs.git tools/mdfs
source tools/mdfs/setup.sh --install
```

### Option C: git clone + activate

```bash
git clone https://github.com/YOUR_USER/mdfs.git ~/.local/share/mdfs
source ~/.local/share/mdfs/setup.sh --install
```

### Option D: just source it

```bash
git clone https://github.com/YOUR_USER/mdfs.git /path/to/mdfs
source /path/to/mdfs/setup.sh   # current session only
```

## Quick start

```bash
# 1. Initialize in your project
cd your-project
mdfs init

# 2. Bundle files for LLM
mdfs bundle -f src/app.py src/lib.py docs/api.md -l "add auth module"
#   📦 Context saved: .mdfs/contexts/2026-04-04_143022__add_auth_module.md

# 3. Attach to LLM chat:
#    📎 Slot 1: PROJECT.md
#    📎 Slot 2: .mdfs/contexts/2026-04-04_143022__add_auth_module.md
#    📝 "Implement authentication module..."

# 4. Copy LLM response to clipboard, then:
mdfs paste -l "add auth module" --extract
#   📋 Response saved: .mdfs/responses/2026-04-04_144500__add_auth_module.md
#      3 file(s), 1 patch(es) detected
#   Extracting...
#   📄 write  src/auth.py
#   📄 write  tests/test_auth.py
#   🩹 patch  src/app.py
#   📄 write  docs/auth.md

# 5. Review and commit
git diff
python -m pytest
git add -A && git commit -m "Add auth module"

# 6. View history
mdfs log
#   📦 context   2026-04-04_143022__add_auth_module
#   📋 response  2026-04-04_144500__add_auth_module
```

## Commands

### `mdfs init`

Create `.mdfs/` directory structure in the current project.

```bash
mdfs init
mdfs init -d /path/to/project
```

Creates:
```
.mdfs/
├── .gitignore          # ignores contexts/ and responses/
├── rules/
│   └── mdfs-system.md  # LLM system prompt (auto-created)
├── contexts/           # bundled files for LLM
└── responses/          # LLM responses
```

### `mdfs bundle`

Pack project files into a single Markdown document.

```bash
mdfs bundle -f file1.py file2.py ...   # paths relative to project root
mdfs bundle -f src/*.py -l "my label"  # with label
mdfs bundle -f src/*.py -o custom.md   # custom output path
mdfs bundle -f src/*.py -s prompt.md   # custom system prompt
```

| Flag | Description |
|------|-------------|
| `-f, --files` | Files to include (required) |
| `-l, --label` | Human-readable label for filename |
| `-s, --system-prompt` | Custom system prompt file |
| `-o, --output` | Custom output path (default: `.mdfs/contexts/<timestamp>.md`) |

### `mdfs paste`

Save clipboard content as a response file.

```bash
mdfs paste -l "my label"              # save only
mdfs paste -l "my label" --extract    # save + extract files + apply patches
mdfs paste -l "my label" -x --dry-run # preview without writing
```

| Flag | Description |
|------|-------------|
| `-l, --label` | Human-readable label for filename |
| `-x, --extract` | Also extract files and apply patches |
| `--dry-run` | Show what would happen without writing |

### `mdfs extract`

Extract files and apply patches from any Markdown file.

```bash
mdfs extract -i response.md
mdfs extract -i response.md --dry-run
```

### `mdfs log`

Show chronological history of contexts and responses.

```bash
mdfs log
```

## File format (MDFS markers)

MDFS uses HTML comments as markers inside Markdown:

### Full file

````markdown
### `path/to/file.ext`

Optional description.

<!-- file: path/to/file.ext -->
```python
print("hello")
```
````

### Patch (unified diff)

````markdown
### `path/to/file.ext`

Description of changes.

<!-- patch: path/to/file.ext -->
```diff
--- a/path/to/file.ext
+++ b/path/to/file.ext
@@ -1,3 +1,4 @@
 context line
 another context line
+added line
 more context
```
````

### Nested Markdown

When a Markdown file contains code blocks, use longer fences:

`````markdown
### `docs/guide.md`

<!-- file: docs/guide.md -->
````markdown
# Guide

```bash
echo "hello"
```
````
`````

**Rule:** outer fence is always strictly longer than any inner fence.

## Fuzzy patching

LLMs are bad at counting lines. MDFS handles this:

1. `@@ -10,3 +10,4 @@` line numbers are treated as **hints**, not requirements
2. Context lines (lines starting with ` `) are used to **find** the right
   location in the file via fuzzy matching
3. Exact match is tried first, then whitespace-tolerant match
4. If context is found at a different line number — patch still applies

This means LLM-generated patches work even when `@@` numbers are wrong,
as long as the context lines are correct.

## System prompt

`mdfs init` creates `.mdfs/rules/mdfs-system.md` — a system prompt that
teaches the LLM to output files in MDFS format. The bundler automatically
prepends it to every context file.

You can customize it or replace it entirely.

## Project layout with MDFS

```
your-project/
├── .mdfs/
│   ├── rules/
│   │   └── mdfs-system.md      ← LLM instructions (in git)
│   ├── contexts/                ← generated, gitignored
│   └── responses/               ← generated, gitignored
├── PROJECT.md                   ← project manifest (always in LLM slot 1)
├── src/
│   └── ...
└── docs/
    └── ...
```

**Workflow:**
```
📎 Slot 1: PROJECT.md              (always)
📎 Slot 2: .mdfs/contexts/xxx.md   (bundled files)
📝 Your prompt
```

## Shell completions

Completions are installed automatically by `setup.sh`.

**Manual setup (zsh):**
```bash
# Add to ~/.zshrc:
fpath=(/path/to/mdfs/completions/zsh $fpath)
autoload -Uz compinit && compinit
```

**Manual setup (bash):**
```bash
# Add to ~/.bashrc:
source /path/to/mdfs/completions/bash/mdfs
```

## Development

```bash
git clone https://github.com/YOUR_USER/mdfs.git
cd mdfs
python -m pytest tests/ -v
```

## License

MIT
