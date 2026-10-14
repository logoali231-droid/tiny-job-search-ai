#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/tiny-job-search-ai.desktop"

echo "🧹  Uninstalling Tiny Job Search AI…"
rm -f "$DESKTOP_FILE"
rm -rf "$PROJECT_DIR/.venv"
rm -f "$PROJECT_DIR/data/q_table.json"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "✅  Removed launcher, virtualenv, and learned data."
echo "   (Source files left intact — delete the folder to fully remove.)"