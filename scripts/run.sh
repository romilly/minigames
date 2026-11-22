#!/usr/bin/env bash
# Run a game that's already on the board (put it there with scripts/deploy.sh).
#
#   scripts/run.sh cave
#
# Runs the board's own copy, not the one on this computer, so what runs is
# what was last deployed. Set MPR_DEVICE (e.g. /dev/ttyACM0) if you have more
# than one board plugged in.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: scripts/run.sh GAME   (e.g. cave, pong, noughts)" >&2
    exit 2
fi

mpremote=(mpremote ${MPR_DEVICE:+connect "$MPR_DEVICE"})
"${mpremote[@]}" exec "import $1; $1.main()"
