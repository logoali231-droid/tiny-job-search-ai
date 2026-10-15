#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/tiny-job-search-ai.desktop"
ICON_PATH="$PROJECT_DIR/assets/icon.svg"

echo "📦  Installing Tiny Job Search AI in $PROJECT_DIR"

# --- Check python3 ---
if ! command -v python3 &>/dev/null; then
    echo "❌  python3 not found. Install it with:"
    echo "    sudo apt install python3 python3-venv python3-tk"
    exit 1
fi

# --- Check tkinter ---
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "❌  tkinter is not installed."
    echo "    Run:  sudo apt install python3-tk"
    exit 1
fi

# --- Check venv module ---
if ! python3 -c "import venv" &>/dev/null; then
    echo "❌  python3-venv is not installed."
    echo "    Run:  sudo apt install python3-venv"
    exit 1
fi

# --- Create virtual env ---
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍  Creating virtual environment…"
    python3 -m venv "$VENV_DIR"
fi

# --- Install dependencies ---
echo "📥  Installing Python dependencies…"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet
# --- Optional Playwright browser installation ---
if [ "${INSTALL_PLAYWRIGHT_BROWSER:-0}" = "1" ]; then
    echo "🌐  Installing Playwright Chromium..."
    "$VENV_DIR/bin/python" -m playwright install chromium || {
        echo "⚠️  Chromium installation failed."
        echo "   Browser-based scrapers may not work."
    }
else
    echo "⏭️  Skipping Chromium installation."
    echo "   To install it later, run:"
    echo "   INSTALL_PLAYWRIGHT_BROWSER=1 ./install.sh"
fi

# --- Make scripts executable ---
chmod +x "$PROJECT_DIR/run.sh" "$PROJECT_DIR/install.sh" "$PROJECT_DIR/uninstall.sh"

# --- Create .desktop entry ---
echo "🖥️   Creating desktop launcher…"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Tiny Job Search AI
GenericName=Job Search Assistant
Comment=Adaptive job search assistant that learns your preferences
Exec=$PROJECT_DIR/run.sh
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Office;Network;
StartupNotify=true
StartupWMClass=tiny-job-search-ai
EOF
chmod +x "$DESKTOP_FILE"

# --- Refresh desktop database ---
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "✅  Installation complete!"
echo ""
echo "   → Launch from your applications menu: 'Tiny Job Search AI'"
echo "   → Or run:  $PROJECT_DIR/run.sh"
echo ""