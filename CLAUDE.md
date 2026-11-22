# minigames

Small games for the Pimoroni Explorer and Presto (RP2350, MicroPython), written
against a subset of the pygame API so the same code runs on the desktop under
real pygame and on the boards under a shim. See README.md for the games and the
maze file format.

## Working here

- TDD: write or change a test first, then the code. Keep `pytest` green.
- Set up: `pip install -r requirements-dev.txt` (pytest, pygame, pyyaml, mpremote).
- Run the tests: `pytest`. Also run `tests/mp_check.py` under the MicroPython
  unix port (`micropython tests/mp_check.py`) when you change anything that
  runs on the board: it catches what CPython doesn't.
- Deploy and run: `scripts/deploy.sh cave` copies everything to the board and
  runs it; `scripts/run.sh cave` runs the board's copy. Set `MPR_DEVICE` if
  more than one board is plugged in.
- Commit and push straight to main. Commit author:
  Romilly Cocking <romilly.cocking@gmail.com>.
- Prefer simplicity, but use hexagonal architecture and
  good object-oriented responsibility driven design


## Layout

- `minigame.py`: the pygame subset. Ports (`Display`, `Buttons`, `Timer`,
  `Speaker`, `Touch`) are plain base classes (MicroPython has no `abc`), with
  adapters for PicoGraphics, the Qw/ST Pad, the boards' buttons and the
  Presto's touchscreen. Fully testable on CPython.
- `board/pygame.py`: deployed to the board as `/pygame.py`. Detects Explorer
  or Presto, wires up the adapters and exposes a `pygame`-like module.
- `gamekit.py`, `tones.py`: helpers shared by the games; `tone(freq, ms)` works
  on both the board and the desktop.
- Games: `pong.py`, `noughts.py`, `cave.py`. Each has `main()` and runs under
  desktop pygame as `python <game>.py`.
- `cave_core.py`: the cave game's core, with no pygame and no files: `Maze`
  (reads a maze spec), `Cave` (state of play: moving, steps, objects, doors),
  and `Kind` (what a cell is, for the map). Tested in `tests/test_cave_core.py`.
- `cave.py`: adapters around the core: maze loading, `Menu`, `handle()` (one
  key or touch event), drawing, and `main()`.
- `mazes/*.yaml`: maze files. `deploy.sh` converts them to JSON for the board.
- `tests/fakes.py`: fakes for the ports and `fake_pygame()`; `tests/mp_check.py`
  runs the games under MicroPython with fakes.

## MicroPython traps

These pass desktop tests but fail on the board:

- No `str.ljust` (or `rjust`/`center`): pad by hand.
- No `abc` module: ports are plain classes raising `NotImplementedError`.
- PicoGraphics `polygon` wants a list of tuples of ints, exactly.
- No YAML parser: mazes reach the board as JSON. `cave.load_maze` reads YAML
  if `yaml` imports, JSON otherwise.
- Keep `import pygame` at module level in games: on the board it's the shim.
- Event and key constants differ from pygame's: use the names, never values.

## Maze files

Players write their own mazes, so keep old maze files loading when the format
grows: add optional keys rather than changing existing ones. A test checks
that `mazes/mine.yaml` can be won (and only with the key).
