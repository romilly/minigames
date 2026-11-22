"""Both games at the Explorer's 320 x 240 and the Presto's 240 x 240."""
import importlib
import sys

import pytest

import minigame as mg
from fakes import RecordingDisplay, ScriptedButtons, fake_pygame

SIZES = [(320, 240), (240, 240)]


def off_screen(display):
    """Everything drawn that doesn't fit on the display."""
    w, h = display.size()
    bad = []
    for call in display.calls:
        if call[0] == 'rect':
            _, _, x, y, cw, ch = call
            if x < 0 or y < 0 or x + cw > w or y + ch > h:
                bad.append(call)
        elif call[0] == 'text':
            _, _, text, x, y, scale = call
            if x < 0 or y < 0 or x + display.text_width(text, scale) > w or \
                    y + display.text_height(scale) > h:
                bad.append(call)
    return bad


def load_on_shim(monkeypatch, name, pg):
    monkeypatch.setitem(sys.modules, 'pygame', pg)
    for module in (name, 'tones', 'gamekit'):
        monkeypatch.delitem(sys.modules, module, raising=False)
    return importlib.import_module(name)


@pytest.mark.parametrize('size', SIZES)
def test_pong_fits(monkeypatch, size):
    display = RecordingDisplay(size)
    pg = fake_pygame(display=display, buttons=ScriptedButtons(*([set()] * 10 + [{mg.K_ESCAPE}])))
    pong = load_on_shim(monkeypatch, 'pong', pg)
    game = pong.main()
    assert (game.width, game.bounds.bottom) == size
    texts = [c for c in display.calls if c[0] == 'text']
    status_bottom = texts[0][4] + display.text_height(texts[0][5])
    assert status_bottom <= game.bounds.top          # the score sits above the play area
    assert off_screen(display) == []


class FirstChoice:
    def random(self):
        return 0.99

    def choice(self, options):
        return options[0]


@pytest.mark.parametrize('size', SIZES)
def test_noughts_fits_even_with_big_scores(monkeypatch, size):
    display = RecordingDisplay(size)
    pg = fake_pygame(display=display, buttons=ScriptedButtons(*([set()] * 3 + [{mg.K_ESCAPE}])))
    noughts = load_on_shim(monkeypatch, 'noughts', pg)
    game = noughts.Noughts(FirstChoice())
    game.board = list('XOXOXOOX ')
    game.scores = {'X': 123, 'O': 456, 'draw': 789}
    noughts.main(game=game)
    texts = [c for c in display.calls if c[0] == 'text']
    assert any('Draws 789' in c[2] for c in texts)
    assert off_screen(display) == []


@pytest.mark.parametrize('size', SIZES)
def test_noughts_grid_is_centred_and_square(monkeypatch, size):
    pg = fake_pygame()
    noughts = load_on_shim(monkeypatch, 'noughts', pg)
    layout = noughts.Layout(*size)
    first, last = layout.cell_rect(0), layout.cell_rect(8)
    assert first.width == first.height == layout.cell
    assert abs(first.left - (size[0] - last.right)) <= 1     # odd pixels can't split evenly
    assert first.top >= noughts.TEXT_BAND and size[1] - last.bottom >= noughts.TEXT_BAND


def test_render_fitting_picks_the_largest_font_that_fits():
    pg = fake_pygame()
    sys.modules.pop('gamekit', None)
    import gamekit
    fonts = [pg.font.Font(None, 24), pg.font.Font(None, 12)]
    assert gamekit.render_fitting(fonts, 'abcd', (1, 1, 1), 48).get_width() == 48
    assert gamekit.render_fitting(fonts, 'abcde', (1, 1, 1), 48).get_width() == 30
    assert gamekit.render_fitting(fonts, 'a' * 20, (1, 1, 1), 48).get_width() == 120


def polygons_off_screen(display):
    w, h = display.size()
    return [c for c in display.calls if c[0] == 'polygon'
            and any(not (0 <= x <= w and 0 <= y <= h) for x, y in c[2])]


@pytest.mark.parametrize('size', SIZES)
def test_cave_fits_and_answers_touches(monkeypatch, size):
    from fakes import ScriptedTouch
    w, h = size
    middle_of_view = (w // 2, h * 3 // 4)
    right_of_view = (w - 5, h * 3 // 4)
    # forward, release, turn right, release, then Esc
    touch = ScriptedTouch(None, middle_of_view, None, right_of_view, None)
    buttons = ScriptedButtons(*([set()] * 6 + [{mg.K_ESCAPE}]))
    display = RecordingDisplay(size)
    pg = fake_pygame(display=display, buttons=buttons, touch=touch)
    cave = load_on_shim(monkeypatch, 'cave', pg)
    game = cave.main()
    assert game.position == (2, 1)                   # one step east from A
    assert game.facing == cave.SOUTH                 # then a right turn
    assert off_screen(display) == []
    assert polygons_off_screen(display) == []
