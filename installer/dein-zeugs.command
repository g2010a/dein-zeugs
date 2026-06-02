#!/bin/zsh
cd "$(dirname "$0")"
xattr -d com.apple.quarantine dein-zeugs 2>/dev/null || true
./dein-zeugs
