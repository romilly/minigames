#!/usr/bin/env bash
# Plays the browser version of cave in Pyodide under Node and checks the
# screen. Needs Node; installs Pyodide and node-canvas into browser/check the
# first time. Pass a directory to keep screenshots:
#
#   scripts/browser_check.sh [SCREENSHOT_DIR]
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -d browser/check/node_modules ]] || (cd browser/check && npm install --silent)

maze=$(mktemp)
trap 'rm -f "$maze"' EXIT
python3 -c "import json, sys, yaml; json.dump(yaml.safe_load(open('mazes/mine.yaml')), sys.stdout)" > "$maze"
node browser/check/check_cave.mjs "$PWD" "$maze" "${1:-}"
