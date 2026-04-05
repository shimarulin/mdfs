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
    local rc_file=""
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    case "$shell_type" in
        zsh)  rc_file="$HOME/.zshrc" ;;
        bash) rc_file="$HOME/.bashrc" ;;
        *)
            echo "Error: unsupported shell. Add manually:" >&2
            echo "  export PATH=\"$BIN_DIR:\$PATH\"" >&2
            exit 1
            ;;
    esac

    local block
    if [[ "$shell_type" == "zsh" ]]; then
        block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
fpath=($ZSH_COMP_DIR \$fpath)
autoload -Uz compinit && compinit -i
$block_end"
    else
        block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
[[ -f \"$BASH_COMP_DIR/mdfs\" ]] && source \"$BASH_COMP_DIR/mdfs\"
$block_end"
    fi

    if [[ -f "$rc_file" ]] && grep -qF "$block_start" "$rc_file"; then
        sed -i.bak "/$block_start/,/$block_end/d" "$rc_file"
        rm -f "${rc_file}.bak"
    fi

    printf '\n%s\n' "$block" >> "$rc_file"
    chmod +x "$BIN_DIR/mdfs"

    echo "✅ Installed to $rc_file"
    echo "   Restart shell or: source $rc_file"
}

if [[ "${1:-}" == "--install" ]]; then
    install_permanent
else
    activate
fi
