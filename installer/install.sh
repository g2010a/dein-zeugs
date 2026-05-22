#!/bin/bash
set -euo pipefail

# Verify arm64 macOS 14+
arch=$(uname -m)
if [[ "$arch" != "arm64" ]]; then
    echo "ERROR: podq requires Apple Silicon (arm64). Detected: $arch" >&2
    exit 1
fi

os_version=$(sw_vers -productVersion)
major=$(echo "$os_version" | cut -d. -f1)
if [[ "$major" -lt 14 ]]; then
    echo "ERROR: podq requires macOS 14 or later. Detected: $os_version" >&2
    exit 1
fi

echo "==> Detected macOS $os_version on arm64. Proceeding with install..."

# Install podq binary
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$SCRIPT_DIR/../dist/podq"

if [[ ! -f "$BINARY" ]]; then
    echo "ERROR: podq binary not found at $BINARY" >&2
    echo "       Run 'make package' first to build the binary." >&2
    exit 1
fi

echo "==> Installing podq to /usr/local/bin/podq..."
mkdir -p /usr/local/bin
cp "$BINARY" /usr/local/bin/podq
chmod +x /usr/local/bin/podq

# Remove quarantine attribute so Gatekeeper allows it
xattr -d com.apple.quarantine /usr/local/bin/podq 2>/dev/null || true

# Pre-warm Whisper, embedding, and LLM model caches
echo "==> Pre-warming model caches..."
/usr/local/bin/podq --warm-models

echo ""
echo "==> podq installed successfully!"
echo ""
echo "=========================================="
echo "  AUTOMATOR SETUP (do this once)"
echo "=========================================="
echo ""
echo "1. Open Automator (Spotlight: 'Automator')"
echo "2. File > New > Folder Action"
echo "3. 'Folder Action receives files and folders added to:'"
echo "   → Browse to your {root}/inbox directory"
echo "4. Add action: 'Run Shell Script'"
echo "   Shell: /bin/zsh"
echo "   Pass input: as arguments"
echo "5. Script body:"
echo ""
echo '   /usr/local/bin/podq "/absolute/path/to/{root}" >> "$HOME/Library/Logs/podq/automator.log" 2>&1'
echo ""
echo "   (Replace /absolute/path/to/{root} with your actual root directory path)"
echo "6. Save as 'podq inbox watcher'"
echo ""
echo "Note: The \$@ arguments are ignored — podq always scans the full inbox directory."
echo ""
echo "See installer/com.podq.folderaction.workflow.md for detailed instructions."
