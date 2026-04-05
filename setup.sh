#!/usr/bin/env bash
# MDFS setup — adds bin/ to PATH and configures shell completions.
#
# Usage:
#   source /path/to/mdfs/setup.sh            # current session
#   /path/to/mdfs/setup.sh --install         # permanent

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
ZSH_COMP_DIR="$SCRIPT_DIR/completions/zsh"
BASH_COMP_DIR="$SCRIPT_DIR/completions/bash"

detect_shell() {
    if [[ -n "${ZSH_VERSION:-}" ]]; then echo "zsh"
    elif [[ -n "${BASH_VERSION:-}" ]]; then echo "bash"
    else echo "unknown"; fi
}

activate() {
    local shell_type
    shell_type="$(detect_shell)"

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
            [[ -f "$BASH_COMP_DIR/mdfs" ]] && source "$BASH_COMP_DIR/mdfs"
            ;;
    esac

    echo "✅ mdfs activated ($(which mdfs 2>/dev/null || echo "$BIN_DIR/mdfs"))"
}

install_permanent() {
    local shell_type
    shell_type="$(detect_shell)"
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    case "$shell_type" in
        zsh)
            install_zsh_permanent "$block_start" "$block_end"
            ;;
        bash)
            install_bash_permanent "$block_start" "$block_end"
            ;;
        *)
            echo "Error: unsupported shell. Add manually:" >&2
            echo "  export PATH=\"$BIN_DIR:\$PATH\"" >&2
            exit 1
            ;;
    esac

    chmod +x "$BIN_DIR/mdfs"
}

install_zsh_permanent() {
    local block_start="$1"
    local block_end="$2"
    local env_file="$HOME/.zshenv"
    local rc_file="$HOME/.zshrc"

    # Always add to ~/.zshenv (for PATH, fpath — needed everywhere)
    local env_block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
fpath=($ZSH_COMP_DIR \$fpath)
$block_end"

    # Only add compinit to ~/.zshrc if it exists and doesn't already have it
    local rc_block="$block_start
autoload -Uz compinit && compinit -i
$block_end"

    echo ""
    echo "═══ ZSH Configuration ═══"

    # Install to ~/.zshenv (create if missing, this is critical)
    if [[ -f "$env_file" ]] && grep -qF "$block_start" "$env_file"; then
        sed -i.bak "/$block_start/,/$block_end/d" "$env_file"
        rm -f "${env_file}.bak"
        echo "ℹ️  Updated (removed old block)"
    fi
    printf '\n%s\n' "$env_block" >> "$env_file"
    echo "✅ Updated $env_file with:"
    echo "   - PATH=$BIN_DIR"
    echo "   - fpath+=$ZSH_COMP_DIR"

    # Install to ~/.zshrc only if it exists
    if [[ -f "$rc_file" ]]; then
        if grep -qF "$block_start" "$rc_file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$rc_file"
            rm -f "${rc_file}.bak"
        fi

        # Only add compinit if not already present
        if ! grep -qF "compinit" "$rc_file"; then
            printf '\n%s\n' "$rc_block" >> "$rc_file"
            echo "✅ Updated $rc_file with:"
            echo "   - autoload -Uz compinit && compinit -i"
        else
            echo "ℹ️  compinit already in $rc_file, skipping"
        fi
    else
        echo "ℹ️  $rc_file not found (you manage zsh config manually)"
        read -rp "Create $rc_file with compinit setup? [y/N] " answer
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            printf '%s\n' "$rc_block" > "$rc_file"
            echo "✅ Created $rc_file with:"
            echo "   - autoload -Uz compinit && compinit -i"
        else
            echo "⚠️  Note: add 'autoload -Uz compinit && compinit -i' to your zsh config"
        fi
    fi

    echo ""
    echo "📝 Next step: Restart your shell"
    echo "   source $env_file"
}

install_bash_permanent() {
    local block_start="$1"
    local block_end="$2"
    local os
    os=$(uname -s)

    local block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
[[ -f \"$BASH_COMP_DIR/mdfs\" ]] && source \"$BASH_COMP_DIR/mdfs\"
$block_end"

    if [[ "$os" == "Darwin" ]]; then
        # macOS: bash reads .bash_profile in login shell
        # Strategy: always use .bash_profile, ensure it sources .bashrc
        install_bash_macos "$block_start" "$block_end" "$block"
    else
        # Linux: depends on whether .bash_profile exists
        install_bash_linux "$block_start" "$block_end" "$block"
    fi
}

install_bash_macos() {
    local block_start="$1"
    local block_end="$2"
    local block="$3"
    local rc_file="$HOME/.bashrc"

    # macOS bash reads login files in this order: .bash_profile → .bash_login → .profile
    # Use the first one that exists, or create .bash_profile if none exist
    local profile_file=""
    for candidate in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do
        if [[ -f "$candidate" ]]; then
            profile_file="$candidate"
            break
        fi
    done

    # If no login file exists, create .bash_profile (standard for macOS)
    if [[ -z "$profile_file" ]]; then
        profile_file="$HOME/.bash_profile"
    fi

    # Remove existing mdfs block from both files if they exist
    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$rc_file"; do
        if [[ -f "$file" ]] && grep -qF "$block_start" "$file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$file"
            rm -f "${file}.bak"
        fi
    done

    # Install to the login profile file
    printf '\n%s\n' "$block" >> "$profile_file"
    echo ""
    echo "═══ Bash Configuration (macOS) ═══"
    echo "✅ Updated $profile_file with:"
    echo "   - export PATH=\"$BIN_DIR:\$PATH\""
    echo "   - Source bash completions from $BASH_COMP_DIR"

    # Ensure profile file sources .bashrc (best practice on macOS)
    if [[ -f "$rc_file" ]] && ! grep -qF "source.*bashrc" "$profile_file" && ! grep -qF "\.bashrc" "$profile_file"; then
        printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
        printf '%s\n' "[[ -f \"$rc_file\" ]] && source \"$rc_file\"" >> "$profile_file"
        echo "ℹ️  Also configured to source $rc_file"
    fi

    echo ""
    echo "📝 Next step: Restart your shell"
    echo "   exec \$SHELL -l"
}

install_bash_linux() {
    local block_start="$1"
    local block_end="$2"
    local block="$3"
    local profile_file="$HOME/.bash_profile"
    local rc_file="$HOME/.bashrc"

    echo ""
    echo "═══ Bash Configuration (Linux) ═══"

    # If .bash_profile exists, user likely manages both login and non-login shells explicitly
    if [[ -f "$profile_file" ]]; then
        # Add to .bash_profile and ensure it sources .bashrc
        if grep -qF "$block_start" "$profile_file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$profile_file"
            rm -f "${profile_file}.bak"
        fi
        printf '\n%s\n' "$block" >> "$profile_file"
        echo "✅ Updated $profile_file with:"
        echo "   - export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Source bash completions from $BASH_COMP_DIR"

        # Ensure .bash_profile sources .bashrc
        if [[ -f "$rc_file" ]] && ! grep -qF "source.*bashrc" "$profile_file" && ! grep -qF "\.bashrc" "$profile_file"; then
            printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
            printf '%s\n' "[[ -f \"$rc_file\" ]] && source \"$rc_file\"" >> "$profile_file"
            echo "ℹ️  Also configured to source $rc_file"
        fi

        echo ""
        echo "📝 Next step: Restart your shell (login shell)"
        echo "   exec \$SHELL -l"
    else
        # No .bash_profile, add to .bashrc (standard for non-login shells)
        if [[ -f "$rc_file" ]] && grep -qF "$block_start" "$rc_file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$rc_file"
            rm -f "${rc_file}.bak"
        fi
        printf '\n%s\n' "$block" >> "$rc_file"
        echo "✅ Updated $rc_file with:"
        echo "   - export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Source bash completions from $BASH_COMP_DIR"

        echo ""
        echo "📝 Next step: Restart your shell"
        echo "   source $rc_file"
    fi
}

uninstall_permanent() {
    local shell_type
    shell_type="$(detect_shell)"
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    echo ""
    echo "═══ Uninstalling MDFS ═══"
    echo ""

    case "$shell_type" in
        zsh)
            uninstall_zsh "$block_start" "$block_end"
            ;;
        bash)
            uninstall_bash "$block_start" "$block_end"
            ;;
        *)
            echo "Error: unsupported shell" >&2
            exit 1
            ;;
    esac
}

uninstall_zsh() {
    local block_start="$1"
    local block_end="$2"
    local env_file="$HOME/.zshenv"
    local rc_file="$HOME/.zshrc"
    local removed=0

    for file in "$env_file" "$rc_file"; do
        if [[ -f "$file" ]] && grep -qF "$block_start" "$file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$file"
            rm -f "${file}.bak"
            echo "✅ Removed from $file"
            ((removed++))
        fi
    done

    if [[ $removed -eq 0 ]]; then
        echo "ℹ️  MDFS configuration not found in zsh config files"
    else
        echo ""
        echo "📝 Next step: Restart your shell"
        echo "   source $env_file"
    fi
}

uninstall_bash() {
    local block_start="$1"
    local block_end="$2"
    local removed=0

    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$HOME/.bashrc"; do
        if [[ -f "$file" ]] && grep -qF "$block_start" "$file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$file"
            rm -f "${file}.bak"
            echo "✅ Removed from $file"
            ((removed++))
        fi
    done

    if [[ $removed -eq 0 ]]; then
        echo "ℹ️  MDFS configuration not found in bash config files"
    else
        echo ""
        echo "📝 Next step: Restart your shell"
        echo "   exec \$SHELL -l"
    fi
}

usage() {
    echo "MDFS setup — adds bin/ to PATH and configures shell completions"
    echo ""
    echo "Usage:"
    echo "  source /path/to/mdfs/setup.sh            # current session"
    echo "  /path/to/mdfs/setup.sh --install         # permanent installation"
    echo "  /path/to/mdfs/setup.sh --uninstall       # remove from config"
    echo "  /path/to/mdfs/setup.sh --help            # show this help"
}

if [[ "${1:-}" == "--install" ]]; then
    install_permanent
elif [[ "${1:-}" == "--uninstall" ]]; then
    uninstall_permanent
elif [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    usage
else
    activate
fi
