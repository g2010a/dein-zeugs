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

# Locate podq binary. Two supported layouts:
#   1. Release archive (end users):  ./install.sh + ./podq + ./Run podq.command  (flat)
#   2. Source tree (maintainers):    ./installer/install.sh + ./dist/podq        (build layout)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/podq" ]]; then
    BINARY="$SCRIPT_DIR/podq"
elif [[ -f "$SCRIPT_DIR/../dist/podq" ]]; then
    BINARY="$SCRIPT_DIR/../dist/podq"
else
    echo "ERROR: podq binary not found next to install.sh (expected '$SCRIPT_DIR/podq')." >&2
    echo "       Re-download the release archive — it is incomplete." >&2
    exit 1
fi

# Locate the Desktop launcher (always next to install.sh in both layouts).
LAUNCHER="$SCRIPT_DIR/Run podq.command"
if [[ ! -f "$LAUNCHER" ]]; then
    echo "ERROR: Desktop launcher not found at '$LAUNCHER'." >&2
    echo "       Re-download the release archive — it is incomplete." >&2
    exit 1
fi

echo "==> Installing podq to /usr/local/bin/podq..."
mkdir -p /usr/local/bin
cp "$BINARY" /usr/local/bin/podq
chmod +x /usr/local/bin/podq

# Remove quarantine attribute so Gatekeeper allows it
xattr -d com.apple.quarantine /usr/local/bin/podq 2>/dev/null || true

# Install desktop launcher
echo "==> Installing Desktop launcher..."
cp "$LAUNCHER" "$HOME/Desktop/Run podq.command"
chmod +x "$HOME/Desktop/Run podq.command"
xattr -d com.apple.quarantine "$HOME/Desktop/Run podq.command" 2>/dev/null || true

# Pre-warm Whisper, embedding, and LLM model caches
echo "==> Pre-warming model caches..."
/usr/local/bin/podq --warm-models

echo ""
echo "==> podq erfolgreich installiert!"
echo ""
echo "So benutzt du podq:"
echo "  1. Lege MP3-Aufnahmen unter ~/Podq/inbox/ ab."
echo "  2. Doppelklicke 'Run podq.command' auf dem Schreibtisch."
echo "  3. Der Bericht öffnet sich automatisch im Browser, sobald podq fertig ist."
echo ""
echo "Optional: Eine Automator-Ordneraktion kann podq automatisch starten, sobald eine"
echo "Datei in den inbox-Ordner gelegt wird. Anleitung: com.podq.folderaction.workflow.md"
echo "(in der Release-Archivdatei oder im Repository unter installer/)."
