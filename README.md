# minigames

Games for the Pimoroni Explorer and Presto (both RP2350), written against a small subset of
pygame (`minigame.py`) for MicroPython, with a Qw/ST Pad as the controller. A game written against the subset runs
unchanged on a desktop under real pygame.

## Games
- `pong.py`: one paddle against three walls. U/D move; a point per return.
  The ball waits a second before each serve.
- `noughts.py`: noughts and crosses against the computer (minimax with
  alpha-beta pruning, with an occasional deliberate mistake so it can be
  beaten). D-pad moves, A places; A again for a new game.

`-` on the pad (Esc on the desktop) quits.

## On the Explorer
With the board plugged in by USB and
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) installed:

    scripts/deploy.sh          # copy everything to the board
    scripts/deploy.sh pong     # copy everything, then run pong.py

The script copies `minigame.py` and the games to `/`, `board/pygame.py` to
`/pygame.py`, and installs Pimoroni's `qwstpad` into `/lib` if it isn't there.
Set `MPR_DEVICE` (e.g. `/dev/ttyACM0`) if more than one board is plugged in.

`board/pygame.py` works out which board it's on. The Presto runs in its
240 x 240 mode (doubled up to fill the screen); the games size themselves from
`screen.get_size()`. If the pad doesn't answer, it says so and the Explorer's
own buttons stand in: A up, C down, X left, Z right, B select (like the pad's
A), Y Enter. The Presto has no spare buttons, so it needs the pad.

On the Presto, text is drawn smoothly with PicoVector in Roboto Medium
(`fonts/`, copied to the board by the deploy script). Without the font it uses
the bitmap font. To try smooth text on the Explorer too, set
`VECTOR_TEXT['explorer'] = True` in `board/pygame.py`; it costs time each frame.

## On the desktop
`python pong.py` with pygame installed. Arrow keys, Esc to quit. Set `SIZE = (240, 240)` at the top of a game to see the Presto's shape.

## Tests
`pytest` (needs pygame: the Rect tests run against both implementations).
`micropython tests/mp_check.py` checks the core under MicroPython.

## The subset
Rect; display.set_mode/flip/update; Surface.fill/blit/get_rect; draw.rect/circle/line
(filled only); font.Font(None, size).render (one bitmap font, size sets the
scale); event.get (KEYDOWN/KEYUP; pad U D L R A B X Y + - map to
K_UP K_DOWN K_LEFT K_RIGHT K_a K_b K_x K_y K_RETURN K_ESCAPE); key.get_pressed;
time.Clock.tick, time.get_ticks; mixer.stop.

Sound: `from tones import tone`, then `tone(frequency, ms).play()`. On the
Explorer it drives the speaker, one note at a time, ended by `display.flip()`
(so lengths round to the frame time). On the desktop it plays a generated
square wave through pygame's mixer.

No off-screen surfaces, images or sound files.

MIT licence.
