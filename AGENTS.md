# AGENTS.md — MDFS Project Architecture & Maintenance Guide

This document serves as the architectural reference and maintenance guide for the MDFS (Markdown FileSystem) project. **All code comments, documentation, and AGENTS.md itself must be maintained in English.**

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Commands Reference](#commands-reference)
4. [Utility Functions](#utility-functions)
5. [Testing](#testing)
6. [Code Style & Conventions](#code-style--conventions)
7. [Maintenance Guidelines](#maintenance-guidelines)
8. [Key State Variables](#key-state-variables)

---

## Project Overview

**MDFS** (Markdown FileSystem) bundles project files into a single Markdown document for LLM chat, then extracts files and applies patches from the LLM response.

### Purpose
- Pack multiple project files into one Markdown document with special markers
- Enable LLMs to read and produce files correctly
- Support fuzzy patching (line numbers are hints, context lines matter)
- Provide chronological history of contexts and responses
- Zero dependencies (Python 3.10+ stdlib only)

### Key Features
- Bundle any number of project files into `.md`
- Extract files from LLM responses back to disk
- Fuzzy patch application for LLM-generated diffs
- Clipboard integration
- Shell completions (zsh, bash)
- Chronological history with timestamps

---

## Architecture

### Directory Structure

```
mdfs/
├── __main__.py              # CLI entry point, argument parser
├── __init__.py              # Package initialization
├── config.py                # Configuration management (NEW)
├── default_system_prompt.py # DEFAULT_SYSTEM_PROMPT constant
├── utils.py                 # Utility functions (clipboard, validation, etc.)
├── commands/                # Command implementations
│   ├── __init__.py
│   ├── init.py             # Initialize .mdfs directory
│   ├── bundle.py           # Bundle files into context
│   ├── paste.py            # Save and extract from clipboard
│   ├── extract.py          # Extract files from Markdown
│   ├── log.py              # Show history of contexts/responses
│   ├── rules.py            # Display system prompt
│   └── setup.py            # Shell setup and completions
└── core/                   # Core functionality modules
    ├── __init__.py
    ├── bundler.py          # File bundling logic
    ├── extractor.py        # File extraction and patching logic
    ├── parser.py           # Markdown marker parsing
    └── gitignore.py        # .gitignore handling

tests/                      # Test suite
├── test_*.py              # Unit and integration tests
└── (uses pytest)

completions/               # Shell completions
├── bash/mdfs              # Bash completion script
└── zsh/_mdfs              # Zsh completion script
```

### Component Relationships

```
__main__.py (CLI parser)
    ↓
commands/*Command classes
    ↓
core/* (business logic)
    ↓
utils.py (helpers)
```

### Data Flow

1. **Bundle Flow**: User files → bundler → context.md
2. **Extract Flow**: response.md → parser → extractor → files + patches
3. **Clipboard Flow**: paste (get) → utils.get_clipboard() → extract
4. **Output Flow**: copy_to_clipboard → utils.copy_to_clipboard() → system clipboard

---

## Commands Reference

Each command is implemented as a class in `mdfs/commands/` and registered in `__main__.py`.

### Command Pattern

All command classes follow this pattern:

```python
class CommandNameCommand:
    def __init__(self, args: Namespace):
        self.args = args
    
    def execute(self) -> int:
        """Execute command. Return 0 on success, non-zero on error."""
        # implementation
        return 0
```

### Available Commands

#### `mdfs init` — Initialize Project

**Class**: `InitCommand` (`mdfs/commands/init.py`)

**Purpose**: Create `.mdfs/` directory structure

**Parameters**:
- `-d, --dir` (optional): Project directory (default: current)

**Creates**:
```
.mdfs/
├── .gitignore       # ignores contexts/ and responses/
├── rules/           # directory for system prompt rules
├── contexts/        # bundled files for LLM
└── responses/       # LLM responses
```

**Notes**:
- System prompt is NOT created on disk (use `mdfs rules` instead)
- Safe to run multiple times (idempotent)

---

#### `mdfs bundle` — Pack Files for LLM

**Class**: `BundleCommand` (`mdfs/commands/bundle.py`)

**Purpose**: Pack project files into single Markdown document

**Parameters**:
- `files` (positional, required): File paths or directories to include
- `-l, --label` (optional): Human-readable label for filename
- `-s, --system-prompt` (optional): Custom system prompt file
- `-o, --output` (optional): Custom output path
- `--no-preamble` (flag): Disable preamble and table of contents
- `--no-gitignore` (flag): Include .gitignore'd files

**Output**: `.mdfs/contexts/<timestamp>__<label>.md`

**Process**:
1. Prepends DEFAULT_SYSTEM_PROMPT
2. Includes table of contents
3. Marks each file with `<!-- file: path -->` markers
4. Saves to contexts directory with timestamp

---

#### `mdfs paste` — Save Clipboard Response

**Class**: `PasteCommand` (`mdfs/commands/paste.py`)

**Purpose**: Save clipboard content as response file, optionally extract

**Parameters**:
- `label` (positional, optional): Label for filename
- `-x, --extract` (flag): Also extract files and apply patches
- `--dry-run` (flag): Show what would happen without writing

**Output**: `.mdfs/responses/<timestamp>__<label>.md`

**Process**:
1. Reads from system clipboard
2. Saves to responses directory with timestamp
3. If `--extract`: invokes extraction and patching

---

#### `mdfs extract` — Extract Files from Markdown

**Class**: `ExtractCommand` (`mdfs/commands/extract.py`)

**Purpose**: Extract files and apply patches from Markdown

**Parameters**:
- `input` (positional, required): Path to Markdown file
- `--dry-run` (flag): Preview without writing
- `-f, --force` (flag): Force overwrite without prompting

**Process**:
1. Parses markers: `<!-- file: ... -->` and `<!-- patch: ... -->`
2. For files: writes to disk (prompts if exists unless `-f`)
3. For patches: applies unified diffs with fuzzy matching
4. Fuzzy matching: line numbers are hints, context lines matter

---

#### `mdfs log` — Show History

**Class**: `LogCommand` (`mdfs/commands/log.py`)

**Purpose**: Display chronological history of contexts and responses

**Parameters**:
- `-d` (optional): Project directory (default: current)

**Output**: Timestamped list of bundles and responses

---

#### `mdfs rules` — Display System Prompt

**Class**: `RulesCommand` (`mdfs/commands/rules.py`) **[NEW]**

**Purpose**: Display and copy system prompt to clipboard

**Parameters**: None

**Output**:
- Prints DEFAULT_SYSTEM_PROMPT to stdout
- Copies to system clipboard
- Prints confirmation message to stderr

**Notes**:
- Useful when `.mdfs/rules/` exists but file is not on disk
- Content is automatically copied to clipboard for pasting into LLM chat

---

#### `mdfs setup` — Shell Configuration

**Class**: `SetupCommand` (`mdfs/commands/setup.py`)

**Purpose**: Install/uninstall shell completions and PATH configuration

**Parameters**:
- `-i, --install-completions` (flag): Install for current shell
- `-u, --uninstall-completions` (flag): Uninstall for current shell
- (none): Interactive mode (auto-detect and ask)

**Supports**: zsh, bash, fish

**Process**:
1. Detects current shell
2. Modifies shell config files (.zshenv, .bashrc, etc.)
3. Adds PATH and completions configuration
4. Creates backups before modifying
5. Fully idempotent

---

## Configuration System

### Overview

MDFS now supports configuration via `.mdfsrc.yaml` file, allowing users to:
- Customize `contexts_dir` and `responses_dir` paths
- Define directories with markdown files for system prompt extensions
- Work with non-standard project structures

The configuration file is searched starting from the current working directory upward to the filesystem root.

### `.mdfsrc.yaml` Format

```yaml
# Directory for bundled context files (default: .mdfs/contexts)
contexts_dir: ".mdfs/contexts"

# Directory for LLM response files (default: .mdfs/responses)
responses_dir: ".mdfs/responses"

# Directories containing .md files for system prompt extensions
# Files are loaded alphabetically, joined with blank lines
prompt_extensions:
  - ".mdfs/extensions"
  - "docs/mdfs-prompts"
```

### Usage

1. Create `.mdfsrc.yaml` in project root (or run `mdfs init`)
2. Customize paths as needed
3. Add markdown files to `prompt_extensions` directories
4. Files are automatically loaded and appended to system prompt

### Configuration Class

**Location**: `mdfs/config.py`

**Key Methods**:
- `Config()` — Load config from `.mdfsrc.yaml`
- `get_contexts_dir(base_dir)` — Get contexts directory path
- `get_responses_dir(base_dir)` — Get responses directory path
- `get_prompt_extensions_dirs(base_dir)` — Get list of extension directories
- `load_prompt_extensions(base_dir)` — Load and concatenate extension files
- `is_configured()` — Check if config file exists
- `create_default_config(path)` — Create default `.mdfsrc.yaml`
- `override(contexts_dir, responses_dir, prompt_extensions_dirs)` — Override config with command-line arguments (takes precedence over `.mdfsrc.yaml`)

### Command-line Config Overrides

All commands support global flags to override configuration values (take precedence over `.mdfsrc.yaml`):

- `--contexts-dir PATH` — Override contexts directory
- `--responses-dir PATH` — Override responses directory
- `--prompt-extensions-dir PATH` — Add/override prompt extension directories (can be used multiple times)

**Example usage:**
```bash
mdfs bundle src/ --contexts-dir ./my-contexts
mdfs paste label --responses-dir ./my-responses -x
mdfs log --contexts-dir ./my-contexts
```

Overrides are applied in `BaseCommand.apply_config_overrides()` method, which is called by commands after loading configuration.

---

## Utility Functions

All utilities are in `mdfs/utils.py`. Public functions:

### `get_clipboard() -> str`
Read system clipboard content.
- **macOS**: Uses `pbpaste`
- **Linux**: Tries `wl-paste`, `xclip`, `xsel` (in order)
- **Raises**: `SystemExit(1)` if clipboard unavailable

### `copy_to_clipboard(text: str) -> None`
Write text to system clipboard.
- **macOS**: Uses `pbcopy`
- **Linux**: Tries `wl-copy`, `xclip`, `xsel` (in order)
- **Raises**: `SystemExit(1)` if clipboard unavailable

### Other Utilities
See `mdfs/utils.py` source for additional helper functions (validation, path handling, etc.)

---

## Core Modules

### `mdfs/core/bundler.py` — File Bundling

Responsible for:
- Reading project files
- Formatting with MDFS markers
- Building context files with system prompt

**Key Classes**:
- `Bundler` — Main bundling logic

### `mdfs/core/extractor.py` — File Extraction & Patching

Responsible for:
- Parsing markers from Markdown
- Extracting file content
- Applying unified diff patches
- Fuzzy matching for patch application

**Key Classes**:
- `Extractor` — Extraction and patching logic
- `FileExtraction` — Result of parsing a file block
- `PatchExtraction` — Result of parsing a patch block

### `mdfs/core/parser.py` — Marker Parsing

Responsible for:
- Finding MDFS markers in Markdown
- Validating marker syntax
- Extracting paths and content

**Marker Formats**:
```markdown
<!-- file: "path/to/file.ext" -->
```lang
content
```

<!-- patch: "path/to/file.ext" -->
```diff
--- a/path/to/file.ext
+++ b/path/to/file.ext
@@ context @@
content
```
```

### `mdfs/core/gitignore.py` — .gitignore Handling

Responsible for:
- Parsing `.gitignore` files
- Determining if a path should be ignored
- Building file lists for bundling

---

## Testing

### Running Tests

```bash
# All tests
uv run --extra test pytest

# Specific test file
uv run --extra test pytest tests/test_bundler.py

# Verbose with coverage
uv run --extra test pytest --cov=mdfs --cov-report=term-missing
```

### Test Organization

```
tests/
├── test_init_and_log.py        # init, log commands
├── test_bundler.py             # bundling logic
├── test_extractor.py           # extraction and patching
├── test_parser.py              # marker parsing
├── test_cli_integration.py      # end-to-end CLI tests
├── test_setup_command.py        # shell setup command
├── test_rules_command.py        # rules command [NEW]
└── test_naming.py              # timestamp and naming
```

### Test Coverage Goals
- Unit tests for core modules
- Integration tests for command workflows
- CLI tests for argument parsing and execution

### Writing Tests
1. Use `pytest` framework
2. Follow naming: `test_<feature>.py`
3. Group related tests in classes: `class Test<Feature>:`
4. Use descriptive test names: `def test_<specific_behavior>():`
5. Mock external dependencies (filesystem, clipboard, shell commands)

---

## Code Style & Conventions

### Python Style
- **Format**: Follow PEP 8
- **Type hints**: Use for function signatures
- **Imports**: Organize as stdlib, then third-party, then local
- **Comments**: English only, clear and concise

### Documentation
- All code comments **must be in English**
- Docstrings for all public classes and functions
- Use Google-style docstring format

### File Organization
- One command class per file in `mdfs/commands/`
- Related utilities grouped in `mdfs/core/`
- Tests mirror source structure

### Naming Conventions
- **Commands**: `NameCommand` class in `name.py`
- **Functions**: `snake_case`
- **Constants**: `CONSTANT_CASE`
- **Private**: Prefix with `_`

---

## Maintenance Guidelines

### When to Update AGENTS.md

AGENTS.md **must be updated** whenever any of the following occur:

#### 1. Command Changes
- **Adding** a new command: Add section to Commands Reference
- **Modifying** a command: Update parameters and behavior description
- **Removing** a command: Remove from Commands Reference and __main__.py

**Also update**:
- `completions/bash/mdfs` — Add command and its flags
- `completions/zsh/_mdfs` — Add command and its flags with descriptions
- `README.md` — Document command for users

#### 2. Function & Configuration Changes
- **Adding** a public function in utils.py or core modules: Add to Utility Functions
- **Modifying** function signature: Update parameters and behavior
- **Removing** a function: Remove from Utility Functions section
- **Adding** configuration options: Update Configuration System section in AGENTS.md and README.md
- **Adding** global command-line flags: Update all commands in `completions/bash/mdfs` and `completions/zsh/_mdfs`

#### 3. Architecture Changes
- **Adding** new module: Update Architecture section
- **Moving** code between files: Update directory structure
- **Changing** data flow: Update Component Relationships

#### 4. All Changes Require
- ✅ Code comments in English
- ✅ Update AGENTS.md accordingly
- ✅ Add/update tests
- ✅ Update README if user-facing
- ✅ Update shell completions if command added/modified:
  - `completions/bash/mdfs` — Bash completion script
  - `completions/zsh/_mdfs` — Zsh completion script

### Maintenance Checklist

Before committing changes:

- [ ] Code written in English with English comments
- [ ] AGENTS.md updated for any architectural/command/function changes
- [ ] Tests added or updated
- [ ] README updated if user-facing changes
- [ ] Shell completions updated if command added/modified
- [ ] All tests pass: `uv run --with pytest pytest`
- [ ] Code follows style guidelines

### Common Scenarios

**Adding a new command**:
1. Create `mdfs/commands/newcommand.py` with `NewcommandCommand` class
2. Register in `mdfs/__main__.py` (add to parser and commands dict)
3. Update `mdfs/commands/__init__.py` to export class
4. Add to AGENTS.md Commands Reference section
5. Add command and flags to `completions/bash/mdfs`
6. Add command and flags to `completions/zsh/_mdfs` with descriptions
7. Update README.md with command documentation
8. Add tests in `tests/test_newcommand.py`

**Modifying existing command**:
1. Edit `mdfs/commands/commandname.py`
2. Update AGENTS.md Commands Reference section
3. Update `completions/bash/mdfs` if parameters changed (add new flags)
4. Update `completions/zsh/_mdfs` if parameters changed (add new flags with descriptions)
5. Update README.md if user-facing changes
6. Update/add tests in `tests/test_<command>.py`

**Adding global flags** (e.g., `--contexts-dir`):
1. Add flag definition in `mdfs/__main__.py` parser
2. Document in AGENTS.md Configuration System section
3. Add to all relevant command classes in `mdfs/commands/`
4. Update all commands in `completions/bash/mdfs` to include new global flags
5. Update all commands in `completions/zsh/_mdfs` to include new global flags with descriptions
6. Document in README.md Configuration section
7. Add tests for new override functionality

**Adding utility function**:
1. Add to `mdfs/utils.py`
2. Add to AGENTS.md Utility Functions section
3. Add tests for new function
4. Document with docstring (English)

---

## Key State Variables

### .mdfs Directory Structure

```
.mdfs/
├── .gitignore              # Prevents contexts/ and responses/ from being tracked
├── rules/                  # Directory for system prompt rules
├── contexts/               # Generated context files (gitignored)
│   └── <timestamp>__<label>.md
└── responses/              # Generated response files (gitignored)
    └── <timestamp>__<label>.md
```

### DEFAULT_SYSTEM_PROMPT

**Location**: `mdfs/default_system_prompt.py`

**Content**: System prompt that teaches LLMs to output files in MDFS format

**Used by**:
- `BundleCommand` — prepended to every context
- `RulesCommand` — displayed to user and copied to clipboard

**Format**: Markdown with sections on markers, fence depth, patching, etc.

### File Formats

#### MDFS Markers

```markdown
<!-- file: "path/to/file.ext" -->
<!-- patch: "path/to/file.ext" -->
```

#### Headings

```markdown
### `path/to/file.ext`   (or #### for nested)
```

#### Language Tags

```markdown
```python
```bash
```diff
```

### Timestamps

Format: `YYYY-MM-DD_HHMMSS`

Used in:
- Context filenames: `.mdfs/contexts/<timestamp>__<label>.md`
- Response filenames: `.mdfs/responses/<timestamp>__<label>.md`

---

## References

- **README.md** — User-facing documentation
- **SETUP_SCRIPT_GUIDE.md** — Shell setup details
- **.gitignore** — Files excluded from bundle by default
- **pyproject.toml** — Python project configuration

---

**Last Updated**: 2026-04-10

**Document Status**: Living document. Update whenever making changes to commands, functions, or architecture.
