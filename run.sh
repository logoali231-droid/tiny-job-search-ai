#!/usr/bin/env bash
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "❌ Environment missing. Run ./install.sh first."
    exit 1
fi
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/src/main.py" "$@"