# minigames

Games for the Pimoroni Explorer and Presto (both RP2350), written against a small subset of
pygame (`minigame.py`) for MicroPython, with a Qw/ST Pad or touchscreen as the controller. A game written against the subset runs unchanged on a desktop under real pygame.

The **cave** game now uses Alistair Cockburn's Hexagonal (Ports and Adapters) architecture, and *it can be run in a browser*!

## Games
- `pong.py`: one paddle against three walls. U/D move; a point per return.
  The ball waits a second before each serve.
- `noughts.py`: noughts and crosses against the computer (minimax with
  alpha-beta pruning, with an occasional deliberate mistake so it can be
  beaten). D-pad moves, A places; A again for a new game.
- `cave.py`: find your way through a maze. A toolbar names where you are;
  below it are a map of what you've seen, a description, and a strip at the
  bottom with your health and moves on the left and the view ahead on the
  right. Touch the middle of the view to step forward, its sides to turn and
  its floor to turn round (pad: L/R turn, U forward, D turn round). The
  button at the left of the toolbar (pad: A) opens a menu to take and drop
  things and see what you're carrying; find the key, and escape with as much
  treasure as you can. Made for the Presto's touchscreen; mazes are YAML
  files in `mazes/`. [Play it in your browser](https://romilly.github.io/minigames/browser/).

## Playing cave in a browser
The same game runs in a web page, using Pyodide (Python compiled to
WebAssembly): **[play it here](https://romilly.github.io/minigames/browser/)**.
The same core runs on the boards, the desktop and the page; only the
adapters differ (see `browser/`). To run it locally, from the repository root:

    python -m http.server

then open http://localhost:8000/browser/. Click or tap the middle of the
view to step forward, its left or right side to turn, and the floor along its
bottom to turn round; faint chevrons mark the turns. Your health and moves
are shown beside the view. The button at the top left opens the menu.
Keys: arrows to move, A or Enter for the menu, B to close it, Esc to start
again.

## Making a maze
Copy `mazes/mine.yaml` and draw your own maps: `#` is rock, anything else is
open. A maze can have several `levels`, top first, or just one `map`. `>` is
steps down and `<` steps up; steps down need steps up at the same place on the
level below, and walking onto either takes you there. Letters mark places with
a `name` and `description` under `rooms` (each letter once, on any level); a
room with `goal: true` ends the game. `start` gives a letter (or `[x, y]`, or
`[x, y, level]` counting levels from 1) and a direction to face. `objects`
have a `name`, a `description`, where they lie (`at`, given the same way as
`start`), and, for treasure, a `value`. A room that `needs` an object is a
locked door: walk into it carrying that object and it opens, and stays open. To play a different maze, change `MAZE` at the top of
`cave.py`, or call `cave.main('yours')`.

`-` on the pad (Esc on the desktop) quits.

## On the Explorer
With the board plugged in by USB and
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) installed:

    scripts/deploy.sh          # copy everything to the board
    scripts/deploy.sh pong     # copy everything, then run pong.py
    scripts/run.sh pong        # run the copy that's on the board

The script copies `minigame.py` and the games to `/`, `board/pygame.py` to
`/pygame.py`, the mazes to `/` as JSON (MicroPython has no YAML parser; the
conversion needs PyYAML on your computer), and installs Pimoroni's `qwstpad`
into `/lib` if it isn't there.
Set `MPR_DEVICE` (e.g. `/dev/ttyACM0`) if more than one board is plugged in.

`board/pygame.py` works out which board it's on. The Presto runs in its
240 x 240 mode (doubled up to fill the screen); the games size themselves from
`screen.get_size()`. If the pad doesn't answer, it says so and the Explorer's
own buttons stand in: A up, C down, X left, Z right, B select (like the pad's
A), Y Enter. The Presto has no spare buttons, so pong and noughts need the pad; cave
plays by touch.

On the Presto, text is drawn smoothly with PicoVector in Roboto Medium
(`fonts/`, copied to the board by the deploy script). Without the font it uses
the bitmap font. To try smooth text on the Explorer too, set
`VECTOR_TEXT['explorer'] = True` in `board/pygame.py`; it costs time each frame.

## On the desktop
`python pong.py` with pygame installed. Arrow keys, Esc to quit. Set `SIZE = (240, 240)` at the top of a game to see the Presto's shape.

## Tests
`pytest` (needs pygame and PyYAML: the Rect tests run against both implementations;
`pip install -r requirements-dev.txt` installs those, pytest and mpremote).
`micropython tests/mp_check.py` checks the core under MicroPython.

## The subset
Rect; display.set_mode/flip/update; Surface.fill/blit/get_rect;
draw.rect/circle/line/polygon (filled only); font.Font(None, size).render (one
bitmap font, size sets the scale); event.get (KEYDOWN/KEYUP; pad U D L R A B X
Y + - map to K_UP K_DOWN K_LEFT K_RIGHT K_a K_b K_x K_y K_RETURN K_ESCAPE;
the Presto's touchscreen gives MOUSEBUTTONDOWN/UP with event.pos); key.get_pressed;
time.Clock.tick, time.get_ticks; mixer.stop.

Sound: `from tones import tone`, then `tone(frequency, ms).play()`. On the
Explorer it drives the speaker, one note at a time, ended by `display.flip()`
(so lengths round to the frame time). On the desktop it plays a generated
square wave through pygame's mixer.

No off-screen surfaces, images or sound files.

MIT licence.
