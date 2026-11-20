#!/usr/bin/env bash
# Deploy minigames to an Explorer over USB with mpr (pip/pipx/uv install mpr mpremote).
#
#   scripts/deploy.sh          copy everything to the board
#   scripts/deploy.sh pong     copy everything, then run pong.py
#
# Copies every top-level .py file (minigame.py and the games) to /, and
# board/pygame.py to /pygame.py. Installs Pimoroni's qwstpad into /lib
# the first time. Set MPR_DEVICE (e.g. /dev/ttyACM0) if you have more
# than one board plugged in.
set -euo pipefail

cd "$(dirname "$0")/.."
mpr=(mpr ${MPR_DEVICE:+-d "$MPR_DEVICE"})

if ! "${mpr[@]}" ls /lib 2>/dev/null | grep -q qwstpad; then
    echo "Installing qwstpad into /lib"
    "${mpr[@]}" mip install github:pimoroni/qwstpad-micropython
fi

"${mpr[@]}" put *.py /
"${mpr[@]}" put -f board/pygame.py /pygame.py

if [[ $# -gt 0 ]]; then
    "${mpr[@]}" run "$1.py"
fi
