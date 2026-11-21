# Run under MicroPython (unix port) from the project root:
#   micropython tests/mp_check.py
# Checks that minigame and pong load and run there, with fakes for the hardware.
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'tests')

import minigame as mg
from fakes import RecordingDisplay, ScriptedButtons, FakeTimer, FakeGraphics, FakePad, RecordingSpeaker, fake_pygame

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

timer = FakeTimer()
speaker = RecordingSpeaker(timer)
spg = fake_pygame(timer=timer, speaker=speaker)
spg.tone(880, 40).play()
timer.t = 40
spg.display.flip()
assert speaker.calls == [('play', 880, 0), ('stop', 40)], speaker.calls
calls = []
mg.ExplorerSpeaker(lambda f: calls.append(f), lambda: calls.append('stop')).play(440.5)
assert calls == [440]

display = RecordingDisplay()
pg = fake_pygame(display=display,
                 buttons=ScriptedButtons({mg.K_UP}, {mg.K_UP}, {mg.K_UP}, {mg.K_ESCAPE}))
sys.modules['pygame'] = pg
import pong
game = pong.main()
assert display.frames == 4, display.frames
assert game.paddle.centery < game.bounds.centery, game.paddle.y
print('MicroPython check passed')


class FirstChoice:
    def random(self):
        return 0.99

    def choice(self, options):
        return options[0]


display = RecordingDisplay()
frames = [set(), {mg.K_a}] + [set()] * 20 + [{mg.K_ESCAPE}]
sys.modules['pygame'] = fake_pygame(display=display, buttons=ScriptedButtons(*frames))
for name in ('noughts', 'tones', 'gamekit'):
    sys.modules.pop(name, None)
import noughts
assert noughts.best_moves(list('XX  O    '), 'O') == [2]
game = noughts.main(game=noughts.Noughts(FirstChoice()))
assert game.board.count('X') == 1 and game.board.count('O') == 1, game.board
print('MicroPython noughts check passed')


# The Presto's shape, and the fallback buttons
display = RecordingDisplay((240, 240))
sys.modules['pygame'] = fake_pygame(display=display,
                                    buttons=ScriptedButtons(set(), set(), {mg.K_ESCAPE}))
for name in ('pong', 'tones', 'gamekit'):
    sys.modules.pop(name, None)
import pong
game = pong.main()
assert (game.width, game.bounds.bottom) == (240, 240)


class Pin:
    def __init__(self, v):
        self.v = v

    def value(self):
        return self.v


assert mg.PinButtons({'A': Pin(0), 'C': Pin(1)}).pressed() == {mg.K_UP}


def missing():
    raise OSError(5)


assert isinstance(mg.pad_or(missing, mg.NoButtons(), lambda m: None), mg.NoButtons)
print('MicroPython Presto-size check passed')
