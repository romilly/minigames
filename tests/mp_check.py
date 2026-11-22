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


# Cave: a maze from JSON (the board has no YAML), drawn with polygons, played by touch
import json
from fakes import ScriptedTouch
spec = {'start': {'at': 'A', 'facing': 'east'},
        'map': '#####\n#A  #\n# # #\n#  B#\n#####\n',
        'rooms': {'A': {'name': 'Start', 'description': 'Dark.'},
                  'B': {'name': 'End', 'goal': True}}}
with open('/tmp/mp_check_maze.json', 'w') as f:
    json.dump(spec, f)
display = RecordingDisplay((240, 240))
touch = ScriptedTouch(None, (120, 180), None, (235, 180), None)
sys.modules['pygame'] = fake_pygame(display=display, touch=touch,
                                    buttons=ScriptedButtons(*([set()] * 6 + [{mg.K_ESCAPE}])))
for name in ('cave', 'cave_core', 'cave_input', 'cave_layout', 'cave_mazes', 'tones'):
    sys.modules.pop(name, None)
import cave
import cave_core
import cave_mazes
assert isinstance(cave_mazes.maze_files(), cave_mazes.JsonMazes)   # no yaml here
maze = cave_mazes.JsonMazes('/tmp').load('mp_check_maze')
game = cave.play(cave_core.Cave(maze))
assert game.position == (2, 1) and game.facing == cave_core.SOUTH, (game.position, game.facing)
assert any(c[0] == 'polygon' for c in display.calls)
g = mg.PicoGraphicsDisplay(FakeGraphics())
g.polygon((1, 2, 3), [(0, 0), (5.5, 0), (3, 4)])
print('MicroPython cave check passed')

two = {'start': {'at': 'A', 'facing': 'east'},
       'levels': [{'map': '#####\n#A >#\n#####'}, {'map': '#####\n#B <#\n#####'}],
       'rooms': {'B': {'goal': True}}}
game = cave_core.Cave(cave_core.Maze(two))
assert [game.act(a) for a in ('forward', 'forward', 'around', 'forward', 'forward')] == \
    [['step'], ['steps'], ['turn'], ['step'], ['win']]
print('MicroPython cave levels check passed')

spec['objects'] = {'gem': {'name': 'gem', 'at': 'A', 'value': 7}}
game = cave_core.Cave(cave_core.Maze(spec))
import cave_input
import cave_layout
layout = cave_layout.Layout(240, 240, 22)
controls = cave_input.Controls(game, cave_input.Menu(), layout)


class Ev:
    def __init__(self, type, key=None, pos=None):
        self.type, self.key, self.pos = type, key, pos


assert controls.handle(Ev(mg.MOUSEBUTTONDOWN, pos=(5, 5))) == ['menu']
x, y, w, h = layout.menu_item_rect(0)
assert controls.handle(Ev(mg.MOUSEBUTTONDOWN, pos=(x + 5, y + 5))) == ['take']
assert game.carried() == ['gem'] and game.treasure() == 7
print('MicroPython cave treasure check passed')

door = {'start': {'at': 'A', 'facing': 'east'}, 'map': '#####\n#AFB#\n#####',
        'rooms': {'F': {'name': 'Gate', 'needs': 'key'}, 'B': {'goal': True}},
        'objects': {'key': {'name': 'key', 'at': 'A'}}}
game = cave_core.Cave(cave_core.Maze(door))
assert game.act('forward') == ['locked'], game.message
game.do(('take', 'key'))
assert game.act('forward') == ['unlock'] and game.act('forward') == ['win']
print('MicroPython cave door check passed')
