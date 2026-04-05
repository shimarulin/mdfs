#!/usr/bin/env bash
# MDFS setup — adds bin/ to PATH and configures shell completions.
#
# Usage:
#   source /path/to/mdfs/setup.sh            # current session
#   /path/to/mdfs/setup.sh --install         # permanent
#   /path/to/mdfs/setup.sh --uninstall       # remove from config
#   /path/to/mdfs/setup.sh --help            # show this help
#
# Alternative (if mdfs is already installed):
#   mdfs setup --install-completions         # install shell completions
#   mdfs setup --uninstall-completions       # uninstall shell completions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
ZSH_COMP_DIR="$SCRIPT_DIR/completions/zsh"
BASH_COMP_DIR="$SCRIPT_DIR/completions/bash"

# ---------------------------------------------------------------------------
# Utility: detect current shell
# Uses [ ] (POSIX test) so it works even if accidentally invoked as sh.
# Fish cannot be detected here — this script runs under bash.
# Fish users are detected via $SHELL fallback in install_permanent.
# ---------------------------------------------------------------------------
detect_shell() {
    if [ -n "${ZSH_VERSION:-}" ]; then echo "zsh"
    elif [ -n "${BASH_VERSION:-}" ]; then echo "bash"
    else echo "unknown"; fi
}

# ---------------------------------------------------------------------------
# Utility: resolve symlinks
# If file is a symlink, sed -i will replace it with a regular file,
# breaking the link. Resolve to the actual target first.
# ---------------------------------------------------------------------------
resolve_file() {
    local file="$1"
    if [ -L "$file" ]; then
        local target
        target="$(readlink -f "$file" 2>/dev/null || readlink "$file")"
        echo "⚠️  $file is a symlink → $target (modifying target)" >&2
        echo "$target"
    else
        echo "$file"
    fi
}

# ---------------------------------------------------------------------------
# Utility: create a timestamped backup before first modification
# ---------------------------------------------------------------------------
backup_file() {
    local file="$1"
    if [ -f "$file" ] && [ ! -f "${file}.mdfs-backup" ]; then
        cp "$file" "${file}.mdfs-backup.$(date +%s)"
        echo "ℹ️  Backup created: ${file}.mdfs-backup.$(date +%s)"
    fi
}

# ---------------------------------------------------------------------------
# Utility: check write access to a file (or its parent directory)
# ---------------------------------------------------------------------------
check_write_access() {
    local file="$1"
    local dir
    dir="$(dirname "$file")"

    if [ ! -d "$dir" ]; then
        echo "❌ Directory does not exist: $dir" >&2
        return 1
    fi

    if [ ! -w "$dir" ]; then
        echo "❌ No write permission for $dir" >&2
        return 1
    fi

    if [ -f "$file" ] && [ ! -w "$file" ]; then
        echo "❌ No write permission for $file" >&2
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Utility: upsert_block — idempotent insert-or-update of a marked block
# ---------------------------------------------------------------------------
upsert_block() {
    local file="$1"
    local block="$2"
    local block_start="$3"
    local block_end="$4"

    # Resolve symlinks to avoid breaking them with sed -i
    file="$(resolve_file "$file")"

    # If file does not exist — create it
    if [ ! -f "$file" ]; then
        mkdir -p "$(dirname "$file")"
        printf '%s\n' "$block" > "$file"
        echo "✅ Created $file"
        return 0
    fi

    # Check write permissions (only after confirming file exists)
    if [ ! -w "$file" ]; then
        echo "❌ Cannot write to $file (no permission)" >&2
        return 1
    fi

    # Backup before first modification
    backup_file "$file"

    # Check for corrupt state (opening marker without closing marker)
    if grep -qF "$block_start" "$file" && ! grep -qF "$block_end" "$file"; then
        echo "⚠️  Found opening marker without closing marker in $file" >&2
        echo "   Manual review recommended. Appending new block anyway." >&2
    fi

    # If block already exists — remove old version
    if grep -qF "$block_start" "$file"; then
        sed -i.bak "\|$block_start|,\|$block_end|d" "$file"
        rm -f "${file}.bak"
        echo "ℹ️  Removed old block from $file"
    fi

    # Append block with controlled newlines
    if [ -s "$file" ]; then
        # File is non-empty — check if it ends with a newline
        if [ "$(tail -c 1 "$file" | wc -l)" -eq 1 ]; then
            printf '%s\n' "$block" >> "$file"
        else
            printf '\n%s\n' "$block" >> "$file"
        fi
    else
        printf '%s\n' "$block" >> "$file"
    fi

    echo "✅ Updated $file"
}

# ---------------------------------------------------------------------------
# Utility: remove_block — remove a marked block from a file
# Returns the number of files modified (0 or 1) via stdout.
# ---------------------------------------------------------------------------
remove_block() {
    local file="$1"
    local block_start="$2"
    local block_end="$3"

    if [ ! -f "$file" ]; then
        echo "0"
        return 0
    fi

    # Resolve symlinks
    file="$(resolve_file "$file")"

    if grep -qF "$block_start" "$file"; then
        backup_file "$file"
        sed -i.bak "\|$block_start|,\|$block_end|d" "$file"
        rm -f "${file}.bak"
        echo "1"
        echo "✅ Removed block from $file" >&2
    else
        echo "0"
    fi
}

# ---------------------------------------------------------------------------
# check_existing_mdfs — check if mdfs is already installed elsewhere
# Returns the path if found, or empty string if not found.
# ---------------------------------------------------------------------------
check_existing_mdfs() {
    which mdfs 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# activate — set up PATH and completions for the current session only
# ---------------------------------------------------------------------------
activate() {
    local shell_type
    shell_type="$(detect_shell)"

    local existing_mdfs
    existing_mdfs="$(check_existing_mdfs)"

    # If mdfs is already installed (e.g., via uv tool install), suggest command
    if [ -n "$existing_mdfs" ]; then
        echo "ℹ️  mdfs is already installed: $existing_mdfs"
        echo ""
        echo "For local development with the current checkout:"
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
        echo "Or add to your shell config for persistent development setup."
        return 0
    fi

    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *) export PATH="$BIN_DIR:$PATH" ;;
    esac

    chmod +x "$BIN_DIR/mdfs" 2>/dev/null || true

    case "$shell_type" in
        zsh)
            case " ${fpath[*]} " in
                *" $ZSH_COMP_DIR "*) ;;
                *) fpath=("$ZSH_COMP_DIR" "${fpath[@]}") ;;
            esac
            autoload -Uz compinit && compinit -i 2>/dev/null
            ;;
        bash)
            [ -f "$BASH_COMP_DIR/mdfs" ] && source "$BASH_COMP_DIR/mdfs"
            ;;
    esac

    echo "✅ mdfs activated ($(which mdfs 2>/dev/null || echo "$BIN_DIR/mdfs"))"
}

# ---------------------------------------------------------------------------
# install_permanent — write configuration to shell dotfiles
# ---------------------------------------------------------------------------
install_permanent() {
    local shell_type
    shell_type="$(detect_shell)"
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    # Check if mdfs is already installed via uv or other means
    local existing_mdfs
    existing_mdfs="$(check_existing_mdfs)"
    if [ -n "$existing_mdfs" ]; then
        echo "⚠️  mdfs is already installed: $existing_mdfs"
        echo ""
        echo "For local development with the current checkout:"
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
        echo "To add to your shell config for persistent development setup,"
        echo "continue with the installation below."
        echo ""
        read -rp "Continue with permanent installation? [y/N] " answer
        case "$answer" in
            [Yy]*) ;;
            *)     echo "Installation cancelled."; exit 0 ;;
        esac
        echo ""
    fi

    # If shell is unknown, check $SHELL as a fallback hint
    if [ "$shell_type" = "unknown" ]; then
        case "${SHELL:-}" in
            */zsh)  shell_type="zsh" ;;
            */bash) shell_type="bash" ;;
            */fish) shell_type="fish" ;;
        esac
    fi

    # Check if script is run as root
    if [ "$EUID" -eq 0 ]; then
        echo "⚠️  ⚠️  ⚠️  WARNING: Script is run as root (sudo)  ⚠️  ⚠️  ⚠️"
        echo ""
        echo "Configuration files will be written with root permissions."
        echo "You may lose access to edit these files later."
        echo ""

        local target_user="${SUDO_USER:-$USER}"
        local target_home="$HOME"

        if [ -n "${SUDO_USER:-}" ]; then
            target_home="$(eval echo "~$SUDO_USER")"
        fi

        echo "Target user: $target_user"
        echo "Home directory: $target_home"
        echo ""
        echo "💡 Recommendation: Run the script WITHOUT sudo:"
        echo "   cd $target_home && $0 --install"
        echo ""

        read -rp "Do you still want to continue? [y/N] " answer
        case "$answer" in
            [Yy]*) echo "" ;;
            *)     echo "Cancelled."; exit 0 ;;
        esac
    fi

    case "$shell_type" in
        zsh)
            install_zsh_permanent "$block_start" "$block_end"
            ;;
        bash)
            install_bash_permanent "$block_start" "$block_end"
            ;;
        fish)
            install_fish_permanent "$block_start" "$block_end"
            ;;
        *)
            echo "Error: unsupported shell ($shell_type)." >&2
            echo "Supported: bash, zsh. For fish, use setup.fish." >&2
            echo "Add manually:" >&2
            echo "  export PATH=\"$BIN_DIR:\$PATH\"" >&2
            exit 1
            ;;
    esac

    chmod +x "$BIN_DIR/mdfs"
}

# ---------------------------------------------------------------------------
# install_zsh_permanent
# ---------------------------------------------------------------------------
install_zsh_permanent() {
    local block_start="$1"
    local block_end="$2"

    # Respect ZDOTDIR: if set in environment, zsh reads $ZDOTDIR/.zshenv
    # instead of ~/.zshenv (and similarly for .zshrc).
    local env_file="$HOME/.zshenv"
    local rc_file="$HOME/.zshrc"
    if [ -n "${ZDOTDIR:-}" ]; then
        env_file="$ZDOTDIR/.zshenv"
        rc_file="$ZDOTDIR/.zshrc"
    fi

    # PATH + fpath block for ~/.zshenv (needed everywhere)
    # typeset -U PATH deduplicates PATH — critical on macOS where
    # path_helper in /etc/zprofile reorders PATH after ~/.zshenv.
    local env_block="$block_start
typeset -U PATH
export PATH=\"$BIN_DIR:\$PATH\"
fpath=($ZSH_COMP_DIR \$fpath)
$block_end"

    # compinit block for ~/.zshrc (interactive shells only)
    local rc_block="$block_start
autoload -Uz compinit && compinit -i
$block_end"

    echo ""
    echo "═══ ZSH Configuration ═══"

    # Check write permissions before any changes
    if ! check_write_access "$env_file"; then
        echo "💡 Try:"
        echo "   1. Run the script without sudo"
        echo "   2. Or change permissions: chmod u+w $env_file"
        exit 1
    fi

    # Install to zshenv
    upsert_block "$env_file" "$env_block" "$block_start" "$block_end"
    echo "   - typeset -U PATH (deduplication)"
    echo "   - PATH=$BIN_DIR"
    echo "   - fpath+=$ZSH_COMP_DIR"

    # Install compinit to zshrc (only if not already present)
    if [ -f "$rc_file" ]; then
        if ! check_write_access "$rc_file"; then
            echo "💡 Try:"
            echo "   1. Run the script without sudo"
            echo "   2. Or change permissions: chmod u+w $rc_file"
            exit 1
        fi

        if grep -qF "$block_start" "$rc_file"; then
            # Our block exists — update it
            upsert_block "$rc_file" "$rc_block" "$block_start" "$block_end"
            echo "   - autoload -Uz compinit && compinit -i"
        elif ! grep -qF "compinit" "$rc_file"; then
            # No compinit at all — add our block
            upsert_block "$rc_file" "$rc_block" "$block_start" "$block_end"
            echo "   - autoload -Uz compinit && compinit -i"
        else
            echo "ℹ️  compinit already in $rc_file, skipping"
        fi
    else
        echo "ℹ️  $rc_file not found (you manage zsh config manually)"
        read -rp "Create $rc_file with compinit setup? [y/N] " answer
        case "$answer" in
            [Yy]*)
                printf '%s\n' "$rc_block" > "$rc_file"
                echo "✅ Created $rc_file with:"
                echo "   - autoload -Uz compinit && compinit -i"
                ;;
            *)
                echo "⚠️  Note: add 'autoload -Uz compinit && compinit -i' to your zsh config"
                ;;
        esac
    fi

    echo ""
    echo "📝 Next step: Open a new terminal window"
    echo "   (or run: source $env_file)"
}

# ---------------------------------------------------------------------------
# install_bash_permanent
# ---------------------------------------------------------------------------
install_bash_permanent() {
    local block_start="$1"
    local block_end="$2"
    local os
    os="$(uname -s)"

    local block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
[ -f \"$BASH_COMP_DIR/mdfs\" ] && . \"$BASH_COMP_DIR/mdfs\"
$block_end"

    if [ "$os" = "Darwin" ]; then
        install_bash_macos "$block_start" "$block_end" "$block"
    else
        install_bash_linux "$block_start" "$block_end" "$block"
    fi
}

# ---------------------------------------------------------------------------
# install_bash_macos
# ---------------------------------------------------------------------------
install_bash_macos() {
    local block_start="$1"
    local block_end="$2"
    local block="$3"
    local rc_file="$HOME/.bashrc"

    # macOS bash reads login files: .bash_profile → .bash_login → .profile
    # Use the first one that exists, or create .bash_profile if none exist
    local profile_file=""
    for candidate in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do
        if [ -f "$candidate" ]; then
            profile_file="$candidate"
            break
        fi
    done

    if [ -z "$profile_file" ]; then
        profile_file="$HOME/.bash_profile"
    fi

    # Check write permissions for all files we might touch
    for file in "$profile_file" "$rc_file"; do
        if [ -f "$file" ] && ! check_write_access "$file"; then
            echo "💡 Try:"
            echo "   1. Run the script without sudo"
            echo "   2. Or change permissions: chmod u+w $file"
            exit 1
        fi
    done

    # Remove existing mdfs blocks from all bash profile files
    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$rc_file"; do
        if [ -f "$file" ] && grep -qF "$block_start" "$file"; then
            local resolved
            resolved="$(resolve_file "$file")"
            backup_file "$resolved"
            sed -i.bak "\|$block_start|,\|$block_end|d" "$resolved"
            rm -f "${resolved}.bak"
        fi
    done

    # Install to the login profile file
    upsert_block "$profile_file" "$block" "$block_start" "$block_end"

    echo ""
    echo "═══ Bash Configuration (macOS) ═══"
    echo "✅ Updated $profile_file with:"
    echo "   - export PATH=\"$BIN_DIR:\$PATH\""
    echo "   - Source bash completions from $BASH_COMP_DIR"

    # Ensure profile file sources .bashrc (best practice on macOS)
    # Use regex (no -F) because we need pattern matching
    if [ -f "$rc_file" ] && [ -f "$profile_file" ] && \
       ! grep -q '\.\s*~/\.bashrc\|source\s.*bashrc\|\.\s.*bashrc' "$profile_file"; then
        printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
        printf '%s\n' '[ -f ~/.bashrc ] && . ~/.bashrc' >> "$profile_file"
        echo "ℹ️  Also configured to source $rc_file"
    fi

    echo ""
    echo "📝 Next step: Open a new terminal window"
    echo "   (or run: source $profile_file)"
}

# ---------------------------------------------------------------------------
# install_bash_linux
# ---------------------------------------------------------------------------
install_bash_linux() {
    local block_start="$1"
    local block_end="$2"
    local block="$3"
    local profile_file="$HOME/.bash_profile"
    local rc_file="$HOME/.bashrc"

    echo ""
    echo "═══ Bash Configuration (Linux) ═══"

    # Check write permissions
    for file in "$profile_file" "$rc_file"; do
        if [ -f "$file" ] && ! check_write_access "$file"; then
            echo "💡 Try:"
            echo "   1. Run the script without sudo"
            echo "   2. Or change permissions: chmod u+w $file"
            exit 1
        fi
    done

    if [ -f "$profile_file" ]; then
        # .bash_profile exists — user manages login shells explicitly
        upsert_block "$profile_file" "$block" "$block_start" "$block_end"
        echo "   - export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Source bash completions from $BASH_COMP_DIR"

        # Ensure .bash_profile sources .bashrc
        if [ -f "$rc_file" ] && \
           ! grep -q '\.\s*~/\.bashrc\|source\s.*bashrc\|\.\s.*bashrc' "$profile_file"; then
            printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
            printf '%s\n' '[ -f ~/.bashrc ] && . ~/.bashrc' >> "$profile_file"
            echo "ℹ️  Also configured to source $rc_file"
        fi

        echo ""
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $profile_file)"
    else
        # No .bash_profile — standard case: add to .bashrc
        upsert_block "$rc_file" "$block" "$block_start" "$block_end"
        echo "   - export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Source bash completions from $BASH_COMP_DIR"

        echo ""
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $rc_file)"
    fi
}

# ---------------------------------------------------------------------------
# install_fish_permanent
# ---------------------------------------------------------------------------
install_fish_permanent() {
    local block_start="$1"
    local block_end="$2"
    local fish_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/fish"
    local fish_conf_dir="$fish_config_dir/conf.d"
    local fish_comp_dir="$fish_config_dir/completions"
    local mdfs_fish_file="$fish_conf_dir/mdfs.fish"
    local mdfs_comp_file="$fish_comp_dir/mdfs.fish"

    echo ""
    echo "═══ Fish Configuration ═══"

    # Create fish config directories if they don't exist
    mkdir -p "$fish_conf_dir" "$fish_comp_dir"

    # fish_add_path (fish 3.0+) automatically deduplicates and is idempotent
    local fish_block="$block_start
# Fish 3.0+ (automatically deduplicates, idempotent)
fish_add_path $BIN_DIR
$block_end"

    printf '%s\n' "$fish_block" > "$mdfs_fish_file"
    echo "✅ Created $mdfs_fish_file with:"
    echo "   - fish_add_path $BIN_DIR"

    # Copy completion file if it exists
    if [ -f "$SCRIPT_DIR/completions/fish/mdfs.fish" ]; then
        cp "$SCRIPT_DIR/completions/fish/mdfs.fish" "$mdfs_comp_file"
        echo "✅ Copied completion file to $mdfs_comp_file"
    else
        echo "ℹ️  No completion file found for fish"
    fi

    echo ""
    echo "📝 Next step: Open a new fish shell"
}

# ---------------------------------------------------------------------------
# uninstall_permanent
# ---------------------------------------------------------------------------
uninstall_permanent() {
    local shell_type
    shell_type="$(detect_shell)"
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    # Fallback to $SHELL if detection fails
    if [ "$shell_type" = "unknown" ]; then
        case "${SHELL:-}" in
            */zsh)  shell_type="zsh" ;;
            */bash) shell_type="bash" ;;
            */fish) shell_type="fish" ;;
        esac
    fi

    echo ""
    echo "═══ Uninstalling MDFS ═══"
    echo ""

    case "$shell_type" in
        zsh)  uninstall_zsh "$block_start" "$block_end" ;;
        bash) uninstall_bash "$block_start" "$block_end" ;;
        fish) uninstall_fish "$block_start" "$block_end" ;;
        *)
            echo "Error: unsupported shell ($shell_type)" >&2
            exit 1
            ;;
    esac
}

# ---------------------------------------------------------------------------
# uninstall_zsh
# ---------------------------------------------------------------------------
uninstall_zsh() {
    local block_start="$1"
    local block_end="$2"
    local removed=0

    # Respect ZDOTDIR (same logic as install)
    local env_file="$HOME/.zshenv"
    local rc_file="$HOME/.zshrc"
    if [ -n "${ZDOTDIR:-}" ]; then
        env_file="$ZDOTDIR/.zshenv"
        rc_file="$ZDOTDIR/.zshrc"
    fi

    for file in "$env_file" "$rc_file"; do
        if [ -f "$file" ] && [ ! -w "$file" ]; then
            echo "⚠️  No write permission for $file" >&2
        fi
    done

    for file in "$env_file" "$rc_file"; do
        local count
        count="$(remove_block "$file" "$block_start" "$block_end")"
        removed=$((removed + count))
    done

    if [ "$removed" -eq 0 ]; then
        echo "ℹ️  MDFS configuration not found in zsh config files"
    else
        echo ""
        echo "📝 Next step: Open a new terminal window"
    fi
}

# ---------------------------------------------------------------------------
# uninstall_bash
# ---------------------------------------------------------------------------
uninstall_bash() {
    local block_start="$1"
    local block_end="$2"
    local removed=0

    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$HOME/.bashrc"; do
        if [ -f "$file" ] && [ ! -w "$file" ]; then
            echo "⚠️  No write permission for $file" >&2
        fi
    done

    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$HOME/.bashrc"; do
        local count
        count="$(remove_block "$file" "$block_start" "$block_end")"
        removed=$((removed + count))
    done

    if [ "$removed" -eq 0 ]; then
        echo "ℹ️  MDFS configuration not found in bash config files"
    else
        echo ""
        echo "📝 Next step: Open a new terminal window"
    fi
}

# ---------------------------------------------------------------------------
# uninstall_fish
# ---------------------------------------------------------------------------
uninstall_fish() {
    local block_start="$1"
    local block_end="$2"
    local fish_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/fish"
    local mdfs_fish_file="$fish_config_dir/conf.d/mdfs.fish"
    local mdfs_comp_file="$fish_config_dir/completions/mdfs.fish"
    local removed=0

    # Remove config file
    if [ -f "$mdfs_fish_file" ]; then
        if grep -qF "$block_start" "$mdfs_fish_file"; then
            backup_file "$mdfs_fish_file"
            sed -i.bak "\|$block_start|,\|$block_end|d" "$mdfs_fish_file"
            rm -f "${mdfs_fish_file}.bak"

            # If file is now empty, remove it
            if [ ! -s "$mdfs_fish_file" ]; then
                rm -f "$mdfs_fish_file"
                echo "✅ Removed $mdfs_fish_file"
            else
                echo "✅ Removed mdfs block from $mdfs_fish_file"
            fi
            removed=$((removed + 1))
        fi
    fi

    # Remove completion file
    if [ -f "$mdfs_comp_file" ]; then
        rm -f "$mdfs_comp_file"
        echo "✅ Removed completion file $mdfs_comp_file"
        removed=$((removed + 1))
    fi

    if [ "$removed" -eq 0 ]; then
        echo "ℹ️  MDFS configuration not found in fish config files"
    else
        echo ""
        echo "📝 Next step: Open a new fish shell"
    fi
}

# ---------------------------------------------------------------------------
# usage
# ---------------------------------------------------------------------------
usage() {
    echo "MDFS setup — adds bin/ to PATH and configures shell completions"
    echo ""
    echo "Usage (shell script):"
    echo "  source /path/to/mdfs/setup.sh            # current session"
    echo "  /path/to/mdfs/setup.sh --install         # permanent installation"
    echo "  /path/to/mdfs/setup.sh --uninstall       # remove from config"
    echo "  /path/to/mdfs/setup.sh --help            # show this help"
    echo ""
    echo "Usage (if mdfs is installed via uv/pipx):"
    echo "  mdfs setup --install-completions         # install shell completions"
    echo "  mdfs setup --uninstall-completions       # uninstall shell completions"
}

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
case "${1:-}" in
    --install)   install_permanent ;;
    --uninstall) uninstall_permanent ;;
    --help|-h)   usage ;;
    *)           activate ;;
esac
