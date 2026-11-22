import pytest

import cave
from cave_core import Cave, Maze
from test_cave_core import TREASURE


def test_touches_beside_the_view_turn_and_on_it_step_forward():
    layout = cave.Layout(240, 240, 22)
    y = layout.view_y + 5
    assert cave.touch_action((layout.view_x - 1, y), layout) == 'left'
    assert cave.touch_action((120, y), layout) == 'forward'
    assert cave.touch_action((layout.view_x + layout.view_w, y), layout) == 'right'
    assert cave.touch_action((120, layout.view_y - 1), layout) is None   # above the view


@pytest.mark.parametrize('size', [(240, 240), (320, 240)])
def test_layout_stacks_toolbar_map_text_and_view(size):
    layout = cave.Layout(size[0], size[1], 22)
    assert layout.toolbar_h >= 22
    assert layout.toolbar_h <= layout.map_y
    assert layout.map_y + layout.map_h <= layout.text_y
    assert layout.text_y + cave.DESCRIPTION_LINES * 22 <= layout.view_y
    assert layout.view_y + layout.view_h == size[1]
    assert layout.view_h < size[1] // 3                        # a strip, not half the screen
    assert layout.view_w == 2 * layout.view_h                  # the corridor keeps its shape
    assert layout.view_x * 2 + layout.view_w == size[0]        # centred, room either side
    assert layout.map_h >= 7 * 10                              # mine.yaml at 10px a cell


class SixPixelFont:
    def size(self, text):
        return (6 * len(text), 8)


def test_wrap_breaks_between_words():
    assert cave.wrap(SixPixelFont(), 'one two three four', 60) == ['one two', 'three four']


def test_wrap_keeps_a_word_too_long_for_a_line():
    assert cave.wrap(SixPixelFont(), 'abcdefghijklmnop x', 30) == ['abcdefghijklmnop', 'x']


# ---- The menu, by touch and by pad ----

import pygame as _pygame


class Ev:
    def __init__(self, type, key=None, pos=None):
        self.type, self.key, self.pos = type, key, pos


def tap(pos):
    return Ev(_pygame.MOUSEBUTTONDOWN, pos=pos)


def press(key):
    return Ev(_pygame.KEYDOWN, key=key)


def menu_setup():
    game = Cave(Maze(TREASURE))
    return game, cave.Menu(), cave.Layout(240, 240, 22)


def test_tapping_the_menu_button_opens_the_menu():
    game, menu, layout = menu_setup()
    assert cave.handle(tap((5, 5)), game, menu, layout) == ['menu']
    assert menu.is_open and menu.items == game.menu_items()


def test_tapping_an_item_does_it_and_closes_the_menu():
    game, menu, layout = menu_setup()
    cave.handle(tap((5, 5)), game, menu, layout)
    x, y, w, h = layout.menu_item_rect(0)
    assert cave.handle(tap((x + 5, y + 5)), game, menu, layout) == ['take']
    assert game.carried() == ['nugget'] and not menu.is_open


def test_tapping_away_from_the_items_just_closes_the_menu():
    game, menu, layout = menu_setup()
    cave.handle(tap((5, 5)), game, menu, layout)
    assert cave.handle(tap((120, 230)), game, menu, layout) == []
    assert not menu.is_open and game.position == (1, 1)


def test_the_pad_opens_moves_through_and_chooses():
    game, menu, layout = menu_setup()
    cave.handle(press(_pygame.K_a), game, menu, layout)
    assert menu.is_open
    cave.handle(press(_pygame.K_DOWN), game, menu, layout)
    assert cave.handle(press(_pygame.K_a), game, menu, layout) == ['take']
    assert game.carried() == ['rope']


def test_b_closes_the_menu_and_arrows_move_again_once_it_is_shut():
    game, menu, layout = menu_setup()
    cave.handle(press(_pygame.K_a), game, menu, layout)
    cave.handle(press(_pygame.K_b), game, menu, layout)
    assert not menu.is_open
    assert cave.handle(press(_pygame.K_UP), game, menu, layout) == ['step']


def test_menu_selection_wraps_round():
    menu = cave.Menu()
    menu.show([('a', 1), ('b', 2)])
    menu.move(-1)
    assert menu.chosen() == 2


def test_only_as_many_items_as_fit_are_offered():
    layout = cave.Layout(240, 240, 22)
    assert 4 <= layout.menu_rows <= 6
    menu = cave.Menu()
    menu.show([(str(i), i) for i in range(20)], layout.menu_rows)
    assert len(menu.items) == layout.menu_rows
