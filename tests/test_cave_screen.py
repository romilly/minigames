import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame                                                    # noqa: E402

import cave_screen                                               # noqa: E402
from cave_core import Cave, Maze                                 # noqa: E402
from cave_input import Menu                                      # noqa: E402
from cave_layout import Layout                                   # noqa: E402
from cave_screen import Screen, wrap                             # noqa: E402
from test_cave_core import TREASURE                              # noqa: E402

pygame.font.init()
FONT = pygame.font.Font(None, 24)
LAYOUT = Layout(240, 240, FONT.size('Ag')[1])


def drawn(game, menu):
    surface = pygame.Surface((240, 240))
    surface.fill((255, 0, 255))                                  # anything not drawn shows
    Screen(surface, FONT, LAYOUT).draw(game, menu)
    return surface


def colour_at(surface, x, y):
    return tuple(surface.get_at((x, y)))[:3]


def test_the_toolbar_runs_across_the_top():
    surface = drawn(Cave(Maze(TREASURE)), Menu())
    assert colour_at(surface, 230, 3) == cave_screen.TOOLBAR


def test_the_whole_screen_is_redrawn():
    surface = drawn(Cave(Maze(TREASURE)), Menu())
    assert colour_at(surface, 120, LAYOUT.text_y - 1) == cave_screen.BLACK


def test_an_open_menu_is_drawn_over_the_map_with_its_first_item_chosen():
    game, menu = Cave(Maze(TREASURE)), Menu()
    menu.show(game.menu_items(), LAYOUT.menu_rows)
    surface = drawn(game, menu)
    x, y, w, h = LAYOUT.menu_item_rect(0)
    assert colour_at(surface, w - 5, y + 2) == cave_screen.MENU_SELECTED
    x, y, w, h = LAYOUT.menu_item_rect(1)
    assert colour_at(surface, w - 5, y + 2) == cave_screen.MENU_BG


def test_the_turn_arrows_sit_either_side_of_the_view():
    surface = drawn(Cave(Maze(TREASURE)), Menu())
    cy = LAYOUT.view_y + LAYOUT.view_h // 2
    assert colour_at(surface, LAYOUT.view_x // 2, cy) == cave_screen.ARROW
    assert colour_at(surface, LAYOUT.width - LAYOUT.view_x // 2, cy) == cave_screen.ARROW


class SixPixelFont:
    def size(self, text):
        return (6 * len(text), 8)


def test_wrap_breaks_between_words():
    assert wrap(SixPixelFont(), 'one two three four', 60) == ['one two', 'three four']


def test_wrap_keeps_a_word_too_long_for_a_line():
    assert wrap(SixPixelFont(), 'abcdefghijklmnop x', 30) == ['abcdefghijklmnop', 'x']
