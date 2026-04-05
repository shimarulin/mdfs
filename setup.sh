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
    elif [[ -n "${fish_version:-}" ]]; then echo "fish"
    else echo "unknown"; fi
}

# Check write access to file
check_write_access() {
    local file="$1"
    local dir="$(dirname "$file")"
    
    if [[ ! -d "$dir" ]]; then
        echo "❌ Directory does not exist: $dir"
        return 1
    fi
    
    if [[ ! -w "$dir" ]]; then
        echo "❌ No write permission in $dir"
        return 1
    fi
    
    # If file exists, check its permissions
    if [[ -f "$file" ]] && [[ ! -w "$file" ]]; then
        echo "❌ No write permission in $file"
        return 1
    fi
    
    return 0
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
        fish)
            # For fish, we assume the user will manually add the path
            # or use the install function
            ;;
    esac

    echo "✅ mdfs activated ($(which mdfs 2>/dev/null || echo "$BIN_DIR/mdfs"))"
}

install_permanent() {
    local shell_type
    shell_type="$(detect_shell)"
    local block_start="# >>> mdfs >>>"
    local block_end="# <<< mdfs <<<"

    # Check if script is run as root
    # DO NOT overwrite files with root permissions to avoid user losing access
    if [[ "$EUID" -eq 0 ]]; then
        echo "⚠️  ⚠️  ⚠️  WARNING: Script is run as root (sudo)  ⚠️  ⚠️  ⚠️"
        echo ""
        echo "Configuration files will be written with root permissions."
        echo "You may lose access to edit these files later."
        echo ""
        
        # Try to determine the real user
        local target_user="${SUDO_USER:-$USER}"
        local target_home="$HOME"
        
        if [[ -n "${SUDO_USER:-}" ]]; then
            target_home="$(eval echo ~$SUDO_USER)"
        fi
        
        echo "Target user: $target_user"
        echo "Home directory: $target_home"
        echo ""
        echo "💡 Recommendation: Run the script WITHOUT sudo:"
        echo "   cd $target_home && $0 --install"
        echo ""
        
        read -rp "Do you still want to continue? [y/N] " answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        echo ""
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

    # Check for ZDOTDIR and adjust env_file accordingly
    # ZDOTDIR overrides the location of .zshenv, .zshrc, etc.
    # If ZDOTDIR is set, we should use $ZDOTDIR/.zshenv instead of $HOME/.zshenv
    if [[ -n "${ZDOTDIR:-}" ]]; then
        env_file="$ZDOTDIR/.zshenv"
    fi

    # Always add to ~/.zshenv (for PATH, fpath — needed everywhere)
    # Note: On macOS, path_helper may reorder PATH, consider using typeset -U PATH
    # to deduplicate (only works in zsh)
    local env_block="$block_start
export PATH=\"$BIN_DIR:\$PATH\"
fpath=($ZSH_COMP_DIR \$fpath)
# Optional: deduplicate PATH (only works in zsh)
# typeset -U PATH
$block_end"

    # Only add compinit to ~/.zshrc if it exists and doesn't already have it
    local rc_block="$block_start
autoload -Uz compinit && compinit -i
$block_end"

    echo ""
    echo "═══ ZSH Configuration ═══"

    # Check write permissions
    if ! check_write_access "$env_file"; then
        echo "❌ Failed to write to $env_file"
        echo "💡 Try:"
        echo "   1. Run the script without sudo"
        echo "   2. Or change permissions: chmod u+w $env_file"
        exit 1
    fi
    
    if [[ -n "$rc_file" ]] && ! check_write_access "$rc_file"; then
        echo "❌ Failed to write to $rc_file"
        echo "💡 Try:"
        echo "   1. Run the script without sudo"
        echo "   2. Or change permissions: chmod u+w $rc_file"
        exit 1
    fi

    # Install to ~/.zshenv (create if missing, this is critical)
    if [[ -f "$env_file" ]] && grep -qF "$block_start" "$env_file"; then
        sed -i.bak "/$block_start/,/$block_end/d" "$env_file"
        rm -f "${env_file}.bak"
        echo "ℹ️  Updated (removed old block)"
    fi
    # Add block with controlled newlines - no extra newline if file ends with newline
    if [[ -s "$env_file" ]]; then
        # File exists and has content - check if it ends with newline
        if [[ "$(tail -c1 "$env_file" | wc -l)" -eq 1 ]]; then
            # File ends with newline - just add the block
            printf '%s\n' "$env_block" >> "$env_file"
        else
            # File doesn't end with newline - add one before the block
            printf '\n%s\n' "$env_block" >> "$env_file"
        fi
    else
        # File is empty or doesn't exist (but we checked -f, so it exists and is empty)
        printf '%s\n' "$env_block" >> "$env_file"
    fi
    echo "✅ Updated $env_file with:"
    echo "   - PATH=$BIN_DIR"
    echo "   - fpath+=$ZSH_COMP_DIR"
    echo "   - Optional: typeset -U PATH (commented out)"

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
    echo "📝 Next step: Open a new terminal window"
    echo "   (or run: source $env_file)"
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

        # Check write permissions for all possible files
        for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$rc_file"; do
            if [[ -f "$file" ]] && ! check_write_access "$file"; then
                echo "❌ Failed to write to $file"
                echo "💡 Try:"
                echo "   1. Run the script without sudo"
                echo "   2. Or change permissions: chmod u+w $file"
                exit 1
            fi
        done

    # Remove existing mdfs block from both files if they exist
    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$rc_file"; do
        if [[ -f "$file" ]] && grep -qF "$block_start" "$file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$file"
            rm -f "${file}.bak"
        fi
    done

    # Install to the login profile file
    # Add block with controlled newlines - no extra newline if file ends with newline
    if [[ -s "$profile_file" ]]; then
        if [[ "$(tail -c1 "$profile_file" | wc -l)" -eq 1 ]]; then
            printf '%s\n' "$block" >> "$profile_file"
        else
            printf '\n%s\n' "$block" >> "$profile_file"
        fi
    else
        printf '%s\n' "$block" >> "$profile_file"
    fi
    echo ""
    echo "═══ Bash Configuration (macOS) ═══"
    echo "✅ Updated $profile_file with:"
    echo "   - export PATH=\"$BIN_DIR:\$PATH\""
    echo "   - Source bash completions from $BASH_COMP_DIR"

    # Ensure profile file sources .bashrc (best practice on macOS)
    # Guard against duplication: check that source ~/.bashrc is not already added
    if [[ -f "$rc_file" ]] && ! grep -qF "source.*bashrc" "$profile_file" && ! grep -qF "\.bashrc" "$profile_file"; then
        printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
        printf '%s\n' "[[ -f \"$rc_file\" ]] && source \"$rc_file\"" >> "$profile_file"
        echo "ℹ️  Also configured to source $rc_file"
    fi

    echo ""
    echo "📝 Next step: Open a new terminal window"
    echo "   (or run: source $profile_file)"
}

install_bash_linux() {
    local block_start="$1"
    local block_end="$2"
    local block="$3"
    local profile_file="$HOME/.bash_profile"
    local rc_file="$HOME/.bashrc"

    echo ""
    echo "═══ Bash Configuration (Linux) ═══"

    # Check write permissions for all possible files
    for file in "$HOME/.bash_profile" "$HOME/.bashrc"; do
        if [[ -f "$file" ]] && ! check_write_access "$file"; then
            echo "❌ Failed to write to $file"
            echo "💡 Try:"
            echo "   1. Run the script without sudo"
            echo "   2. Or change permissions: chmod u+w $file"
            exit 1
        fi
    done

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
        # Guard against duplication: check that source ~/.bashrc is not already added
        if [[ -f "$rc_file" ]] && ! grep -qF "source.*bashrc" "$profile_file" && ! grep -qF "\.bashrc" "$profile_file"; then
            printf '\n%s\n' "# Source .bashrc if it exists" >> "$profile_file"
            printf '%s\n' "[[ -f \"$rc_file\" ]] && source \"$rc_file\"" >> "$profile_file"
            echo "ℹ️  Also configured to source $rc_file"
        fi

        echo ""
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $profile_file)"
    else
        # No .bash_profile, add to .bashrc (standard for non-login shells)
        if [[ -f "$rc_file" ]] && grep -qF "$block_start" "$rc_file"; then
            sed -i.bak "/$block_start/,/$block_end/d" "$rc_file"
            rm -f "${rc_file}.bak"
        fi
        # Add block with controlled newlines
        if [[ -s "$rc_file" ]]; then
            if [[ "$(tail -c1 "$rc_file" | wc -l)" -eq 1 ]]; then
                printf '%s\n' "$block" >> "$rc_file"
            else
                printf '\n%s\n' "$block" >> "$rc_file"
            fi
        else
            printf '%s\n' "$block" >> "$rc_file"
        fi
        echo "✅ Updated $rc_file with:"
        echo "   - export PATH=\"$BIN_DIR:\$PATH\""
        echo "   - Source bash completions from $BASH_COMP_DIR"

        echo ""
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $rc_file)"
    fi
}

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

    # Check for write permissions on fish config directories
    if [[ ! -w "$fish_conf_dir" ]] || [[ ! -w "$fish_comp_dir" ]]; then
        echo "⚠️  Warning: Permission denied on fish config directories:"
        echo "   - $fish_conf_dir"
        echo "   - $fish_comp_dir"
        echo "   Consider running with sudo or fixing permissions."
        echo ""
    fi

    # Create fish config directories if they don't exist
    mkdir -p "$fish_conf_dir" "$fish_comp_dir"

    # For fish, we use fish_add_path (available in fish 3.0+)
    # This automatically deduplicates PATH and adds to the beginning
    local fish_block="$block_start
# Fish 3.0+ — modern approach (automatically deduplicates, idempotent)
fish_add_path $BIN_DIR
$block_end"

    # Write the configuration to mdfs.fish
    printf '%s\n' "$fish_block" > "$mdfs_fish_file"
    echo "✅ Created $mdfs_fish_file with:"
    echo "   - fish_add_path $BIN_DIR"

    # Copy completion file if it exists
    if [[ -f "$SCRIPT_DIR/completions/fish/mdfs.fish" ]]; then
        cp "$SCRIPT_DIR/completions/fish/mdfs.fish" "$mdfs_comp_file"
        echo "✅ Copied completion file to $mdfs_comp_file"
    else
        echo "ℹ️  No completion file found for fish"
    fi

    echo ""
    echo "📝 Next step: Open a new terminal window"
    echo "   (or run: source $mdfs_fish_file)"
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
        fish)
            uninstall_fish "$block_start" "$block_end"
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

    # Check for write permissions
    local problematic_files=()
    for file in "$env_file" "$rc_file"; do
        if [[ -f "$file" ]] && [[ ! -w "$file" ]]; then
            problematic_files+=("$file")
        fi
    done

    if [[ ${#problematic_files[@]} -gt 0 ]]; then
        echo "⚠️  Warning: Permission denied on some config files:"
        for file in "${problematic_files[@]}"; do
            echo "   - $file"
        done
        echo "   Consider running with sudo or fixing permissions."
        echo ""
    fi

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
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $env_file)"
    fi
}

uninstall_bash() {
    local block_start="$1"
    local block_end="$2"
    local removed=0

    # Check for write permissions on all files we might modify
    local problematic_files=()
    for file in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$HOME/.bashrc"; do
        if [[ -f "$file" ]] && [[ ! -w "$file" ]]; then
            problematic_files+=("$file")
        fi
    done

    if [[ ${#problematic_files[@]} -gt 0 ]]; then
        echo "⚠️  Warning: Permission denied on some config files:"
        for file in "${problematic_files[@]}"; do
            echo "   - $file"
        done
        echo "   Consider running with sudo or fixing permissions."
        echo ""
    fi

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
        echo "📝 Next step: Open a new terminal window"
    fi
}

uninstall_fish() {
    local block_start="$1"
    local block_end="$2"
    local fish_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/fish"
    local fish_conf_dir="$fish_config_dir/conf.d"
    local fish_comp_dir="$fish_config_dir/completions"
    local mdfs_fish_file="$fish_conf_dir/mdfs.fish"
    local mdfs_comp_file="$fish_comp_dir/mdfs.fish"
    local removed=0

    # Check for write permissions on fish config files
    local problematic_files=()
    if [[ -f "$mdfs_fish_file" ]] && [[ ! -w "$mdfs_fish_file" ]]; then
        problematic_files+=("$mdfs_fish_file")
    fi
    if [[ -f "$mdfs_comp_file" ]] && [[ ! -w "$mdfs_comp_file" ]]; then
        problematic_files+=("$mdfs_comp_file")
    fi

    if [[ ${#problematic_files[@]} -gt 0 ]]; then
        echo "⚠️  Warning: Permission denied on some config files:"
        for file in "${problematic_files[@]}"; do
            echo "   - $file"
        done
        echo "   Consider running with sudo or fixing permissions."
        echo ""
    fi

    # Remove the mdfs.fish configuration file if it exists and contains our block
    if [[ -f "$mdfs_fish_file" ]] && grep -qF "$block_start" "$mdfs_fish_file"; then
        sed -i.bak "/$block_start/,/$block_end/d" "$mdfs_fish_file"
        rm -f "${mdfs_fish_file}.bak"
        
        # If the file is now empty, remove it completely
        if [[ ! -s "$mdfs_fish_file" ]]; then
            rm -f "$mdfs_fish_file"
        fi
        
        echo "✅ Removed from $mdfs_fish_file"
        ((removed++))
    fi

    # Remove the mdfs.fish completion file if it exists
    if [[ -f "$mdfs_comp_file" ]]; then
        rm -f "$mdfs_comp_file"
        echo "✅ Removed completion file $mdfs_comp_file"
        ((removed++))
    fi

    if [[ $removed -eq 0 ]]; then
        echo "ℹ️  MDFS configuration not found in fish config files"
    else
        echo ""
        echo "📝 Next step: Open a new terminal window"
        echo "   (or run: source $mdfs_fish_file)"
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
