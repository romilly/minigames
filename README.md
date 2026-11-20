# minigames

Games for the Pimoroni Explorer, written against a small subset of pygame for MicroPython on the Pimoroni Explorer (RP2350),
with a Qw/ST Pad as the controller. A game written against the subset runs
unchanged on a desktop under real pygame.

## On the Explorer
Copy these to the board: `minigame.py`, `board/pygame.py` (as `pygame.py`),
`qwstpad.py` (from pimoroni/qwstpad-micropython) and `pong.py`. Run `pong.py`.
Pad: U/D move the paddle, `-` quits.

## On the desktop
`python pong.py` with pygame installed. Arrow keys, Esc to quit.

## Tests
`pytest` (needs pygame: the Rect tests run against both implementations).
`micropython tests/mp_check.py` checks the core under MicroPython.

## The subset
Rect; display.set_mode/flip/update; Surface.fill/get_rect; draw.rect/circle/line
(filled only); event.get (KEYDOWN/KEYUP; pad U D L R A B X Y + - map to
K_UP K_DOWN K_LEFT K_RIGHT K_a K_b K_x K_y K_RETURN K_ESCAPE); key.get_pressed;
time.Clock.tick, time.get_ticks. No off-screen surfaces, images, fonts or sound yet.

MIT licence.
