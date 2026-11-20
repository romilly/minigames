#!/usr/bin/env bash
# Deploy minigames to an Explorer over USB with mpremote (pip/pipx/uv install mpremote).
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
mpremote=(mpremote ${MPR_DEVICE:+connect "$MPR_DEVICE"})

if ! "${mpremote[@]}" ls :/lib 2>/dev/null | grep -q qwstpad; then
    echo "Installing qwstpad into /lib"
    "${mpremote[@]}" mip install github:pimoroni/qwstpad-micropython
fi

"${mpremote[@]}" cp *.py : + cp board/pygame.py :pygame.py

if [[ $# -gt 0 ]]; then
    "${mpremote[@]}" run "$1.py"
fi
