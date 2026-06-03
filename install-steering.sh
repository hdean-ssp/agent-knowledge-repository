#!/bin/bash
# Install AKR steering files and hooks to ~/.kiro and the target workspace
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGETS=("$HOME/.kiro" "$HOME/work/genero/.kiro")

for target in "${TARGETS[@]}"; do
    mkdir -p "$target/steering" "$target/hooks"
    cp -r "$SCRIPT_DIR/.kiro/steering/." "$target/steering/"
    cp -r "$SCRIPT_DIR/.kiro/hooks/." "$target/hooks/"
    echo "✓ Installed to $target"
done
