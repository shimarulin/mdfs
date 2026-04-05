#!/usr/bin/env bash
# MDFS setup — minimal wrapper for shell completions installation.
#
# This script is designed for git clone installations (Option E in README).
# It adds bin/ to PATH and delegates to `mdfs setup` for completions management.
#
# Usage:
#   source setup.sh                  # current session only
#   ./setup.sh --install             # permanent installation (install completions)
#   ./setup.sh --uninstall           # remove completions
#   ./setup.sh --help                # show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"

# Add bin/ to PATH for current session
export PATH="$BIN_DIR:$PATH"

# Handle command line arguments
case "${1:-}" in
    --install)
        # Delegate to mdfs setup for permanent completions installation
        mdfs setup -i
        ;;
    --uninstall)
        # Delegate to mdfs setup for completions removal
        mdfs setup -u
        ;;
    --help|-h)
        echo "MDFS setup — shell completions installation"
        echo ""
        echo "Usage:"
        echo "  source setup.sh              # activate for current session"
        echo "  ./setup.sh --install         # install completions permanently"
        echo "  ./setup.sh --uninstall       # uninstall completions"
        echo "  ./setup.sh --help            # show this help"
        ;;
    *)
        # Default: show activation message
        echo "✅ mdfs activated: $(which mdfs)"
        echo ""
        echo "For permanent installation (shell completions):"
        echo "  $0 --install"
        ;;
esac
