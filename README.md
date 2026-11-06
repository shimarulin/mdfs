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
- **Rules** — project rules from `.mdfs/rules/` in every bundle; rules-only
  bundles for session start, ready to paste into chats without attachments
- **Extract** files from LLM responses back to disk
- **Fuzzy patch** — apply unified diffs even when line numbers are wrong
  (LLMs are notoriously bad at counting lines)
- **Clipboard integration** — paste LLM response directly from clipboard
- **Chronological history** — contexts and responses are timestamped
- **Zero dependencies** — Python 3.10+ stdlib only
- **Shell completions** — zsh and bash

## Installation

### Option A: pipx install (recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools into isolated environments,
fully compatible with PEP 668 ("externally managed" Python).
 
 ```bash
pipx install git+https://github.com/shimarulin/mdfs.git
```

This gives you the `mdfs` command globally.

> Don't have pipx?
> Most distros package it: apt install pipx, dnf install pipx,
> pacman -S python-pipx, brew install pipx.
> Or: python3 -m pip install --user pipx && pipx ensurepath.

> ℹ️ Shell completions not installed automatically.
> See [Shell completions](#shell-setup--completions) section for setup.

### Option B: uv tool install

uv is a fast Python package manager that also
manages CLI tools (like pipx, but faster).

```bash
uv tool install git+https://github.com/shimarulin/mdfs.git
```

> ℹ️ Shell completions not installed automatically.
> See [Shell completions](#shell-setup--completions) section for setup.

### Option C: pip install in a virtual environment

```bash
python3 -m venv ~/.local/share/mdfs/venv
~/.local/share/mdfs/venv/bin/pip install git+https://github.com/shimarulin/mdfs.git
export PATH="$HOME/.local/share/mdfs/venv/bin:$PATH"  # add to your shell profile
```

> ℹ️ Shell completions not installed automatically.
> See [Shell completions](#shell-setup--completions) section for setup.

### Option D: git submodule (for project-local tools)

```bash
cd your-project
git submodule add https://github.com/shimarulin/mdfs.git tools/mdfs
tools/mdfs/setup.sh --install
```

> ✅ Shell completions installed via `mdfs setup`.

### Option E: git clone + activate

```bash
git clone https://github.com/shimarulin/mdfs.git ~/.local/share/mdfs
~/.local/share/mdfs/setup.sh --install
```

> ✅ Shell completions installed via `mdfs setup`.

### Option F: just source it

```bash
git clone https://github.com/shimarulin/mdfs.git /path/to/mdfs
source /path/to/mdfs/setup.sh   # current session only
```

## Quick start

```bash
# 1. Initialize in your project
cd your-project
mdfs init

# 2. Bundle files for LLM
mdfs bundle src/app.py src/lib.py docs/api.md -l "add auth module"
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

## Configuration

MDFS supports optional configuration via `.mdfsrc.yaml` file, allowing you to:
- Use custom directories for bundled contexts and LLM responses
- Work with non-standard project structures

### Configuration File (`.mdfsrc.yaml`)

The configuration file is automatically searched starting from your current directory and moving up to the filesystem root.

**Command-line overrides**: You can override configuration values using global flags that take precedence over `.mdfsrc.yaml`:

```bash
mdfs bundle src/ --contexts-dir ./my-contexts
mdfs paste response --responses-dir ./my-responses -x
mdfs log --contexts-dir ./my-contexts
```

| Flag | Description |
|------|-------------|
| `--contexts-dir` | Override contexts directory path |
| `--responses-dir` | Override responses directory path |

**Example `.mdfsrc.yaml`:**

```yaml
# Directory for bundled context files (default: .mdfs/contexts)
contexts_dir: ".mdfs/contexts"

# Directory for LLM response files (default: .mdfs/responses)  
responses_dir: ".mdfs/responses"

# Directory with rule files (default: .mdfs/rules)
rules_dir: ".mdfs/rules"

# Rules included in every bundle (filename globs).
# Default: only the file output format rule. Use ["*"] for all rules.
rules_always:
  - "00-*"
```

### Using Configuration

1. **Create config**: Run `mdfs init` to create a default `.mdfsrc.yaml`
2. **Customize paths**: Edit `contexts_dir` and `responses_dir` as needed
3. **Auto-loading**: MDFS automatically loads and uses the configuration

**Notes:**
- Configuration is optional — MDFS works fine with defaults
- Paths can be relative (relative to config file) or absolute

### Rules (`.mdfs/rules/`)

MDFS includes project rules in every bundle. Rules are plain Markdown
files in `.mdfs/rules/` — no frontmatter, no metadata: the entire file
is the rule body.

**Selection** is by filename globs, **ordering** by the filesystem:

1. Files are loaded in **filename order** — use numeric prefixes
   (`00-system.md`, `10-style.md`, `20-domain.md`) to pin the sequence
2. Which rules are included is controlled by filename globs:
   - config `rules_always` — rules included in **every** bundle
     (default: `00-*`, i.e. only the file output format rule)
   - `bundle --rules GLOB` — additional rules for a single bundle;
     repeatable and comma-separated (`--rules '1*,2*'`), `*` = all
3. The two glob sets are combined (union)

The file output format rule (`00-file-output-format.md`) is special:
`mdfs init` writes it into the project, and if it is absent from the
rules directory, the built-in copy shipped with the package is used
automatically.

**Notes:**
- Non-markdown files and empty files are skipped
- Rules are inserted inside the rules block delimited by
  `<!-- mdfs:rules:start -->` / `<!-- mdfs:rules:end -->` HTML-comment
  markers; each rule is framed by
  `<!-- mdfs:rule:start name="file.md" -->` / `<!-- mdfs:rule:end ... -->`
- There is no token budget, truncation or dropping: every included rule
  file is written to the bundle in full

---

## Commands

### `mdfs init`

Create `.mdfsrc.yaml` configuration file in the current project.

```bash
mdfs init                   # initialize in current directory
mdfs init -d /path/to/proj  # initialize in specific directory
```

Creates:
```
.mdfsrc.yaml                          # Configuration file with default paths
.mdfs/rules/00-file-output-format.md  # File output format rule (editable copy)
```

**Why**: Sets up configuration for MDFS workflow. Safe to run multiple times.

**How directories are created:**
- `.mdfs/`, `.mdfs/contexts/`, `.mdfs/responses/` are created **automatically** when you first use `mdfs bundle`, `mdfs paste`, or `mdfs log`
- Alternatively, you can create them manually: `mkdir -p .mdfs/{contexts,responses,rules}`
- Add to `.gitignore`: `echo ".mdfs/contexts\n.mdfs/responses" >> .gitignore`

> **Note**: `00-file-output-format.md` is the built-in format rule as an
> editable file — tune it to your project. If you delete it, the built-in
> packaged copy is used instead. Use `mdfs rules` to view and copy the
> packaged copy directly.

### `mdfs bundle`

Pack project rules and/or files into a single Markdown document.

```bash
mdfs bundle file1.py file2.py ...      # paths relative to project root
mdfs bundle src/*.py -l "my label"     # with label
mdfs bundle src/*.py -o custom.md      # custom output path
mdfs bundle src/*.py -s prompt.md      # custom system prompt
mdfs bundle src/*.py -q "Review this"  # append your question
mdfs bundle src/*.py --clip            # also copy to clipboard
mdfs bundle --rules '*'                # include all rules
mdfs bundle --rules '10-*,20-*'        # include rules by filename globs
mdfs bundle --no-preamble              # without table of contents
mdfs bundle src/*.py --no-gitignore    # include .gitignore'd files
```

| Argument/Flag | Description |
|---------------|-------------|
| `files` (positional, optional) | File paths or directories to include (multiple allowed). **Without files, bundles only the rules** — useful at session start |
| `-l, --label` | Human-readable label for filename |
| `-s, --system-prompt` | Custom system prompt file (legacy mode, with `--no-preamble`) |
| `-o, --output` | Custom output path (default: `.mdfs/contexts/<timestamp>.md`) |
| `-q, --query` | User question to append to the bundle |
| `--clip` | Also copy the bundle to clipboard |
| `--rules GLOB` | Extra rules to include, by filename globs (repeatable/comma-separated, `*` = all). On top of config `rules_always` |
| `--no-preamble` | Disable preamble and table of contents |
| `--no-gitignore` | Include files that are in `.gitignore` |

**Usage notes:**
- `files` are positional arguments (come before flags)
- Multiple files/directories are supported
- Paths are relative to project root

**Session-start workflow** (rules-only bundle, no attachments needed):

```bash
# Start of a chat session: copy rules + your question to the clipboard,
# then paste into the chat input
mdfs bundle --clip -q "Help me design the auth module"
#   📦 Context saved: .mdfs/contexts/2026-04-04_143000.md
#   📋 Copied to clipboard

# Follow-up messages need no re-paste if the chat keeps context:
# the rules block explicitly says they apply to the entire conversation
mdfs bundle src/auth.py -q "Now review this file"
```

### `mdfs paste`

Save clipboard content as a response file.

```bash
mdfs paste                                 # save only (auto-label)
mdfs paste "my label"                      # save with label
mdfs paste "my label" --extract            # save + extract files + apply patches
mdfs paste "my label" -x --dry-run         # preview without writing
```

| Argument/Flag | Description |
|---------------|-------------|
| `label` (positional, optional) | Human-readable label for filename. If omitted, auto-generated from timestamp |
| `-x, --extract` | Also extract files and apply patches from response |
| `--dry-run` | Show what would happen without writing files |

**Usage notes:**
- Label is a positional argument (not a flag), comes after `mdfs paste`
- Without `--extract`, only saves the response file, doesn't process it
- With `--extract`, also extracts files and applies patches (useful for single-command workflow)
- `--dry-run` works with both save and extract modes

### `mdfs extract`

Extract files and apply patches from any Markdown file.

```bash
mdfs extract response.md            # extract and write files
mdfs extract response.md --dry-run  # preview without writing
mdfs extract response.md -f         # force overwrite all files
```

| Flag | Description |
|------|-------------|
| `input` (positional) | Path to Markdown file to extract from (required) |
| `--dry-run` | Show what would happen without writing files |
| `-f, --force` | Force overwrite all existing files without prompting |

**Usage notes:**
- Without `--force`, prompts before overwriting existing files
- Supports both full files and unified diff patches
- Uses fuzzy matching for patches (line numbers are hints, context lines matter)

### `mdfs rules`

Display and copy system prompt rules to clipboard.

```bash
mdfs rules              # print rules to console and copy to clipboard
```

Prints the MDFS system prompt that instructs LLMs how to format files
and patches. Automatically copies to clipboard for easy pasting into
chat interfaces.

**Usage notes:**
- Output goes to stdout (can be piped or redirected)
- Content is also copied to system clipboard
- Useful when `.mdfs/rules/` directory exists but file is not on disk

### `mdfs log`

Show chronological history of contexts and responses in `.mdfs/`.

```bash
mdfs log              # show all contexts and responses
mdfs log -d /path    # show history for specific project directory
```

Displays all bundled contexts and LLM responses with timestamps.

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

The system prompt teaches the LLM to output files in MDFS format.
The bundler automatically prepends it to every context file.

Use `mdfs rules` to view the system prompt and copy it to clipboard.
You can also add project rules by placing files in `.mdfs/rules/`
(see [Rules](#rules-mdfsrules)).

In a rules-only bundle (`mdfs bundle` without files), the document ends
with a note that the rules apply to the entire conversation, so a single
paste at session start covers all subsequent messages.

## Project layout with MDFS

```
your-project/
├── .mdfs/
│   ├── rules/
│   │   └── 00-file-output-format.md  ← LLM instructions (in git)
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

## Shell Setup & Completions

### What `setup.sh` Does (git clone installations only)

For git clone installations (Option E), the `setup.sh` script:
1. Adds MDFS `bin/` to `$PATH` (for current session)
2. Delegates to `mdfs setup` (for permanent setup)

**For other installation methods** (uv, pipx), use `mdfs setup` directly:
```bash
mdfs setup                 # interactive: auto-detect and ask
mdfs setup -i              # install completions for current shell
mdfs setup -u              # uninstall completions
```

| Flag | Description |
|------|-------------|
| `-i, --install-completions` | Install shell completions for detected shell |
| `-u, --uninstall-completions` | Uninstall shell completions |
| (none) | Interactive mode: auto-detects shell and asks for confirmation |

### Usage

#### Current Session Only
```bash
source /path/to/mdfs/setup.sh
# or for git clone in ~/.local/share/mdfs:
source ~/.local/share/mdfs/setup.sh
```
Activates MDFS in the current shell session. After closing the terminal, you'll need to run this again.

#### Permanent Installation
```bash
/path/to/mdfs/setup.sh --install
# or directly:
mdfs setup -i
```

#### Removing Installation
```bash
/path/to/mdfs/setup.sh --uninstall
# or directly:
mdfs setup -u
```

#### Help
```bash
/path/to/mdfs/setup.sh --help
```

### What Gets Installed

When you run `mdfs setup -i`, it:
- Detects your shell (zsh, bash, or fish)
- Adds MDFS `bin/` to `$PATH` in your shell config files
- Configures shell completions (fpath for zsh, source for bash, fish_add_path for fish)
- Creates backups before modifying config files
- Is fully idempotent (safe to run multiple times)

**Where configuration is added:**

| Shell | Files |
|-------|-------|
| **zsh** | `~/.zshenv` (PATH), `~/.zshrc` (completions) |
| **bash (macOS)** | `~/.bash_profile` (PATH + completions) |
| **bash (Linux)** | `~/.bashrc` (PATH + completions) |
| **fish** | `~/.config/fish/conf.d/mdfs.fish` |

**Why different files?**
- **zsh:** Uses `~/.zshenv` for PATH (read by all shells) and `~/.zshrc` for interactive setup
- **bash:** Has different files for login vs non-login shells; macOS always treats new terminal as login shell
- **fish:** Uses conf.d for automatic initialization

### Manual Setup (if preferred)

**For zsh:**
```bash
# Add to ~/.zshenv (for PATH — needed everywhere):
export PATH="/path/to/mdfs/bin:$PATH"
fpath=(/path/to/mdfs/completions/zsh $fpath)

# Add to ~/.zshrc (for interactive shells):
autoload -Uz compinit && compinit
```

**For bash:**
```bash
# Add to ~/.bashrc (or ~/.bash_profile on macOS):
export PATH="/path/to/mdfs/bin:$PATH"
[[ -f /path/to/mdfs/completions/bash/mdfs ]] && source /path/to/mdfs/completions/bash/mdfs
```

**For fish:**
```bash
# Add to ~/.config/fish/conf.d/mdfs.fish:
fish_add_path /path/to/mdfs/bin
```

## Development

### Setup

```bash
git clone https://github.com/shimarulin/mdfs.git
cd mdfs
```

### Running tests

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install test dependencies and run all tests
uv run --extra test pytest

# Run tests with verbose output
uv run --extra test pytest -v

# Run tests with coverage report
uv run --extra test pytest --cov=mdfs --cov-report=term-missing

# Run specific test file
uv run --extra test pytest tests/test_bundler.py
```

The `--extra test` flag installs optional test dependencies defined in
`pyproject.toml` (pytest, pytest-cov).

## License

MIT
