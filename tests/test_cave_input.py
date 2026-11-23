import pygame

from cave_core import Cave, Maze
from cave_input import Controls, Menu, touch_action
from cave_layout import Layout
from test_cave_core import TREASURE


class Ev:
    def __init__(self, type, key=None, pos=None):
        self.type, self.key, self.pos = type, key, pos


def tap(pos):
    return Ev(pygame.MOUSEBUTTONDOWN, pos=pos)


def press(key):
    return Ev(pygame.KEYDOWN, key=key)


LAYOUT = Layout(240, 240, 22)


def controls():
    return Controls(Cave(Maze(TREASURE)), Menu(), LAYOUT)


VIEW_MIDDLE = LAYOUT.view_x + LAYOUT.view_w // 2


def test_the_sides_of_the_view_turn_its_middle_steps_and_its_floor_turns_round():
    x0, x1, y = LAYOUT.view_x, LAYOUT.view_x + LAYOUT.view_w - 1, LAYOUT.view_y + 5
    third = LAYOUT.view_w // 3
    assert touch_action((x0, y), LAYOUT) == 'left'
    assert touch_action((x0 + third - 1, y), LAYOUT) == 'left'
    assert touch_action((x0 + third, y), LAYOUT) == 'forward'
    assert touch_action((x1 - third, y), LAYOUT) == 'forward'
    assert touch_action((x1 - third + 1, y), LAYOUT) == 'right'
    assert touch_action((x1, y), LAYOUT) == 'right'
    assert touch_action((VIEW_MIDDLE, LAYOUT.floor_y - 1), LAYOUT) == 'forward'
    for x in (x0, VIEW_MIDDLE, x1):
        assert touch_action((x, LAYOUT.floor_y), LAYOUT) == 'around'
        assert touch_action((x, LAYOUT.height - 1), LAYOUT) == 'around'


def test_touches_off_the_view_do_nothing():
    assert touch_action((VIEW_MIDDLE, LAYOUT.view_y - 1), LAYOUT) is None   # above it
    assert touch_action((LAYOUT.view_x - 1, LAYOUT.view_y + 5), LAYOUT) is None  # the stats


def test_tapping_the_menu_button_opens_the_menu():
    c = controls()
    assert c.handle(tap((5, 5))) == ['menu']
    assert c.menu.is_open and c.menu.items == c.game.menu_items()


def test_tapping_an_item_does_it_and_closes_the_menu():
    c = controls()
    c.handle(tap((5, 5)))
    x, y, w, h = LAYOUT.menu_item_rect(0)
    assert c.handle(tap((x + 5, y + 5))) == ['take']
    assert c.game.carried() == ['nugget'] and not c.menu.is_open


def test_tapping_away_from_the_items_just_closes_the_menu():
    c = controls()
    c.handle(tap((5, 5)))
    assert c.handle(tap((120, 230))) == []
    assert not c.menu.is_open and c.game.position == (1, 1)


def test_the_pad_opens_moves_through_and_chooses():
    c = controls()
    c.handle(press(pygame.K_a))
    assert c.menu.is_open
    c.handle(press(pygame.K_DOWN))
    assert c.handle(press(pygame.K_a)) == ['take']
    assert c.game.carried() == ['rope']


def test_b_closes_the_menu_and_arrows_move_again_once_it_is_shut():
    c = controls()
    c.handle(press(pygame.K_a))
    c.handle(press(pygame.K_b))
    assert not c.menu.is_open
    assert c.handle(press(pygame.K_UP)) == ['step']


def test_taps_on_the_view_move_you():
    c = controls()
    assert c.handle(tap((VIEW_MIDDLE, LAYOUT.view_y + 5))) == ['step']
    assert c.handle(tap((VIEW_MIDDLE, LAYOUT.floor_y + 2))) == ['turn']


def test_once_you_have_won_any_key_or_touch_starts_again():
    c = controls()
    c.game.won = True
    assert c.handle(tap((5, 5))) == ['new']
    c.game.won = True
    assert c.handle(press(pygame.K_a)) == ['new']


def test_other_events_do_nothing():
    c = controls()
    assert c.handle(Ev(pygame.KEYUP, key=pygame.K_a)) == []


def test_menu_selection_wraps_round():
    menu = Menu()
    menu.show([('a', (1,)), ('b', (2,))])
    menu.move(-1)
    assert menu.chosen() == (2,)


def test_only_as_many_items_as_fit_are_offered_keeping_inventory():
    menu = Menu()
    items = [(str(i), (i,)) for i in range(20)]
    menu.show(items, LAYOUT.menu_rows)
    assert len(menu.items) == LAYOUT.menu_rows
    assert menu.items[-1] == items[-1]
