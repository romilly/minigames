# Run under MicroPython (unix port) from the project root:
#   micropython tests/mp_check.py
# Checks that minigame and pong load and run there, with fakes for the hardware.
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'tests')

import minigame as mg
from fakes import RecordingDisplay, ScriptedButtons, FakeTimer, FakeGraphics, FakePad, fake_pygame

r = mg.Rect(0, 0, 10, 20)
r.right = 100
r.clamp_ip(mg.Rect(0, 0, 50, 50))
assert tuple(r) == (40, 0, 10, 20), r
assert r.colliderect((45, 5, 10, 10))

buttons = mg.QwstPadButtons(FakePad())
assert buttons.pressed() == set()

g = FakeGraphics()
mg.PicoGraphicsDisplay(g).rect((1, 2, 3), 0, 0, 5, 5)
assert g.calls[-1] == ('rectangle', 0, 0, 5, 5)

t = mg.TicksTimer()
clock = mg.Clock(t)
clock.tick(50)
assert 15 <= clock.tick(50) <= 40

display = RecordingDisplay()
pg = fake_pygame(display=display,
                 buttons=ScriptedButtons({mg.K_UP}, {mg.K_UP}, {mg.K_UP}, {mg.K_ESCAPE}))
sys.modules['pygame'] = pg
import pong
game = pong.main()
assert display.frames == 4, display.frames
assert game.paddle.y < 100, game.paddle.y
print('MicroPython check passed')
