# Shell Setup Script Guide

This guide documents best practices and technical decisions for creating
installation scripts that configure the shell environment and manage PATH.

Developed based on experience building `setup.sh` for MDFS.

## Table of Contents

1. [Shell Detection](#shell-detection)
2. [PATH Management](#path-management)
3. [Shell Completions](#shell-completions)
4. [Persistent Installation](#persistent-installation)
5. [OS Differences](#os-differences)
6. [Error Handling](#error-handling)
7. [Configuration Removal](#configuration-removal)
8. [Permissions and sudo](#permissions-and-sudo)
9. [User Communication](#user-communication)
10. [Testing](#testing)
11. [Idempotent Utilities](#idempotent-utilities)
12. [FAQ](#faq)
13. [Examples in Other Projects](#examples-in-other-projects)
14. [Final Checklist](#final-checklist)

---

## Shell Detection

### Problem

The script must work with different shells (zsh, bash, fish, etc.), each
having its own configuration files and syntax.

### Solution

Detect the current shell through environment variables:

```bash
detect_shell() {
    if [ -n "${ZSH_VERSION:-}" ]; then echo "zsh"
    elif [ -n "${BASH_VERSION:-}" ]; then echo "bash"
    else echo "unknown"; fi
}
```

### Why This Approach

- `$ZSH_VERSION` — set only by zsh (reliable indicator).
- `$BASH_VERSION` — set only by bash (reliable indicator).
- Order matters: check zsh first because some systems may have both shells
  active (e.g., bash running inside zsh or vice versa).
- `${VAR:-}` syntax ensures the script does not break under `set -u`.

### Why fish Is Not Included

Fish uses a completely different syntax and cannot execute bash scripts
natively. A bash script with `#!/usr/bin/env bash` will always run under
bash, so `$fish_version` will never be set inside it. Fish also does not
export `fish_version` to child processes.

**Recommendation:** Create a separate `setup.fish` script for fish support.
Use `detect_shell` only for bash and zsh. If you need to inform a fish user,
check `$SHELL` as a fallback hint (see below).

### POSIX Compatibility

The function above uses `[ ]` (POSIX test) instead of `[[ ]]` (bash
extension). This means it works even if accidentally invoked as
`sh setup.sh`. However, the rest of this guide assumes bash features, so
always use an explicit shebang:

```bash
#!/usr/bin/env bash
```

### Alternative Methods (NOT Recommended)

```bash
# ❌ DO NOT RELY ON $SHELL
# May be set to a different shell or not match the current process.
# However, it can be used as a fallback to suggest manual steps to the user.
echo "$SHELL"

# ❌ DO NOT USE ps OR OTHER PROCESS INSPECTION
# OS-dependent, output format varies, may fail in restricted environments.
ps -p $$
```

---

## PATH Management

### Problem 1: PATH Must Be Available Everywhere

The user needs `PATH` to be set in:
- Login shells (SSH, new terminal on macOS).
- Non-login interactive shells (new tab in a terminal on Linux).
- Non-interactive shells and subprocesses (`:!command` in Neovim, cron jobs).

### Solution for zsh

**Recommended file:** `~/.zshenv` — the only file zsh reads in **every**
invocation mode (login, non-login, interactive, non-interactive).

```bash
# ~/.zshenv
export PATH="/path/to/bin:$PATH"
fpath=(/path/to/completions/zsh $fpath)
```

**The `path_helper` problem on macOS:**

On macOS, `/etc/zprofile` calls `/usr/libexec/path_helper -s`, which
**reorders PATH** by moving system paths (`/usr/bin`, `/bin`) to the front.
This happens *after* `~/.zshenv` is read:

```
# You add in ~/.zshenv:
export PATH="/custom/bin:$PATH"

# After path_helper runs in /etc/zprofile:
PATH="/usr/bin:/bin:/custom/bin"   # your path moved to the end
```

**Unified recommendation for zsh:**

1. Add PATH to `~/.zshenv` so it is available in all contexts.
2. On macOS, also add `typeset -U PATH` (deduplicates PATH entries) and
   optionally re-prepend your path in `~/.zshrc` (which runs after
   `path_helper`):
   ```bash
   # ~/.zshenv
   typeset -U PATH
   export PATH="/path/to/bin:$PATH"
   ```
   `typeset -U PATH` ensures that even if `path_helper` reorders entries,
   there are no duplicates. If ordering is critical (your binary must
   shadow a system binary), add the path again in `~/.zshrc`.

**ZDOTDIR handling:**

Zsh checks the `ZDOTDIR` environment variable **before** reading any user
dotfiles. The logic is:

1. If `ZDOTDIR` is set in the environment (e.g., via `/etc/zshenv`, a
   parent process, or a PAM module), zsh reads `$ZDOTDIR/.zshenv` **instead
   of** `~/.zshenv`. The file `~/.zshenv` is never read.
2. If `ZDOTDIR` is not set, zsh reads `~/.zshenv`. If `~/.zshenv` sets
   `ZDOTDIR`, subsequent files (`.zprofile`, `.zshrc`, `.zlogin`) will be
   read from `$ZDOTDIR`, but `.zshenv` itself was already read from `$HOME`.

**Recommendation for setup scripts:** Check `ZDOTDIR` before writing:

```bash
if [ -n "${ZDOTDIR:-}" ]; then
    zshenv_file="$ZDOTDIR/.zshenv"
else
    zshenv_file="$HOME/.zshenv"
fi
```

### zsh File Loading Order (login shell)

1. `/etc/zshenv` (system)
2. `~/.zshenv` or `$ZDOTDIR/.zshenv` (user) — **always read**
3. `/etc/zprofile` (system) — macOS runs `path_helper` here
4. `~/.zprofile` (user)
5. `/etc/zshrc` (system)
6. `~/.zshrc` (user)
7. `/etc/zlogin` (system)
8. `~/.zlogin` (user)

For non-login interactive shells, only steps 1–2 and 5–6 apply.
For non-interactive shells, only steps 1–2 apply.

### Solution for bash

Bash has two distinct loading paths:

```
┌──────────────────────────────────┐
│ Login shell (SSH, macOS, TTY)    │
├──────────────────────────────────┤
│ 1. /etc/profile                  │
│ 2. First found of:              │
│    ~/.bash_profile               │
│    ~/.bash_login                 │
│    ~/.profile                    │
│ 3. ~/.bashrc is NOT read         │
│    automatically!                │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ Non-login interactive shell      │
│ (new tab on most Linux terms)    │
├──────────────────────────────────┤
│ 1. ~/.bashrc                     │
│ 2. ~/.bash_profile is NOT read!  │
└──────────────────────────────────┘
```

**Key insight:** On macOS, every new terminal window is a login shell. On
Linux, it is usually a non-login shell (but SSH, TTY login, and WSL are
login shells). This means:

- On macOS: `.bash_profile` is read, `.bashrc` is not (unless sourced).
- On Linux terminal: `.bashrc` is read, `.bash_profile` is not.
- On Linux SSH/TTY/WSL: `.bash_profile` is read, `.bashrc` is not.

### Solution: Source .bashrc from .bash_profile

Best practice — ensure `.bash_profile` sources `.bashrc`:

```bash
# Add to ~/.bash_profile so both configs load in login shells
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
```

**Guard against duplication:**

```bash
# Check that the source line is not already present
# Note: using -q (quiet) without -F because we need regex matching
if [ -f "$$HOME/.bash_profile" ] && ! grep -q '[.[:space:]].*bashrc\|source.*bashrc' "$$HOME/.bash_profile"; then
    printf '\n%s\n' '# Source .bashrc if it exists' >> "$HOME/.bash_profile"
    printf '%s\n' '[ -f ~/.bashrc ] && . ~/.bashrc' >> "$HOME/.bash_profile"
fi
```

Then add all PATH and configuration to `~/.bashrc`, which will be loaded in
both login and non-login shells.

**On macOS:** `/etc/profile` may also call `path_helper`, reordering PATH.
Use a guard:

```bash
case ":$PATH:" in
    *":/path/to/bin:"*) ;;
    *) export PATH="/path/to/bin:$PATH" ;;
esac
```

### Solution for fish

Fish uses a completely different syntax and should have a separate setup
script (`setup.fish`). Bash logic does not apply.

```fish
# ~/.config/fish/conf.d/tool.fish

# Fish 3.0+ (recommended): automatically deduplicates, idempotent
fish_add_path /path/to/bin

# Alternative for fish < 3.0:
set -gx PATH /path/to/bin $PATH
```

**Notes:**
- `fish_add_path` (fish 3.0+) is the recommended modern approach — it
  automatically deduplicates PATH and prepends.
- `set -gx` exports the variable to child processes; needed for `PATH` but
  often `set -g` suffices for other variables.
- Fish completions go in `~/.config/fish/completions/` named
  `<command>.fish`.

### Problem 2: Different OSes Use Different Files

See [OS Differences](#os-differences) for a detailed breakdown. The short
version:

**For bash on macOS:**

```bash
# Find the existing profile file in priority order
profile_file=""
for candidate in "$$HOME/.bash_profile" "$$HOME/.bash_login" "$HOME/.profile"; do
    if [ -f "$candidate" ]; then
        profile_file="$candidate"
        break
    fi
done

# If none exists, create .bash_profile
if [ -z "$profile_file" ]; then
    profile_file="$HOME/.bash_profile"
fi
```

**For bash on Linux:**

```bash
# If .bash_profile exists, the user manages login shells manually
if [ -f "$HOME/.bash_profile" ]; then
    # Add to .bash_profile (and ensure it sources .bashrc)
    :
else
    # Standard case: add to .bashrc
    :
fi
```

---

## Shell Completions

### Problem

Different shells use different completion systems:
- **zsh:** `fpath` + `compinit`
- **bash:** Sourcing completion files
- **fish:** Automatic loading from `~/.config/fish/completions/`

### Solution for zsh

```bash
# 1. Add directory to fpath (in ~/.zshenv or ~/.zshrc)
fpath=(/path/to/completions/zsh $fpath)

# 2. Initialize compinit (in ~/.zshrc — interactive shells only)
autoload -Uz compinit && compinit -i
```

**Why `compinit -i` (ignore ownership checks)?**
- `compinit` verifies that completion files are owned correctly.
- In systems with NFS, Docker, or shared mounts this may fail.
- The `-i` flag skips these checks (safe for completions).

### Solution for bash

```bash
# Source the completion file (in ~/.bashrc)
[ -f /path/to/completions/bash/mdfs ] && . /path/to/completions/bash/mdfs
```

### Solution for fish

Completions are automatically loaded from `~/.config/fish/completions/` if
the file is named `<command>.fish`:

```
~/.config/fish/completions/mdfs.fish
```

### Completion File Naming Conventions

```
completions/
├── zsh/
│   └── _mdfs          ← Name matters! Must have `_` prefix
├── bash/
│   └── mdfs           ← Name does not matter
└── fish/
    └── mdfs.fish      ← Name matters! Must match the command
```

- **zsh:** File must be in an `fpath` directory, named `_<command>`.
- **bash:** Any name works; the file is explicitly sourced.
- **fish:** Must be in the completions directory, named `<command>.fish`.

---

## Persistent Installation

### Problem

Configuration must be added to user files in a way that:
1. Can be updated without duplication.
2. Can be removed without damaging the file.
3. Is visible and understandable to the user.
4. Survives manual edits to the file.

### Solution: Marked Blocks

```bash
# >>> TOOL_NAME >>>
# Configuration here
# <<< TOOL_NAME <<<
```

**Use a unique marker name** for each tool to avoid collisions if multiple
tools use the same pattern. For example: `# >>> MDFS >>>`, `# >>> PYENV >>>`.

**Optional versioning:** Include a version in the marker to detect when an
update is needed:

```bash
# >>> TOOL_NAME v2 >>>
# Configuration here
# <<< TOOL_NAME <<<
```

### Updating and Removing Blocks

```bash
# Remove old block (cross-platform sed)
# Use | as delimiter instead of / in case the marker contains /
sed -i.bak "\|$$block_start|,\|$$block_end|d" "$file"
rm -f "${file}.bak"

# Then append the new block
printf '%s\n' "$$block" >> "$$file"
```

**Cross-platform `sed -i`:**
- **macOS (BSD sed):** requires a backup extension: `sed -i.bak` or
  `sed -i ''`.
- **Linux (GNU sed):** backup extension is optional.

**Recommendation:** Always use `sed -i.bak` + `rm -f "${file}.bak"` for
compatibility.

### Handling Symbolic Links

If the target file is a symbolic link (common with dotfiles managers like
chezmoi, stow, or yadm), `sed -i` will **replace the symlink with a regular
file**, breaking the link.

**Solution:** Detect and resolve symlinks before modifying:

```bash
resolve_file() {
    local file="\$1"
    if [ -L "$file" ]; then
        # Resolve the symlink to its target
        local target
        target="$$(readlink -f "$$file" 2>/dev/null || readlink "$file")"
        echo "⚠️  $$file is a symlink to $$target" >&2
        echo "   Modifying the symlink target instead." >&2
        echo "$target"
    else
        echo "$file"
    fi
}

# Usage:
file="$$(resolve_file "$$HOME/.zshenv")"
```

### Backup Before Modification

Before modifying any user configuration file for the first time, create a
timestamped backup:

```bash
backup_file() {
    local file="\$1"
    if [ -f "$file" ]; then
        local backup="$${file}.backup.$$(date +%s)"
        cp "$$file" "$$backup"
        echo "ℹ️  Backup created: $backup"
    fi
}
```

### Why Not Other Methods?

```bash
# ❌ DO NOT just append to the end
# Result: duplicates on repeated installation
echo "export PATH=..." >> ~/.bashrc

# ❌ DO NOT overwrite the entire file
# Result: user configuration is lost
echo "only TOOL config" > ~/.bashrc

# ❌ DO NOT use fragile regex replacements
# Result: brittle code, hard to maintain

# ❌ DO NOT use sed -i without a backup extension
# Breaks on macOS
sed -i "/$$block_start/,/$$block_end/d" "$file"
```

### Handling Edge Cases

⚠️ **The examples below show individual cases. In production code, use the
`upsert_block` function from the [Idempotent Utilities](#idempotent-utilities)
section.**

```bash
# Case 1: File does not exist — create it
if [ ! -f "$file" ]; then
    mkdir -p "$$(dirname "$$file")"
    printf '%s\n' "$$block" > "$$file"

# Case 2: File exists, block is absent — append
elif ! grep -qF "$$block_start" "$$file"; then
    printf '\n%s\n' "$$block" >> "$$file"

# Case 3: File exists, block is present — replace
else
    sed -i.bak "\|$$block_start|,\|$$block_end|d" "$file"
    rm -f "${file}.bak"
    printf '\n%s\n' "$$block" >> "$$file"
fi
```

---

## OS Differences

### macOS vs Linux

| Aspect | macOS | Linux |
|--------|-------|-------|
| Default terminal mode | Login shell | Non-login shell (usually) |
| Bash primary file | `.bash_profile` | `.bashrc` |
| Bash fallback chain | `.bash_profile` → `.bash_login` → `.profile` | `.bashrc` or `.profile` |
| Zsh files | `.zshenv` → `.zprofile` → `.zshrc` → `.zlogin` | Same |
| Default shell | zsh (since Catalina, 2019) | bash (usually) |
| PATH interference | `path_helper` in `/etc/zprofile` and `/etc/profile` | Usually none |
| GUI app PATH | Shell PATH may not be available in GUI apps launched from Dock | Usually inherited |

**Linux login shell contexts:**
- TTY login (Ctrl+Alt+F1): login shell.
- SSH: login shell.
- WSL: login shell by default.
- Most terminal emulators (GNOME Terminal, Konsole): non-login shell by
  default, but often configurable.

This means on Linux, if `.bash_profile` exists and does not source
`.bashrc`, SSH sessions will miss `.bashrc` configuration. Always ensure
`.bash_profile` sources `.bashrc` (see [PATH Management](#path-management)).

### Detecting the OS

```bash
os="$(uname -s)"

case "$os" in
    Darwin)
        # macOS-specific code
        ;;
    Linux)
        # Linux-specific code
        ;;
    *)
        # Other OSes (FreeBSD, OpenBSD, etc.)
        ;;
esac
```

---

## Error Handling

### Problem 0: The Script Must Stop on Any Error

```bash
#!/usr/bin/env bash
set -euo pipefail
```

**Why:**
- `set -e` — exit on the first error.
- `set -u` — error on undefined variables (prevents `$HOME` expanding to
  an empty string).
- `set -o pipefail` — a pipeline returns the exit status of the last
  command that failed (not just the last command).

**Without this:** the script may continue after an error and corrupt
configuration.

⚠️ **Important:** With `set -e`, commands like `grep -qF` or `test` will
**kill the script** if they return exit code 1 (not found). **Always wrap
them in conditionals:**

```bash
# ❌ BREAKS with set -e if the pattern is not found
grep -qF "pattern" "$file"

# ✅ CORRECT — wrapped in if
if grep -qF "pattern" "$file"; then
    # pattern found
fi

# ✅ OR use negation
if ! grep -qF "pattern" "$file"; then
    # pattern not found
fi

# ✅ OR suppress the exit code
grep -qF "pattern" "$file" || true
```

### Problem 1: Unsupported Shell

```bash
case "$shell_type" in
    zsh|bash)
        # Install
        ;;
    *)
        printf 'Error: unsupported shell (%s)\n' "$shell_type" >&2
        printf 'Supported: bash, zsh\n' >&2
        printf 'For fish, use setup.fish instead.\n' >&2
        exit 1
        ;;
esac
```

### Problem 2: Config File Cannot Be Created

```bash
read -rp "Create $file? [y/N] " answer
case "$answer" in
    [Yy]*)
        printf '%s\n' "$$block" > "$$file"
        ;;
    *)
        echo "Manually add the following to your shell config:"
        echo "$block"
        ;;
esac
```

### Problem 3: compinit Already Present in .zshrc

```bash
if ! grep -qF "compinit" "$rc_file"; then
    printf '\n%s\n' "$$compinit_block" >> "$$rc_file"
else
    echo "ℹ️  compinit already configured, skipping"
fi
```

### Problem 4: PATH Duplication Guard

```bash
case ":$PATH:" in
    *":/path/to/bin:"*)
        # Already in PATH
        ;;
    *)
        export PATH="/path/to/bin:$PATH"
        ;;
esac
```

**Note:** Duplicates in PATH are harmless at runtime but look
unprofessional. This guard is optional.

---

## Configuration Removal

### Problem

Users may want to remove the tool, and configuration should be cleaned up
without leaving artifacts.

### Solution

```bash
uninstall() {
    local block_start="# >>> TOOL >>>"
    local block_end="# <<< TOOL <<<"

    # Determine zshenv location (respecting ZDOTDIR)
    local zshenv_file="$HOME/.zshenv"
    if [ -n "${ZDOTDIR:-}" ]; then
        zshenv_file="$ZDOTDIR/.zshenv"
    fi

    # Remove block from all possible files
    for file in \
        "$zshenv_file" \
        "$HOME/.zshrc" \
        "$HOME/.bash_profile" \
        "$HOME/.bash_login" \
        "$HOME/.bashrc" \
        "$HOME/.profile" \
        "$HOME/.config/fish/conf.d/tool.fish"; do

        if [ -f "$$file" ] && grep -qF "$$block_start" "$file"; then
            sed -i.bak "\|$$block_start|,\|$$block_end|d" "$file"
            rm -f "${file}.bak"
            echo "✅ Removed from $file"
        fi
    done
}
```

### Why an --uninstall Option Matters

1. Users periodically remove tools.
2. Configuration files should remain clean.
3. Demonstrates that the installation is reversible and well-engineered.

---

## Permissions and sudo

### Problem 1: Script Run as root but Targeting a User's HOME

When a script runs via `sudo`, environment variables may change:
- `HOME` points to `/root`, not the user's home.
- `SUDO_USER` identifies the original user.

```bash
# User runs:
sudo ./setup.sh

# Inside the script:
echo "$HOME"   # /root — NOT what we want!
```

**Solution:**

```bash
if [ "$EUID" -eq 0 ]; then
    if [ -n "${SUDO_USER:-}" ]; then
        TARGET_USER="$SUDO_USER"
        TARGET_HOME="$$(eval echo "~$$SUDO_USER")"
    elif [ -n "${USER:-}" ]; then
        TARGET_USER="$USER"
        TARGET_HOME="$HOME"
    else
        echo "❌ Cannot determine target user" >&2
        exit 1
    fi
else
    TARGET_USER="$USER"
    TARGET_HOME="$HOME"
fi

echo "✅ Installing for user: $TARGET_USER"
echo "   Home directory: $TARGET_HOME"
```

### Problem 2: File Not Writable

Even without root, a file may be protected (immutable flag, read-only
filesystem, etc.):

```bash
check_write_access() {
    local file="\$1"
    local dir
    dir="$$(dirname "$$file")"

    if [ ! -d "$dir" ]; then
        echo "❌ Directory does not exist: $dir" >&2
        return 1
    fi

    if [ ! -w "$dir" ]; then
        echo "❌ No write permission for $dir" >&2
        return 1
    fi

    if [ -f "$$file" ] && [ ! -w "$$file" ]; then
        echo "❌ No write permission for $file" >&2
        return 1
    fi

    return 0
}

# Usage:
if ! check_write_access "$HOME/.zshenv"; then
    echo ""
    echo "💡 Solutions:"
    echo "   1. Fix permissions: chmod u+w $HOME/.zshenv"
    echo "   2. Or run with appropriate privileges"
    exit 1
fi
```

**Recommendation:** Always check file accessibility **before** attempting to
write, not after an error.

---

## User Communication

### Problem

The user must know exactly what happened to debug any issues.

### Solution: Detailed Output

```bash
echo ""
echo "═══ Bash Configuration (macOS) ═══"
echo "✅ Updated $profile_file with:"
echo "   - export PATH=\"$BIN_DIR:\$PATH\""
echo "   - Source bash completions"
echo ""
echo "📝 Next step: Open a new terminal window"
```

### What to Include in Output

1. ✅/❌ Status indicators.
2. Specific files that were modified.
3. Specific lines/configuration that were added.
4. Commands to verify or reload the shell.
5. Alternatives if something did not work.

### What NOT to Output

```bash
# ❌ Too abstract
echo "Installation complete"

# ❌ Not enough detail
echo "Updated shell config"

# ✅ Good
echo "✅ Updated $HOME/.zshenv with:"
echo "   - export PATH=\"/path/to/bin:\$PATH\""
```

---

## Testing

### Problem

A setup script must work across different OSes and shells, but manual
testing is tedious and error-prone.

### Solution: Automated Testing

#### Docker for Linux

```bash
# Dockerfile
FROM ubuntu:latest
RUN apt-get update && apt-get install -y bash zsh

COPY setup.sh /tmp/setup.sh
RUN bash /tmp/setup.sh --install
RUN bash /tmp/setup.sh --install  # Must be idempotent

# Verify PATH is set
RUN bash -c 'source ~/.bashrc && echo "$PATH" | grep /bin'
```

#### Clean Shell for Idempotency Checks

```bash
# Test: run setup twice, result must be identical
env -i HOME="$HOME" bash --norc --noprofile -c 'bash /path/to/setup.sh --install'
env -i HOME="$HOME" bash --norc --noprofile -c 'bash /path/to/setup.sh --install'

# Verify blocks are not duplicated
count="$(grep -c '>>> TOOL >>>' ~/.bashrc)"
if [ "$count" -ne 1 ]; then
    echo "FAIL: expected 1 block, found $count"
fi
```

#### Manual Testing Checklist

- [ ] macOS: new terminal window — does PATH work?
- [ ] macOS: SSH session — does PATH work?
- [ ] Linux: new terminal tab — does PATH work?
- [ ] Linux: SSH session — does PATH work?
- [ ] Linux: `env -i bash --norc` — does PATH work?
- [ ] WSL: new shell — does PATH work?
- [ ] Completions work (`tool <TAB>`)?
- [ ] Uninstall removes blocks without damaging the file?
- [ ] Repeated installation does not create duplicates?
- [ ] Symlinked config files are handled correctly?

---

## Idempotent Utilities

### Problem

The code for upsert (update or insert) of a block is repeated in multiple
places. This invites bugs.

### Solution: Generalized Functions

```bash
upsert_block() {
    local file="\$1"
    local block="\$2"
    local block_start="\$3"
    local block_end="\$4"

    # 🔹 Handle ZDOTDIR for zshenv
    if [ -n "$${ZDOTDIR:-}" ] && [ "$$file" = "$HOME/.zshenv" ]; then
        file="$ZDOTDIR/.zshenv"
    fi

    # 🔹 Handle symbolic links
    if [ -L "$file" ]; then
        local target
        target="$$(readlink -f "$$file" 2>/dev/null || readlink "$file")"
        echo "⚠️  $$file is a symlink → $$target" >&2
        file="$target"
    fi

    # 🔹 If file does not exist — create it
    if [ ! -f "$file" ]; then
        mkdir -p "$$(dirname "$$file")"
        printf '%s\n' "$$block" > "$$file"
        echo "✅ Created $file"
        return 0
    fi

    # 🔹 Check write permissions (only after confirming file exists)
    if [ ! -w "$file" ]; then
        echo "❌ Cannot write to $file (no permission)" >&2
        return 1
    fi

    # 🔹 Create a backup before first modification
    if [ ! -f "${file}.setup-backup" ]; then
        cp "$$file" "$${file}.setup-backup"
    fi

    # 🔹 Check for corrupt state (opening marker without closing marker)
    if grep -qF "$$block_start" "$$file" && ! grep -qF "$$block_end" "$$file"; then
        echo "⚠️  Found opening marker without closing marker in $file" >&2
        echo "   Manual review recommended. Appending new block anyway." >&2
    fi

    # 🔹 If block already exists — remove old version
    if grep -qF "$$block_start" "$$file"; then
        sed -i.bak "\|$$block_start|,\|$$block_end|d" "$file"
        rm -f "${file}.bak"
        echo "ℹ️  Removed old block from $file"
    fi

    # 🔹 Append block (handle trailing newline)
    if [ -s "$file" ]; then
        # File is non-empty — check if it ends with a newline
        if [ "$$(tail -c 1 "$$file" | wc -l)" -eq 1 ]; then
            printf '%s\n' "$$block" >> "$$file"
        else
            printf '\n%s\n' "$$block" >> "$$file"
        fi
    else
        printf '%s\n' "$$block" >> "$$file"
    fi

    echo "✅ Updated $file"
}
```

**Notes:**
- Markers are passed explicitly rather than extracted from the block
  (`head -1`/`tail -1`) to avoid issues with trailing newlines.
- The function checks for corrupt state (orphaned opening marker).
- Write permission is checked **after** the existence check, so a
  non-existent file does not trigger a false "no permission" error.
- Symbolic links are resolved before modification to avoid breaking them.

### Removal Function

```bash
remove_block() {
    local file="\$1"
    local block_start="\$2"
    local block_end="\$3"

    # Handle ZDOTDIR
    if [ -n "$${ZDOTDIR:-}" ] && [ "$$file" = "$HOME/.zshenv" ]; then
        file="$ZDOTDIR/.zshenv"
    fi

    # Handle symbolic links
    if [ -L "$file" ]; then
        local target
        target="$$(readlink -f "$$file" 2>/dev/null || readlink "$file")"
        file="$target"
    fi

    if [ ! -f "$file" ]; then
        return 0
    fi

    if grep -qF "$$block_start" "$$file"; then
        sed -i.bak "\|$$block_start|,\|$$block_end|d" "$file"
        rm -f "${file}.bak"
        echo "✅ Removed block from $file"
    fi
}
```

**Note on accumulated blank lines:** Repeated update cycles (remove + append)
may accumulate blank lines at the end of the file. For production code,
consider adding a trailing-whitespace trim step or controlling blank lines
explicitly in the block content.

### Usage Example

```bash
block_start="# >>> MDFS >>>"
block_end="# <<< MDFS <<<"

env_block="$block_start
export PATH=\"/path/to/bin:\$PATH\"
fpath=(/path/to/completions/zsh \$fpath)
$block_end"

rc_block="$block_start
autoload -Uz compinit && compinit -i
$block_end"

upsert_block "$$HOME/.zshenv" "$$env_block" "$$block_start" "$$block_end"
upsert_block "$$HOME/.zshrc" "$$rc_block" "$$block_start" "$$block_end"
```

---

## FAQ

### Why not use dotfiles managers with symlinks?

- Requires cloning a git repo + creating symlinks (fragile).
- Does not work well for tools installed via pip, npm, etc.
- Harder to update (requires committing to a repo).

Setup scripts with marked blocks are self-contained and work alongside
dotfiles managers without conflict.

### Why not just append to `~/.bashrc`?

- No clean way to remove (you would need to know which lines were added).
- Not idempotent (duplicates on repeated runs).
- Fragile when the user manually edits the file.

### When to use `~/.zshrc` instead of `~/.zshenv`?

Use `~/.zshrc` when:
- Configuration is needed only in interactive shells (aliases, prompts).
- You need to override variables set in `/etc/zprofile` (e.g., PATH after
  `path_helper` on macOS).

Use `~/.zshenv` when:
- A variable is needed everywhere (PATH for tools).
- It must be available in non-interactive shells (scripts, editor
  subprocesses).

For PATH specifically: put it in `~/.zshenv` with `typeset -U PATH`, and
optionally re-prepend in `~/.zshrc` if ordering on macOS is critical.

### How to handle fish users?

Fish requires a separate setup script. See the
[fish solution in PATH Management](#solution-for-fish) for details.

### Why use `printf` instead of `echo`?

`echo` has varying implementations across shells and platforms (some
interpret escape sequences, some do not). `printf` is predictable:

```bash
# ❌ echo behavior varies across systems
echo "text" >> file

# ✅ printf is consistent everywhere
printf '%s\n' "text" >> file
```

---

## Examples in Other Projects

### nvm (Node Version Manager)

nvm uses marked blocks in `.bashrc`, `.zshrc`, and `.profile`:

```bash
# >>> nvm >>>
export NVM_DIR="$HOME/.nvm"
[ -s "$$NVM_DIR/nvm.sh" ] && \. "$$NVM_DIR/nvm.sh"
# <<< nvm <<<
```

Source: [nvm install script](https://github.com/nvm-sh/nvm/blob/master/install.sh)

### conda

conda uses a similar approach with `conda init`, adding marked blocks to
shell configuration files:

```bash
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
# ... conda setup code ...
# <<< conda initialize <<<
```

Source: [conda init documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)

### pyenv

pyenv adds PATH and init code through marked blocks in shell configs.

Source: [pyenv installer](https://github.com/pyenv/pyenv-installer)

### Dotfiles Managers

Tools like [chezmoi](https://www.chezmoi.io/),
[yadm](https://yadm.io/), and
[GNU Stow](https://www.gnu.org/software/stow/) use similar patterns for
shell detection and post-install script execution. They typically manage
entire files via symlinks rather than marked blocks, which is why the two
approaches can coexist.

---

## Final Checklist

When creating a setup script, verify:

### Core

- [ ] `#!/usr/bin/env bash` on the first line (explicitly bash, not sh).
- [ ] `set -euo pipefail` for safety.
- [ ] Shell detected correctly (`ZSH_VERSION`, `BASH_VERSION`).
- [ ] OS detected (`uname -s`) for bash-specific file paths.

### PATH and Completions

- [ ] PATH added to the correct files for each shell.
- [ ] For zsh: PATH in `~/.zshenv` (or `$ZDOTDIR/.zshenv`), `compinit` in
      `~/.zshrc`.
- [ ] For zsh: `typeset -U PATH` to handle macOS `path_helper` reordering.
- [ ] For bash: Profile file found via fallback chain
      (`.bash_profile` → `.bash_login` → `.profile`).
- [ ] For bash: `.bash_profile` sources `.bashrc` (with duplication guard).
- [ ] For fish: Separate `setup.fish` with `fish_add_path` or `set -gx`.
- [ ] Completions installed correctly (`fpath` for zsh, source for bash,
      auto-load for fish).
- [ ] macOS `path_helper` issue documented and mitigated.

### Safety and Idempotency

- [ ] Marked blocks used (`# >>> TOOL >>>`) with a unique tool name.
- [ ] `sed -i.bak` + `rm -f` for cross-platform compatibility.
- [ ] Safe delimiter in sed (`|` instead of `/`).
- [ ] Block presence checked before adding (no duplicates).
- [ ] `--uninstall` option available for clean removal.
- [ ] Script is idempotent (running twice produces the same result).
- [ ] Symbolic links detected and resolved before modification.
- [ ] Backup created before first modification.

### Error Handling and Edge Cases

- [ ] All cases handled (file missing, block present, `compinit` present).
- [ ] PATH duplication guard (optional: `case ":$PATH:" in ...`).
- [ ] Clear error messages for unsupported shells.
- [ ] `grep`/`test` commands wrapped in conditionals (safe with `set -e`).
- [ ] Corrupt block state detected (orphaned opening marker).
- [ ] ZDOTDIR respected in both install and uninstall paths.
- [ ] `.bash_login` included in uninstall file list.

### Permissions

- [ ] `SUDO_USER` and `HOME` handled correctly when run as root.
- [ ] Write access checked before modification.

### Communication and Documentation

- [ ] Output is detailed and informative (files changed, what was added,
      how to reload).
- [ ] Uses ✅/❌/ℹ️ symbols for clarity.
- [ ] Documentation explains WHAT and WHY (not just HOW).
- [ ] `path_helper` and other OS-specific issues documented.

### Testing

- [ ] Tested on macOS and Linux.
- [ ] Idempotency tested (run twice).
- [ ] Uninstall function tested.
- [ ] Docker or clean shell used for isolated verification.
- [ ] Symlinked config files tested.
- [ ] Login shell contexts tested (SSH, TTY, WSL).