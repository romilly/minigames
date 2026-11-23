"""One frame at a time: what the browser's loop will drive."""
import minigame as mg
from cave_core import Cave, Maze
from fakes import RecordingDisplay, ScriptedButtons, ScriptedTouch, fake_pygame
from test_sizes import load_on_shim

SPEC = {'start': {'at': 'A', 'facing': 'east'}, 'map': '#####\n#A  #\n#####'}


def session_on_shim(monkeypatch, buttons=None, touch=None):
    display = RecordingDisplay((240, 240))
    pg = fake_pygame(display=display, buttons=buttons or ScriptedButtons(), touch=touch)
    cave = load_on_shim(monkeypatch, 'cave', pg)
    pg.init()
    surface = pg.display.set_mode((240, 240))
    game = Cave(Maze(SPEC))
    return cave.Session(game, surface, pg.font.Font(None, 24)), game, display


def test_each_frame_handles_what_happened_since_the_last(monkeypatch):
    touch = ScriptedTouch(None, (176, 186), None)          # one tap on the view
    session, game, display = session_on_shim(monkeypatch, touch=touch)
    assert session.frame() is True
    assert game.position == (1, 1)
    assert session.frame() is True
    assert game.position == (2, 1)


def test_the_first_frame_draws_the_screen(monkeypatch):
    session, game, display = session_on_shim(monkeypatch)
    session.frame()
    assert any(call[0] == 'polygon' for call in display.calls)


def test_quitting_ends_the_frames(monkeypatch):
    buttons = ScriptedButtons(set(), {mg.K_ESCAPE})
    session, game, display = session_on_shim(monkeypatch, buttons=buttons)
    assert session.frame() is True
    assert session.frame() is False
