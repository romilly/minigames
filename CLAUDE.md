# minigames

Small games for the Pimoroni Explorer and Presto (RP2350, MicroPython), written
against a subset of the pygame API so the same code runs on the desktop under
real pygame and on the boards under a shim. See README.md for the games and the
maze file format.

## Working here

- TDD: write or change a test first, then the code. Keep `pytest` green.
- Set up: `pip install -r requirements-dev.txt` (pytest, pygame, pyyaml,
  mpremote, pyright).
- Type-check: `pyright` (pyrightconfig.json lists the files with hints so far;
  add a file there once it has hints).
- Run the tests: `pytest`. Also run `tests/mp_check.py` under the MicroPython
  unix port (`micropython tests/mp_check.py`) when you change anything that
  runs on the board: it catches what CPython doesn't.
- Deploy and run: `scripts/deploy.sh cave` copies everything to the board and
  runs it; `scripts/run.sh cave` runs the board's copy. Set `MPR_DEVICE` if
  more than one board is plugged in.
- Commit and push straight to main, in small commits that each leave `pytest`,
  pyright and `mp_check.py` passing. Use a branch for large refactors, so main
  stays playable; merge when it has been played on the board. Commit author:
  Romilly Cocking <romilly.cocking@gmail.com>.

## Design and style

- Prefer simplicity, but use hexagonal architecture and good object-oriented,
  responsibility-driven design.
- Hexagonal: a game's core (e.g. `cave_core.py`) holds the rules and state and
  imports neither pygame nor anything that touches files or hardware; a test
  checks it imports with pygame blocked. Drawing, input and loading are
  adapters around it. Hardware sits behind ports in `minigame.py`.
- One composition root per game: `main()` builds the pieces and passes them
  in. Collaborators are required parameters, never `None` defaults that a
  function fills in itself; tests build what they need and pass it.
- Responsibility-driven: ask the object that knows. The core answers questions
  in its own terms (`Cave.map_cells()` gives a `Kind` per cell, `view()` says
  what's ahead); adapters turn the answers into pixels and sounds and never
  dig into the core's data (cells, room dicts) to work things out themselves.
- Type hints on new and changed code, kept pyright-clean, within the
  MicroPython rules below.
- When a refactor shouldn't change behaviour, check it: tests pass and the
  screens render the same.

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
- `cave_mazes.py`: where mazes come from. The `Mazes` port, with `YamlMazes`
  (mazes/*.yaml, the desktop) and `JsonMazes` (the JSON copies on the board);
  `maze_files()` picks the one this machine can read.
- `cave.py`: adapters around the core: `Menu`, `handle()` (one key or touch
  event), and drawing. `main(maze_name)` is the composition root: it loads the
  maze, builds the `Cave` and hands it to `play(game)`, the loop.
  Tests call `play()` with a game they've built.
- `mazes/*.yaml`: maze files. `deploy.sh` converts them to JSON for the board.
- `tests/fakes.py`: fakes for the ports and `fake_pygame()`; `tests/mp_check.py`
  runs the games under MicroPython with fakes.

## MicroPython traps

These pass desktop tests but fail on the board:

- No `str.ljust` (or `rjust`/`center`): pad by hand.
- No `abc` module: ports are plain classes raising `NotImplementedError`.
- PicoGraphics `polygon` wants a list of tuples of ints, exactly.
- No YAML parser: mazes reach the board as JSON. `cave_mazes.maze_files()`
  reads YAML if `yaml` imports, JSON otherwise.
- Keep `import pygame` at module level in games: on the board it's the shim.
- Event and key constants differ from pygame's: use the names, never values.
- Type hints are fine (MicroPython ignores annotations), but: never import
  `typing` unguarded (`try: from typing import ...` / `except ImportError:`),
  never use `from __future__ import annotations` (no `__future__` on the board),
  and use string hints for forward references (`-> "Cave"`), since CPython
  evaluates annotations when it defines a function. Type aliases are evaluated
  at import on both, and MicroPython can't subscript `tuple` or `list`, so write
  `tuple[int, int]` inline in annotations rather than as an alias.
  Hint pygame types as strings (`screen: "pygame.Surface"`): under the shim
  in tests, CPython would evaluate them and the shim lacks some names.

## Maze files

Players write their own mazes, so keep old maze files loading when the format
grows: add optional keys rather than changing existing ones. A test checks
that `mazes/mine.yaml` can be won (and only with the key).
